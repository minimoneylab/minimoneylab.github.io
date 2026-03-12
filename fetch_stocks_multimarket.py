#!/usr/bin/env python3
"""
Multi-Market Stock Heatmap Data Fetcher
Fetches stock data for Taiwan, Korea, and India markets
"""

import yfinance as yf
import json
from datetime import datetime
import os

# Market configurations
MARKETS = {
    'twse': {
        'name': 'Taiwan Stock Exchange',
        'stocks': [
            {'symbol': '2330.TW', 'name': 'TSMC'},
            {'symbol': '2317.TW', 'name': 'Hon Hai'},
            {'symbol': '2454.TW', 'name': 'MediaTek'},
            {'symbol': '2412.TW', 'name': 'Chunghwa Tel'},
            {'symbol': '2882.TW', 'name': 'Cathay FHC'},
            {'symbol': '2881.TW', 'name': 'Fubon FHC'},
            {'symbol': '2891.TW', 'name': 'CTBC FHC'},
            {'symbol': '2886.TW', 'name': 'Mega FHC'},
            {'symbol': '2303.TW', 'name': 'UMC'},
            {'symbol': '2308.TW', 'name': 'Delta'},
            {'symbol': '2382.TW', 'name': 'Quanta'},
            {'symbol': '2357.TW', 'name': 'Asustek'},
            {'symbol': '2395.TW', 'name': 'Advantech'},
            {'symbol': '2301.TW', 'name': 'Lite-On'},
            {'symbol': '2327.TW', 'name': 'Yageo'},
            {'symbol': '2345.TW', 'name': 'Accton'},
            {'symbol': '3711.TW', 'name': 'ASE'},
            {'symbol': '2885.TW', 'name': 'Yuanta FHC'},
            {'symbol': '2892.TW', 'name': 'First FHC'},
            {'symbol': '2002.TW', 'name': 'China Steel'}
        ]
    },
    'kospi': {
        'name': 'Korea Stock Exchange',
        'stocks': [
            {'symbol': '005930.KS', 'name': 'Samsung Elec'},
            {'symbol': '000660.KS', 'name': 'SK Hynix'},
            {'symbol': '373220.KS', 'name': 'LG Energy'},
            {'symbol': '207940.KS', 'name': 'Samsung Bio'},
            {'symbol': '005490.KS', 'name': 'POSCO'},
            {'symbol': '035420.KS', 'name': 'Naver'},
            {'symbol': '105560.KS', 'name': 'KB Financial'},
            {'symbol': '055550.KS', 'name': 'Shinhan FG'},
            {'symbol': '005380.KS', 'name': 'Hyundai Motor'},
            {'symbol': '000270.KS', 'name': 'Kia'},
            {'symbol': '051910.KS', 'name': 'LG Chem'},
            {'symbol': '006400.KS', 'name': 'Samsung SDI'},
            {'symbol': '035720.KS', 'name': 'Kakao'},
            {'symbol': '066570.KS', 'name': 'LG Electronics'},
            {'symbol': '032830.KS', 'name': 'Samsung Life'},
            {'symbol': '012450.KS', 'name': 'Hanwha Aero'},
            {'symbol': '010130.KS', 'name': 'Korea Zinc'},
            {'symbol': '267250.KS', 'name': 'HD Hyundai'},
            {'symbol': '028050.KS', 'name': 'Samsung E&A'},
            {'symbol': '068270.KS', 'name': 'Celltrion'}
        ]
    },
    'nse': {
        'name': 'India National Stock Exchange',
        'stocks': [
            {'symbol': 'RELIANCE.NS', 'name': 'Reliance'},
            {'symbol': 'TCS.NS', 'name': 'TCS'},
            {'symbol': 'HDFCBANK.NS', 'name': 'HDFC Bank'},
            {'symbol': 'INFY.NS', 'name': 'Infosys'},
            {'symbol': 'ICICIBANK.NS', 'name': 'ICICI Bank'},
            {'symbol': 'BHARTIARTL.NS', 'name': 'Bharti Airtel'},
            {'symbol': 'SBIN.NS', 'name': 'SBI'},
            {'symbol': 'HINDUNILVR.NS', 'name': 'HUL'},
            {'symbol': 'ITC.NS', 'name': 'ITC'},
            {'symbol': 'LT.NS', 'name': 'L&T'},
            {'symbol': 'AXISBANK.NS', 'name': 'Axis Bank'},
            {'symbol': 'BAJFINANCE.NS', 'name': 'Bajaj Finance'},
            {'symbol': 'MARUTI.NS', 'name': 'Maruti'},
            {'symbol': 'HCLTECH.NS', 'name': 'HCL Tech'},
            {'symbol': 'M&M.NS', 'name': 'M&M'},
            {'symbol': 'ASIANPAINT.NS', 'name': 'Asian Paints'},
            {'symbol': 'WIPRO.NS', 'name': 'Wipro'},
            {'symbol': 'KOTAKBANK.NS', 'name': 'Kotak Bank'},
            {'symbol': 'SUNPHARMA.NS', 'name': 'Sun Pharma'},
            {'symbol': 'TITAN.NS', 'name': 'Titan'}
        ]
    }
}


def fetch_market_data(market_id):
    """Fetch stock data for a specific market"""
    market = MARKETS[market_id]
    print(f"\n{'='*70}")
    print(f"FETCHING {market['name'].upper()} DATA")
    print(f"{'='*70}\n")
    
    stocks_data = []
    
    for stock in market['stocks']:
        try:
            print(f"Fetching {stock['name']} ({stock['symbol']})...")
            
            ticker = yf.Ticker(stock['symbol'])
            hist = ticker.history(period='2d')
            
            if len(hist) < 2:
                print(f"  ⚠️  Not enough data, skipping")
                continue
            
            # Get latest price and previous close
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            
            # Calculate change
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100
            
            # Get market cap
            try:
                info = ticker.info
                market_cap = info.get('marketCap', 0)
            except:
                market_cap = 0
            
            stocks_data.append({
                'symbol': stock['symbol'],
                'name': stock['name'],
                'price': round(current_price, 2),
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'market_cap': market_cap
            })
            
            print(f"  ✓ {stock['name']}: {change_pct:+.2f}%")
            
        except Exception as e:
            print(f"  ✗ Error fetching {stock['name']}: {e}")
            continue
    
    print(f"\n✓ Fetched {len(stocks_data)}/{len(market['stocks'])} stocks")
    return stocks_data


def main():
    """Main function to fetch all markets"""
    print("=" * 70)
    print("MULTI-MARKET STOCK HEATMAP DATA FETCHER")
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 70)
    
    # Fetch all markets
    all_data = {}
    for market_id in ['twse', 'kospi', 'nse']:
        stocks_data = fetch_market_data(market_id)
        all_data[market_id] = {
            'market_name': MARKETS[market_id]['name'],
            'stocks': stocks_data,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    # Save to separate JSON files
    os.makedirs('./data', exist_ok=True)
    
    for market_id, data in all_data.items():
        filename = f'./data/stocks-heatmap-{market_id}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Saved {market_id.upper()} data to: {filename}")
    
    print("\n" + "=" * 70)
    print("ALL MARKETS COMPLETED!")
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
