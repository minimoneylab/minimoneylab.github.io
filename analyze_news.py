#!/usr/bin/env python3
"""
STEP 2: AI News Analyzer
Reads articles from Google Sheets and uses Claude to analyze
Run this ANYTIME you want a new analysis (costs ~$0.11 per run)
Can tweak the prompt and re-run as many times as you want!
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
    # Claude API - read from environment variable if available
    "claude_api_key": os.environ.get('CLAUDE_API_KEY', 'PASTE_YOUR_CLAUDE_API_KEY_HERE'),
    
    # Google Sheets
    "credentials_file": "credentials.json",
    "token_file": "token.pickle",
    "sheet_name": "News Scraper Database",
    "raw_articles_tab": "Raw Articles",
    "digest_tab": "Daily Digest",
    
    # How many recent articles to analyze
    # Set to 0 to analyze ALL unanalyzed articles
    # Set to 30 to analyze last 30 articles
    "max_articles_to_analyze": 0,  # 0 = all new articles
    
    # Save summary locally
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
    """Build the analysis prompt - EDIT THIS to change analysis criteria!"""
    
    # Format articles
    articles_text = ""
    for i, article in enumerate(articles, 1):
        articles_text += "---\n"
        articles_text += "Article " + str(i) + "\n"
        articles_text += "Section: " + article['section'] + "\n"
        articles_text += "Title: " + article['title'] + "\n"
        articles_text += "Date: " + article['date'] + "\n"
        articles_text += "URL: " + article['url'] + "\n"
        articles_text += "Content: " + article['content'][:1000] + "\n\n"

    prompt = """You are a senior financial research analyst specializing in Taiwan's 
financial markets, insurance sector, and macroeconomic policy.

Your job is to review today's news and produce a professional daily briefing 
for a fund manager who focuses on Taiwan listed companies, life insurers, 
and monetary policy. Be precise, professional, and highlight market 
implications where relevant.

IMPORTANT: Write ALL summaries in ENGLISH. Translate Chinese article titles to English.

Below are """ + str(len(articles)) + """ news articles from UDN Money.

CRITICAL RULES:
- Use ONLY the exact URLs provided in the article data above
- DO NOT modify, shorten, or make up URLs
- Copy the URL exactly as it appears for each article
- Filter articles based on relevance to the topics below
- Write ALL content in ENGLISH (translate titles and summaries)

RELEVANT TOPICS (ONLY summarize articles about these):
- Taiwan life insurance companies (壽險公司)
- Financial regulators FSC (金管會)
- Foreign investors (外資)
- Life insurer accounting/investments (壽險會計/投資)
- Central Bank of Taiwan CBC (央行)
- Monetary policy / interest rates (貨幣政策/利率)
- Taiwan Dollar (台幣/新台幣)
- TSMC (台積電), MediaTek (聯發科), Hon Hai (鴻海)
- Other major Taiwan listed companies

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:

═══════════════════════════════════════
🔴 HIGH IMPORTANCE
═══════════════════════════════════════

**[Article Title in English]**
📂 Section: [section] | 📅 Date: [date]
🔗 [EXACT URL - copy it completely from the data]

[Thorough summary up to 200 words. Explain what happened, 
why it matters, and market implications for investors.]

---

═══════════════════════════════════════
🟡 MEDIUM IMPORTANCE
═══════════════════════════════════════

**[Article Title in English]**
📂 Section: [section] | 📅 Date: [date]
🔗 [EXACT URL - copy it completely from the data]

[3-5 sentence summary covering key points and relevance.]

---

═══════════════════════════════════════
⚪ NOT RELEVANT
═══════════════════════════════════════
[List only titles of irrelevant articles]

═══════════════════════════════════════
📊 DAILY STATS
═══════════════════════════════════════
- Total articles reviewed: [X]
- High importance: [X]
- Medium importance: [X]
- Not relevant: [X]
- Analysis date: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """
═══════════════════════════════════════

HERE ARE THE ARTICLES:

""" + articles_text

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
            print("Connected to: " + self.sheet_name)
            print()
            return True
        except Exception as e:
            print("Connection error: " + str(e))
            return False

    def read_articles(self, tab_name, max_articles=0):
        """Read articles from the Raw Articles tab"""
        try:
            print("Reading articles from '" + tab_name + "' tab...")
            sheet = self.spreadsheet.worksheet(tab_name)
            all_rows = sheet.get_all_values()
            
            if len(all_rows) <= 1:
                print("No articles found in sheet!")
                return []
            
            # Parse rows into article dictionaries
            headers = all_rows[0]
            articles = []
            
            for row in all_rows[1:]:  # Skip header
                if len(row) < 7:
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
                
                # Only include articles with content
                if article['content'] and len(article['content']) > 100:
                    articles.append(article)
            
            # Get most recent articles if limit is set
            if max_articles > 0:
                articles = articles[-max_articles:]
            
            print("Found " + str(len(articles)) + " articles to analyze")
            print()
            return articles
            
        except Exception as e:
            print("Read error: " + str(e))
            return []

    def save_digest(self, summary, total_articles, digest_tab):
        """Save analysis to Daily Digest tab"""
        try:
            print("Saving analysis to '" + digest_tab + "' tab...")
            
            # Get or create digest tab
            try:
                sheet = self.spreadsheet.worksheet(digest_tab)
            except gspread.exceptions.WorksheetNotFound:
                sheet = self.spreadsheet.add_worksheet(
                    title=digest_tab,
                    rows=1000,
                    cols=5
                )
                # Setup headers
                headers = ['Analysis Date', 'Total Articles', 'High', 'Medium', 'Summary']
                sheet.update([headers], 'A1:E1')
                sheet.format('A1:E1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.2, 'green': 0.5, 'blue': 0.9}
                })
            
            # Count priorities
            high_count = summary.count('🔴') - 1 if '🔴' in summary else 0
            medium_count = summary.count('🟡') - 1 if '🟡' in summary else 0
            
            # Add row
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
            print("Save error: " + str(e))
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
        """Send articles to Claude for analysis"""
        print("=" * 70)
        print("SENDING TO CLAUDE API FOR ANALYSIS")
        print("=" * 70)
        print()
        print("Analyzing " + str(len(articles)) + " articles...")
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
            
            summary = message.content[0].text
            
            print("=" * 70)
            print("ANALYSIS COMPLETE!")
            print("=" * 70)
            print()
            
            return summary

        except Exception as e:
            print("Claude API error: " + str(e))
            return None


# ============================================================================
# MAIN
# ============================================================================

def main():
    print()
    print("=" * 70)
    print("STEP 2: AI NEWS ANALYZER")
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 70)
    print()

    # Check API key
    if CONFIG["claude_api_key"] == "PASTE_YOUR_CLAUDE_API_KEY_HERE":
        print("ERROR: Please add your Claude API key!")
        print("Either set CLAUDE_API_KEY environment variable")
        print("Or edit this file and add your key at line 16")
        return

    # Read articles from Google Sheets
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
        print("Run scrape_daily.py first to get articles")
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

    # Save summary locally
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    summary_file = os.path.join(
        CONFIG["output_dir"],
        "analysis_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".txt"
    )
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary)
    print("Saved locally: " + summary_file)
    print()

    # Save to Google Sheets
    reader.save_digest(summary, len(articles), CONFIG["digest_tab"])

    url = reader.get_sheet_url()
    if url:
        print("Google Sheet: " + url)
        print("Open '" + CONFIG["digest_tab"] + "' tab to see analysis")

    print()
    print("=" * 70)
    print("ALL DONE!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped")
    except Exception as e:
        print("Error: " + str(e))
        import traceback
        traceback.print_exc()
