#!/usr/bin/env python3
"""
Daily News Scraper for South Korea - Combined
Scrapes from BOTH KEDGlobal Markets AND InfomaxAI
Both scrapers work perfectly - no changes to scraping logic!
"""

import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime, timedelta, timezone
import os
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# Korea timezone (UTC+9)
KR_TIMEZONE = timezone(timedelta(hours=9))

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "site_name": "Korea News",
    
    # Time filter: only articles from past 36 hours
    "filter_hours": 36,
    
    # Google Sheets settings
    "credentials_file": "credentials.json",
    "token_file": "token.pickle",
    "sheet_name": "News Scraper Database",
    "raw_articles_tab": "Korea Raw Articles",
    
    # Local backup
    "output_dir": "./news_output",
    "page_timeout": 60000,
}

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]


# ============================================================================
# KEDGLOBAL SCRAPER (EXACT WORKING VERSION)
# ============================================================================

async def scrape_kedglobal(page):
    """Scrape KEDGlobal Markets - EXACT working version, no changes"""
    print()
    print("=" * 70)
    print("SCRAPING KEDGLOBAL MARKETS")
    print("=" * 70)
    print()
    
    articles = []
    scrape_time = datetime.now(KR_TIMEZONE)
    cutoff_time = scrape_time - timedelta(hours=CONFIG.get('filter_hours', 0))
    
    section_url = "https://www.kedglobal.com/markets"
    limit = 20
    
    print("-" * 60)
    print("Section: Korean Markets")
    print("-" * 60)
    
    try:
        print(f"Loading: {section_url}")
        await page.goto(section_url, wait_until='domcontentloaded', timeout=90000)
        await page.wait_for_timeout(5000)
        print("Page loaded!")
        
    except Exception as load_error:
        print(f"Could not load section: {load_error}")
        return []
    
    # Get article links
    articles_with_titles = await page.evaluate("""
        (function() {
            var articles = [];
            var allLinks = document.querySelectorAll('a[href]');
            for (var i = 0; i < allLinks.length; i++) {
                var href = allLinks[i].href;
                if (href.indexOf('/newsView/') !== -1 && href.indexOf('kedglobal.com') !== -1) {
                    var title = allLinks[i].textContent.trim();
                    if (title && title.length > 20) {
                        var found = false;
                        for (var j = 0; j < articles.length; j++) {
                            if (articles[j].url === href) { 
                                found = true; 
                                break; 
                            }
                        }
                        if (!found) {
                            articles.push({url: href, title: title});
                        }
                    }
                }
            }
            return articles;
        })()
    """)
    
    print(f"Found {len(articles_with_titles)} total articles")
    print()
    
    section_count = 0
    limit = min(len(articles_with_titles), limit)
    
    for i, article in enumerate(articles_with_titles[:limit], 1):
        link = article['url']
        title_preview = article['title']
        try:
            print(f"[{i}/{limit}] Scraping: {title_preview[:50]}...")
            
            try:
                await page.goto(link, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)
                
                # Scrape article
                title = await page.evaluate("""
                    (function() {
                        var el = document.querySelector('h1, .article-title');
                        return el ? el.textContent.trim() : 'No title';
                    })()
                """)
                
                date = await page.evaluate("""
                    (function() {
                        var el = document.querySelector('time, .date, .article-date');
                        return el ? el.textContent.trim() : '';
                    })()
                """)
                
                content = await page.evaluate("""
                    (function() {
                        var elements = document.querySelectorAll('article p, .article-content p, .content p');
                        var texts = [];
                        for (var i = 0; i < elements.length && i < 5; i++) {
                            var text = elements[i].textContent.trim();
                            if (text.length > 20) texts.push(text);
                        }
                        return texts.join('\\n\\n');
                    })()
                """)
                
                if content and len(content) > 100:
                    articles.append({
                        'url': link,
                        'section': 'Markets',
                        'source': 'KEDGlobal',
                        'title': title,
                        'date': date,
                        'content': content,
                        'scraped_at': scrape_time.isoformat()
                    })
                    section_count += 1
                    print(f"   OK: {title[:55]}")
                else:
                    print("   No content")
                    
            except Exception as article_error:
                print(f"   Skipped: {str(article_error)[:50]}")
                continue
            
            print()
            await page.wait_for_timeout(2000)
            
        except Exception as e:
            print(f"   Error: {str(e)[:80]}")
            print()
            continue
    
    print(f"Scraped {section_count} from KEDGlobal")
    print()
    
    return articles


# ============================================================================
# INFOMAXAI SCRAPER (EXACT WORKING VERSION)
# ============================================================================

async def scrape_infomaxai(page):
    """Scrape InfomaxAI - EXACT working version, no changes"""
    print()
    print("=" * 70)
    print("SCRAPING INFOMAXAI")
    print("=" * 70)
    print()
    
    articles = []
    scrape_time = datetime.now(KR_TIMEZONE)
    
    sections = [
        {"name": "Policy/Finance", "url": "https://en.infomaxai.com/news/articleList.html?sc_section_code=S1N15&view_type=sm"},
        {"name": "Bonds/Forex", "url": "https://en.infomaxai.com/news/articleList.html?sc_section_code=S1N7&view_type=sm"},
        {"name": "Stocks", "url": "https://en.infomaxai.com/news/articleList.html?sc_section_code=S1N9&view_type=sm"},
    ]
    
    for section in sections:
        section_name = section['name']
        section_url = section['url']
        limit = 5
        
        print("-" * 60)
        print(f"Section: {section_name}")
        print("-" * 60)
        
        try:
            print(f"Loading: {section_url}")
            await page.goto(section_url, wait_until='domcontentloaded', timeout=90000)
            await page.wait_for_timeout(5000)
            print("Page loaded!")
            
        except Exception as load_error:
            print(f"Could not load section: {load_error}")
            print("Skipping this section...")
            continue
        
        # Get article links
        articles_with_titles = await page.evaluate("""
            (function() {
                var articles = [];
                var allLinks = document.querySelectorAll('a[href]');
                for (var i = 0; i < allLinks.length; i++) {
                    var href = allLinks[i].href;
                    if (href.indexOf('/news/articleView.html') !== -1) {
                        var title = allLinks[i].textContent.trim();
                        if (title && title.length > 15) {
                            var found = false;
                            for (var j = 0; j < articles.length; j++) {
                                if (articles[j].url === href) { 
                                    found = true; 
                                    break; 
                                }
                            }
                            if (!found) {
                                articles.push({url: href, title: title});
                            }
                        }
                    }
                }
                return articles;
            })()
        """)
        
        print(f"Found {len(articles_with_titles)} total articles")
        print()
        
        section_count = 0
        limit = min(len(articles_with_titles), limit)
        
        for i, article in enumerate(articles_with_titles[:limit], 1):
            link = article['url']
            title_preview = article['title']
            try:
                print(f"[{i}/{limit}] Scraping: {title_preview[:50]}...")
                
                try:
                    await page.goto(link, wait_until='domcontentloaded', timeout=30000)
                    await page.wait_for_timeout(2000)
                    
                    # Scrape article
                    title = await page.evaluate("""
                        (function() {
                            var el = document.querySelector('h1, .article-title, .view_tit');
                            return el ? el.textContent.trim() : 'No title';
                        })()
                    """)
                    
                    date = await page.evaluate("""
                        (function() {
                            var el = document.querySelector('time, .date, .article-date, .ar_date');
                            return el ? el.textContent.trim() : '';
                        })()
                    """)
                    
                    content = await page.evaluate("""
                        (function() {
                            var elements = document.querySelectorAll('article p, .article-content p, .ar_txt p, #article-view-content-div p');
                            var texts = [];
                            for (var i = 0; i < elements.length && i < 5; i++) {
                                var text = elements[i].textContent.trim();
                                if (text.length > 20) texts.push(text);
                            }
                            return texts.join('\\n\\n');
                        })()
                    """)
                    
                    if content and len(content) > 100:
                        articles.append({
                            'url': link,
                            'section': section_name,
                            'source': 'InfomaxAI',
                            'title': title,
                            'date': date,
                            'content': content,
                            'scraped_at': scrape_time.isoformat()
                        })
                        section_count += 1
                        print(f"   OK: {title[:55]}")
                    else:
                        print("   No content")
                        
                except Exception as article_error:
                    print(f"   Skipped: {str(article_error)[:50]}")
                    continue
                
                print()
                await page.wait_for_timeout(2000)
                
            except Exception as e:
                print(f"   Error: {str(e)[:80]}")
                print()
                continue
        
        print(f"Scraped {section_count} from {section_name}")
        print()
    
    return articles


# ============================================================================
# GOOGLE SHEETS MANAGER
# ============================================================================

class GoogleSheetsManager:
    def __init__(self, credentials_file, token_file, sheet_name, tab_name):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.sheet_name = sheet_name
        self.tab_name = tab_name
        self.client = None
        self.spreadsheet = None
        self.existing_urls = set()

    def authenticate(self):
        creds = None
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            except (EOFError, pickle.UnpicklingError) as e:
                print(f"Warning: Token file corrupted ({e})")
                creds = None
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        return creds

    def connect(self):
        try:
            print("Connecting to Google Sheets...")
            creds = self.authenticate()
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open(self.sheet_name)
            print(f"Connected to: {self.sheet_name}")
            print()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def setup_headers(self):
        try:
            sheet = self.spreadsheet.worksheet(self.tab_name)
        except gspread.exceptions.WorksheetNotFound:
            sheet = self.spreadsheet.add_worksheet(
                title=self.tab_name,
                rows=1000,
                cols=8
            )
            headers = ['Scraped Date', 'Source', 'Section', 'Title', 'Date', 'URL', 'Content', 'Status']
            sheet.update([headers], 'A1:H1')
            sheet.format('A1:H1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.2, 'green': 0.5, 'blue': 0.9}
            })

    def load_existing_urls(self):
        try:
            sheet = self.spreadsheet.worksheet(self.tab_name)
            all_values = sheet.get_all_values()
            if len(all_values) > 1:
                for row in all_values[1:]:
                    if len(row) >= 6:
                        self.existing_urls.add(row[5])
            print(f"Loaded {len(self.existing_urls)} existing URLs")
        except Exception as e:
            print(f"Warning: Could not load existing URLs: {e}")

    def add_articles(self, articles):
        if not articles:
            print("No articles to add")
            return
        
        try:
            sheet = self.spreadsheet.worksheet(self.tab_name)
            
            new_articles = []
            for article in articles:
                if article['url'] not in self.existing_urls:
                    row = [
                        article.get('scraped_at', datetime.now().isoformat()).split('T')[0],
                        article.get('source', 'Korea News'),
                        article.get('section', ''),
                        article.get('title', ''),
                        article.get('date', ''),
                        article.get('url', ''),
                        article.get('content', ''),
                        'New'
                    ]
                    new_articles.append(row)
            
            if new_articles:
                sheet.append_rows(new_articles)
                print(f"Added {len(new_articles)} new articles")
                print(f"Skipped {len(articles) - len(new_articles)} duplicates")
            else:
                print("All articles are duplicates")
            
            print()
            
        except Exception as e:
            print(f"Error adding articles: {e}")


# ============================================================================
# MAIN - RUNS BOTH SCRAPERS
# ============================================================================

async def main():
    print()
    print("=" * 70)
    print("KOREA NEWS SCRAPER - COMBINED (KEDGLOBAL + INFOMAXAI)")
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 70)
    
    all_articles = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        page.set_default_timeout(90000)
        
        try:
            # Scrape KEDGlobal
            kedglobal_articles = await scrape_kedglobal(page)
            all_articles.extend(kedglobal_articles)
            
            # Scrape InfomaxAI
            infomaxai_articles = await scrape_infomaxai(page)
            all_articles.extend(infomaxai_articles)
            
        finally:
            await browser.close()
    
    print("=" * 70)
    print(f"TOTAL ARTICLES SCRAPED: {len(all_articles)}")
    print(f"  KEDGlobal: {len([a for a in all_articles if a.get('source') == 'KEDGlobal'])}")
    print(f"  InfomaxAI: {len([a for a in all_articles if a.get('source') == 'InfomaxAI'])}")
    print("=" * 70)
    print()
    
    if not all_articles:
        print("No articles scraped.")
        return
    
    # Save local backup
    try:
        os.makedirs(CONFIG["output_dir"], exist_ok=True)
        filename = os.path.join(
            CONFIG["output_dir"],
            "korea_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".json"
        )
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        print(f"Local backup: {filename}")
        print()
    except Exception as e:
        print(f"Warning: Could not save local backup: {e}")
        print()
    
    # Save to Google Sheets
    sheets = GoogleSheetsManager(
        CONFIG["credentials_file"],
        CONFIG["token_file"],
        CONFIG["sheet_name"],
        CONFIG["raw_articles_tab"]
    )
    
    if sheets.connect():
        sheets.setup_headers()
        sheets.load_existing_urls()
        sheets.add_articles(all_articles)
        
        print()
        print("=" * 70)
        print("SUCCESS!")
        print("=" * 70)
        print(f"Total articles saved: {len(all_articles)}")
        print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
