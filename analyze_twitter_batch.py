#!/usr/bin/env python3
"""
Twitter Analyzer - Uses Claude API to categorize tweets by market impact
IMPROVED: Processes tweets in batches to avoid connection timeouts
"""

import json
import os
from datetime import datetime, timezone
from anthropic import Anthropic

def analyze_tweets_batch(client, tweets_batch):
    """
    Analyze a batch of tweets with Claude API
    """
    
    # Prepare tweets for Claude
    tweets_text = ""
    for i, tweet in enumerate(tweets_batch, 1):
        tweets_text += f"\n{i}. @{tweet['username']} ({tweet['date']})\n"
        tweets_text += f"   {tweet['text']}\n"
    
    prompt = f"""You are a financial market analyst. Analyze these tweets and categorize them by market relevance.

TWEETS TO ANALYZE:
{tweets_text}

TASK:
1. Categorize each tweet into ONE of these categories:
   - **Macro Market**: Fed policy, interest rates, tariffs, inflation, GDP, recession, central bank actions
   - **Stock Market**: Broad market indices (S&P, Nasdaq, Dow), sector rotation, market sentiment, volatility
   - **Specific Stock/Company**: Individual companies, earnings, activist positions, short reports, IPOs
   - **Geopolitics**: Wars, sanctions, elections, international relations affecting markets
   - **Crypto/Commodities**: Bitcoin, crypto, oil, gold, metals, agricultural commodities
   - **Not Relevant**: Personal opinions, non-market tweets, irrelevant content

2. For each RELEVANT tweet (not "Not Relevant"), provide:
   - Category
   - Market impact summary (1-2 sentences)
   - Affected sectors/assets

3. Return ONLY a JSON array:

[
  {{
    "tweet_number": 1,
    "username": "username",
    "text": "original tweet text",
    "date": "tweet date",
    "category": "Macro Market",
    "impact_summary": "Brief market impact explanation",
    "affected_sectors": ["Sector1", "Sector2"]
  }}
]

CRITICAL: 
- Only include market-relevant tweets (exclude "Not Relevant")
- Return ONLY the JSON array, no other text
- Use the exact category names listed above"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    # Extract JSON from response
    response_text = response.content[0].text
    
    # Parse JSON
    try:
        analyzed_tweets = json.loads(response_text)
        return analyzed_tweets
    except json.JSONDecodeError:
        # Try to extract JSON if Claude added explanation
        import re
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            analyzed_tweets = json.loads(json_match.group())
            return analyzed_tweets
        else:
            return []


def analyze_tweets_with_claude(tweets):
    """
    Send tweets to Claude API for categorization
    Processes in batches to avoid timeout
    """
    
    client = Anthropic()
    
    # Process in batches of 20 tweets
    BATCH_SIZE = 20
    all_analyzed = []
    
    total_batches = (len(tweets) + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"Processing {len(tweets)} tweets in {total_batches} batches...")
    print()
    
    for i in range(0, len(tweets), BATCH_SIZE):
        batch = tweets[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        
        print(f"  Batch {batch_num}/{total_batches}: Analyzing {len(batch)} tweets...")
        
        try:
            analyzed = analyze_tweets_batch(client, batch)
            all_analyzed.extend(analyzed)
            print(f"    ✓ Found {len(analyzed)} market-relevant tweets")
        except Exception as e:
            print(f"    ✗ Error: {e}")
            continue
    
    return all_analyzed


def categorize_and_rank(analyzed_tweets):
    """
    Organize tweets by category and rank by importance
    """
    
    categories = {
        'Macro Market': [],
        'Stock Market': [],
        'Specific Stock/Company': [],
        'Geopolitics': [],
        'Crypto/Commodities': []
    }
    
    for tweet in analyzed_tweets:
        category = tweet.get('category', 'Stock Market')
        if category in categories:
            categories[category].append(tweet)
    
    # Sort each category by engagement
    for category in categories:
        categories[category].sort(
            key=lambda x: x.get('likes', 0) + x.get('retweets', 0), 
            reverse=True
        )
    
    return categories


def merge_tweet_data(analyzed_tweets, raw_tweets):
    """
    Merge engagement data from raw tweets into analyzed tweets
    """
    
    # Create lookup dictionary
    raw_lookup = {}
    for tweet in raw_tweets:
        key = f"{tweet['username']}_{tweet['text'][:50]}"
        raw_lookup[key] = tweet
    
    # Merge data
    for tweet in analyzed_tweets:
        key = f"{tweet['username']}_{tweet['text'][:50]}"
        if key in raw_lookup:
            tweet['likes'] = raw_lookup[key].get('likes', 0)
            tweet['retweets'] = raw_lookup[key].get('retweets', 0)
            tweet['url'] = raw_lookup[key].get('url', '')
    
    return analyzed_tweets


def main():
    print("=" * 70)
    print("TWITTER ANALYZER - Claude API Analysis (Batch Processing)")
    print(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'))
    print("=" * 70)
    print()
    
    # Load raw tweets
    try:
        with open('./data/twitter-raw.json', 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        raw_tweets = raw_data.get('tweets', [])
        
        if not raw_tweets:
            print("No tweets found in twitter-raw.json")
            return
        
        print(f"Loaded {len(raw_tweets)} tweets")
        print()
        
        # Analyze with Claude (in batches)
        analyzed_tweets = analyze_tweets_with_claude(raw_tweets)
        
        print()
        print(f"✓ Total market-relevant tweets: {len(analyzed_tweets)}")
        print()
        
        # Merge engagement data
        analyzed_tweets = merge_tweet_data(analyzed_tweets, raw_tweets)
        
        # Categorize and rank
        categories = categorize_and_rank(analyzed_tweets)
        
        # Print summary
        print("CATEGORY BREAKDOWN:")
        for category, tweets in categories.items():
            print(f"  {category}: {len(tweets)} tweets")
        print()
        
        # Prepare final output
        output_data = {
            'update_time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
            'total_analyzed': len(analyzed_tweets),
            'categories': categories
        }
        
        # Save to JSON
        os.makedirs('./data', exist_ok=True)
        output_file = './data/twitter-analyzed.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Saved analyzed tweets to: {output_file}")
        print()
        print("=" * 70)
        print("Next step: View results at twitter-monitor.html")
        print("=" * 70)
        
    except FileNotFoundError:
        print("Error: twitter-raw.json not found. Run scrape_twitter.py first!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
