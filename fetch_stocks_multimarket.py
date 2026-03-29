#!/usr/bin/env python3
"""
Multi-Market Stock Heatmap Data Fetcher
Fetches stock data for Taiwan, Korea, and India markets
"""

import yfinance as yf
import json
from datetime import datetime, timezone, timedelta
import os

# Hong Kong timezone (UTC+8)
HK_TZ = timezone(timedelta(hours=8))

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
    },
    'hose': {
        'name': 'Vietnam Ho Chi Minh Stock Exchange',
        'stocks': [
            {'symbol': 'VNM.VN', 'name': 'Vinamilk'},
            {'symbol': 'VCB.VN', 'name': 'Vietcombank'},
            {'symbol': 'VHM.VN', 'name': 'Vinhomes'},
            {'symbol': 'VIC.VN', 'name': 'Vingroup'},
            {'symbol': 'HPG.VN', 'name': 'Hoa Phat'},
            {'symbol': 'GAS.VN', 'name': 'PetroVietnam Gas'},
            {'symbol': 'TCB.VN', 'name': 'Techcombank'},
            {'symbol': 'BID.VN', 'name': 'BIDV'},
            {'symbol': 'CTG.VN', 'name': 'VietinBank'},
            {'symbol': 'MBB.VN', 'name': 'MB Bank'},
            {'symbol': 'VPB.VN', 'name': 'VPBank'},
            {'symbol': 'PLX.VN', 'name': 'Petrolimex'},
            {'symbol': 'MSN.VN', 'name': 'Masan'},
            {'symbol': 'SSI.VN', 'name': 'SSI Securities'},
            {'symbol': 'VRE.VN', 'name': 'Vincom Retail'},
            {'symbol': 'POW.VN', 'name': 'PetroVietnam Power'},
            {'symbol': 'SAB.VN', 'name': 'Sabeco'},
            {'symbol': 'FPT.VN', 'name': 'FPT Corp'},
            {'symbol': 'TPB.VN', 'name': 'TPBank'},
            {'symbol': 'ACB.VN', 'name': 'ACB'}
        ]
    },
    'pse': {
        'name': 'Philippines Stock Exchange',
        'stocks': [
            {'symbol': 'SM.PSE', 'name': 'SM Investments'},
            {'symbol': 'BDO.PSE', 'name': 'BDO Unibank'},
            {'symbol': 'SMPH.PSE', 'name': 'SM Prime'},
            {'symbol': 'ALI.PSE', 'name': 'Ayala Land'},
            {'symbol': 'JGS.PSE', 'name': 'JG Summit'},
            {'symbol': 'TEL.PSE', 'name': 'PLDT'},
            {'symbol': 'MBT.PSE', 'name': 'Metrobank'},
            {'symbol': 'GLO.PSE', 'name': 'Globe Telecom'},
            {'symbol': 'AC.PSE', 'name': 'Ayala Corp'},
            {'symbol': 'BPI.PSE', 'name': 'BPI'},
            {'symbol': 'GTCAP.PSE', 'name': 'GT Capital'},
            {'symbol': 'MEG.PSE', 'name': 'Megaworld'},
            {'symbol': 'URC.PSE', 'name': 'Universal Robina'},
            {'symbol': 'ICT.PSE', 'name': 'International Container'},
            {'symbol': 'SECB.PSE', 'name': 'Security Bank'},
            {'symbol': 'DMC.PSE', 'name': 'DMCI Holdings'},
            {'symbol': 'AGI.PSE', 'name': 'Alliance Global'},
            {'symbol': 'RLC.PSE', 'name': 'Robinsons Land'},
            {'symbol': 'AP.PSE', 'name': 'Aboitiz Power'},
            {'symbol': 'MONDE.PSE', 'name': 'Monde Nissin'}
        ]
    },
    'klse': {
        'name': 'Malaysia Stock Exchange',
        'stocks': [
            {'symbol': '1155.KL', 'name': 'Maybank'},
            {'symbol': '1023.KL', 'name': 'CIMB Group'},
            {'symbol': '1295.KL', 'name': 'Public Bank'},
            {'symbol': '5347.KL', 'name': 'Tenaga Nasional'},
            {'symbol': '6033.KL', 'name': 'Petronas Gas'},
            {'symbol': '5681.KL', 'name': 'Petronas Dagangan'},
            {'symbol': '1961.KL', 'name': 'IOI Corp'},
            {'symbol': '4197.KL', 'name': 'Sime Darby'},
            {'symbol': '3816.KL', 'name': 'MISC'},
            {'symbol': '6947.KL', 'name': 'Digi'},
            {'symbol': '6888.KL', 'name': 'Axiata'},
            {'symbol': '6012.KL', 'name': 'Maxis'},
            {'symbol': '4715.KL', 'name': 'Genting Malaysia'},
            {'symbol': '3182.KL', 'name': 'Genting'},
            {'symbol': '1066.KL', 'name': 'RHB Bank'},
            {'symbol': '5819.KL', 'name': 'Hong Leong Bank'},
            {'symbol': '1015.KL', 'name': 'AMMB Holdings'},
            {'symbol': '4065.KL', 'name': 'PPB Group'},
            {'symbol': '4707.KL', 'name': 'Nestle Malaysia'},
            {'symbol': '7113.KL', 'name': 'Top Glove'}
        ]
    },
    'idx': {
        'name': 'Indonesia Stock Exchange',
        'stocks': [
            {'symbol': 'BBCA.JK', 'name': 'Bank Central Asia'},
            {'symbol': 'BBRI.JK', 'name': 'Bank Rakyat'},
            {'symbol': 'BMRI.JK', 'name': 'Bank Mandiri'},
            {'symbol': 'TLKM.JK', 'name': 'Telkom Indonesia'},
            {'symbol': 'ASII.JK', 'name': 'Astra International'},
            {'symbol': 'BBNI.JK', 'name': 'Bank Negara'},
            {'symbol': 'UNVR.JK', 'name': 'Unilever Indonesia'},
            {'symbol': 'GOTO.JK', 'name': 'GoTo'},
            {'symbol': 'ADRO.JK', 'name': 'Adaro Energy'},
            {'symbol': 'INDF.JK', 'name': 'Indofood'},
            {'symbol': 'ICBP.JK', 'name': 'Indofood CBP'},
            {'symbol': 'PTBA.JK', 'name': 'Bukit Asam'},
            {'symbol': 'KLBF.JK', 'name': 'Kalbe Farma'},
            {'symbol': 'EXCL.JK', 'name': 'XL Axiata'},
            {'symbol': 'INCO.JK', 'name': 'Vale Indonesia'},
            {'symbol': 'ITMG.JK', 'name': 'Indo Tambangraya'},
            {'symbol': 'SMGR.JK', 'name': 'Semen Indonesia'},
            {'symbol': 'PWON.JK', 'name': 'Pakuwon Jati'},
            {'symbol': 'ANTM.JK', 'name': 'Aneka Tambang'},
            {'symbol': 'UNTR.JK', 'name': 'United Tractors'}
        ]
    }
}


def fetch_market_data(market_id):
    """Fetch stock data for a specific market"""
    market = MARKETS[market_id]
    print(f"\n{'='*70}")
    print(f"FETCHING {market['name'].upper()} DATA")
    print(f"{'='*70}\n")
    
    # Get live FX rates from Yahoo Finance
    print("Fetching live FX rates...")
    fx_rates = {}
    
    try:
        # Fetch live FX rates
        if market_id == 'twse':
            usdtwd = yf.Ticker('TWD=X').history(period='1d')
            fx_rates['twse'] = usdtwd['Close'].iloc[-1] if len(usdtwd) > 0 else 31.5
        elif market_id == 'kospi':
            usdkrw = yf.Ticker('KRW=X').history(period='1d')
            fx_rates['kospi'] = usdkrw['Close'].iloc[-1] if len(usdkrw) > 0 else 1350
        elif market_id == 'nse':
            usdinr = yf.Ticker('INR=X').history(period='1d')
            fx_rates['nse'] = usdinr['Close'].iloc[-1] if len(usdinr) > 0 else 83
        elif market_id == 'hose':
            usdvnd = yf.Ticker('VND=X').history(period='1d')
            fx_rates['hose'] = usdvnd['Close'].iloc[-1] if len(usdvnd) > 0 else 25000
        elif market_id == 'pse':
            usdphp = yf.Ticker('PHP=X').history(period='1d')
            fx_rates['pse'] = usdphp['Close'].iloc[-1] if len(usdphp) > 0 else 56
        elif market_id == 'klse':
            usdmyr = yf.Ticker('MYR=X').history(period='1d')
            fx_rates['klse'] = usdmyr['Close'].iloc[-1] if len(usdmyr) > 0 else 4.7
        elif market_id == 'idx':
            usdidr = yf.Ticker('IDR=X').history(period='1d')
            fx_rates['idx'] = usdidr['Close'].iloc[-1] if len(usdidr) > 0 else 16000
        
        fx_rate = fx_rates.get(market_id, 1)
        print(f"✓ FX Rate: {fx_rate:.2f} (local currency per USD)")
        print()
    except:
        # Fallback to approximate rates if live fetch fails
        fallback_rates = {
            'twse': 31.5, 
            'kospi': 1350, 
            'nse': 83,
            'hose': 25000,
            'pse': 56,
            'klse': 4.7,
            'idx': 16000
        }
        fx_rate = fallback_rates.get(market_id, 1)
        print(f"⚠️  Using fallback FX rate: {fx_rate}")
        print()
    
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
            
            # Get market cap in local currency and convert to USD
            try:
                info = ticker.info
                market_cap_local = info.get('marketCap', 0)
                
                if market_cap_local and market_cap_local > 0:
                    # Convert local currency to USD
                    market_cap_usd = market_cap_local / fx_rate
                else:
                    # Default 1B if missing
                    market_cap_usd = 1000000000
                
                # Get PE ratio (try trailing first, then forward for Korea/etc)
                pe_ratio = info.get('trailingPE')
                if not pe_ratio:
                    pe_ratio = info.get('forwardPE')  # Fallback for Korean stocks
                
                # Get PB ratio  
                pb_ratio = info.get('priceToBook')
                
                # Get dividend yield (Yahoo returns as decimal, e.g., 0.0129 = 1.29%)
                dividend_yield = info.get('dividendYield', None)
                if dividend_yield and dividend_yield < 1:  # If < 1, it's decimal format
                    dividend_yield = dividend_yield * 100  # Convert to percentage
                
                # Get 52-week high
                week_52_high = info.get('fiftyTwoWeekHigh', None)
                pct_from_high = None
                if week_52_high and week_52_high > 0:
                    pct_from_high = ((current_price - week_52_high) / week_52_high) * 100
                    
            except Exception as e:
                market_cap_usd = 1000000000
                pe_ratio = None
                pb_ratio = None
                dividend_yield = None
                pct_from_high = None
            
            # Debug output for first stock of each market
            if len(stocks_data) == 1:
                print(f"  [DEBUG FETCHED] PE={pe_ratio}, PB={pb_ratio}, Div={dividend_yield}")
                pe_saved = round(pe_ratio, 2) if (pe_ratio and 0 < pe_ratio < 1000) else None
                pb_saved = round(pb_ratio, 2) if (pb_ratio and 0 < pb_ratio < 100) else None
                print(f"  [DEBUG SAVED] PE={pe_saved}, PB={pb_saved}")
            
            stocks_data.append({
                'symbol': stock['symbol'],
                'name': stock['name'],
                'price': round(current_price, 2),
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'market_cap': round(market_cap_usd, 0),  # Converted to USD
                'pe_ratio': round(pe_ratio, 2) if (pe_ratio and 0 < pe_ratio < 1000) else None,
                'pb_ratio': round(pb_ratio, 2) if (pb_ratio and 0 < pb_ratio < 100) else None,
                'dividend_yield': round(dividend_yield, 2) if (dividend_yield and dividend_yield > 0) else None,
                'pct_from_high': round(pct_from_high, 2) if pct_from_high else None
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
    hk_now = datetime.now(HK_TZ)
    print(hk_now.strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 70)
    
    # Fetch working markets only (Philippines not available on Yahoo Finance)
    all_data = {}
    hk_now = datetime.now(HK_TZ)
    update_time_str = hk_now.strftime('%Y-%m-%d %H:%M:%S')
    
    for market_id in ['twse', 'kospi', 'nse', 'hose', 'klse', 'idx']:
        stocks_data = fetch_market_data(market_id)
        all_data[market_id] = {
            'market_name': MARKETS[market_id]['name'],
            'stocks': stocks_data,
            'update_time': update_time_str
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
