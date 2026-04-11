#!/usr/bin/env python3
"""
Synthetic Overnight Indicator Data Fetcher
Fetches US market close, Taiwan ADRs, and Asia futures to predict Taiwan market open

HYBRID APPROACH FOR SGX FUTURES:
1. Try Yahoo Finance first (fast)
2. If Yahoo data is stale (>1 day old), use Investing.com scraper (slower but reliable)
"""

import yfinance as yf
import json
import math
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional

# Hong Kong timezone (UTC+8)
HK_TIMEZONE = timezone(timedelta(hours=8))

# Taiwan ADR pairs
ADR_PAIRS = [
    {
        'name': 'TSMC',
        'tw_ticker': '2330.TW',
        'adr_ticker': 'TSM',
        'ratio': 5
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
        'ratio': 2
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

# Monthly futures month codes
# F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec
MONTH_TO_CODE = {
    1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M',
    7: 'N', 8: 'Q', 9: 'U', 10: 'V', 11: 'X', 12: 'Z'
}

MONTH_NAMES = {
    1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
    7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
}


def get_sgx_contract_tickers() -> List[Tuple[str, str, str]]:
    """
    Get current and next month SGX contract tickers
    Returns: List of (ticker, contract_code, month_name) tuples
    
    Contract expires on 2nd last business day of the contract month.
    """
    now = datetime.now(HK_TIMEZONE)
    current_month = now.month
    current_year = now.year
    
    contracts = []
    
    # Current month contract
    month_code = MONTH_TO_CODE[current_month]
    year_code = current_year % 100
    ticker = f"TWN-{month_code}{year_code:02d}.SI"
    contract_code = f"{month_code}{year_code:02d}"
    month_name = f"{MONTH_NAMES[current_month]} {current_year}"
    contracts.append((ticker, contract_code, month_name))
    
    # Next month contract
    next_month = current_month + 1 if current_month < 12 else 1
    next_year = current_year if current_month < 12 else current_year + 1
    next_month_code = MONTH_TO_CODE[next_month]
    next_year_code = next_year % 100
    next_ticker = f"TWN-{next_month_code}{next_year_code:02d}.SI"
    next_contract_code = f"{next_month_code}{next_year_code:02d}"
    next_month_name = f"{MONTH_NAMES[next_month]} {next_year}"
    contracts.append((next_ticker, next_contract_code, next_month_name))
    
    return contracts


def safe_round(value, decimals=2):
    """Round value, return None if NaN or inf"""
    if value is None or math.isnan(value) or math.isinf(value):
        return None
    return round(value, decimals)


def is_data_stale(date_str: str, max_age_days: int = 1) -> bool:
    """Check if data date is older than max_age_days"""
    try:
        data_date = datetime.strptime(date_str, '%Y-%m-%d')
        now = datetime.now(HK_TIMEZONE).replace(tzinfo=None)
        age_days = (now - data_date).days
        return age_days > max_age_days
    except:
        return True


def try_yahoo_sgx_futures(ticker: str, contract_code: str, month_name: str) -> Optional[dict]:
    """
    Try to fetch SGX futures data from Yahoo Finance
    Returns dict if successful, None if failed or stale
    """
    try:
        print(f"    Trying Yahoo Finance: {ticker}")
        data = yf.Ticker(ticker)
        hist = data.history(period='5d')
        
        if len(hist) < 1:
            print(f"    ✗ No data from Yahoo")
            return None
        
        # Get latest trading day
        latest = hist.iloc[-1]
        latest_date = hist.index[-1].strftime('%Y-%m-%d')
        
        # Check if data is stale (>1 day old)
        if is_data_stale(latest_date, max_age_days=1):
            print(f"    ⚠ Yahoo data is stale ({latest_date}), will try scraping")
            return None
        
        # Try to get previous close
        prev_close = None
        change_pct = None
        if len(hist) >= 2:
            prev_close = safe_round(hist['Close'].iloc[-2], 2)
            current_close = safe_round(latest['Close'], 2)
            if prev_close and current_close:
                change_pct = safe_round(((current_close - prev_close) / prev_close) * 100, 2)
        
        result = {
            'name': 'SGX FTSE Taiwan',
            'contract': f"TWN {contract_code}",
            'ticker': ticker,
            'month': month_name,
            'date': latest_date,
            'open': safe_round(latest['Open'], 2),
            'high': safe_round(latest['High'], 2),
            'low': safe_round(latest['Low'], 2),
            'close': safe_round(latest['Close'], 2),
            'prev_close': prev_close,
            'change_pct': change_pct,
            'volume': int(latest['Volume']) if not math.isnan(latest['Volume']) else 0,
            'source': 'Yahoo Finance'
        }
        
        print(f"    ✓ Yahoo: {latest_date}, Close={latest['Close']:.2f}")
        return result
        
    except Exception as e:
        print(f"    ✗ Yahoo error: {e}")
        return None


def try_investing_scraper(contract_code: str, month_name: str) -> Optional[dict]:
    """
    Scrape SGX futures data from Investing.com using Playwright
    Only called if Yahoo Finance fails or has stale data
    """
    try:
        print(f"    Trying Investing.com scraper for {contract_code}...")
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Investing.com SGX FTSE Taiwan futures page
            url = "https://www.investing.com/indices/sgx-ftse-taiwan-futures"
            page.goto(url, wait_until='domcontentloaded', timeout=20000)
            page.wait_for_timeout(2000)
            
            # Try to extract price data from the page
            # This is a simplified scraper - might need adjustment based on actual page structure
            try:
                # Get current price
                price_elem = page.query_selector('[data-test="instrument-price-last"]')
                close_price = float(price_elem.inner_text().replace(',', '')) if price_elem else None
                
                # Get change percentage
                change_elem = page.query_selector('[data-test="instrument-price-change-percent"]')
                change_pct_text = change_elem.inner_text() if change_elem else None
                change_pct = float(change_pct_text.replace('%', '').replace('+', '')) if change_pct_text else None
                
                # Get date (use today since it's live data)
                today = datetime.now(HK_TIMEZONE).strftime('%Y-%m-%d')
                
                if close_price:
                    result = {
                        'name': 'SGX FTSE Taiwan',
                        'contract': f"TWN {contract_code}",
                        'ticker': f"TWN-{contract_code}.SI",
                        'month': month_name,
                        'date': today,
                        'open': None,  # Not always available from Investing.com
                        'high': None,
                        'low': None,
                        'close': safe_round(close_price, 2),
                        'prev_close': None,
                        'change_pct': safe_round(change_pct, 2) if change_pct else None,
                        'volume': 0,
                        'source': 'Investing.com (scraped)'
                    }
                    
                    print(f"    ✓ Investing.com: {today}, Close={close_price:.2f}")
                    browser.close()
                    return result
                
            except Exception as e:
                print(f"    ✗ Investing.com scraping error: {e}")
            
            browser.close()
            
    except ImportError:
        print(f"    ✗ Playwright not installed, skipping scraper")
    except Exception as e:
        print(f"    ✗ Investing.com error: {e}")
    
    return None


def get_sgx_futures():
    """
    Get SGX futures data with hybrid approach:
    1. Try Yahoo Finance (fast)
    2. If Yahoo fails or stale, try Investing.com scraper (slower but fresh)
    """
    print("Fetching SGX futures data (hybrid mode)...")
    futures = []
    
    contracts = get_sgx_contract_tickers()
    
    for ticker, contract_code, month_name in contracts:
        print(f"  Processing {contract_code} ({month_name})...")
        
        # Try Yahoo first
        result = try_yahoo_sgx_futures(ticker, contract_code, month_name)
        
        # If Yahoo failed or stale, try scraping
        if result is None:
            print(f"    Yahoo failed/stale, trying Investing.com scraper...")
            result = try_investing_scraper(contract_code, month_name)
        
        # Add to list if we got data
        if result:
            futures.append(result)
        else:
            print(f"  ✗ Could not get data for {contract_code}")
    
    return futures


# ============================================================================
# ALL OTHER FUNCTIONS REMAIN EXACTLY THE SAME
# (ADR signals, US indices, Asia indices - NO CHANGES)
# ============================================================================

def get_historical_basis(tw_ticker, adr_ticker, ratio=5, days=5):
    """Calculate historical ADR basis - UNCHANGED"""
    try:
        tw = yf.Ticker(tw_ticker)
        adr = yf.Ticker(adr_ticker)
        fx = yf.Ticker('TWD=X')
        
        tw_hist = tw.history(period='15d')
        adr_hist = adr.history(period='15d')
        fx_hist = fx.history(period='15d')
        
        if len(tw_hist) < days+1 or len(adr_hist) < days+1:
            return None, None
        
        basis_table = []
        
        for i in range(-days-1, -1):
            try:
                adr_date = adr_hist.index[i]
                adr_close_T = adr_hist['Close'].iloc[i]
                fx_rate_T = fx_hist['Close'].iloc[i]
                tw_open_T1 = tw_hist['Open'].iloc[i+1]
                
                if any(math.isnan(v) or math.isinf(v) for v in [adr_close_T, fx_rate_T, tw_open_T1]):
                    continue
                
                adr_fx = adr_close_T * fx_rate_T
                tw_x_ratio = tw_open_T1 * ratio
                basis = adr_fx / tw_x_ratio
                premium_pct = (basis - 1) * 100
                
                basis_table.append({
                    'adr_date': adr_date.strftime('%b %d'),
                    'adr_close': safe_round(adr_close_T, 2),
                    'fx_rate': safe_round(fx_rate_T, 2),
                    'tw_open_next': safe_round(tw_open_T1, 2),
                    'adr_fx': safe_round(adr_fx, 2),
                    'tw_x_ratio': safe_round(tw_x_ratio, 2),
                    'basis': safe_round(basis, 4),
                    'premium_pct': safe_round(premium_pct, 2)
                })
            except:
                continue
        
        if not basis_table:
            return None, None
        
        avg_basis = sum([row['basis'] for row in basis_table if row['basis']]) / len(basis_table)
        return basis_table, round(avg_basis, 4)
        
    except Exception as e:
        print(f"Error calculating basis for {tw_ticker}: {e}")
        return None, None


def get_adr_signal(pair):
    """Get ADR signal - UNCHANGED"""
    try:
        tw = yf.Ticker(pair['tw_ticker'])
        adr = yf.Ticker(pair['adr_ticker'])
        fx = yf.Ticker('TWD=X')
        
        tw_hist = tw.history(period='2d')
        adr_hist = adr.history(period='2d')
        fx_hist = fx.history(period='1d')
        
        if len(tw_hist) < 2 or len(adr_hist) < 2 or len(fx_hist) < 1:
            return None
        
        tw_close = tw_hist['Close'].iloc[-1]
        tw_prev = tw_hist['Close'].iloc[-2]
        tw_change = ((tw_close - tw_prev) / tw_prev) * 100 if tw_prev > 0 else 0
        
        adr_close = adr_hist['Close'].iloc[-1]
        adr_prev = adr_hist['Close'].iloc[-2]
        adr_change = ((adr_close - adr_prev) / adr_prev) * 100 if adr_prev > 0 else 0
        
        fx_rate = fx_hist['Close'].iloc[-1]
        
        if any(math.isnan(v) or math.isinf(v) for v in [tw_close, adr_close, fx_rate]):
            return None
        
        basis_table, avg_basis = get_historical_basis(pair['tw_ticker'], pair['adr_ticker'], pair['ratio'])
        
        if avg_basis is None:
            return None
        
        predicted_open = (adr_close * fx_rate) / (pair['ratio'] * avg_basis)
        gap_pct = ((predicted_open - tw_close) / tw_close) * 100
        
        if gap_pct > 1.5:
            signal, signal_icon, signal_text = "BULLISH", "🟢", "Strong catch-up rally expected"
        elif gap_pct < -1.5:
            signal, signal_icon, signal_text = "BEARISH", "🔴", "Already ahead, expect pullback"
        else:
            signal, signal_icon, signal_text = "NEUTRAL", "⚪", "Minor adjustment expected"
        
        return {
            'name': pair['name'],
            'tw_ticker': pair['tw_ticker'],
            'adr_ticker': pair['adr_ticker'],
            'tw_close': safe_round(tw_close, 2),
            'tw_change_pct': safe_round(tw_change, 2),
            'adr_close': safe_round(adr_close, 2),
            'adr_change_pct': safe_round(adr_change, 2),
            'fx_rate': safe_round(fx_rate, 2),
            'basis_table': basis_table,
            'avg_basis': avg_basis,
            'avg_premium_pct': safe_round((avg_basis - 1) * 100, 2),
            'predicted_open': safe_round(predicted_open, 2),
            'gap_pct': safe_round(gap_pct, 2),
            'signal': signal,
            'signal_icon': signal_icon,
            'signal_text': signal_text
        }
    except Exception as e:
        print(f"Error getting ADR signal for {pair['name']}: {e}")
        return None


def get_us_indices():
    """Get US market indices - UNCHANGED"""
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
                
                if math.isnan(close) or math.isinf(close) or math.isnan(prev_close) or math.isinf(prev_close):
                    continue
                
                change = close - prev_close
                change_pct = (change / prev_close) * 100
                
                indices.append({
                    'name': name,
                    'ticker': ticker,
                    'close': safe_round(close, 2),
                    'change': safe_round(change, 2),
                    'change_pct': safe_round(change_pct, 2)
                })
            except Exception as e:
                print(f"Error fetching {name}: {e}")
                continue
    
    return indices


def get_asia_indices():
    """Get Asia market indices - UNCHANGED"""
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
                
                if math.isnan(close) or math.isinf(close) or math.isnan(prev_close) or math.isinf(prev_close):
                    continue
                
                change = close - prev_close
                change_pct = (change / prev_close) * 100
                
                indices.append({
                    'name': name,
                    'ticker': ticker,
                    'close': safe_round(close, 2),
                    'change': safe_round(change, 2),
                    'change_pct': safe_round(change_pct, 2)
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
    
    # Get SGX futures (HYBRID METHOD)
    sgx_futures = get_sgx_futures()
    print(f"✓ Fetched {len(sgx_futures)} SGX futures contracts")
    
    # Get ADR signals
    print("Calculating ADR signals...")
    adr_signals = []
    for pair in ADR_PAIRS:
        print(f"  Processing {pair['name']}...")
        signal = get_adr_signal(pair)
        if signal:
            adr_signals.append(signal)
            gap = signal['gap_pct'] if signal['gap_pct'] else 0
            print(f"  ✓ {pair['name']}: {signal['signal']} ({gap:+.2f}%)")
    
    # Compile data
    output_data = {
        'update_time': datetime.now(HK_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S'),
        'us_indices': us_indices,
        'asia_indices': asia_indices,
        'sgx_futures': sgx_futures,
        'adr_signals': adr_signals
    }
    
    # Save to JSON
    output_file = './data/overnight-indicators.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2, allow_nan=False)
    
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
