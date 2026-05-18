#!/usr/bin/env python3
"""
Daily News Scraper for Indonesia - Bisnis.com Market
Scrapes Indonesian business/finance news in Bahasa Indonesia
Uses OAuth authentication (same as Vietnam/Malaysia)
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
    "sheet_name": "News Scraper Database",
    "raw_articles_tab": "Indonesia Raw Articles",
}

def authenticate_google_sheets():
    """Authenticate using OAuth (exact same as Vietnam)"""
    creds = None
    if os.path.exists(CONFIG["token_file"]):
        with open(CONFIG["token_file"], 'rb') as token:
            creds = pickle.load(token)
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
                    'ANTARA News',
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

def scrape_antara_ekonomi():
    """Scrape Indonesian economic news from ANTARA News"""
    
    print("=" * 70)
    print("INDONESIA NEWS SCRAPER - ANTARA News Ekonomi")
    print(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'))
    print("=" * 70)
    print()
    
    # ANTARA News Ekonomi section
    url = "https://www.antaranews.com/ekonomi"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        print(f"Fetching: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        articles = []
        
        # Find article links
        # ANTARA uses links like: https://www.antaranews.com/berita/...
        # Try multiple selectors
        article_links = []
        
        # Method 1: Find all links with /berita/ in href
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            if '/berita/' in href:
                article_links.append(link)
        
        print(f"Found {len(article_links)} article links")
        print()
        
        seen_urls = set()
        
        for idx, elem in enumerate(article_links[:50], 1):  # Check first 50 links
            try:
                article_url = elem.get('href', '')
                
                if not article_url:
                    continue
                
                # Make full URL if needed
                if article_url.startswith('/'):
                    article_url = 'https://www.antaranews.com' + article_url
                elif not article_url.startswith('http'):
                    continue
                
                # Skip if already seen
                if article_url in seen_urls:
                    continue
                
                # Only ekonomi section articles
                if '/berita/' not in article_url or 'antaranews.com' not in article_url:
                    continue
                
                seen_urls.add(article_url)
                
                # Get article title
                # Try to find title in heading tags first
                title_elem = elem.find(['h1', 'h2', 'h3', 'h4'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    title = elem.get_text(strip=True)
                
                if not title or len(title) < 15:
                    continue
                
                print(f"  [{len(articles)+1}] {title[:70]}...")
                
                # Try to get article content
                try:
                    article_response = requests.get(article_url, headers=headers, timeout=15)
                    article_soup = BeautifulSoup(article_response.content, 'html.parser')
                    
                    # Get category from URL or page
                    # Check URL path: /ekonomi/finansial, /ekonomi/bisnis, /ekonomi/bursa
                    category = 'Ekonomi'
                    if '/finansial' in article_url:
                        category = 'Finansial'
                    elif '/bisnis' in article_url:
                        category = 'Bisnis'
                    elif '/bursa' in article_url:
                        category = 'Bursa'
                    
                    # Get article text/summary
                    # ANTARA uses <p> tags in article body
                    paragraphs = article_soup.find_all('p')
                    summary = ' '.join([p.get_text(strip=True) for p in paragraphs[:3] if len(p.get_text(strip=True)) > 20])[:500]
                    
                    if not summary:
                        summary = title
                    
                    # Get date
                    date_elem = article_soup.find('time') or article_soup.find('span', class_='simple-share-date')
                    if date_elem:
                        date_str = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
                    else:
                        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                    
                    article_data = {
                        'title': title,
                        'url': article_url,
                        'summary': summary,
                        'date': date_str,
                        'category': category
                    }
                    
                    articles.append(article_data)
                    print(f"      ✓ OK ({category})")
                    
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
                        'category': 'Ekonomi'
                    }
                    articles.append(article_data)
                    
                    if len(articles) >= 20:
                        break
                
            except Exception as e:
                print(f"  ✗ Error processing article {idx}: {e}")
                continue
        
        print()
        print(f"✓ Successfully scraped {len(articles)} Indonesian economic articles")
        print()
        
        return articles
        
    except Exception as e:
        print(f"✗ Error scraping ANTARA News: {e}")
        import traceback
        traceback.print_exc()
        return []
        return []

def main():
    try:
        # Scrape articles
        articles = scrape_antara_ekonomi()
        
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
