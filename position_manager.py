"""
DealerEdge Position Manager
Handles position tracking, auto-close, and P&L calculations
"""

import re
from datetime import datetime
from typing import Dict, List, Optional
import requests
from config import DISCORD_WEBHOOK, STRATEGIES_CONFIG

class PositionManager:
    """Manages positions with auto-close functionality"""
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.positions = []
        self.closed_positions = []
        self.position_counter = 0
        
    def add_position(self, symbol: str, entry_price: float, size: float, 
                    strategy: str, signal_data: Dict) -> Dict:
        """Add a new position to tracking"""
        self.position_counter += 1
        
        position = {
            'id': self.position_counter,
            'symbol': symbol,
            'entry_price': entry_price,
            'current_price': entry_price,
            'size': size,
            'strategy': strategy,
            'entry_time': datetime.now(),
            'status': 'OPEN',
            'pnl': 0,
            'pnl_percent': 0,
            'target': signal_data.get('target', 'N/A'),
            'stop': signal_data.get('stop', 'N/A'),
            'signal_confidence': signal_data.get('confidence', 0),
            'target_price': self.extract_price_from_target(signal_data.get('target', '')),
            'stop_price': self.extract_price_from_stop(signal_data.get('stop', '')),
            'expected_move': signal_data.get('expected_move', 0),
            'time_horizon': signal_data.get('time_horizon', 'N/A'),
            'win_rate': signal_data.get('win_rate', 0)
        }
        
        self.positions.append(position)
        self.send_position_alert(position, 'OPENED')
        return position
    
    def extract_price_from_target(self, target_str: str) -> Optional[float]:
        """Extract numerical price from target string"""
        try:
            if '$' in target_str:
                match = re.search(r'\$(\d+\.?\d*)', target_str)
                if match:
                    return float(match.group(1))
            elif '%' in target_str:
                match = re.search(r'(\d+)%', target_str)
                if match:
                    return float(match.group(1))
        except:
            pass
        return None
    
    def extract_price_from_stop(self, stop_str: str) -> Optional[float]:
        """Extract numerical price from stop string"""
        try:
            if '$' in stop_str:
                match = re.search(r'\$(\d+\.?\d*)', stop_str)
                if match:
                    return float(match.group(1))
        except:
            pass
        return None
    
    def update_positions(self) -> List[Dict]:
        """Update all positions and check for auto-close conditions"""
        closed_positions = []
        
        for position in self.positions:
            if position['status'] == 'OPEN':
                current_price = self.analyzer.get_current_price(position['symbol'])
                
                if current_price:
                    position['current_price'] = current_price
                    position['pnl'] = (current_price - position['entry_price']) * position['size']
                    position['pnl_percent'] = ((current_price - position['entry_price']) / 
                                              position['entry_price']) * 100
                    
                    should_close = False
                    close_reason = ""
                    
                    # Check target hit
                    if position['target_price'] and current_price >= position['target_price']:
                        should_close = True
                        close_reason = "TARGET HIT"
                    
                    # Check stop hit
                    elif position['stop_price'] and current_price <= position['stop_price']:
                        should_close = True
                        close_reason = "STOP HIT"
                    
                    # Check profit/loss thresholds
                    elif position['strategy'] in ['SQUEEZE_PLAY', 'PREMIUM_SELLING']:
                        if position['pnl_percent'] >= 100:
                            should_close = True
                            close_reason = "100% PROFIT"
                        elif position['pnl_percent'] <= -50:
                            should_close = True
                            close_reason = "50% LOSS"
                    
                    # Check time-based exits
                    hours_held = (datetime.now() - position['entry_time']).total_seconds() / 3600
                    if position['strategy'] == 'SQUEEZE_PLAY' and hours_held > 24:
                        should_close = True
                        close_reason = "TIME EXIT (24H)"
                    
                    if should_close:
                        self.close_position(position, current_price, close_reason)
                        closed_positions.append(position)
        
        # Remove closed positions from active list
        for position in closed_positions:
            if position in self.positions:
                self.positions.remove(position)
                self.closed_positions.append(position)
        
        return closed_positions
    
    def close_position(self, position: Dict, exit_price: float, close_reason: str):
        """Close a position and calculate final metrics"""
        position['exit_price'] = exit_price
        position['exit_time'] = datetime.now()
        position['status'] = 'CLOSED'
        position['close_reason'] = close_reason
        position['final_pnl'] = (exit_price - position['entry_price']) * position['size']
        position['final_pnl_percent'] = ((exit_price - position['entry_price']) / 
                                        position['entry_price']) * 100
        position['hours_held'] = (position['exit_time'] - position['entry_time']).total_seconds() / 3600
        
        self.send_close_alert(position)
    
    def manual_close_position(self, position_id: int) -> Optional[Dict]:
        """Manually close a position by ID"""
        for position in self.positions:
            if position['id'] == position_id and position['status'] == 'OPEN':
                current_price = self.analyzer.get_current_price(position['symbol'])
                if current_price:
                    self.close_position(position, current_price, 'MANUAL CLOSE')
                    self.positions.remove(position)
                    self.closed_positions.append(position)
                    return position
        return None
    
    def send_position_alert(self, position: Dict, action: str):
        """Send Discord alert when position is opened"""
        message = f"""
🎯 **Position {action}** - {position['symbol']}

**Strategy**: {position['strategy']}
**Entry**: ${position['entry_price']:.2f}
**Size**: {position['size']:.2f}
**Target**: {position['target']}
**Stop**: {position['stop']}
**Confidence**: {position['signal_confidence']:.0f}%

Expected Move: {position['expected_move']:.1f}%
Time Horizon: {position['time_horizon']}
"""
        try:
            payload = {'content': message}
            requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        except:
            pass
    
    def send_close_alert(self, position: Dict):
        """Send alert when position is closed"""
        profit_emoji = "🎉" if position['final_pnl'] > 0 else "❌"
        
        message = f"""
🔔 **Position Closed** - {position['symbol']}

**Result**: {position['close_reason']}
**P&L**: ${position['final_pnl']:.2f} ({position['final_pnl_percent']:.1f}%)
**Entry**: ${position['entry_price']:.2f}
**Exit**: ${position['exit_price']:.2f}
**Duration**: {position['hours_held']:.1f} hours

{profit_emoji} {'PROFIT!' if position['final_pnl'] > 0 else 'LOSS'}
"""
        try:
            payload = {'content': message}
            requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        except:
            pass
    
    def get_active_positions(self) -> List[Dict]:
        """Get all active positions"""
        return [p for p in self.positions if p['status'] == 'OPEN']
    
    def get_closed_positions(self) -> List[Dict]:
        """Get all closed positions"""
        return self.closed_positions
    
    def calculate_total_pnl(self) -> float:
        """Calculate total P&L across all positions"""
        total = sum(p['final_pnl'] for p in self.closed_positions if 'final_pnl' in p)
        total += sum(p['pnl'] for p in self.positions if p['status'] == 'OPEN')
        return total
    
    def calculate_win_rate(self) -> float:
        """Calculate win rate percentage"""
        if not self.closed_positions:
            return 0
        
        wins = sum(1 for p in self.closed_positions if p.get('final_pnl', 0) > 0)
        return (wins / len(self.closed_positions)) * 100
    
    def get_position_summary(self) -> Dict:
        """Get comprehensive position summary"""
        active = self.get_active_positions()
        closed = self.get_closed_positions()
        
        return {
            'active_count': len(active),
            'closed_count': len(closed),
            'total_pnl': self.calculate_total_pnl(),
            'win_rate': self.calculate_win_rate(),
            'active_positions': active,
            'recent_closed': closed[-5:] if closed else []
        }
