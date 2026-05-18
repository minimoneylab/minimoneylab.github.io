#!/usr/bin/env python3
"""
Daily News Scraper for Indonesia - Detik Finance
Scrapes Indonesian business/finance news using Playwright
Simple approach like Vietnam
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

# Indonesia timezone (UTC+7)
ID_TIMEZONE = timezone(timedelta(hours=7))

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "site_name": "Detik Finance",
    
    # News sections to scrape
    "sections": [
        {"name": "Berita Ekonomi", "url": "https://finance.detik.com/berita-ekonomi-bisnis"},
        {"name": "Bursa & Valas", "url": "https://finance.detik.com/bursa-dan-valas"},
    ],
    
    "articles_per_section": 10,  # Get 10 per section = 20 total
    
    # Time filter: only articles from past 36 hours
    "filter_hours": 36,
    
    # Google Sheets settings
    "credentials_file": "credentials.json",
    "token_file": "token.pickle",
    "sheet_name": "News Scraper Database",
    "raw_articles_tab": "Indonesia Raw Articles",
    
    # Local backup
    "output_dir": "./news_output",
    "page_timeout": 60000,
}

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]


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
                print(f"Warning: Token file corrupted ({e}), will try to use anyway")
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

    def add_articles(self, articles, source_name):
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
                        source_name,
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
# NEWS SCRAPER
# ============================================================================

class NewsAutomation:
    def __init__(self, config):
        self.config = config
        self.articles = []
        self.scrape_time = datetime.now(ID_TIMEZONE)
        self.cutoff_time = self.scrape_time - timedelta(hours=config.get('filter_hours', 0))
    
    def is_article_recent(self, article_date_str):
        """Check if article is within the time window"""
        if self.config.get('filter_hours', 0) == 0:
            return True
        
        try:
            # Detik date format varies - try to parse
            # Try common formats
            for fmt in ['%A, %d %b %Y %H:%M', '%d %b %Y %H:%M', '%d %b %Y']:
                try:
                    article_dt = datetime.strptime(article_date_str.strip(), fmt)
                    article_dt = article_dt.replace(tzinfo=ID_TIMEZONE)
                    break
                except:
                    continue
            else:
                # If parsing fails, include the article
                return True
            
            is_recent = article_dt >= self.cutoff_time
            return is_recent
            
        except Exception as e:
            return True  # Include if can't parse

    async def get_article_links(self, page):
        """Get article links from current page"""
        # Page is already loaded, just extract links
        
        # Detik uses links with /d- in the URL
        articles = await page.evaluate("""
            (function() {
                var articles = [];
                var allLinks = document.querySelectorAll('a[href]');
                for (var i = 0; i < allLinks.length; i++) {
                    var href = allLinks[i].href;
                    // Detik article URLs contain /d-
                    if (href.indexOf('/d-') !== -1 && href.indexOf('finance.detik.com') !== -1) {
                        var title = allLinks[i].textContent.trim();
                        if (title && title.length > 15) {
                            // Check if URL already exists
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
        return articles

    async def scrape_article(self, page, url):
        """Scrape individual article"""
        title = await page.evaluate("""
            (function() {
                var el = document.querySelector('h1');
                return el ? el.textContent.trim() : 'No title';
            })()
        """)
        
        date = await page.evaluate("""
            (function() {
                var el = document.querySelector('.detail__date');
                if (!el) el = document.querySelector('time');
                if (!el) el = document.querySelector('.date');
                return el ? el.textContent.trim() : '';
            })()
        """)
        
        content = await page.evaluate("""
            (function() {
                var elements = document.querySelectorAll('.detail__body-text p, article p, .content p');
                var texts = [];
                for (var i = 0; i < elements.length && i < 5; i++) {
                    var text = elements[i].textContent.trim();
                    if (text.length > 20) texts.push(text);
                }
                return texts.join('\\n\\n');
            })()
        """)
        
        return {'title': title, 'date': date, 'content': content}

    async def scrape_news(self):
        print()
        print("=" * 70)
        print("SCRAPING NEWS FROM DETIK FINANCE")
        print("=" * 70)
        print()

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
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                locale='id-ID'
            )
            page = await context.new_page()
            page.set_default_timeout(90000)  # 90 seconds

            try:
                for section in self.config['sections']:
                    section_name = section['name']
                    section_url = section['url']
                    limit = self.config['articles_per_section']

                    print("-" * 60)
                    print(f"Section: {section_name}")
                    print("-" * 60)

                    try:
                        print(f"Loading: {section_url}")
                        await page.goto(section_url, wait_until='domcontentloaded', timeout=90000)
                        await page.wait_for_timeout(5000)  # Wait longer
                        print("Page loaded!")
                        
                    except Exception as load_error:
                        print(f"Could not load section: {load_error}")
                        print("Skipping this section...")
                        continue

                    articles_with_titles = await self.get_article_links(page)
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

                                article_data = await self.scrape_article(page, link)

                                if article_data['content'] and len(article_data['content']) > 100:
                                    if self.is_article_recent(article_data['date']):
                                        self.articles.append({
                                            'url': link,
                                            'section': section_name,
                                            'title': article_data['title'],
                                            'date': article_data['date'],
                                            'content': article_data['content'],
                                            'scraped_at': self.scrape_time.isoformat()
                                        })
                                        section_count += 1
                                        print(f"   OK: {article_data['title'][:55]}")
                                    else:
                                        print(f"   Too old")
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

            except Exception as e:
                print(f"Fatal error: {e}")
            finally:
                try:
                    await browser.close()
                except:
                    pass

        print("=" * 70)
        filter_hours = self.config.get('filter_hours', 0)
        if filter_hours > 0:
            print(f"Time window: Past {filter_hours} hours")
            print(f"Cutoff: {self.cutoff_time.strftime('%Y-%m-%d %H:%M')} ID")
        print(f"Total articles scraped: {len(self.articles)}")
        print("=" * 70)
        print()
        return self.articles

    def save_local_backup(self):
        """Save JSON backup locally"""
        if not self.articles:
            return None
        
        try:
            os.makedirs(self.config["output_dir"], exist_ok=True)
            
            filename = os.path.join(
                self.config["output_dir"],
                "indonesia_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".json"
            )
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.articles, f, ensure_ascii=False, indent=2)
            
            print(f"Local backup: {filename}")
            print()
            return filename
        except Exception as e:
            print(f"Warning: Could not save local backup: {e}")
            print()
            return None


# ============================================================================
# MAIN
# ============================================================================

async def main():
    print()
    print("=" * 70)
    print("INDONESIA NEWS SCRAPER (DETIK FINANCE)")
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 70)

    # Scrape news
    automation = NewsAutomation(CONFIG)
    await automation.scrape_news()

    if not automation.articles:
        print("No articles scraped.")
        return

    # Save local backup
    automation.save_local_backup()

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
        sheets.add_articles(automation.articles, CONFIG["site_name"])
        
        print()
        print("=" * 70)
        print("SUCCESS!")
        print("=" * 70)
        print(f"Total articles saved: {len(automation.articles)}")
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
