#!/usr/bin/env python3
"""
News Analyzer for Malaysia - Uses Claude API
Reads from Google Sheets, analyzes with Claude, saves digest back to Sheets
GitHub version - uses environment variable for API key
"""

import os
from anthropic import Anthropic
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from datetime import datetime, timezone

# Google Sheets setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

SHEET_NAME = 'News Scraper Database'  # Same as Vietnam/Brazil
RAW_WORKSHEET = 'Malaysia Raw Articles'
DIGEST_WORKSHEET = 'Malaysia Daily Digest'
TOKEN_FILE = 'token.pickle'

def authenticate_google_sheets():
    """Authenticate using OAuth (same method as Vietnam)"""
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def setup_google_sheets():
    """Setup Google Sheets connection"""
    try:
        creds = authenticate_google_sheets()
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_articles_from_sheet(client):
    """Get recent articles from Google Sheets"""
    try:
        spreadsheet = client.open(SHEET_NAME)
        worksheet = spreadsheet.worksheet(RAW_WORKSHEET)
        
        records = worksheet.get_all_records()
        
        # Get articles from today
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        recent_articles = []
        for record in records:
            scraped_date = record.get('Scraped At', '')
            if today in scraped_date or not scraped_date:
                recent_articles.append({
                    'title': record.get('Title', ''),
                    'url': record.get('URL', ''),
                    'summary': record.get('Summary', ''),
                    'date': record.get('Date', ''),
                    'category': record.get('Category', '')
                })
        
        return recent_articles[-30:]  # Last 30 articles
        
    except Exception as e:
        print(f"Error reading from Google Sheets: {e}")
        return []

def analyze_with_claude(articles):
    """Analyze articles with Claude API"""
    
    # Get API key from environment variable
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    client = Anthropic(api_key=api_key)
    
    # Prepare articles text
    articles_text = ""
    for i, article in enumerate(articles, 1):
        articles_text += f"\n{i}. {article['title']}\n"
        articles_text += f"   URL: {article['url']}\n"
        articles_text += f"   Summary: {article['summary'][:200]}...\n"
        articles_text += f"   Category: {article['category']}\n"
    
    prompt = f"""You are analyzing Malaysian business and finance news. Here are today's articles from Malay Mail:

{articles_text}

Categorize each article as:
- HIGH: Critical market-moving news (major economic policy, significant corporate events, market crashes/rallies)
- MEDIUM: Important but not urgent (notable business deals, sector trends, regulatory changes)
- NOT_RELEVANT: Non-financial news, minor updates, or irrelevant content

For each HIGH and MEDIUM article, provide:
1. Title (original)
2. URL (original)  
3. Brief summary (2-3 sentences explaining why it matters to Malaysian investors/businesses)
4. Source: "Malay Mail"
5. Date (original)

Return ONLY a JSON object with this structure:
{{
  "high": [
    {{"title": "...", "url": "...", "summary": "...", "source": "Malay Mail", "date": "..."}}
  ],
  "medium": [
    {{"title": "...", "url": "...", "summary": "...", "source": "Malay Mail", "date": "..."}}
  ],
  "not_relevant": [
    {{"title": "...", "url": "..."}}
  ]
}}

CRITICAL: Return ONLY the JSON object, no other text."""

    print("Sending to Claude API for analysis...")
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    response_text = response.content[0].text
    
    # Parse JSON
    import json
    import re
    
    try:
        digest = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON if Claude added explanation
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            digest = json.loads(json_match.group())
        else:
            raise ValueError("Could not parse Claude's response as JSON")
    
    return digest

def save_digest_to_sheet(client, digest):
    """Save categorized digest to Google Sheets"""
    try:
        spreadsheet = client.open(SHEET_NAME)
        
        try:
            worksheet = spreadsheet.worksheet(DIGEST_WORKSHEET)
            # Clear existing content
            worksheet.clear()
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=DIGEST_WORKSHEET, rows=1000, cols=10)
        
        # Add headers
        headers = ['Priority', 'Title', 'URL', 'Summary', 'Source', 'Date', 'Generated At']
        worksheet.append_row(headers)
        
        generated_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Add HIGH priority articles
        for article in digest.get('high', []):
            row = [
                'HIGH',
                article.get('title', ''),
                article.get('url', ''),
                article.get('summary', ''),
                article.get('source', 'Malay Mail'),
                article.get('date', ''),
                generated_time
            ]
            worksheet.append_row(row)
        
        # Add MEDIUM priority articles
        for article in digest.get('medium', []):
            row = [
                'MEDIUM',
                article.get('title', ''),
                article.get('url', ''),
                article.get('summary', ''),
                article.get('source', 'Malay Mail'),
                article.get('date', ''),
                generated_time
            ]
            worksheet.append_row(row)
        
        print(f"✓ Saved digest to Google Sheets")
        print(f"  HIGH: {len(digest.get('high', []))} articles")
        print(f"  MEDIUM: {len(digest.get('medium', []))} articles")
        print(f"  NOT_RELEVANT: {len(digest.get('not_relevant', []))} articles")
        
    except Exception as e:
        print(f"✗ Error saving digest: {e}")

def main():
    print("=" * 70)
    print("MALAYSIA NEWS ANALYZER - Claude API")
    print(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'))
    print("=" * 70)
    print()
    
    try:
        # Setup Google Sheets
        print("Connecting to Google Sheets...")
        client = setup_google_sheets()
        
        # Get articles
        print("Reading articles from Google Sheets...")
        articles = get_articles_from_sheet(client)
        
        if not articles:
            print("No articles found to analyze!")
            return
        
        print(f"Found {len(articles)} articles to analyze")
        print()
        
        # Analyze with Claude
        digest = analyze_with_claude(articles)
        
        print()
        print("Analysis complete!")
        print()
        
        # Save digest
        save_digest_to_sheet(client, digest)
        
        print()
        print("=" * 70)
        print("ANALYSIS COMPLETE")
        print("=" * 70)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
