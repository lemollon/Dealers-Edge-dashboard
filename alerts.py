"""
DealerEdge Alert System
Handles Discord, Telegram, and Email alerts
"""

import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Optional
from config import DISCORD_WEBHOOK, SIGNAL_EMOJIS

class AlertManager:
    """Manages all alert channels"""
    
    def __init__(self):
        self.discord_webhook = DISCORD_WEBHOOK
        
    def format_discord_alert(self, symbol: str, gex_profile: Dict, signal: Dict) -> Optional[str]:
        """Format alert for Discord with complete market data"""
        if not gex_profile or not signal:
            return None
        
        confidence = signal.get('confidence', 0)
        if confidence > 80:
            rec_level = "⚡ HIGH RECOMMENDATION"
        elif confidence > 65:
            rec_level = "⚡ MODERATE RECOMMENDATION"
        else:
            rec_level = "📊 LOW CONFIDENCE"
        
        type_emoji = SIGNAL_EMOJIS.get(signal.get('type', 'WAIT'), '📊')
        
        message = f"""
{rec_level} - {symbol} {signal.get('type', 'Signal').replace('_', ' ').title()}
{signal.get('direction', 'Action')}

🎯 **Trade Setup**
Strategy: {signal.get('strategy_type', 'N/A')}
Confidence: {confidence}%

📊 **Market Data**
Spot: ${gex_profile.get('current_price', 0):.2f}
Net GEX: {gex_profile.get('net_gex', 0)/1e9:.2f}B
Gamma Flip: ${gex_profile.get('gamma_flip', 0):.2f}
Dealer Pain: {gex_profile.get('dealer_pain', 0):.0f}/100

💼 **Trade Details**
Entry: {signal.get('entry', 'N/A')}
Target: {signal.get('target', 'N/A')}
Stop: {signal.get('stop', 'N/A')}
Size: {signal.get('size', 'N/A')}

📈 **Expected Performance**
Move: {signal.get('expected_move', 0):.1f}%
Time: {signal.get('time_horizon', 'N/A')}
Win Rate: {signal.get('win_rate', 0)}%

💡 **Analysis**
{signal.get('reasoning', 'Analysis unavailable')}
MM Status: {gex_profile.get('mm_status', 'neutral')}

⏰ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}
"""
        
        return message[:2000]
    
    def send_discord_alert(self, message: str) -> bool:
        """Send alert to Discord webhook"""
        try:
            payload = {'content': message}
            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            return response.status_code == 204
        except:
            return False
    
    def send_test_alert(self) -> bool:
        """Send test alert to verify configuration"""
        test_message = f"""
🧪 **Test Alert**
System is configured and working!
Time: {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send_discord_alert(test_message)
    
    def send_batch_alerts(self, opportunities: list, max_alerts: int = 3) -> int:
        """Send alerts for top opportunities"""
        sent_count = 0
        
        for opp in opportunities[:max_alerts]:
            if opp.get('gex_profile') and opp.get('best_signal'):
                message = self.format_discord_alert(
                    opp['symbol'],
                    opp['gex_profile'],
                    opp['best_signal']
                )
                
                if message and self.send_discord_alert(message):
                    sent_count += 1
                    import time
                    time.sleep(1)
        
        return sent_count
