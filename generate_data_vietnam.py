#!/usr/bin/env python3
"""
Vietnam Data Generator
Reads digest from Google Sheets and generates JSON data files
"""

import os
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from datetime import datetime, timedelta, timezone
import json
import re
import glob

# Vietnam timezone (UTC+7)
VN_TIMEZONE = timezone(timedelta(hours=7))

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    # Google Sheets
    "credentials_file": "credentials.json",
    "token_file": "token.pickle",
    "sheet_name": "News Scraper Database",
    "digest_tab": "Vietnam Daily Digest",
    
    # Output
    "output_dir": "./vietnam/data",
    "days_to_keep": 7,
}

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
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
    def parse_summary(self, summary_text):
        """Parse Claude's summary into structured data"""
        
        data = {
            'high': [],
            'medium': [],
            'not_relevant': []
        }
        
        # Split by sections - skip the ═ line right after the header
        high_section = re.search(r'🔴 HIGH IMPORTANCE\s*\n═+\n(.*?)(?=🟡|⚪|📊|$)', summary_text, re.DOTALL)
        medium_section = re.search(r'🟡 MEDIUM IMPORTANCE\s*\n═+\n(.*?)(?=⚪|📊|$)', summary_text, re.DOTALL)
        not_relevant_section = re.search(r'⚪ NOT RELEVANT\s*\n═+\n(.*?)(?=📊|═|$)', summary_text, re.DOTALL)
        
        # Parse high priority
        if high_section:
            # Look for pattern: **Title** ... 📂 Section: X | 📅 Date: Y 🔗 URL [content until --- or ═]
            articles = re.findall(r'\*\*(.*?)\*\*.*?📂 Section:\s*(.*?)\s*\|\s*📅 Date:\s*(.*?)\s*🔗\s*(https?://[^\s]+)\s*(.*?)(?=\n---|\n═{3,}|\*\*|$)', 
                                high_section.group(1), re.DOTALL)
            for title, section, date, url, summary in articles:
                if title.strip() and not title.strip().startswith('No articles'):
                    data['high'].append({
                        'title': title.strip(),
                        'section': section.strip(),
                        'date': date.strip(),
                        'url': url.strip(),
                        'summary': summary.strip()
                    })
        
        # Parse medium priority
        if medium_section:
            articles = re.findall(r'\*\*(.*?)\*\*.*?📂 Section:\s*(.*?)\s*\|\s*📅 Date:\s*(.*?)\s*🔗\s*(https?://[^\s]+)\s*(.*?)(?=\n---|\n═{3,}|\*\*|$)', 
                                medium_section.group(1), re.DOTALL)
            for title, section, date, url, summary in articles:
                if title.strip():
                    data['medium'].append({
                        'title': title.strip(),
                        'section': section.strip(),
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
        
        json_data = {
            'date': digest_data['date'].split()[0],
            'update_time': digest_data['date'],
            'total_articles': int(digest_data['total_articles']),
            'high': parsed['high'],
            'medium': parsed['medium'],
            'not_relevant': parsed['not_relevant']
        }
        
        return json_data
    
    def save_json(self, json_data, output_dir, days_to_keep=7):
        """Save JSON file and manage archive"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Use Vietnam time for filename
        vn_now = datetime.now(VN_TIMEZONE)
        date_str = vn_now.strftime('%Y-%m-%d')
        filename = f"{date_str}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Update json_data with correct VN date
        json_data['date'] = date_str
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved: {filepath}")
        
        # Cleanup old files
        self._cleanup_old_files(output_dir, days_to_keep)
        
        return filepath
    
    def _cleanup_old_files(self, output_dir, days_to_keep):
        """Delete JSON files older than specified days"""
        try:
            vn_now = datetime.now(VN_TIMEZONE)
            cutoff_date = vn_now - timedelta(days=days_to_keep)
            
            for filepath in glob.glob(os.path.join(output_dir, '*.json')):
                filename = os.path.basename(filepath)
                try:
                    file_date_str = filename.replace('.json', '')
                    file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                    
                    if file_date < cutoff_date.replace(tzinfo=None):
                        os.remove(filepath)
                        print(f"Deleted old file: {filename}")
                except:
                    pass
        except Exception as e:
            print(f"Cleanup warning: {e}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print()
    print("=" * 70)
    print("VIETNAM DATA GENERATOR")
    vn_now = datetime.now(VN_TIMEZONE)
    print(f"{vn_now.strftime('%Y-%m-%d %H:%M:%S')} VN Time")
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
        print("Run analyze_news_vietnam.py first")
        return

    # Generate JSON
    print("Generating JSON data...")
    generator = JsonGenerator()
    json_data = generator.generate_json(digest_data)

    # Save JSON file
    filepath = generator.save_json(
        json_data,
        CONFIG["output_dir"],
        CONFIG["days_to_keep"]
    )

    print()
    print("=" * 70)
    print("DATA READY!")
    print("=" * 70)
    print(f"JSON file: {filepath}")
    print(f"Open website: /vietnam/index.html")
    print()
    print("The smart template will automatically load and display this data!")
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
