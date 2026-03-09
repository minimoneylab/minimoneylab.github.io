#!/usr/bin/env python3
"""
Vietnam Daily News Scraper
Scrapes financial news from CafeF.vn
Filters to only include articles from the past 24 hours
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

# Vietnam timezone (UTC+7)
VN_TIMEZONE = timezone(timedelta(hours=7))

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "site_name": "CafeF",
    
    # News sections to scrape
    "sections": [
        {"name": "Tài chính ngân hàng", "url": "https://cafef.vn/tai-chinh-ngan-hang.chn"},  # Banking/finance/FX
        {"name": "Kinh tế vĩ mô", "url": "https://cafef.vn/vi-mo.chn"},  # Macro economy
        {"name": "Thị trường", "url": "https://cafef.vn/thi-truong.chn"},  # Markets
    ],
    
    "articles_per_section": 15,  # Maximum relevant articles to scrape per section
    
    # Vietnamese financial keywords - articles must contain at least one
    "financial_keywords": [
        # Banking & Finance
        "ngân hàng", "lãi suất", "tiền gửi", "tín dụng", "nợ xấu", "npl",
        "bidv", "vietcombank", "techcombank", "acb", "mbbank", "vpbank",
        
        # FX & Monetary Policy
        "tỷ giá", "vnd", "usd", "ngoại tệ", "dự trữ ngoại hối",
        "nhnn", "ngân hàng nhà nước", "chính sách tiền tệ",
        
        # Markets & Bonds
        "trái phiếu", "lãi suất trái phiếu", "tăng trưởng tín dụng",
        "vn-index", "chứng khoán", "cổ phiếu ngân hàng",
        
        # Economic indicators
        "lạm phát", "gdp", "cán cân thương mại", "xuất khẩu", "nhập khẩu",
        "vốn đầu tư nước ngoài", "fdi", "remittance", "kiều hối"
    ],
    
    # Time filter: only articles from past 24 hours
    "filter_hours": 24,
    
    # Google Sheets settings
    "credentials_file": "credentials.json",
    "token_file": "token.pickle",
    "sheet_name": "News Scraper Database",
    "raw_articles_tab": "Vietnam Raw Articles",
    
    # Local backup
    "output_dir": "./news_output",
    "page_timeout": 60000,
}

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]


# ============================================================================
# NEWS SCRAPER
# ============================================================================

class NewsAutomation:
    def __init__(self, config):
        self.config = config
        self.articles = []
        self.scrape_time = datetime.now(VN_TIMEZONE)
        self.cutoff_time = self.scrape_time - timedelta(hours=config.get('filter_hours', 0))
    
    def is_article_recent(self, article_date_str):
        """Check if article is within the time window (past 24 hours)"""
        if self.config.get('filter_hours', 0) == 0:
            return True
        
        try:
            # CafeF date format: "07/03/2026 - 14:30" or similar
            # Try different formats
            for fmt in ['%d/%m/%Y - %H:%M', '%d/%m/%Y %H:%M', '%d/%m/%Y']:
                try:
                    article_dt = datetime.strptime(article_date_str.strip(), fmt)
                    article_dt = article_dt.replace(tzinfo=VN_TIMEZONE)
                    break
                except:
                    continue
            else:
                # If no format worked, try to parse just the date
                print(f"   Warning: Could not parse date '{article_date_str}'")
                return True
            
            is_recent = article_dt >= self.cutoff_time
            
            if not is_recent:
                hours_old = (self.scrape_time - article_dt).total_seconds() / 3600
                print(f"   Skipping old article ({hours_old:.1f}h old)")
            
            return is_recent
            
        except Exception as e:
            print(f"   Warning: Date parse error '{article_date_str}': {e}")
            return True

    def filter_relevant_articles(self, articles_with_titles):
        """Filter articles based on financial keywords in titles"""
        keywords = self.config.get("financial_keywords", [])
        if not keywords:
            # No filtering if no keywords defined
            return articles_with_titles
        
        relevant = []
        for url, title in articles_with_titles:
            title_lower = title.lower()
            
            # Check if title contains any financial keyword
            if any(keyword.lower() in title_lower for keyword in keywords):
                relevant.append((url, title))
        
        return relevant

    async def scrape_article(self, page, url):
        """Scrape individual article content"""
        try:
            # Get article title
            title_elem = await page.query_selector('h1.title, h1.detail-title, h1')
            title = await title_elem.inner_text() if title_elem else 'No title'
            
            # Get article date - CafeF only shows time, so we add today's date
            date_elem = await page.query_selector('span.date, span.time, time, .publish-date')
            time_str = await date_elem.inner_text() if date_elem else ''
            
            # Add full date (Vietnam timezone)
            vn_now = datetime.now(VN_TIMEZONE)
            if time_str.strip():
                # Format: "DD/MM/YYYY HH:MM" 
                date = f"{vn_now.strftime('%d/%m/%Y')} {time_str.strip()}"
            else:
                date = vn_now.strftime('%d/%m/%Y %H:%M')
            
            # Get article content
            content_elem = await page.query_selector('.detail-content, .content-detail, article')
            if content_elem:
                # Get all paragraphs
                paragraphs = await content_elem.query_selector_all('p')
                content_parts = []
                for p in paragraphs[:10]:  # First 10 paragraphs
                    text = await p.inner_text()
                    if text.strip():
                        content_parts.append(text.strip())
                content = ' '.join(content_parts)
            else:
                content = 'No content'
            
            return {
                'title': title.strip(),
                'date': date.strip(),
                'content': content[:2000] if content else 'No content'  # Limit length
            }
            
        except Exception as e:
            return {
                'title': 'Error',
                'date': '',
                'content': 'No content'
            }

    async def get_article_links(self, page, section_url):
        """Extract article links with titles from section page"""
        try:
            await page.goto(section_url, wait_until='domcontentloaded', timeout=self.config["page_timeout"])
            await page.wait_for_timeout(3000)
            
            # Get all links on the page
            all_links = await page.query_selector_all('a')
            
            articles = []  # List of (url, title) tuples
            for elem in all_links:
                href = await elem.get_attribute('href')
                if href:
                    # Convert relative URLs to absolute
                    if href.startswith('/') and not href.startswith('//'):
                        href = 'https://cafef.vn' + href
                    
                    # CafeF article URLs end with .chn and contain long numbers
                    if (href.startswith('https://cafef.vn/') and 
                        href.endswith('.chn') and 
                        any(char.isdigit() for char in href[-20:]) and
                        len(href) > 50):
                        
                        # Get the link text (title)
                        title = await elem.inner_text()
                        title = title.strip() if title else ""
                        
                        if title:  # Only add if we got a title
                            articles.append((href, title))
            
            # Remove duplicates while preserving order
            unique_articles = []
            seen = set()
            for url, title in articles:
                if url not in seen:
                    unique_articles.append((url, title))
                    seen.add(url)
            
            return unique_articles
            
        except Exception as e:
            print(f"Error getting links: {e}")
            return []

    async def scrape_news(self):
        """Main scraping function"""
        print()
        print("=" * 70)
        print("SCRAPING NEWS FROM CAFEF.VN")
        print("=" * 70)
        
        async with async_playwright() as p:
            browser = None
            try:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                for section in self.config["sections"]:
                    section_name = section["name"]
                    section_url = section["url"]
                    limit = self.config["articles_per_section"]
                    
                    print()
                    print("-" * 60)
                    print(f"Section: {section_name}")
                    print("-" * 60)

                    articles_with_titles = await self.get_article_links(page, section_url)
                    print(f"Found {len(articles_with_titles)} total articles")
                    
                    # Filter by financial keywords
                    relevant_articles = self.filter_relevant_articles(articles_with_titles)
                    print(f"Filtered to {len(relevant_articles)} relevant articles (by title keywords)")
                    
                    if relevant_articles and len(relevant_articles) > 0:
                        print("\nRelevant articles found:")
                        for url, title in relevant_articles[:5]:
                            print(f"  • {title[:70]}...")
                    print()

                    section_count = 0
                    limit = min(len(relevant_articles), self.config["articles_per_section"])
                    
                    for i, (link, title_preview) in enumerate(relevant_articles[:limit], 1):
                        try:
                            print(f"[{i}/{limit}] Scraping: {title_preview[:50]}...")
                            
                            try:
                                await page.goto(link, wait_until='domcontentloaded', timeout=30000)
                                await page.wait_for_timeout(2000)

                                article_data = await self.scrape_article(page, link)

                                if article_data['content'] != 'No content' and len(article_data['content']) > 100:
                                    # Check if article is within time window
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
                                        print(f"   Too old: {article_data['title'][:50]}")
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
                print(f"Browser error: {e}")
            finally:
                if browser:
                    try:
                        await browser.close()
                    except:
                        pass

        print("=" * 70)
        filter_hours = self.config.get('filter_hours', 0)
        if filter_hours > 0:
            print(f"Time window: Past {filter_hours} hours")
            print(f"Cutoff: {self.cutoff_time.strftime('%Y-%m-%d %H:%M')} VN")
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
                "vietnam_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".json"
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
# MAIN
# ============================================================================

async def main():
    print()
    print("=" * 70)
    print("VIETNAM NEWS SCRAPER (CAFEF.VN)")
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
        
        url = sheets.spreadsheet.url
        print("=" * 70)
        print("SUCCESS!")
        print("=" * 70)
        print(f"Google Sheet: {url}")
        print(f"Tab: {CONFIG['raw_articles_tab']}")
        print(f"Total articles saved: {len(automation.articles)}")
        print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
