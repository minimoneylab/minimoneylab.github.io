#!/usr/bin/env python3
"""
Taiwan Stock Heatmap Data Fetcher
Fetches top Taiwan stocks data and generates heatmap JSON
"""

import yfinance as yf
import json
from datetime import datetime

# Top 20 Taiwan stocks by market cap
TAIWAN_STOCKS = [
    {"symbol": "2330.TW", "name": "TSMC", "name_zh": "台積電", "sector": "半導體"},
    {"symbol": "2317.TW", "name": "Hon Hai", "name_zh": "鴻海", "sector": "電子"},
    {"symbol": "2454.TW", "name": "MediaTek", "name_zh": "聯發科", "sector": "半導體"},
    {"symbol": "2412.TW", "name": "Chunghwa Tel", "name_zh": "中華電", "sector": "電信"},
    {"symbol": "2882.TW", "name": "Cathay FHC", "name_zh": "國泰金", "sector": "金融"},
    {"symbol": "2881.TW", "name": "Fubon FHC", "name_zh": "富邦金", "sector": "金融"},
    {"symbol": "2891.TW", "name": "CTBC FHC", "name_zh": "中信金", "sector": "金融"},
    {"symbol": "2886.TW", "name": "Mega FHC", "name_zh": "兆豐金", "sector": "金融"},
    {"symbol": "2303.TW", "name": "UMC", "name_zh": "聯電", "sector": "半導體"},
    {"symbol": "2308.TW", "name": "Delta", "name_zh": "台達電", "sector": "電子"},
    {"symbol": "2382.TW", "name": "Quanta", "name_zh": "廣達", "sector": "電子"},
    {"symbol": "2357.TW", "name": "Asustek", "name_zh": "華碩", "sector": "電子"},
    {"symbol": "2395.TW", "name": "Advantech", "name_zh": "研華", "sector": "電子"},
    {"symbol": "2301.TW", "name": "Lite-On", "name_zh": "光寶科", "sector": "電子"},
    {"symbol": "2327.TW", "name": "Yageo", "name_zh": "國巨", "sector": "電子"},
    {"symbol": "2345.TW", "name": "Accton", "name_zh": "智邦", "sector": "電子"},
    {"symbol": "3711.TW", "name": "ASE", "name_zh": "日月光投控", "sector": "半導體"},
    {"symbol": "2885.TW", "name": "Yuanta FHC", "name_zh": "元大金", "sector": "金融"},
    {"symbol": "2892.TW", "name": "First FHC", "name_zh": "第一金", "sector": "金融"},
    {"symbol": "2002.TW", "name": "China Steel", "name_zh": "中鋼", "sector": "鋼鐵"},
]

def fetch_stock_data():
    """Fetch stock data from Yahoo Finance"""
    print("=" * 70)
    print("FETCHING TAIWAN STOCK DATA")
    print("=" * 70)
    print()
    
    stocks_data = []
    
    for stock in TAIWAN_STOCKS:
        try:
            print(f"Fetching {stock['name']} ({stock['symbol']})...")
            
            ticker = yf.Ticker(stock['symbol'])
            info = ticker.info
            hist = ticker.history(period="2d")
            
            if len(hist) < 2:
                print(f"  ⚠️  Not enough data, skipping")
                continue
            
            # Get latest price and previous close
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            
            # Calculate change
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100
            
            # Get market cap (in billions TWD)
            market_cap = info.get('marketCap', 0)
            if market_cap == 0:
                # Fallback: estimate from shares * price
                shares = info.get('sharesOutstanding', 0)
                if shares > 0:
                    market_cap = shares * current_price
            
            market_cap_b = market_cap / 1_000_000_000  # Convert to billions
            
            stocks_data.append({
                'symbol': stock['symbol'].replace('.TW', ''),
                'name': stock['name'],
                'name_zh': stock['name_zh'],
                'sector': stock['sector'],
                'price': round(current_price, 2),
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'market_cap': round(market_cap_b, 2),
                'volume': int(hist['Volume'].iloc[-1]) if len(hist) > 0 else 0
            })
            
            print(f"  ✅ {stock['name_zh']}: {change_pct:+.2f}%")
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            continue
    
    print()
    print(f"Successfully fetched {len(stocks_data)}/{len(TAIWAN_STOCKS)} stocks")
    print("=" * 70)
    
    return stocks_data

def save_heatmap_data(stocks_data, output_file):
    """Save data in format ready for treemap visualization"""
    
    # Group by sector
    sectors = {}
    for stock in stocks_data:
        sector = stock['sector']
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(stock)
    
    heatmap_data = {
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_stocks': len(stocks_data),
        'sectors': sectors,
        'stocks': stocks_data
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(heatmap_data, f, ensure_ascii=False, indent=2)
    
    print(f"Saved heatmap data to: {output_file}")
    print()

def main():
    print()
    print("=" * 70)
    print("TAIWAN STOCK HEATMAP DATA GENERATOR")
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 70)
    print()
    
    # Fetch data
    stocks_data = fetch_stock_data()
    
    if not stocks_data:
        print("No stock data fetched!")
        return
    
    # Save to file
    output_file = "./data/stocks-heatmap.json"
    save_heatmap_data(stocks_data, output_file)
    
    # Print summary
    gainers = [s for s in stocks_data if s['change_pct'] > 0]
    losers = [s for s in stocks_data if s['change_pct'] < 0]
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Gainers: {len(gainers)}")
    print(f"Losers:  {len(losers)}")
    print(f"Unchanged: {len(stocks_data) - len(gainers) - len(losers)}")
    
    if gainers:
        top_gainer = max(gainers, key=lambda x: x['change_pct'])
        print(f"\n📈 Top Gainer: {top_gainer['name_zh']} ({top_gainer['change_pct']:+.2f}%)")
    
    if losers:
        top_loser = min(losers, key=lambda x: x['change_pct'])
        print(f"📉 Top Loser: {top_loser['name_zh']} ({top_loser['change_pct']:+.2f}%)")
    
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
