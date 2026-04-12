#!/usr/bin/env python3
"""
Twitter Monitor - Selenium Scraper
Works without Twitter API or login - scrapes public tweets using browser automation
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Twitter accounts to monitor
TWITTER_ACCOUNTS = [
    # Policy Makers
    'realDonaldTrump',
    'POTUS',
    'SecYellen',
    'federalreserve',
    # Hedge Funds / Investors
    'BillAckman',
    'muddywatersre',
    'HindenburgRes',
    'CitronResearch',
    'CathieDWood',
    'elonmusk',
    # Economists
    'elerianm',
    'paulkrugman',
    'JustinWolfers',
    'robin_j_brooks',
    # Market Commentators
    'carlquintanilla',
    'jimcramer',
    'RaoulGMI',
    'TheStalwart',
]


def setup_driver():
    """Setup Chrome driver with options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Add user agent
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver


def scrape_user_tweets(driver, username: str, hours: int = 24) -> List[Dict]:
    """
    Scrape recent tweets from a user using Selenium
    """
    tweets = []
    
    try:
        url = f"https://twitter.com/{username}"
        print(f"  Scraping @{username}...")
        
        driver.get(url)
        time.sleep(4)  # Wait for initial page load
        
        # DON'T SCROLL - just get what's visible (most recent tweets)
        # Find all tweet articles (only what's loaded initially)
        tweet_elements = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
        
        # Only process first 5 tweets (guaranteed to be recent)
        for tweet_elem in tweet_elements[:5]:
            try:
                # Get tweet text
                try:
                    text_elem = tweet_elem.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                    text = text_elem.text
                except:
                    continue
                
                # Skip if too short
                if len(text) < 20:
                    continue
                
                # Get timestamp
                try:
                    time_elem = tweet_elem.find_element(By.TAG_NAME, 'time')
                    tweet_time = time_elem.get_attribute('datetime')
                    
                    # CRITICAL: Check if tweet is recent (past 48 hours)
                    from dateutil import parser
                    tweet_date = parser.parse(tweet_time)
                    if tweet_date.tzinfo is None:
                        tweet_date = tweet_date.replace(tzinfo=timezone.utc)
                    
                    now = datetime.now(timezone.utc)
                    age_hours = (now - tweet_date).total_seconds() / 3600
                    
                    # Skip if older than 48 hours
                    if age_hours > 48:
                        print(f"    ⏭ Skipping old tweet from {tweet_time}")
                        continue
                        
                except:
                    # If can't get/parse time, skip it
                    continue
                
                # Get tweet URL
                try:
                    link_elem = tweet_elem.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]')
                    tweet_url = link_elem.get_attribute('href')
                except:
                    tweet_url = f"https://twitter.com/{username}"
                
                # Get engagement metrics (approximate)
                likes = 0
                retweets = 0
                
                try:
                    # Try to get likes/retweets from aria-labels
                    buttons = tweet_elem.find_elements(By.CSS_SELECTOR, '[role="group"] button')
                    for button in buttons:
                        aria_label = button.get_attribute('aria-label') or ''
                        if 'like' in aria_label.lower():
                            # Extract number from "X Likes" or similar
                            import re
                            match = re.search(r'(\d+(?:,\d+)*)', aria_label)
                            if match:
                                likes = int(match.group(1).replace(',', ''))
                        elif 'retweet' in aria_label.lower():
                            match = re.search(r'(\d+(?:,\d+)*)', aria_label)
                            if match:
                                retweets = int(match.group(1).replace(',', ''))
                except:
                    pass
                
                tweets.append({
                    'username': username,
                    'text': text,
                    'url': tweet_url,
                    'date': tweet_time,
                    'likes': likes,
                    'retweets': retweets,
                })
                
            except Exception as e:
                continue
        
        print(f"    ✓ Found {len(tweets)} tweets")
        
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    return tweets


def scrape_all_accounts(hours: int = 24) -> Dict:
    """Scrape all Twitter accounts"""
    
    print("=" * 70)
    print("TWITTER MONITOR - Selenium Scraper")
    print(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'))
    print("=" * 70)
    print()
    print("Setting up Chrome browser...")
    
    driver = setup_driver()
    all_tweets = []
    
    try:
        print(f"Scraping {len(TWITTER_ACCOUNTS)} accounts...")
        print()
        
        for username in TWITTER_ACCOUNTS:
            tweets = scrape_user_tweets(driver, username, hours)
            all_tweets.extend(tweets)
            time.sleep(2)  # Be polite, don't hammer Twitter
        
        print()
        print(f"✓ Total tweets collected: {len(all_tweets)}")
        
    finally:
        driver.quit()
        print("✓ Browser closed")
    
    return {
        'scrape_time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'hours_scraped': hours,
        'total_tweets': len(all_tweets),
        'tweets': all_tweets
    }


def save_raw_tweets(data: Dict):
    """Save raw scraped tweets to JSON"""
    
    os.makedirs('./data', exist_ok=True)
    
    output_file = './data/twitter-raw.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Saved to: {output_file}")


def main():
    try:
        # Scrape tweets from past 24 hours
        data = scrape_all_accounts(hours=24)
        
        # Save raw data
        save_raw_tweets(data)
        
        print()
        print("=" * 70)
        print("Next step: Run analyze_twitter.py to categorize tweets")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
