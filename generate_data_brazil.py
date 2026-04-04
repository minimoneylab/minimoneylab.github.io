#!/usr/bin/env python3
"""
Brazil Data Generator
Reads digest from Google Sheets and generates JSON data files
"""

import os
import gspread
from google.oauth2.service_account import Credentials
import pickle
from datetime import datetime, timedelta, timezone
import json
import re

# Brazil timezone (UTC-3)
BRAZIL_TZ = timezone(timedelta(hours=-3))

# Time filter: only include articles from past 36 hours
FILTER_HOURS = 36

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    # Google Sheets
    "credentials_file": "credentials.json",
    "token_file": "token.pickle",
    "sheet_name": "News Scraper Database",
    "digest_tab": "Brazil Daily Digest",
    
    # Output
    "output_dir": "./data",
    "output_file": "brazil-news.json",
}

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


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
        else:
            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=SCOPES
            )
        
        client = gspread.authorize(creds)
        return client

    def connect(self):
        try:
            print("Connecting to Google Sheets...")
            self.client = self.authenticate()
            self.spreadsheet = self.client.open(self.sheet_name)
            print("Connected!")
            print()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def get_latest_digest(self, digest_tab):
        """Get the most recent digest"""
        try:
            print(f"Reading latest digest from '{digest_tab}'...")
            sheet = self.spreadsheet.worksheet(digest_tab)
            all_rows = sheet.get_all_values()
            
            if len(all_rows) <= 1:
                print("No digest found!")
                return None
            
            # Get last row
            last_row = all_rows[-1]
            
            digest_data = {
                'date': last_row[0],
                'total_articles': last_row[1],
                'high': last_row[2],
                'medium': last_row[3],
                'summary': last_row[4]
            }
            
            print(f"Found digest from: {digest_data['date']}")
            print()
            return digest_data
            
        except Exception as e:
            print(f"Read error: {e}")
            return None


# ============================================================================
# DATA PARSER
# ============================================================================

class DataParser:
    def __init__(self):
        """Initialize with current Brazil time"""
        self.now = datetime.now(BRAZIL_TZ)
        self.cutoff_time = self.now - timedelta(hours=FILTER_HOURS)
    
    def parse_summary(self, summary_text):
        """Parse Claude's summary into structured data"""
        
        data = {
            'high': [],
            'medium': [],
            'not_relevant': []
        }
        
        # Split by sections
        high_section = re.search(r'🔴 HIGH IMPORTANCE\s*\n═+\n(.*?)(?=🟡|⚪|📊|$)', summary_text, re.DOTALL)
        medium_section = re.search(r'🟡 MEDIUM IMPORTANCE\s*\n═+\n(.*?)(?=⚪|📊|$)', summary_text, re.DOTALL)
        not_relevant_section = re.search(r'⚪ NOT RELEVANT\s*\n═+\n(.*?)(?=📊|═|$)', summary_text, re.DOTALL)
        
        # Parse high priority
        if high_section:
            articles = re.findall(r'\*\*(.*?)\*\*.*?📂 Source:\s*(.*?)\s*\|\s*📅 Date:\s*(.*?)\s*🔗\s*(https?://[^\s]+)\s*(.*?)(?=\n---|\n═{3,}|\*\*|$)', 
                                high_section.group(1), re.DOTALL)
            for title, source, date, url, summary in articles:
                if title.strip() and not title.strip().startswith('No articles'):
                    data['high'].append({
                        'title': title.strip(),
                        'source': source.strip(),
                        'date': date.strip(),
                        'url': url.strip(),
                        'summary': summary.strip()
                    })
        
        # Parse medium priority
        if medium_section:
            articles = re.findall(r'\*\*(.*?)\*\*.*?📂 Source:\s*(.*?)\s*\|\s*📅 Date:\s*(.*?)\s*🔗\s*(https?://[^\s]+)\s*(.*?)(?=\n---|\n═{3,}|\*\*|$)', 
                                medium_section.group(1), re.DOTALL)
            for title, source, date, url, summary in articles:
                if title.strip():
                    data['medium'].append({
                        'title': title.strip(),
                        'source': source.strip(),
                        'date': date.strip(),
                        'url': url.strip(),
                        'summary': summary.strip()
                    })
        
        # Parse not relevant
        if not_relevant_section:
            text = not_relevant_section.group(1)
            lines = [line.strip() for line in text.split('\n') if line.strip() and not line.startswith('═') and '⚪' not in line]
            data['not_relevant'] = [line.lstrip('-•* ') for line in lines if line and not line.startswith('📊')]
        
        return data


# ============================================================================
# JSON GENERATOR
# ============================================================================

class JsonGenerator:
    def __init__(self):
        self.parser = DataParser()
    
    def generate_json(self, digest_data):
        """Generate JSON data file"""
        
        parsed = self.parser.parse_summary(digest_data['summary'])
        
        # Print summary
        print()
        print("=" * 70)
        print(f"High priority articles: {len(parsed['high'])}")
        print(f"Medium priority articles: {len(parsed['medium'])}")
        print("=" * 70)
        print()
        
        json_data = {
            'date': digest_data['date'].split()[0],
            'update_time': digest_data['date'],
            'total_articles': int(digest_data['total_articles']),
            'high': parsed['high'],
            'medium': parsed['medium'],
            'not_relevant': parsed['not_relevant']
        }
        
        return json_data
    
    def save_json(self, json_data, output_dir, output_file):
        """Save JSON file"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Use Brazil time for date
        brazil_now = datetime.now(BRAZIL_TZ)
        date_str = brazil_now.strftime('%Y-%m-%d')
        filepath = os.path.join(output_dir, output_file)
        
        # Update json_data with correct Brazil date
        json_data['date'] = date_str
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved: {filepath}")
        
        return filepath


# ============================================================================
# MAIN
# ============================================================================

def main():
    print()
    print("=" * 70)
    print("BRAZIL DATA GENERATOR")
    brazil_now = datetime.now(BRAZIL_TZ)
    print(f"{brazil_now.strftime('%Y-%m-%d %H:%M:%S')} BRT")
    print("=" * 70)
    print()

    # Read digest from Google Sheets
    reader = SheetsReader(
        CONFIG["credentials_file"],
        CONFIG["token_file"],
        CONFIG["sheet_name"]
    )

    if not reader.connect():
        print("Could not connect to Google Sheets")
        return

    digest_data = reader.get_latest_digest(CONFIG["digest_tab"])

    if not digest_data:
        print("No digest found!")
        print("Run analyze_news_brazil.py first")
        return

    # Generate JSON
    print("Generating JSON data...")
    generator = JsonGenerator()
    json_data = generator.generate_json(digest_data)

    # Save JSON file
    filepath = generator.save_json(
        json_data,
        CONFIG["output_dir"],
        CONFIG["output_file"]
    )

    print()
    print("=" * 70)
    print("DATA READY!")
    print("=" * 70)
    print(f"JSON file: {filepath}")
    print(f"Articles ready for website display")
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
