#!/usr/bin/env python3
"""
Polymarket Trends Fetcher
Fetches prediction market data from Polymarket API
Uses hybrid approach: featured markets + auto-discovery
"""

import requests
import json
from datetime import datetime, timedelta
import os

# Configuration
CONFIG = {
    # Featured markets (always show these)
    'featured': [
        {
            'slug': 'will-iran-conduct-a-direct-military-strike-on-israel-before-april-2026',
            'label': '🌍 Iran Strikes Israel',
            'category': 'Geopolitics'
        },
        {
            'slug': 'will-the-federal-reserve-cut-interest-rates-in-march-2026',
            'label': '💰 Fed Cuts March 2026',
            'category': 'Fed & Economy'
        },
        {
            'slug': 'will-bitcoin-reach-100000-in-2026',
            'label': '₿ Bitcoin $100K',
            'category': 'Crypto'
        }
    ],
    
    # Auto-discovery by category
    'auto_discover': {
        'Geopolitics': {
            'keywords': ['iran', 'israel', 'war', 'ukraine', 'china', 'taiwan', 'military', 'conflict'],
            'min_volume': 50000,
            'limit': 5
        },
        'Fed & Economy': {
            'keywords': ['fed', 'federal reserve', 'rate cut', 'inflation', 'recession', 'cpi', 'unemployment', 'powell'],
            'min_volume': 100000,
            'limit': 5
        },
        'Crypto': {
            'keywords': ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto'],
            'min_volume': 150000,
            'limit': 3
        },
        'Markets': {
            'keywords': ['s&p', 'dow', 'nasdaq', 'stock market', 'bear market', 'correction'],
            'min_volume': 100000,
            'limit': 3
        }
    },
    
    # Global filters
    'max_days_to_close': 180,  # Within 6 months
    'min_liquidity': 25000      # At least $25K traded
}

POLYMARKET_API = "https://gamma-api.polymarket.com/markets"


def fetch_all_markets():
    """Fetch all active markets from Polymarket"""
    print("=" * 70)
    print("FETCHING POLYMARKET DATA")
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 70)
    print()
    
    try:
        print("Fetching markets from Polymarket API...")
        
        # Get active markets
        params = {
            'closed': 'false',
            'limit': 100,
            'offset': 0
        }
        
        response = requests.get(POLYMARKET_API, params=params, timeout=10)
        response.raise_for_status()
        
        markets = response.json()
        print(f"✓ Fetched {len(markets)} active markets")
        
        return markets
        
    except Exception as e:
        print(f"✗ Error fetching markets: {e}")
        return []


def filter_market_by_keywords(market, keywords):
    """Check if market matches any keyword"""
    text = f"{market.get('question', '')} {market.get('description', '')}".lower()
    return any(keyword.lower() in text for keyword in keywords)


def get_market_data(market):
    """Extract relevant data from market"""
    try:
        # Get probability (price of YES outcome)
        outcomes = market.get('outcomes', [])
        yes_outcome = next((o for o in outcomes if o.get('outcome') == 'Yes'), None)
        
        if not yes_outcome:
            return None
        
        probability = float(yes_outcome.get('price', 0)) * 100
        
        # Get volume
        volume = float(market.get('volume', 0))
        
        # Get liquidity
        liquidity = float(market.get('liquidity', 0))
        
        # Get close date
        end_date_iso = market.get('endDate')
        if end_date_iso:
            end_date = datetime.fromisoformat(end_date_iso.replace('Z', '+00:00'))
            days_to_close = (end_date - datetime.now(end_date.tzinfo)).days
        else:
            days_to_close = None
        
        return {
            'question': market.get('question', 'Unknown'),
            'slug': market.get('slug', ''),
            'probability': round(probability, 1),
            'volume': round(volume, 0),
            'liquidity': round(liquidity, 0),
            'end_date': end_date_iso,
            'days_to_close': days_to_close,
            'url': f"https://polymarket.com/event/{market.get('slug', '')}"
        }
        
    except Exception as e:
        print(f"  Warning: Could not parse market: {e}")
        return None


def get_featured_markets(all_markets):
    """Get data for featured markets"""
    print("\nFetching featured markets...")
    featured_data = []
    
    for featured in CONFIG['featured']:
        # Find market by slug
        market = next((m for m in all_markets if m.get('slug') == featured['slug']), None)
        
        if market:
            data = get_market_data(market)
            if data:
                data['label'] = featured['label']
                data['category'] = featured['category']
                data['is_featured'] = True
                featured_data.append(data)
                print(f"  ✓ {featured['label']}: {data['probability']}%")
        else:
            print(f"  ✗ Not found: {featured['label']}")
    
    return featured_data


def auto_discover_markets(all_markets):
    """Auto-discover markets by category"""
    print("\nAuto-discovering markets by category...")
    discovered = {}
    
    for category, config in CONFIG['auto_discover'].items():
        print(f"\n{category}:")
        
        # Filter markets
        filtered = []
        for market in all_markets:
            # Check keywords
            if not filter_market_by_keywords(market, config['keywords']):
                continue
            
            # Check volume
            volume = float(market.get('volume', 0))
            if volume < config['min_volume']:
                continue
            
            # Check close date
            end_date_iso = market.get('endDate')
            if end_date_iso:
                end_date = datetime.fromisoformat(end_date_iso.replace('Z', '+00:00'))
                days_to_close = (end_date - datetime.now(end_date.tzinfo)).days
                if days_to_close > CONFIG['max_days_to_close'] or days_to_close < 0:
                    continue
            
            # Check liquidity
            liquidity = float(market.get('liquidity', 0))
            if liquidity < CONFIG['min_liquidity']:
                continue
            
            data = get_market_data(market)
            if data:
                data['category'] = category
                data['is_featured'] = False
                filtered.append(data)
        
        # Sort by volume and take top N
        filtered.sort(key=lambda x: x['volume'], reverse=True)
        top_markets = filtered[:config['limit']]
        
        discovered[category] = top_markets
        
        for market in top_markets:
            print(f"  • {market['question'][:60]}... ({market['probability']}%, ${market['volume']:,.0f})")
    
    return discovered


def main():
    """Main function"""
    
    # Fetch all markets
    all_markets = fetch_all_markets()
    
    if not all_markets:
        print("No markets fetched. Exiting.")
        return
    
    # Get featured markets
    featured = get_featured_markets(all_markets)
    
    # Auto-discover markets
    discovered = auto_discover_markets(all_markets)
    
    # Combine data
    output = {
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'featured': featured,
        'categories': discovered
    }
    
    # Save to JSON
    os.makedirs('./data', exist_ok=True)
    filename = './data/polymarket-trends.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 70)
    print(f"✓ Saved to: {filename}")
    print(f"Featured markets: {len(featured)}")
    print(f"Auto-discovered: {sum(len(markets) for markets in discovered.values())}")
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
