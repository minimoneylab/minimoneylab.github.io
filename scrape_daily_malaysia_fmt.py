#!/usr/bin/env python3
"""
Daily News Scraper for Malaysia - Free Malaysia Today (FMT)
Scrapes Local Business section for Malaysian market news
Uses OAuth authentication (same as Vietnam)
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
import time

# Google Sheets setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

CONFIG = {
    "credentials_file": "credentials.json",
    "token_file": "token.pickle",
    "sheet_name": "News Scraper Database",  # Same as Vietnam/Brazil
    "raw_articles_tab": "Malaysia Raw Articles",
}

def authenticate_google_sheets():
    """Authenticate using OAuth (exact same as Vietnam)"""
    creds = None
    if os.path.exists(CONFIG["token_file"]):
        try:
            with open(CONFIG["token_file"], 'rb') as token:
                creds = pickle.load(token)
        except (EOFError, pickle.UnpicklingError) as e:
            print(f"Warning: Token file corrupted ({e}), will try to use anyway")
            # File is empty or corrupted, continue without creds
            creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CONFIG["credentials_file"], SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(CONFIG["token_file"], 'wb') as token:
            pickle.dump(creds, token)
    return creds

def setup_google_sheets():
    """Setup Google Sheets connection"""
    try:
        print("Connecting to Google Sheets...")
        creds = authenticate_google_sheets()
        client = gspread.authorize(creds)
        spreadsheet = client.open(CONFIG["sheet_name"])
        print(f"Connected to: {CONFIG['sheet_name']}")
        print()
        return client, spreadsheet
    except Exception as e:
        print(f"Connection error: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return None, None

def setup_worksheet(spreadsheet):
    """Setup worksheet with headers"""
    try:
        sheet = spreadsheet.worksheet(CONFIG["raw_articles_tab"])
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(
            title=CONFIG["raw_articles_tab"],
            rows=1000,
            cols=7
        )
        headers = ['Scraped Date', 'Source', 'Title', 'Date', 'URL', 'Summary', 'Category']
        sheet.update([headers], 'A1:G1')
        sheet.format('A1:G1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.2, 'green': 0.5, 'blue': 0.9}
        })
    
    return sheet

def get_existing_urls(sheet):
    """Load existing URLs to avoid duplicates"""
    try:
        all_values = sheet.get_all_values()
        existing_urls = set()
        if len(all_values) > 1:
            for row in all_values[1:]:
                if len(row) >= 5:
                    existing_urls.add(row[4])  # URL column
        print(f"Loaded {len(existing_urls)} existing URLs")
        return existing_urls
    except Exception as e:
        print(f"Warning: Could not load existing URLs: {e}")
        return set()

def save_articles_to_sheet(sheet, articles, existing_urls):
    """Save new articles to Google Sheets"""
    if not articles:
        print("No articles to save")
        return
    
    try:
        new_articles = []
        for article in articles:
            if article['url'] not in existing_urls:
                row = [
                    datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                    'FMT',
                    article['title'],
                    article['date'],
                    article['url'],
                    article['summary'],
                    article['category']
                ]
                new_articles.append(row)
        
        if new_articles:
            sheet.append_rows(new_articles)
            print(f"✓ Added {len(new_articles)} new articles")
            print(f"  Skipped {len(articles) - len(new_articles)} duplicates")
        else:
            print("All articles are duplicates")
        
        print()
        
    except Exception as e:
        print(f"✗ Error saving articles: {e}")

def scrape_fmt_local_business():
    """Scrape Malaysian business news from FMT Local Business section"""
    
    print("=" * 70)
    print("MALAYSIA NEWS SCRAPER - Free Malaysia Today")
    print(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'))
    print("=" * 70)
    print()
    
    # FMT Local Business section
    url = "https://www.freemalaysiatoday.com/category/category/business/local-business"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"Fetching: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        articles = []
        
        # Find article links in FMT
        # FMT article structure: links in article cards
        article_links = soup.find_all('a', href=lambda x: x and '/category/' in x and x.count('/') >= 5)
        
        print(f"Found {len(article_links)} article links")
        print()
        
        seen_urls = set()
        
        for idx, elem in enumerate(article_links[:25], 1):  # Check first 25 links
            try:
                article_url = elem.get('href', '')
                
                # Skip if already seen
                if article_url in seen_urls:
                    continue
                
                # Make full URL if needed
                if not article_url.startswith('http'):
                    article_url = 'https://www.freemalaysiatoday.com' + article_url
                
                # Only get articles from business/local-business section
                if '/category/business/' not in article_url and '/category/category/business/' not in article_url:
                    continue
                
                seen_urls.add(article_url)
                
                # Get article title
                title = elem.get_text(strip=True)
                
                if not title or len(title) < 10:
                    continue
                
                print(f"  [{len(articles)+1}] {title[:70]}...")
                
                # Try to get article content
                try:
                    article_response = requests.get(article_url, headers=headers, timeout=15)
                    article_soup = BeautifulSoup(article_response.content, 'html.parser')
                    
                    # Get article text/summary - FMT uses article or .entry-content
                    content_div = article_soup.find('article') or article_soup.find('div', class_='entry-content')
                    if content_div:
                        paragraphs = content_div.find_all('p')
                        summary = ' '.join([p.get_text(strip=True) for p in paragraphs[:3]])[:500]
                    else:
                        summary = title
                    
                    # Get date - FMT uses time tag or .post-date
                    date_elem = article_soup.find('time') or article_soup.find('span', class_='post-date')
                    if date_elem:
                        date_str = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
                    else:
                        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                    
                    article_data = {
                        'title': title,
                        'url': article_url,
                        'summary': summary if summary else title,
                        'date': date_str,
                        'category': 'Local Business'
                    }
                    
                    articles.append(article_data)
                    print(f"      ✓ OK")
                    
                    # Get up to 20 articles
                    if len(articles) >= 20:
                        break
                    
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"      ⚠ Could not fetch content: {e}")
                    # Still save the article with basic info
                    article_data = {
                        'title': title,
                        'url': article_url,
                        'summary': title,
                        'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                        'category': 'Local Business'
                    }
                    articles.append(article_data)
                    
                    if len(articles) >= 20:
                        break
                
            except Exception as e:
                print(f"  ✗ Error processing article {idx}: {e}")
                continue
        
        print()
        print(f"✓ Successfully scraped {len(articles)} Malaysian business articles")
        print()
        
        return articles
        
    except Exception as e:
        print(f"✗ Error scraping FMT: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    try:
        # Scrape articles
        articles = scrape_fmt_local_business()
        
        if not articles:
            print("No articles found!")
            return
        
        # Setup Google Sheets
        client, spreadsheet = setup_google_sheets()
        
        if not client or not spreadsheet:
            print("Could not connect to Google Sheets!")
            return
        
        # Setup worksheet
        sheet = setup_worksheet(spreadsheet)
        
        # Load existing URLs
        existing_urls = get_existing_urls(sheet)
        
        # Save articles
        save_articles_to_sheet(sheet, articles, existing_urls)
        
        print()
        print("=" * 70)
        print("SUCCESS!")
        print("=" * 70)
        print(f"Google Sheet: {spreadsheet.url}")
        print(f"Tab: {CONFIG['raw_articles_tab']}")
        print(f"Total articles scraped: {len(articles)}")
        print("=" * 70)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
