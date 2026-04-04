#!/usr/bin/env python3
"""
Brazil News Analyzer
Reads Brazilian articles from Google Sheets and uses Claude to analyze
Focuses on Bovespa, BRL/USD, Selic rate, and Brazilian markets
Outputs in ENGLISH
"""

import os
import sys
from datetime import datetime, timezone, timedelta
import gspread
from google.oauth2.service_account import Credentials
import pickle
from anthropic import Anthropic

# Brazil timezone (UTC-3)
BRAZIL_TZ = timezone(timedelta(hours=-3))

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    # Claude API
    "claude_api_key": os.environ.get('CLAUDE_API_KEY'),
    
    # Google Sheets setup
    "credentials_file": "credentials.json",
    "token_file": "token.pickle",
    "sheet_name": "News Scraper Database",
    "raw_articles_tab": "Brazil Raw Articles",
    "digest_tab": "Brazil Daily Digest",
    
    # Analysis settings
    "max_articles_to_analyze": 0,  # 0 = all new articles
    
    # Output
    "output_dir": "./news_output",
}

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Check for API key
if not CONFIG["claude_api_key"]:
    print("Error: CLAUDE_API_KEY environment variable not set")
    sys.exit(1)


# ============================================================================
# PROMPT BUILDER
# ============================================================================

def build_prompt(articles):
    """Build Brazil-focused analysis prompt"""
    
    articles_text = ""
    for i, article in enumerate(articles, 1):
        articles_text += "---\n"
        articles_text += f"Article {i}\n"
        articles_text += f"Source: {article['source']}\n"
        articles_text += f"Title: {article['title']}\n"
        articles_text += f"Date: {article['date']}\n"
        articles_text += f"URL: {article['url']}\n"
        articles_text += f"Content: {article['content'][:1000]}\n\n"

    prompt = f"""You are a senior emerging markets analyst specializing in Brazil's 
financial markets, currency dynamics, and monetary policy.

Your job is to review Brazilian financial news and produce a professional daily 
briefing for an international fund manager who trades Brazilian Real (BRL), 
Brazilian government bonds, and Brazilian equities.

IMPORTANT: 
- The articles are in PORTUGUESE but you MUST write ALL summaries in ENGLISH
- Translate Portuguese article titles to English
- All analysis and commentary must be in ENGLISH

Below are {len(articles)} news articles from MoneyTimes.com.br.

CRITICAL RULES:
- Use ONLY the exact URLs provided in the article data above
- DO NOT modify, shorten, or make up URLs
- Copy the URL exactly as it appears for each article
- Filter articles based on relevance to the topics below
- Write ALL content in ENGLISH (translate titles and summaries from Portuguese)

RELEVANT TOPICS (ONLY summarize articles about these):
- **BRL/USD exchange rate** and FX market dynamics
- **Banco Central do Brasil (BCB)** monetary policy, COPOM decisions, intervention
- **Selic rate** and interest rate policy
- **Brazilian government bond yields** and fixed income markets
- **Ibovespa (B3)** and São Paulo Stock Exchange
- **Capital flows** (foreign investment, portfolio flows)
- **Inflation (IPCA)** and its impact on rates and FX
- **Trade balance**, exports, imports
- **Banking sector** (Itaú, Bradesco, Banco do Brasil, etc.)
- **Petrobras, Vale** and major SOEs affecting markets
- **Fiscal policy** and government budget

NOT RELEVANT (skip these):
- Individual small company earnings
- Real estate projects
- Retail/consumer news unrelated to macro
- Technology startups
- General business news

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:

═══════════════════════════════════════
🔴 HIGH IMPORTANCE
═══════════════════════════════════════

**[Translated English Title]**
📂 Source: [source] | 📅 Date: [date]
🔗 [EXACT URL - copy it completely from the data]

[Thorough English summary up to 200 words. Explain:
- What happened with BRL/USD, yields, Selic, or policy?
- Why it matters for FX traders and bond investors?
- Market implications and what to watch next]

---

═══════════════════════════════════════
🟡 MEDIUM IMPORTANCE
═══════════════════════════════════════

**[Translated English Title]**
📂 Source: [source] | 📅 Date: [date]
🔗 [EXACT URL]

[3-5 sentence English summary covering key points and relevance to BRL, yields, or markets]

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
- Analysis date: {datetime.now(BRAZIL_TZ).strftime('%Y-%m-%d %H:%M')} BRT
═══════════════════════════════════════

HERE ARE THE ARTICLES:

{articles_text}"""

    return prompt


# ============================================================================
# GOOGLE SHEETS MANAGER
# ============================================================================

class SheetsManager:
    def __init__(self, credentials_file, token_file, sheet_name):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.sheet_name = sheet_name
        self.client = None
        self.spreadsheet = None

    def authenticate(self):
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            else:
                creds = Credentials.from_service_account_file(
                    self.credentials_file,
                    scopes=SCOPES
                )
            
            client = gspread.authorize(creds)
            return client
        except Exception as e:
            print(f"Error authenticating: {e}")
            sys.exit(1)

    def connect(self):
        try:
            print("Connecting to Google Sheets...")
            self.client = self.authenticate()
            self.spreadsheet = self.client.open(self.sheet_name)
            print(f"Connected to: {self.sheet_name}")
            print()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def read_articles(self, tab_name):
        """Read articles from Raw Articles tab"""
        try:
            print(f"Reading articles from '{tab_name}' tab...")
            sheet = self.spreadsheet.worksheet(tab_name)
            all_rows = sheet.get_all_values()
            
            if len(all_rows) <= 1:
                print("No articles found!")
                return []
            
            articles = []
            now = datetime.now(BRAZIL_TZ)
            cutoff = now - timedelta(hours=36)
            
            for row in all_rows[1:]:
                if len(row) < 7:
                    continue
                
                # Filter by date - only last 36 hours
                try:
                    date_str = row[0].strip()
                    if len(date_str) > 10 and ' ' in date_str:
                        scraped_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    else:
                        scraped_date = datetime.strptime(date_str, '%Y-%m-%d')
                    scraped_date = scraped_date.replace(tzinfo=BRAZIL_TZ)
                    
                    if scraped_date < cutoff:
                        continue
                except:
                    continue
                
                article = {
                    'scraped_date': row[0],
                    'timestamp': row[1],
                    'title': row[2],
                    'url': row[3],
                    'source': row[4],
                    'content': row[5],
                    'date': row[0]  # Use scraped date
                }
                
                if article['content'] and len(article['content']) > 100:
                    articles.append(article)
            
            print(f"Found {len(articles)} articles to analyze")
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
                sheet.update(range_name='A1:E1', values=[headers])
            
            high_count = summary.count('🔴') - 1 if '🔴' in summary else 0
            medium_count = summary.count('🟡') - 1 if '🟡' in summary else 0
            
            row = [
                datetime.now(BRAZIL_TZ).strftime('%Y-%m-%d %H:%M:%S'),
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


# ============================================================================
# CLAUDE ANALYZER
# ============================================================================

class ClaudeAnalyzer:
    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)

    def analyze(self, articles):
        """Send articles to Claude for analysis"""
        print("=" * 70)
        print("SENDING TO CLAUDE API FOR ANALYSIS")
        print("=" * 70)
        print()
        
        total_articles = len(articles)
        print(f"Analyzing {total_articles} Brazilian articles...")
        print("Please wait...")
        print()
        
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


# ============================================================================
# MAIN
# ============================================================================

def main():
    print()
    print("=" * 70)
    print("BRAZIL NEWS ANALYZER")
    print(datetime.now(BRAZIL_TZ).strftime('%Y-%m-%d %H:%M:%S BRT'))
    print("=" * 70)
    print()

    # Read articles
    sheets = SheetsManager(
        CONFIG["credentials_file"],
        CONFIG["token_file"],
        CONFIG["sheet_name"]
    )

    if not sheets.connect():
        print("Could not connect to Google Sheets")
        return

    articles = sheets.read_articles(CONFIG["raw_articles_tab"])

    if not articles:
        print("No articles to analyze!")
        print("Run scrape_daily_brazil.py first")
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
        "brazil_analysis_" + datetime.now(BRAZIL_TZ).strftime('%Y%m%d_%H%M%S') + ".txt"
    )
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary)
    print(f"Saved locally: {summary_file}")
    print()

    # Save to Google Sheets
    sheets.save_digest(summary, len(articles), CONFIG["digest_tab"])

    print()
    print("=" * 70)
    print("ALL DONE!")
    print("=" * 70)
    print(f"Check '{CONFIG['digest_tab']}' tab in Google Sheets")
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
