#!/usr/bin/env python3
"""
STEP 1: Daily News Scraper
Scrapes news from UDN Money and saves RAW articles to Google Sheets
Filters to only include articles from the past 24 hours
Run this ONCE per day (morning)
No AI API needed - completely free!
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

# Hong Kong timezone (UTC+8)
HK_TIMEZONE = timezone(timedelta(hours=8))

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
    
    "articles_per_section": 15,  # Maximum relevant articles to scrape per section
    
    # Taiwan financial keywords - HIGH QUALITY FOCUS
    "financial_keywords": [
        # ========== TIER 1: REGULATORS & GOVERNMENT (HIGHEST PRIORITY) ==========
        "金管會", "FSC", "金融監督管理委員會", "黃天牧", "金管會主委",
        "銀行局", "證期局", "保險局", "檢查局",
        "央行", "中央銀行", "楊金龍", "總裁", "理監事會議",
        "財政部", "國庫署", "賦稅署",
        "行政院", "主計總處", "國發會", "經濟部",
        
        # ========== TIER 1: LIFE INSURANCE COMPANIES (HIGHEST PRIORITY) ==========
        # Top 9 Life Insurers by assets
        "國泰人壽", "富邦人壽", "新光人壽", "南山人壽", "中國人壽",
        "台灣人壽", "全球人壽", "三商美邦", "國華人壽",
        "保德信", "安聯人壽", "宏泰人壽", "遠雄人壽", "元大人壽",
        "壽險業", "人壽保險", "壽險公會", "壽險", "保險業",
        
        # Insurance specific terms
        "壽險資金", "海外投資", "匯兌損益", "避險成本", "外匯價格變動準備金",
        "責任準備金", "淨值比", "RBC", "資本適足率", "清償能力",
        "投資型保單", "利變型", "傳統型", "保費收入", "新契約保費",
        "保單貸款", "解約率", "死差益", "利差益", "費差益",
        
        # ========== TIER 1: FINANCIAL HOLDINGS & BANKS ==========
        # Major financial holdings
        "富邦金", "國泰金", "中信金", "兆豐金", "第一金", "玉山金",
        "元大金", "台新金", "永豐金", "開發金", "合庫金", "華南金",
        
        # Major banks
        "台灣銀行", "土地銀行", "合作金庫", "第一銀行", "華南銀行",
        "彰化銀行", "兆豐銀行", "台灣企銀", "中國輸出入銀行",
        "台北富邦", "國泰世華", "中信銀", "玉山銀", "台新銀",
        
        # Banking terms
        "存款", "放款", "逾放比", "備抵呆帳", "利差", "淨利差",
        "房貸", "企業貸款", "消費金融", "信用卡", "財富管理",
        
        # ========== TIER 2: MONETARY POLICY & MACRO ==========
        "利率", "升息", "降息", "貼放利率", "重貼現率",
        "存款準備率", "公開市場操作", "選擇性信用管制",
        "匯率", "新台幣", "TWD", "USD/TWD", "外匯存底",
        "匯兌", "匯市", "央行干預", "阻升", "阻貶",
        
        # Economic indicators
        "GDP", "經濟成長率", "CPI", "通膨", "通貨膨脹",
        "PMI", "景氣燈號", "景氣對策信號", "領先指標", "同時指標",
        "失業率", "就業", "薪資", "經常帳", "貿易順差", "貿易逆差",
        
        # ========== TIER 2: MARKETS & INVESTORS ==========
        "台股", "加權指數", "台指期", "股市", "證券",
        "外資", "三大法人", "投信", "自營商", "散戶",
        "融資", "融券", "借券", "當沖", "隔日沖",
        "ADR", "台積電ADR", "聯電ADR", "日月光ADR",
        
        # Bond market
        "債券", "公債", "公司債", "金融債", "可轉債",
        "殖利率", "殖利率曲線", "利差", "債市", "天期",
        "十年期公債", "美債", "美國公債", "公債標售",
        
        # ========== TIER 2: KEY LISTED COMPANIES (Selective) ==========
        # Only mega-cap / systemically important
        "台積電", "TSMC", "鴻海", "聯發科", "廣達",
        "台塑", "中鋼", "中華電", "台電", "中油",
        
        # ========== TIER 3: GLOBAL MACRO (Affecting Taiwan) ==========
        "Fed", "聯準會", "FOMC", "Powell", "鮑爾",
        "升息循環", "降息循環", "QE", "QT", "縮表",
        "美元指數", "DXY", "日圓", "歐元", "人民幣",
        
        "油價", "原油", "WTI", "布蘭特", "OPEC",
        "黃金", "金價", "避險", "通膨預期",
        
        "戰爭", "地緣政治", "衝突", "制裁", "關稅",
        "中東", "伊朗", "以色列", "俄烏", "台海",
        "中美", "美中", "貿易戰", "科技戰", "脫鉤",
        
        # ========== TIER 3: FINTECH & NEW REGULATIONS ==========
        "純網銀", "樂天銀行", "將來銀行", "LINE Bank",
        "開放銀行", "API", "數位金融", "金融科技", "FinTech",
        "穩定幣", "CBDC", "數位貨幣", "虛擬資產", "加密貨幣",
        "比特幣", "以太幣", "區塊鏈", "DeFi",
        
        # ========== TIER 3: MARKET EVENTS ==========
        "MSCI", "權重", "調整", "納入", "剔除",
        "除權", "除息", "配息", "股利", "現金股利",
        "增資", "減資", "合併", "收購", "下市", "私有化",
        "董事會", "股東會", "法說會", "重訊", "停牌"
    ],
    
    # Time filter: only articles from past 36 hours
    "filter_hours": 36,  # Captures full previous day + early morning articles
    
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
    
    def delete_old_articles(self, hours_to_keep=48):
        """Delete articles older than specified hours"""
        try:
            print(f"Deleting articles older than {hours_to_keep} hours...")
            
            all_values = self.sheet.get_all_values()
            if len(all_values) <= 1:
                print("No articles to clean")
                return
            
            # Current time in HK timezone
            now = datetime.now(timezone(timedelta(hours=8)))
            cutoff = now - timedelta(hours=hours_to_keep)
            
            rows_to_delete = []
            
            # Check each row (skip header)
            for idx, row in enumerate(all_values[1:], start=2):  # Start from row 2
                if len(row) > 3 and row[3]:  # Date column
                    try:
                        # Parse date: "2026/03/07 13:41:03"
                        article_dt = datetime.strptime(row[3], '%Y/%m/%d %H:%M:%S')
                        article_dt = article_dt.replace(tzinfo=timezone(timedelta(hours=8)))
                        
                        if article_dt < cutoff:
                            rows_to_delete.append(idx)
                    except:
                        continue
            
            if rows_to_delete:
                # Delete from bottom to top to avoid row number changes
                rows_to_delete.reverse()
                for row_num in rows_to_delete:
                    self.sheet.delete_rows(row_num)
                
                print(f"✓ Deleted {len(rows_to_delete)} old articles")
            else:
                print("No old articles to delete")
            
            print()
            
        except Exception as e:
            print(f"Warning: Could not delete old articles: {e}")
            print()

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
        self.scrape_time = datetime.now(HK_TIMEZONE)
        self.cutoff_time = self.scrape_time - timedelta(hours=config.get('filter_hours', 0))
    
    def is_article_recent(self, article_date_str):
        """Check if article is within the time window (past 30 hours)"""
        if self.config.get('filter_hours', 0) == 0:
            return True  # No filtering
        
        try:
            # Parse article date: "2026/03/04 12:30:15" format
            article_dt = datetime.strptime(article_date_str, '%Y/%m/%d %H:%M:%S')
            # Make timezone-aware (assume HK time)
            article_dt = article_dt.replace(tzinfo=HK_TIMEZONE)
            
            # Check if article is newer than cutoff
            is_recent = article_dt >= self.cutoff_time
            
            if not is_recent:
                hours_old = (self.scrape_time - article_dt).total_seconds() / 3600
                print(f"   Skipping old article ({hours_old:.1f}h old)")
                print(f"   Too old: {article_date_str}")
            
            return is_recent
            
        except Exception as e:
            print(f"   Warning: Could not parse date '{article_date_str}': {e}")
            return False  # REJECT if we can't parse - safer approach
        os.makedirs(config["output_dir"], exist_ok=True)

    async def get_article_links(self, page, section_url):
        await page.goto(section_url, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        articles = await page.evaluate("""
            (function() {
                var articles = [];
                var allLinks = document.querySelectorAll('a[href]');
                for (var i = 0; i < allLinks.length; i++) {
                    var href = allLinks[i].href;
                    if (href.indexOf('/money/story/') !== -1) {
                        var title = allLinks[i].textContent.trim();
                        if (title && title.length > 5) {
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

    def filter_relevant_articles(self, articles_with_titles):
        """Filter articles based on financial keywords in titles"""
        keywords = self.config.get("financial_keywords", [])
        if not keywords:
            # No filtering if no keywords defined
            return articles_with_titles
        
        relevant = []
        for article in articles_with_titles:
            url = article['url']
            title = article['title']
            title_lower = title.lower()
            
            # Check if title contains any financial keyword
            if any(keyword in title for keyword in keywords):
                relevant.append(article)
        
        return relevant

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

                    articles_with_titles = await self.get_article_links(page, section_url)
                    print("Found " + str(len(articles_with_titles)) + " total articles")
                    
                    # 金融 section: Scrape ALL (already curated by UDN)
                    # 產經/證券: Filter by keywords (reduce noise)
                    if section_name == "金融":
                        relevant_articles = articles_with_titles
                        print("Scraping ALL articles from 金融 (pre-curated financial news)")
                    else:
                        relevant_articles = self.filter_relevant_articles(articles_with_titles)
                        print("Filtered to " + str(len(relevant_articles)) + " relevant articles (by title keywords)")
                    
                    if relevant_articles and len(relevant_articles) > 0:
                        print("\nRelevant articles found:")
                        for article in relevant_articles[:5]:
                            print("  • " + article['title'][:70] + "...")
                    print()

                    section_count = 0
                    limit = min(len(relevant_articles), self.config['articles_per_section'])
                    
                    for i, article in enumerate(relevant_articles[:limit], 1):
                        link = article['url']
                        title_preview = article['title']
                        try:
                            print("[" + str(i) + "/" + str(limit) + "] Scraping: " + title_preview[:50] + "...")
                            
                            # Add individual timeout wrapper
                            try:
                                await page.goto(link, wait_until='domcontentloaded', timeout=30000)
                                await page.wait_for_timeout(2000)

                                article_data = await self.scrape_article(page, link)

                                if article_data['content'] != 'No content' and len(article_data['content']) > 100:
                                    # Check if article is within time window (past 24 hours)
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
                                        print("   OK: " + article_data['title'][:55])
                                    else:
                                        print("   Too old: " + article_data['title'][:50])
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
        filter_hours = self.config.get('filter_hours', 0)
        if filter_hours > 0:
            print(f"Time window: Past {filter_hours} hours")
            print(f"Cutoff: {self.cutoff_time.strftime('%Y-%m-%d %H:%M')} HK")
        print("Total articles scraped: " + str(len(self.articles)))
        print("=" * 70)
        print()
        return self.articles

    def save_local_backup(self):
        """Save JSON backup locally"""
        if not self.articles:
            return None
        
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.config["output_dir"], exist_ok=True)
            
            filename = os.path.join(
                self.config["output_dir"],
                "scraped_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".json"
            )
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.articles, f, ensure_ascii=False, indent=2)
            
            print("Local backup: " + filename)
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
        sheets.delete_old_articles(hours_to_keep=48)  # Clean up articles older than 48 hours
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
