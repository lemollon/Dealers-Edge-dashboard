"""
DealerEdge Historical GEX Database
Store and analyze historical GEX patterns for pattern recognition
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import streamlit as st

class GEXDatabase:
    """Manages historical GEX data storage and analysis"""
    
    def __init__(self, db_path="gex_history.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for GEX history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create main GEX table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gex_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                price REAL NOT NULL,
                net_gex REAL NOT NULL,
                gamma_flip REAL NOT NULL,
                dealer_pain REAL NOT NULL,
                distance_to_flip REAL NOT NULL,
                call_wall_1 REAL,
                put_wall_1 REAL,
                vix REAL,
                regime TEXT,
                mm_status TEXT,
                UNIQUE(symbol, timestamp)
            )
        ''')
        
        # Create patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_date DATETIME NOT NULL,
                symbol TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                outcome REAL,
                duration_hours REAL,
                initial_gex REAL,
                initial_pain REAL
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
            ON gex_history(symbol, timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_pattern_date 
            ON pattern_outcomes(pattern_date)
        ''')
        
        conn.commit()
        conn.close()
    
    def store_gex_snapshot(self, symbol: str, gex_profile: Dict):
        """Store current GEX snapshot in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Extract call and put walls safely
            call_wall_1 = None
            put_wall_1 = None
            
            if 'call_walls' in gex_profile and len(gex_profile['call_walls']) > 0:
                if hasattr(gex_profile['call_walls'], 'iloc'):
                    call_wall_1 = gex_profile['call_walls'].iloc[0]['strike']
                elif isinstance(gex_profile['call_walls'], list):
                    call_wall_1 = gex_profile['call_walls'][0] if gex_profile['call_walls'] else None
            
            if 'put_walls' in gex_profile and len(gex_profile['put_walls']) > 0:
                if hasattr(gex_profile['put_walls'], 'iloc'):
                    put_wall_1 = gex_profile['put_walls'].iloc[0]['strike']
                elif isinstance(gex_profile['put_walls'], list):
                    put_wall_1 = gex_profile['put_walls'][0] if gex_profile['put_walls'] else None
            
            cursor.execute('''
                INSERT OR REPLACE INTO gex_history 
                (symbol, timestamp, price, net_gex, gamma_flip, dealer_pain, 
                 distance_to_flip, call_wall_1, put_wall_1, vix, regime, mm_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                datetime.now(),
                gex_profile.get('current_price', 0),
                gex_profile.get('net_gex', 0),
                gex_profile.get('gamma_flip', 0),
                gex_profile.get('dealer_pain', 0),
                gex_profile.get('distance_to_flip', 0),
                call_wall_1,
                put_wall_1,
                gex_profile.get('vix', 0),
                gex_profile.get('regime', 'UNKNOWN'),
                gex_profile.get('mm_status', 'UNKNOWN')
            ))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Database error: {e}")
            return False
        finally:
            conn.close()
    
    def get_pattern_statistics(self, symbol: str, pattern_type: str, days: int = 30) -> Dict:
        """Get historical success rates for specific patterns"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT 
                COUNT(*) as total_occurrences,
                AVG(CASE WHEN outcome > 0 THEN 1 ELSE 0 END) * 100 as win_rate,
                AVG(outcome) as avg_return,
                AVG(duration_hours) as avg_duration,
                MAX(outcome) as best_return,
                MIN(outcome) as worst_return
            FROM pattern_outcomes
            WHERE symbol = ? 
            AND pattern_type = ?
            AND pattern_date > datetime('now', '-' || ? || ' days')
        '''
        
        df = pd.read_sql_query(query, conn, params=(symbol, pattern_type, days))
        conn.close()
        
        if not df.empty:
            return df.iloc[0].to_dict()
        return {
            'total_occurrences': 0,
            'win_rate': 0,
            'avg_return': 0,
            'avg_duration': 0,
            'best_return': 0,
            'worst_return': 0
        }
    
    def find_similar_setups(self, current_gex: Dict, symbol: str, lookback_days: int = 90) -> List[Dict]:
        """Find historically similar GEX setups and their outcomes"""
        conn = sqlite3.connect(self.db_path)
        
        # Get historical data
        query = '''
            SELECT * FROM gex_history
            WHERE symbol = ?
            AND timestamp > datetime('now', '-' || ? || ' days')
            ORDER BY timestamp DESC
        '''
        
        df = pd.read_sql_query(query, conn, params=(symbol, lookback_days))
        
        if df.empty:
            conn.close()
            return []
        
        # Find similar conditions
        current_pain = current_gex.get('dealer_pain', 0)
        current_net_gex = current_gex.get('net_gex', 0)
        current_distance = current_gex.get('distance_to_flip', 0)
        
        similar_setups = []
        
        for _, row in df.iterrows():
            # Calculate similarity score
            pain_diff = abs(row['dealer_pain'] - current_pain)
            gex_diff = abs(row['net_gex'] - current_net_gex) / 1e9  # Normalize to billions
            distance_diff = abs(row['distance_to_flip'] - current_distance)
            
            # Weighted similarity score
            similarity_score = 100 - (pain_diff * 0.5 + gex_diff * 10 + distance_diff * 5)
            similarity_score = max(0, min(100, similarity_score))
            
            if similarity_score > 70:  # 70% similarity threshold
                # Get what happened next (price 24 hours later)
                future_query = '''
                    SELECT price FROM gex_history
                    WHERE symbol = ?
                    AND timestamp > ?
                    AND timestamp <= datetime(?, '+1 day')
                    ORDER BY timestamp ASC
                    LIMIT 1
                '''
                
                future_df = pd.read_sql_query(
                    future_query, 
                    conn, 
                    params=(symbol, row['timestamp'], row['timestamp'])
                )
                
                if not future_df.empty:
                    future_price = future_df.iloc[0]['price']
                    return_pct = ((future_price - row['price']) / row['price']) * 100
                    
                    similar_setups.append({
                        'date': row['timestamp'],
                        'similarity': similarity_score,
                        'initial_price': row['price'],
                        'future_price': future_price,
                        'return_24h': return_pct,
                        'dealer_pain': row['dealer_pain'],
                        'net_gex': row['net_gex'],
                        'mm_status': row['mm_status'],
                        'regime': row['regime']
                    })
        
        conn.close()
        return sorted(similar_setups, key=lambda x: x['similarity'], reverse=True)[:5]
    
    def record_pattern_outcome(self, symbol: str, pattern_type: str, 
                              entry_price: float, exit_price: float,
                              initial_gex: float, initial_pain: float,
                              duration_hours: float):
        """Record the outcome of a pattern trade"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        outcome = ((exit_price - entry_price) / entry_price) * 100
        
        cursor.execute('''
            INSERT INTO pattern_outcomes
            (pattern_date, symbol, pattern_type, entry_price, exit_price, 
             outcome, duration_hours, initial_gex, initial_pain)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(),
            symbol,
            pattern_type,
            entry_price,
            exit_price,
            outcome,
            duration_hours,
            initial_gex,
            initial_pain
        ))
        
        conn.commit()
        conn.close()
        
        return outcome
    
    def get_historical_patterns(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Get all historical patterns for analysis"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT * FROM pattern_outcomes
            WHERE symbol = ?
            AND pattern_date > datetime('now', '-' || ? || ' days')
            ORDER BY pattern_date DESC
        '''
        
        df = pd.read_sql_query(query, conn, params=(symbol, days))
        conn.close()
        
        return df
    
    def get_best_patterns(self, min_occurrences: int = 5) -> List[Dict]:
        """Get the most profitable patterns historically"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT 
                pattern_type,
                COUNT(*) as occurrences,
                AVG(outcome) as avg_return,
                AVG(CASE WHEN outcome > 0 THEN 1 ELSE 0 END) * 100 as win_rate,
                MAX(outcome) as best_return,
                AVG(duration_hours) as avg_duration
            FROM pattern_outcomes
            GROUP BY pattern_type
            HAVING COUNT(*) >= ?
            ORDER BY avg_return DESC
        '''
        
        df = pd.read_sql_query(query, conn, params=(min_occurrences,))
        conn.close()
        
        return df.to_dict('records')
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent high-value setups from database"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT * FROM gex_history
            WHERE timestamp > datetime('now', '-' || ? || ' hours')
            AND dealer_pain > 70
            ORDER BY dealer_pain DESC
            LIMIT 10
        '''
        
        df = pd.read_sql_query(query, conn, params=(hours,))
        conn.close()
        
        if not df.empty:
            return df.to_dict('records')
        return []
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data to manage database size"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete old GEX history
        cursor.execute('''
            DELETE FROM gex_history
            WHERE timestamp < datetime('now', '-' || ? || ' days')
        ''', (days_to_keep,))
        
        # Delete old pattern outcomes older than 1 year
        cursor.execute('''
            DELETE FROM pattern_outcomes
            WHERE pattern_date < datetime('now', '-365 days')
        ''')
        
        conn.commit()
        conn.close()
