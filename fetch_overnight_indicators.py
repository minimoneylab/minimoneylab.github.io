#!/usr/bin/env python3
"""
Synthetic Overnight Indicator Data Fetcher
Fetches US market close, Taiwan ADRs, and Asia futures to predict Taiwan market open
"""

import yfinance as yf
import json
from datetime import datetime, timezone, timedelta

# Hong Kong timezone (UTC+8)
HK_TIMEZONE = timezone(timedelta(hours=8))

# Taiwan ADR pairs
ADR_PAIRS = [
    {
        'name': 'TSMC',
        'tw_ticker': '2330.TW',
        'adr_ticker': 'TSM',
        'ratio': 5  # 1 ADR = 5 ordinary shares
    },
    {
        'name': 'UMC',
        'tw_ticker': '2303.TW',
        'adr_ticker': 'UMC',
        'ratio': 5
    },
    {
        'name': 'ASE',
        'tw_ticker': '3711.TW',
        'adr_ticker': 'ASX',
        'ratio': 2  # 1 ADR = 2 ordinary shares
    }
]

US_INDICES = [
    {'^GSPC': 'S&P 500'},
    {'^IXIC': 'Nasdaq'},
    {'^DJI': 'Dow Jones'},
    {'^VIX': 'VIX'},
    {'^SOX': 'SOX (Semiconductors)'}
]

ASIA_INDICES = [
    {'^TWII': 'TWSE Index'},
    {'^HSI': 'Hang Seng'},
    {'^N225': 'Nikkei 225'}
]


def get_historical_basis(tw_ticker, adr_ticker, ratio=5, days=5):
    """
    Calculate historical ADR basis using next-day Taiwan open
    basis = (ADR_close_T × FX_T) / (TW_open_T+1 × ratio)
    """
    try:
        # Fetch data
        tw = yf.Ticker(tw_ticker)
        adr = yf.Ticker(adr_ticker)
        fx = yf.Ticker('TWD=X')
        
        # Get 15 days to ensure we have enough data
        tw_hist = tw.history(period='15d')
        adr_hist = adr.history(period='15d')
        fx_hist = fx.history(period='15d')
        
        if len(tw_hist) < days+1 or len(adr_hist) < days+1:
            return None, None
        
        basis_table = []
        
        # Calculate for last 5 days (need T+1, so we stop at -1)
        for i in range(-days-1, -1):
            try:
                adr_date = adr_hist.index[i]
                
                # Get values
                adr_close_T = adr_hist['Close'].iloc[i]
                fx_rate_T = fx_hist['Close'].iloc[i]
                tw_open_T1 = tw_hist['Open'].iloc[i+1]  # NEXT DAY OPEN
                
                # Calculate basis
                adr_fx = adr_close_T * fx_rate_T
                tw_x_ratio = tw_open_T1 * ratio
                basis = adr_fx / tw_x_ratio
                premium_pct = (basis - 1) * 100
                
                basis_table.append({
                    'adr_date': adr_date.strftime('%b %d'),
                    'adr_close': round(adr_close_T, 2),
                    'fx_rate': round(fx_rate_T, 2),
                    'tw_open_next': round(tw_open_T1, 2),
                    'adr_fx': round(adr_fx, 2),
                    'tw_x_ratio': round(tw_x_ratio, 2),
                    'basis': round(basis, 4),
                    'premium_pct': round(premium_pct, 2)
                })
            except Exception as e:
                continue
        
        if not basis_table:
            return None, None
        
        # Calculate average
        avg_basis = sum([row['basis'] for row in basis_table]) / len(basis_table)
        avg_premium = (avg_basis - 1) * 100
        
        return basis_table, round(avg_basis, 4)
        
    except Exception as e:
        print(f"Error calculating basis for {tw_ticker}: {e}")
        return None, None


def get_adr_signal(pair):
    """Get ADR signal for a Taiwan stock"""
    try:
        tw = yf.Ticker(pair['tw_ticker'])
        adr = yf.Ticker(pair['adr_ticker'])
        fx = yf.Ticker('TWD=X')
        
        # Get latest data
        tw_hist = tw.history(period='2d')
        adr_hist = adr.history(period='2d')
        fx_hist = fx.history(period='1d')
        
        tw_close = tw_hist['Close'].iloc[-1]
        tw_change = ((tw_hist['Close'].iloc[-1] - tw_hist['Close'].iloc[-2]) / tw_hist['Close'].iloc[-2]) * 100
        
        adr_close = adr_hist['Close'].iloc[-1]
        adr_change = ((adr_hist['Close'].iloc[-1] - adr_hist['Close'].iloc[-2]) / adr_hist['Close'].iloc[-2]) * 100
        
        fx_rate = fx_hist['Close'].iloc[-1]
        
        # Get historical basis
        basis_table, avg_basis = get_historical_basis(
            pair['tw_ticker'], 
            pair['adr_ticker'], 
            pair['ratio']
        )
        
        if avg_basis is None:
            return None
        
        # Predict Taiwan open
        predicted_open = (adr_close * fx_rate) / (pair['ratio'] * avg_basis)
        gap_pct = ((predicted_open - tw_close) / tw_close) * 100
        
        # Generate signal
        if gap_pct > 1.5:
            signal = "BULLISH"
            signal_icon = "🟢"
            signal_text = "Strong catch-up rally expected"
        elif gap_pct < -1.5:
            signal = "BEARISH"
            signal_icon = "🔴"
            signal_text = "Already ahead, expect pullback"
        else:
            signal = "NEUTRAL"
            signal_icon = "⚪"
            signal_text = "Minor adjustment expected"
        
        return {
            'name': pair['name'],
            'tw_ticker': pair['tw_ticker'],
            'adr_ticker': pair['adr_ticker'],
            'tw_close': round(tw_close, 2),
            'tw_change_pct': round(tw_change, 2),
            'adr_close': round(adr_close, 2),
            'adr_change_pct': round(adr_change, 2),
            'fx_rate': round(fx_rate, 2),
            'basis_table': basis_table,
            'avg_basis': avg_basis,
            'avg_premium_pct': round((avg_basis - 1) * 100, 2),
            'predicted_open': round(predicted_open, 2),
            'gap_pct': round(gap_pct, 2),
            'signal': signal,
            'signal_icon': signal_icon,
            'signal_text': signal_text
        }
        
    except Exception as e:
        print(f"Error getting ADR signal for {pair['name']}: {e}")
        return None


def get_us_indices():
    """Get US market indices"""
    indices = []
    for idx_dict in US_INDICES:
        for ticker, name in idx_dict.items():
            try:
                data = yf.Ticker(ticker)
                hist = data.history(period='2d')
                
                if len(hist) < 2:
                    continue
                
                close = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
                change = close - prev_close
                change_pct = (change / prev_close) * 100
                
                indices.append({
                    'name': name,
                    'ticker': ticker,
                    'close': round(close, 2),
                    'change': round(change, 2),
                    'change_pct': round(change_pct, 2)
                })
            except Exception as e:
                print(f"Error fetching {name}: {e}")
                continue
    
    return indices


def get_asia_indices():
    """Get Asia market indices"""
    indices = []
    for idx_dict in ASIA_INDICES:
        for ticker, name in idx_dict.items():
            try:
                data = yf.Ticker(ticker)
                hist = data.history(period='2d')
                
                if len(hist) < 2:
                    continue
                
                close = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
                change = close - prev_close
                change_pct = (change / prev_close) * 100
                
                indices.append({
                    'name': name,
                    'ticker': ticker,
                    'close': round(close, 2),
                    'change': round(change, 2),
                    'change_pct': round(change_pct, 2)
                })
            except Exception as e:
                print(f"Error fetching {name}: {e}")
                continue
    
    return indices


def main():
    print("=" * 70)
    print("SYNTHETIC OVERNIGHT INDICATOR")
    print(datetime.now(HK_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S HK'))
    print("=" * 70)
    print()
    
    # Get US indices
    print("Fetching US market data...")
    us_indices = get_us_indices()
    print(f"✓ Fetched {len(us_indices)} US indices")
    
    # Get Asia indices
    print("Fetching Asia market data...")
    asia_indices = get_asia_indices()
    print(f"✓ Fetched {len(asia_indices)} Asia indices")
    
    # Get ADR signals
    print("Calculating ADR signals...")
    adr_signals = []
    for pair in ADR_PAIRS:
        print(f"  Processing {pair['name']}...")
        signal = get_adr_signal(pair)
        if signal:
            adr_signals.append(signal)
            print(f"  ✓ {pair['name']}: {signal['signal']} ({signal['gap_pct']:+.2f}%)")
    
    # Compile data
    output_data = {
        'update_time': datetime.now(HK_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S'),
        'us_indices': us_indices,
        'asia_indices': asia_indices,
        'adr_signals': adr_signals
    }
    
    # Save to JSON
    output_file = './data/overnight-indicators.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print()
    print(f"✓ Data saved to: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
