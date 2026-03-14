#!/usr/bin/env python3
"""
Polymarket Trends Fetcher - Using Official API
Based on https://docs.polymarket.com/market-data/fetching-markets
"""

import requests
import json
from datetime import datetime
import os

# Featured event slugs from your URLs
FEATURED_SLUGS = [
    # Iran/Middle East
    'will-iran-close-the-strait-of-hormuz-by-2027',
    'iran-strikes-israel-on',
    'us-x-iran-ceasefire-by',
    'us-forces-enter-iran-by',
    'will-the-iranian-regime-fall-by-march-31',
    'will-the-iranian-regime-fall-by-june-30',
    
    # Oil
    'will-crude-oil-cl-hit-by-end-of-march',
    
    # Fed
    'how-many-fed-rate-cuts-in-2026',
    'fed-decision-in-march-885',
    'fed-decision-in-april',
]

EVENTS_API = "https://gamma-api.polymarket.com/events"

def fetch_event_by_slug(slug):
    """Fetch a specific event by slug"""
    try:
        # Use query parameter method
        url = f"{EVENTS_API}?slug={slug}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        data = response.json()
        
        # API returns array, get first item
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        
        return None
        
    except Exception as e:
        print(f"  ✗ Error fetching {slug}: {e}")
        return None


def parse_event(event):
    """Parse event data into our format"""
    try:
        title = event.get('title', '')
        slug = event.get('slug', '')
        
        # Get markets within this event
        markets = event.get('markets', [])
        
        if not markets:
            return None
        
        # Get aggregate data
        volume = float(event.get('volume', 0))
        liquidity = float(event.get('liquidity', 0))
        
        # Get end date
        end_date = event.get('endDate', '')
        days_to_close = None
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                days_to_close = (end_dt - datetime.now(end_dt.tzinfo)).days
            except:
                pass
        
        # Parse individual markets for probabilities
        market_data = []
        for market in markets:
            try:
                question = market.get('question', '')
                
                # Get probability
                outcome_prices = market.get('outcomePrices', '[]')
                if isinstance(outcome_prices, str):
                    prices = json.loads(outcome_prices)
                else:
                    prices = outcome_prices
                
                if prices and len(prices) > 0:
                    prob = float(prices[0]) * 100
                    market_data.append({
                        'question': question,
                        'probability': round(prob, 1)
                    })
            except:
                continue
        
        return {
            'title': title,
            'slug': slug,
            'volume': round(volume, 0),
            'liquidity': round(liquidity, 0),
            'end_date': end_date,
            'days_to_close': days_to_close,
            'markets': market_data,
            'url': f"https://polymarket.com/event/{slug}"
        }
        
    except Exception as e:
        return None


def categorize_events(events):
    """Categorize events by topic"""
    categories = {
        'Iran & Middle East': [],
        'Oil & Energy': [],
        'Fed & Rates': [],
    }
    
    for event in events:
        title = event['title'].lower()
        
        # Categorize
        if any(term in title for term in ['iran', 'israel', 'middle east', 'strait', 'hormuz', 'regime']):
            categories['Iran & Middle East'].append(event)
        elif any(term in title for term in ['oil', 'crude', 'wti']):
            categories['Oil & Energy'].append(event)
        elif any(term in title for term in ['fed', 'rate cut', 'fomc']):
            categories['Fed & Rates'].append(event)
    
    # Sort by volume
    for category in categories:
        categories[category].sort(key=lambda x: x['volume'], reverse=True)
    
    return categories


def main():
    """Main function"""
    print("=" * 70)
    print("POLYMARKET TRENDS FETCHER - Official API")
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 70)
    print()
    
    print("Fetching featured events by slug...\n")
    
    events = []
    for slug in FEATURED_SLUGS:
        print(f"Fetching: {slug}")
        event = fetch_event_by_slug(slug)
        
        if event:
            parsed = parse_event(event)
            if parsed:
                events.append(parsed)
                print(f"  ✓ {parsed['title']}")
                print(f"    Volume: ${parsed['volume']:,.0f}")
                if parsed['markets']:
                    for m in parsed['markets'][:2]:  # Show first 2 markets
                        print(f"    • {m['question'][:50]}... ({m['probability']}%)")
            else:
                print(f"  ✗ Could not parse event")
        else:
            print(f"  ✗ Event not found or closed")
        print()
    
    if not events:
        print("No events found!")
        return
    
    # Categorize
    categorized = categorize_events(events)
    
    print("=" * 70)
    print("SUMMARY BY CATEGORY")
    print("=" * 70)
    
    for category, cat_events in categorized.items():
        if cat_events:
            print(f"\n{category}: {len(cat_events)} events")
            for e in cat_events:
                print(f"  • {e['title']}")
                print(f"    ${e['volume']:,.0f} | {len(e['markets'])} markets")
    
    # Save to JSON
    output = {
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'categories': categorized,
        'total_events': len(events)
    }
    
    os.makedirs('./data', exist_ok=True)
    filename = './data/polymarket-trends.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 70)
    print(f"✓ Saved to: {filename}")
    print(f"Total events: {len(events)}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
