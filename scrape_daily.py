#!/usr/bin/env python3
"""
STEP 1: Daily News Scraper
Scrapes news from UDN Money and saves RAW articles to Google Sheets
Run this ONCE per day (morning)
No AI API needed - completely free!
"""

import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime
import os
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "site_name": "UDN Money",
    
    # News sections to scrape
    "sections": [
        {"name": "金融", "url": "https://money.udn.com/money/cate/5591"},
        {"name": "產經", "url": "https://money.udn.com/money/cate/5612"},
        {"name": "證券", "url": "https://money.udn.com/money/cate/5590"},
    ],
    
    "articles_per_section": 10,  # 10 x 3 = 30 articles per day
    
    # Google Sheets settings
    "credentials_file": "credentials.json",
    "token_file": "token.pickle",
    "sheet_name": "News Scraper Database",
    "raw_articles_tab": "Raw Articles",
    
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
        self.sheet = None
        self.existing_urls = set()

    def authenticate(self):
        creds = None
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
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

            # Open or create spreadsheet
            try:
                self.spreadsheet = self.client.open(self.sheet_name)
            except gspread.exceptions.SpreadsheetNotFound:
                self.spreadsheet = self.client.create(self.sheet_name)

            # Get or create Raw Articles tab
            try:
                self.sheet = self.spreadsheet.worksheet(self.tab_name)
                print("Found tab: " + self.tab_name)
            except gspread.exceptions.WorksheetNotFound:
                self.sheet = self.spreadsheet.add_worksheet(
                    title=self.tab_name,
                    rows=5000,
                    cols=8
                )
                print("Created tab: " + self.tab_name)

            print()
            return True

        except Exception as e:
            print("Sheets error: " + str(e))
            return False

    def setup_headers(self):
        """Setup column headers"""
        try:
            first_row = self.sheet.row_values(1)
            if not first_row or first_row[0] != 'Scraped Date':
                print("Setting up headers...")
                headers = [
                    'Scraped Date',
                    'Source',
                    'Section',
                    'Title',
                    'Article Date',
                    'URL',
                    'Content',
                    'Status'
                ]
                self.sheet.update([headers], 'A1:H1')
                self.sheet.format('A1:H1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                })
                print("Headers created!")
        except Exception as e:
            print("Header error: " + str(e))

    def load_existing_urls(self):
        """Load existing URLs to avoid duplicates"""
        try:
            print("Checking for existing articles...")
            all_values = self.sheet.get_all_values()
            
            for row in all_values[1:]:  # Skip header
                if len(row) > 5 and row[5]:
                    url = row[5].split('?')[0]  # Normalize URL
                    self.existing_urls.add(url)
            
            print("Found " + str(len(self.existing_urls)) + " existing articles")
            print()
            
        except Exception as e:
            print("Warning: " + str(e))
            print()

    def is_duplicate(self, url):
        """Check if URL already exists"""
        clean_url = url.split('?')[0]
        return clean_url in self.existing_urls

    def add_articles(self, articles, source_name):
        """Add new articles to sheet"""
        if not articles:
            return 0

        # Filter duplicates
        new_articles = []
        skipped = 0
        
        for article in articles:
            if self.is_duplicate(article.get('url', '')):
                skipped += 1
            else:
                new_articles.append(article)
                clean_url = article.get('url', '').split('?')[0]
                self.existing_urls.add(clean_url)

        print("------------------------------------------------------------")
        print("Total scraped:    " + str(len(articles)))
        print("Already in sheet: " + str(skipped))
        print("New articles:     " + str(len(new_articles)))
        print("------------------------------------------------------------")
        print()

        if not new_articles:
            print("No new articles to save!")
            return 0

        try:
            rows = []
            for article in new_articles:
                row = [
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    source_name,
                    article.get('section', ''),
                    article.get('title', ''),
                    article.get('date', ''),
                    article.get('url', ''),
                    article.get('content', '')[:10000],  # Limit content length
                    'New'  # Status column
                ]
                rows.append(row)

            self.sheet.append_rows(rows)
            print("Saved " + str(len(new_articles)) + " new articles!")
            print()
            return len(new_articles)

        except Exception as e:
            print("Save error: " + str(e))
            return 0

    def get_sheet_url(self):
        try:
            return self.spreadsheet.url
        except:
            return None


# ============================================================================
# NEWS SCRAPER
# ============================================================================

class NewsAutomation:
    def __init__(self, config):
        self.config = config
        self.articles = []
        os.makedirs(config["output_dir"], exist_ok=True)

    async def get_article_links(self, page, section_url):
        await page.goto(section_url, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        links = await page.evaluate("""
            (function() {
                var links = [];
                var allLinks = document.querySelectorAll('a[href]');
                for (var i = 0; i < allLinks.length; i++) {
                    var href = allLinks[i].href;
                    if (href.indexOf('/money/story/') !== -1) {
                        var found = false;
                        for (var j = 0; j < links.length; j++) {
                            if (links[j] === href) { found = true; break; }
                        }
                        if (!found) links.push(href);
                    }
                }
                return links;
            })()
        """)
        return links

    async def scrape_article(self, page, url):
        title = await page.evaluate("""
            (function() {
                var el = document.querySelector('h1.article-content__title');
                if (!el) el = document.querySelector('h1');
                return el ? el.textContent.trim() : 'No title';
            })()
        """)
        
        date = await page.evaluate("""
            (function() {
                var el = document.querySelector('time');
                if (!el) el = document.querySelector('.article-content__time');
                if (!el) return 'Unknown';
                return el.textContent.trim() || el.getAttribute('datetime') || 'Unknown';
            })()
        """)
        
        content = await page.evaluate("""
            (function() {
                var selectors = [
                    '.article-content__paragraph p',
                    'article p',
                    '.article-body p',
                    'p'
                ];
                for (var i = 0; i < selectors.length; i++) {
                    var elements = document.querySelectorAll(selectors[i]);
                    var texts = [];
                    for (var j = 0; j < elements.length; j++) {
                        var text = elements[j].textContent.trim();
                        if (text.length > 20) texts.push(text);
                    }
                    if (texts.length > 0) return texts.join('\\n\\n');
                }
                return 'No content';
            })()
        """)
        
        return {'title': title, 'date': date, 'content': content}

    async def scrape_news(self):
        print()
        print("=" * 70)
        print("SCRAPING NEWS FROM UDN MONEY")
        print("=" * 70)
        print()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            page.set_default_timeout(self.config['page_timeout'])

            try:
                for section in self.config['sections']:
                    section_name = section['name']
                    section_url = section['url']
                    limit = self.config['articles_per_section']

                    print("------------------------------------------------------------")
                    print("Section: " + section_name)
                    print("------------------------------------------------------------")

                    links = await self.get_article_links(page, section_url)
                    print("Found " + str(len(links)) + " articles")
                    print()

                    section_count = 0
                    for i, link in enumerate(links[:limit], 1):
                        try:
                            print("[" + str(i) + "/" + str(min(len(links), limit)) + "] Scraping...")
                            
                            # Add individual timeout wrapper
                            try:
                                await page.goto(link, wait_until='domcontentloaded', timeout=30000)
                                await page.wait_for_timeout(2000)

                                article_data = await self.scrape_article(page, link)

                                if article_data['content'] != 'No content' and len(article_data['content']) > 100:
                                    self.articles.append({
                                        'url': link,
                                        'section': section_name,
                                        'title': article_data['title'],
                                        'date': article_data['date'],
                                        'content': article_data['content'],
                                        'scraped_at': datetime.now().isoformat()
                                    })
                                    section_count += 1
                                    print("   OK: " + article_data['title'][:55])
                                else:
                                    print("   No content")
                            except Exception as article_error:
                                print("   Skipped: " + str(article_error)[:50])
                                continue

                            print()
                            await page.wait_for_timeout(2000)

                        except Exception as e:
                            print("   Error: " + str(e)[:80])
                            print()
                            continue

                    print("Scraped " + str(section_count) + " from " + section_name)
                    print()

            except Exception as e:
                print("Fatal error: " + str(e))
            finally:
                try:
                    await browser.close()
                except:
                    pass  # Browser already closed

        print("=" * 70)
        print("Total articles scraped: " + str(len(self.articles)))
        print("=" * 70)
        print()
        return self.articles

    def save_local_backup(self):
        """Save JSON backup locally"""
        if not self.articles:
            return None
            
        filename = os.path.join(
            self.config["output_dir"],
            "scraped_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".json"
        )
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=2)
        
        print("Local backup: " + filename)
        print()
        return filename


# ============================================================================
# MAIN
# ============================================================================

async def main():
    print()
    print("=" * 70)
    print("STEP 1: DAILY NEWS SCRAPER")
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
        
        url = sheets.get_sheet_url()
        if url:
            print("Your Google Sheet: " + url)
            print("Open 'Raw Articles' tab to see the data")

    print()
    print("=" * 70)
    print("SCRAPING COMPLETE!")
    print("Next: Run analyze_news.py to get AI summary")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")
    except Exception as e:
        print("Error: " + str(e))
        import traceback
        traceback.print_exc()
