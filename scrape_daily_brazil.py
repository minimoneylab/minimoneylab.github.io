#!/usr/bin/env python3
"""
Brazil Daily News Scraper - MoneyTimes.com.br
Scrapes financial news about Brazil markets, FX, rates, and central bank
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials
import pickle

# Brazil timezone (UTC-3)
BRAZIL_TZ = timezone(timedelta(hours=-3))

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SPREADSHEET_NAME = "News Scraper Database"  # Same as Vietnam
SHEET_NAME = "Brazil Raw Articles"  # New tab for Brazil

# News source
NEWS_URL = "https://www.moneytimes.com.br/"

# Keywords to filter relevant news
KEYWORDS = [
    # Stock market
    'bovespa', 'b3', 'ibovespa', 'bolsa', 'ações', 'mercado',
    # FX
    'dólar', 'real', 'câmbio', 'forex', 'moeda',
    # Rates & Central Bank
    'selic', 'juros', 'taxa', 'banco central', 'copom', 'bc',
    # Economy
    'inflação', 'ipca', 'pib', 'economia', 'fiscal',
    # Companies
    'petrobras', 'vale', 'itaú', 'bradesco', 'ambev'
]


def authenticate_google():
    """Authenticate with Google Sheets"""
    try:
        # Try to load existing token
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        else:
            # Load from service account
            creds = Credentials.from_service_account_file(
                'credentials.json',
                scopes=SCOPES
            )
        
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Error authenticating: {e}")
        sys.exit(1)


def scrape_moneytimes():
    """Scrape news from MoneyTimes.com.br"""
    print(f"Scraping MoneyTimes.com.br at {datetime.now(BRAZIL_TZ).strftime('%Y-%m-%d %H:%M:%S')} BRT")
    
    articles = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Load homepage with longer timeout
            print(f"Loading {NEWS_URL}")
            page.goto(NEWS_URL, wait_until='domcontentloaded', timeout=60000)  # Changed to domcontentloaded, 60s timeout
            page.wait_for_timeout(3000)  # Wait 3 seconds for dynamic content
            
            # Find article links
            # MoneyTimes structure: articles are typically in <article> tags or specific classes
            # We'll need to inspect the actual page structure
            
            # Try common selectors
            selectors_to_try = [
                '.news-item a',
                'article a[href*="moneytimes.com.br"]',
                '.post a[href]',
                '.article-card a[href]',
                'a.article-link'
            ]
            
            links = []
            for selector in selectors_to_try:
                try:
                    elements = page.query_selector_all(selector)
                    if elements:
                        print(f"✓ Found {len(elements)} links with selector: {selector}")
                        links = elements
                        break
                except:
                    continue
            
            if not links:
                # Fallback: get all links and filter
                print("Using fallback: getting all links")
                links = page.query_selector_all('a[href]')
            
            # Extract article data
            seen_urls = set()
            url_to_title = {}  # Map URL to best title
            
            # First pass: collect all URLs with their titles
            for link in links:
                try:
                    url = link.get_attribute('href')
                    if not url:
                        continue
                    
                    # Filter for article URLs only
                    if 'moneytimes.com.br' not in url:
                        continue
                    if any(skip in url for skip in ['autor/', 'categoria/', 'tag/', 'page/', '/tag/']):
                        continue
                    
                    # Get title
                    title = link.inner_text().strip()
                    
                    # Keep the longest/best title for each URL
                    if url not in url_to_title or len(title) > len(url_to_title[url]):
                        url_to_title[url] = title
                        
                except Exception as e:
                    continue
            
            # Second pass: filter by keywords and build article list
            for url, title in url_to_title.items():
                if not title or len(title) < 15:
                    continue
                
                # Check URL and title for keywords
                text_to_check = (title + ' ' + url).lower()
                
                # More lenient: check if ANY keyword matches
                if not any(kw in text_to_check for kw in KEYWORDS):
                    continue
                
                articles.append({
                    'title': title,
                    'url': url,
                    'source': 'MoneyTimes'
                })
                
                print(f"  ✓ {title[:70]}...")
                
                if len(articles) >= 15:  # Limit to 15 articles
                    break
            
        except Exception as e:
            print(f"Error scraping: {e}")
        finally:
            browser.close()
    
    print(f"\nScraped {len(articles)} relevant articles")
    return articles


def fetch_article_content(url):
    """Fetch full article content"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url, wait_until='networkidle', timeout=20000)
            page.wait_for_timeout(1000)
            
            # Try to find article content
            # Common selectors for Brazilian news sites
            content_selectors = [
                'article .entry-content',
                '.post-content',
                '.article-content',
                'article p',
                '.content p'
            ]
            
            content = ""
            for selector in content_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    if elements:
                        content = '\n'.join([el.inner_text() for el in elements])
                        if len(content) > 100:
                            break
                except:
                    continue
            
            return content[:2000] if content else None  # Limit to 2000 chars
            
        except Exception as e:
            print(f"  Error fetching content: {e}")
            return None
        finally:
            browser.close()


def save_to_sheet(client, articles):
    """Save articles to Google Sheet with retry logic"""
    
    # Retry logic for API errors (503, rate limits, etc.)
    max_retries = 3
    retry_delay = 5  # seconds
    
    spreadsheet = None
    for attempt in range(max_retries):
        try:
            # Open spreadsheet
            spreadsheet = client.open(SPREADSHEET_NAME)
            break  # Success, exit retry loop
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  Attempt {attempt + 1} failed: {e}")
                print(f"  Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"  All {max_retries} attempts failed")
                raise  # Final attempt failed, re-raise error
    
    try:
        # Try to get existing tab, or create it
        try:
            sheet = spreadsheet.worksheet(SHEET_NAME)
            print(f"Using existing tab: {SHEET_NAME}")
        except gspread.exceptions.WorksheetNotFound:
            # Create new tab
            print(f"Creating new tab: {SHEET_NAME}")
            sheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=7)
            # Add headers
            sheet.append_row(['Date', 'Timestamp', 'Title', 'URL', 'Source', 'Content', 'Summary'])
            print(f"✓ Created tab with headers")
        
        # Prepare data
        today = datetime.now(BRAZIL_TZ).strftime('%Y-%m-%d')
        timestamp = datetime.now(BRAZIL_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        rows = []
        for article in articles:
            rows.append([
                today,
                timestamp,
                article['title'],
                article['url'],
                article['source'],
                article.get('content', ''),
                ''  # Summary column (filled by analyze script)
            ])
        
        # Clear today's data and append new
        all_data = sheet.get_all_values()
        header = all_data[0] if all_data else ['Date', 'Timestamp', 'Title', 'URL', 'Source', 'Content', 'Summary']
        
        # Filter out today's old data
        existing = [row for row in all_data[1:] if row[0] != today]
        
        # Update sheet
        sheet.clear()
        sheet.append_row(header)
        if existing:
            sheet.append_rows(existing)
        sheet.append_rows(rows)
        
        print(f"\n✓ Saved {len(rows)} articles to Google Sheet")
        
    except Exception as e:
        print(f"Error saving to sheet: {e}")
        raise


def main():
    print("=" * 70)
    print("BRAZIL DAILY NEWS SCRAPER")
    print(f"{datetime.now(BRAZIL_TZ).strftime('%Y-%m-%d %H:%M:%S')} BRT")
    print("=" * 70)
    print()
    
    # Authenticate
    print("Authenticating with Google...")
    client = authenticate_google()
    print("✓ Authenticated")
    print()
    
    # Scrape news
    articles = scrape_moneytimes()
    
    if not articles:
        print("No articles found!")
        return
    
    # Fetch content for each article
    print("\nFetching article content...")
    for i, article in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {article['title'][:50]}...")
        content = fetch_article_content(article['url'])
        if content:
            article['content'] = content
            print(f"  ✓ Got {len(content)} characters")
        else:
            print(f"  ✗ No content")
    
    # Save to sheet
    print("\nSaving to Google Sheet...")
    save_to_sheet(client, articles)
    
    print("\n" + "=" * 70)
    print("SCRAPING COMPLETE")
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
        sys.exit(1)
