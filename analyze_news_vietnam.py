#!/usr/bin/env python3
"""
Vietnam News Analyzer
Reads Vietnamese articles from Google Sheets and uses Claude to analyze
Focuses on FX market, yields, and capital flows
Outputs in ENGLISH
"""

import os
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from anthropic import Anthropic
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    # Claude API
    "claude_api_key": os.environ.get('CLAUDE_API_KEY', 'PASTE_YOUR_CLAUDE_API_KEY_HERE'),
    
    # Google Sheets
    "credentials_file": "credentials.json",
    "token_file": "token.pickle",
    "sheet_name": "News Scraper Database",
    "raw_articles_tab": "Vietnam Raw Articles",
    "digest_tab": "Vietnam Daily Digest",
    
    # Analysis settings
    "max_articles_to_analyze": 0,  # 0 = all new articles
    
    # Output
    "output_dir": "./news_output",
}

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]


# ============================================================================
# PROMPT BUILDER
# ============================================================================

def build_prompt(articles):
    """Build Vietnam-focused analysis prompt"""
    
    articles_text = ""
    for i, article in enumerate(articles, 1):
        articles_text += "---\n"
        articles_text += f"Article {i}\n"
        articles_text += f"Section: {article['section']}\n"
        articles_text += f"Title: {article['title']}\n"
        articles_text += f"Date: {article['date']}\n"
        articles_text += f"URL: {article['url']}\n"
        articles_text += f"Content: {article['content'][:1000]}\n\n"

    prompt = f"""You are a senior emerging markets analyst specializing in Vietnam's 
financial markets, FX dynamics, and monetary policy.

Your job is to review Vietnamese financial news and produce a professional daily 
briefing for an international fund manager who trades Vietnamese Dong (VND), 
Vietnamese government bonds, and Vietnamese equities.

IMPORTANT: 
- The articles are in VIETNAMESE but you MUST write ALL summaries in ENGLISH
- Translate Vietnamese article titles to English
- All analysis and commentary must be in ENGLISH

Below are {len(articles)} news articles from CafeF.vn.

CRITICAL RULES:
- Use ONLY the exact URLs provided in the article data above
- DO NOT modify, shorten, or make up URLs
- Copy the URL exactly as it appears for each article
- Filter articles based on relevance to the topics below
- Write ALL content in ENGLISH (translate titles and summaries from Vietnamese)

RELEVANT TOPICS (ONLY summarize articles about these):
- **VND/USD exchange rate** and FX market dynamics
- **State Bank of Vietnam (SBV)** monetary policy, intervention, reserve management
- **Interest rates** (policy rate, deposit rates, lending rates)
- **Vietnamese government bond yields** and bond market
- **Capital flows** (foreign investment inflows/outflows, remittances)
- **Inflation** and its impact on FX and rates
- **Trade balance** and current account
- **VN-Index** and Ho Chi Minh Stock Exchange
- **Banking sector** regulations and developments
- **Foreign reserves** and balance of payments

NOT RELEVANT (skip these):
- Individual company earnings (unless major banks or FX-related)
- Real estate development projects
- Retail/consumer news
- Technology startups
- General business news

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:

═══════════════════════════════════════
🔴 HIGH IMPORTANCE
═══════════════════════════════════════

**[Translated English Title]**
📂 Section: [section] | 📅 Date: [date]
🔗 [EXACT URL - copy it completely from the data]

[Thorough English summary up to 200 words. Explain:
- What happened with VND/USD, yields, or policy?
- Why it matters for FX traders and bond investors?
- Market implications and what to watch next]

---

═══════════════════════════════════════
🟡 MEDIUM IMPORTANCE
═══════════════════════════════════════

**[Translated English Title]**
📂 Section: [section] | 📅 Date: [date]
🔗 [EXACT URL]

[3-5 sentence English summary covering key points and relevance to VND, yields, or markets]

---

═══════════════════════════════════════
⚪ NOT RELEVANT
═══════════════════════════════════════
[List only English-translated titles of irrelevant articles]

═══════════════════════════════════════
📊 DAILY STATS
═══════════════════════════════════════
- Total articles reviewed: [X]
- High importance: [X]
- Medium importance: [X]
- Not relevant: [X]
- Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
═══════════════════════════════════════

HERE ARE THE ARTICLES:

{articles_text}"""

    return prompt


# ============================================================================
# GOOGLE SHEETS READER
# ============================================================================

class SheetsReader:
    def __init__(self, credentials_file, token_file, sheet_name):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.sheet_name = sheet_name
        self.client = None
        self.spreadsheet = None

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

    def read_articles(self, tab_name, max_articles=0):
        """Read articles from Raw Articles tab"""
        try:
            print(f"Reading articles from '{tab_name}' tab...")
            sheet = self.spreadsheet.worksheet(tab_name)
            all_rows = sheet.get_all_values()
            
            if len(all_rows) <= 1:
                print("No articles found!")
                return []
            
            headers = all_rows[0]
            articles = []
            
            # Get current time for filtering
            from datetime import datetime, timedelta, timezone
            vn_tz = timezone(timedelta(hours=7))
            now = datetime.now(vn_tz)
            cutoff = now - timedelta(hours=36)  # Match scraper's 36-hour window
            
            skipped_old = 0
            skipped_bad_date = 0
            
            for row in all_rows[1:]:
                if len(row) < 7:
                    continue
                
                # Filter by scraped date - only include articles from last 36 hours
                try:
                    # Handle both date formats: 'YYYY-MM-DD' and 'YYYY-MM-DD HH:MM:SS'
                    date_str = row[0].strip()
                    if len(date_str) > 10 and ' ' in date_str:
                        # Has time component
                        scraped_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    else:
                        # Date only
                        scraped_date = datetime.strptime(date_str, '%Y-%m-%d')
                    scraped_date = scraped_date.replace(tzinfo=vn_tz)
                    
                    # Skip old articles
                    if scraped_date < cutoff:
                        skipped_old += 1
                        continue
                except Exception as parse_error:
                    # If date parsing fails, SKIP the article (don't include it)
                    print(f"  Warning: Could not parse date '{row[0]}': {parse_error}")
                    skipped_bad_date += 1
                    continue
                    
                article = {
                    'scraped_date': row[0],
                    'source': row[1],
                    'section': row[2],
                    'title': row[3],
                    'date': row[4],
                    'url': row[5],
                    'content': row[6],
                    'status': row[7] if len(row) > 7 else 'New'
                }
                
                if article['content'] and len(article['content']) > 100:
                    articles.append(article)
            
            if max_articles > 0:
                articles = articles[-max_articles:]
            
            print(f"Found {len(articles)} articles to analyze")
            if skipped_old > 0:
                print(f"  (Skipped {skipped_old} old articles beyond 36h)")
            if skipped_bad_date > 0:
                print(f"  (Skipped {skipped_bad_date} articles with unparseable dates)")
            print()
            return articles
            
        except Exception as e:
            print(f"Read error: {e}")
            return []

    def save_digest(self, summary, total_articles, digest_tab):
        """Save analysis to Digest tab"""
        try:
            print(f"Saving analysis to '{digest_tab}' tab...")
            
            try:
                sheet = self.spreadsheet.worksheet(digest_tab)
            except gspread.exceptions.WorksheetNotFound:
                sheet = self.spreadsheet.add_worksheet(
                    title=digest_tab,
                    rows=1000,
                    cols=5
                )
                headers = ['Analysis Date', 'Total Articles', 'High', 'Medium', 'Summary']
                sheet.update([headers], 'A1:E1')
                sheet.format('A1:E1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.2, 'green': 0.5, 'blue': 0.9}
                })
            
            high_count = summary.count('🔴') - 1 if '🔴' in summary else 0
            medium_count = summary.count('🟡') - 1 if '🟡' in summary else 0
            
            row = [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                total_articles,
                high_count,
                medium_count,
                summary
            ]
            
            sheet.append_rows([row])
            print("Analysis saved!")
            print()
            return True
            
        except Exception as e:
            print(f"Save error: {e}")
            return False

    def get_sheet_url(self):
        try:
            return self.spreadsheet.url
        except:
            return None


# ============================================================================
# CLAUDE ANALYZER
# ============================================================================

class ClaudeAnalyzer:
    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)

    def analyze(self, articles):
        """Send articles to Claude for analysis with automatic batching"""
        print("=" * 70)
        print("SENDING TO CLAUDE API FOR ANALYSIS")
        print("=" * 70)
        print()
        
        total_articles = len(articles)
        print(f"Analyzing {total_articles} Vietnamese articles...")
        
        # If more than 75 articles, split into batches to avoid rate limits
        # Rate limit: 30,000 tokens/min ≈ 75 articles per batch
        BATCH_SIZE = 70
        
        if total_articles <= BATCH_SIZE:
            # Small enough - send all at once
            print("Please wait...")
            print()
            return self._send_single_batch(articles)
        else:
            # Split into batches
            num_batches = (total_articles + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"Splitting into {num_batches} batches to avoid rate limits...")
            print()
            
            all_summaries = []
            
            for i in range(0, total_articles, BATCH_SIZE):
                batch_num = (i // BATCH_SIZE) + 1
                batch = articles[i:i + BATCH_SIZE]
                
                print(f"Batch {batch_num}/{num_batches}: Analyzing {len(batch)} articles...")
                
                summary = self._send_single_batch(batch)
                if summary is None:
                    print(f"✗ Batch {batch_num} failed!")
                    return None
                
                all_summaries.append(summary)
                print(f"✓ Batch {batch_num} complete!")
                print()
                
                # Wait 65 seconds between batches to avoid rate limit
                if batch_num < num_batches:
                    import time
                    print(f"Waiting 65 seconds before next batch...")
                    time.sleep(65)
                    print()
            
            # Combine all batch summaries
            print("=" * 70)
            print("COMBINING BATCH RESULTS")
            print("=" * 70)
            print()
            
            combined_summary = self._combine_summaries(all_summaries)
            
            print("=" * 70)
            print("ANALYSIS COMPLETE!")
            print("=" * 70)
            print()
            
            return combined_summary

    def _send_single_batch(self, articles):
        """Send a single batch to Claude"""
        try:
            prompt = build_prompt(articles)
            
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text

        except Exception as e:
            print(f"Claude API error: {e}")
            return None

    def _combine_summaries(self, summaries):
        """Combine multiple batch summaries into one"""
        # Simple combination - just concatenate with separators
        # The JSON parser will merge the high/medium/not_relevant arrays
        combined = "\n\n".join(summaries)
        return combined


# ============================================================================
# MAIN
# ============================================================================

def main():
    print()
    print("=" * 70)
    print("VIETNAM NEWS ANALYZER")
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 70)
    print()

    # Check API key
    if CONFIG["claude_api_key"] == "PASTE_YOUR_CLAUDE_API_KEY_HERE":
        print("ERROR: Please add your Claude API key!")
        print("Either set CLAUDE_API_KEY environment variable")
        print("Or edit this file and add your key")
        return

    # Read articles
    reader = SheetsReader(
        CONFIG["credentials_file"],
        CONFIG["token_file"],
        CONFIG["sheet_name"]
    )

    if not reader.connect():
        print("Could not connect to Google Sheets")
        return

    articles = reader.read_articles(
        CONFIG["raw_articles_tab"],
        CONFIG["max_articles_to_analyze"]
    )

    if not articles:
        print("No articles to analyze!")
        print("Run scrape_daily_vietnam.py first")
        return

    # Analyze with Claude
    analyzer = ClaudeAnalyzer(CONFIG["claude_api_key"])
    summary = analyzer.analyze(articles)

    if not summary:
        print("Analysis failed")
        return

    # Display summary
    print(summary)
    print()

    # Save locally
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    summary_file = os.path.join(
        CONFIG["output_dir"],
        "vietnam_analysis_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".txt"
    )
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary)
    print(f"Saved locally: {summary_file}")
    print()

    # Save to Google Sheets
    reader.save_digest(summary, len(articles), CONFIG["digest_tab"])

    url = reader.get_sheet_url()
    if url:
        print(f"Google Sheet: {url}")
        print(f"Open '{CONFIG['digest_tab']}' tab to see analysis")

    print()
    print("=" * 70)
    print("ALL DONE!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
