#!/usr/bin/env python3
"""
Data Generator for MiniMoneyLab
Reads digest from Google Sheets and generates JSON data files
The smart template will automatically load and display these files
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

# Hong Kong timezone (UTC+8)
HK_TIMEZONE = timezone(timedelta(hours=8))

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    # Google Sheets
    "credentials_file": "credentials.json",
    "token_file": "token.pickle",
    "sheet_name": "News Scraper Database",
    "digest_tab": "Daily Digest",
    
    # Output
    "output_dir": "./website/data",
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
            print("Connection error: " + str(e))
            return False

    def get_latest_digest(self, tab_name):
        """Get the most recent digest entry"""
        try:
            print("Reading latest digest...")
            sheet = self.spreadsheet.worksheet(tab_name)
            all_rows = sheet.get_all_values()
            
            if len(all_rows) <= 1:
                print("No digest found!")
                return None
            
            # Get last row (most recent)
            last_row = all_rows[-1]
            
            digest = {
                'date': last_row[0],
                'total_articles': last_row[1],
                'high_count': last_row[2],
                'medium_count': last_row[3],
                'summary': last_row[4]
            }
            
            print("Found digest from: " + digest['date'])
            print()
            return digest
            
        except Exception as e:
            print("Read error: " + str(e))
            return None


# ============================================================================
# DATA PARSER
# ============================================================================

class DataParser:
    def parse_summary(self, summary):
        """Parse Claude's summary into structured JSON data"""
        
        data = {
            'high': [],
            'medium': [],
            'not_relevant': []
        }
        
        # Parse High Priority
        if '🔴 HIGH IMPORTANCE' in summary:
            start = summary.find('🔴 HIGH IMPORTANCE')
            end = summary.find('🟡 MEDIUM IMPORTANCE')
            if end == -1:
                end = summary.find('⚪ NOT RELEVANT')
            if end == -1:
                end = summary.find('📊 DAILY STATS')
            
            section = summary[start:end] if end != -1 else summary[start:]
            data['high'] = self._parse_articles(section)
        
        # Parse Medium Priority
        if '🟡 MEDIUM IMPORTANCE' in summary:
            start = summary.find('🟡 MEDIUM IMPORTANCE')
            end = summary.find('⚪ NOT RELEVANT')
            if end == -1:
                end = summary.find('📊 DAILY STATS')
            
            section = summary[start:end] if end != -1 else summary[start:]
            data['medium'] = self._parse_articles(section)
        
        # Parse Not Relevant
        if '⚪ NOT RELEVANT' in summary:
            start = summary.find('⚪ NOT RELEVANT')
            end = summary.find('📊 DAILY STATS')
            
            section = summary[start:end] if end != -1 else summary[start:]
            data['not_relevant'] = self._parse_not_relevant(section)
        
        return data
    
    def _parse_articles(self, section_text):
        """Extract articles from a priority section"""
        articles = []
        article_blocks = section_text.split('---')
        
        for block in article_blocks:
            if '**' not in block:
                continue
            
            article = {}
            
            # Title
            title_match = re.search(r'\*\*(.*?)\*\*', block)
            if title_match:
                article['title'] = title_match.group(1).strip()
            
            # Section and date
            meta_match = re.search(r'📂 Section: (.*?)\s*\|\s*📅 Date: (.*?)(?:\n|$)', block)
            if meta_match:
                article['section'] = meta_match.group(1).strip()
                article['date'] = meta_match.group(2).strip()
            
            # URL
            url_match = re.search(r'🔗\s*(https?://[^\s]+)', block)
            if url_match:
                article['url'] = url_match.group(1).strip()
            
            # Summary
            if url_match:
                summary_start = url_match.end()
                summary_text = block[summary_start:].strip()
                summary_text = re.sub(r'═+', '', summary_text).strip()
                summary_text = re.sub(r'^\s*\n+', '', summary_text)
                if summary_text:
                    article['summary'] = summary_text
            
            if 'title' in article and article['title']:
                articles.append(article)
        
        return articles
    
    def _parse_not_relevant(self, section_text):
        """Extract not relevant titles"""
        titles = []
        lines = section_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if (line and 
                not line.startswith('═') and 
                not line.startswith('📊') and
                not line.startswith('-') and
                not line.startswith('⚪') and
                len(line) > 3):
                titles.append(line)
        
        return titles[:15]


# ============================================================================
# JSON GENERATOR
# ============================================================================

class JSONGenerator:
    def generate_json(self, digest_data):
        """Generate JSON data file"""
        
        # Parse the summary
        parser = DataParser()
        parsed = parser.parse_summary(digest_data['summary'])
        
        # Create JSON structure
        json_data = {
            'date': digest_data['date'].split()[0],  # Just the date part
            'update_time': digest_data['date'],
            'total_articles': int(digest_data['total_articles']),
            'high': parsed['high'],
            'medium': parsed['medium'],
            'not_relevant': parsed['not_relevant']
        }
        
        return json_data
    
    def save_json(self, json_data, output_dir, days_to_keep=7):
        """Save JSON file and manage archive"""
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Use Hong Kong time for filename (not the digest date which might be UTC)
        hk_now = datetime.now(HK_TIMEZONE)
        date_str = hk_now.strftime('%Y-%m-%d')
        filename = date_str + '.json'
        filepath = os.path.join(output_dir, filename)
        
        # Update json_data with correct HK date
        json_data['date'] = date_str
        
        # Save JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print("Saved: " + filepath)
        
        # Cleanup old files
        self._cleanup_old_files(output_dir, days_to_keep)
        
        return filepath
    
    def _cleanup_old_files(self, output_dir, days_to_keep):
        """Delete JSON files older than specified days"""
        try:
            hk_now = datetime.now(HK_TIMEZONE)
            cutoff_date = hk_now - timedelta(days=days_to_keep)
            
            for filepath in glob.glob(os.path.join(output_dir, '*.json')):
                filename = os.path.basename(filepath)
                try:
                    file_date_str = filename.replace('.json', '')
                    file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                    
                    if file_date < cutoff_date:
                        os.remove(filepath)
                        print("Deleted old file: " + filename)
                except:
                    pass
                    
        except Exception as e:
            print("Cleanup warning: " + str(e))


# ============================================================================
# MAIN
# ============================================================================

def main():
    print()
    print("=" * 70)
    print("MINIMONEYLAB DATA GENERATOR")
    hk_now = datetime.now(HK_TIMEZONE)
    print(hk_now.strftime('%Y-%m-%d %H:%M:%S') + " HK Time")
    print("=" * 70)
    print()

    # Read digest from Google Sheets
    reader = SheetsReader(
        CONFIG["credentials_file"],
        CONFIG["token_file"],
        CONFIG["sheet_name"]
    )

    if not reader.connect():
        return

    digest_data = reader.get_latest_digest(CONFIG["digest_tab"])

    if not digest_data:
        print("No digest found! Run analyze_news.py first.")
        return

    # Generate JSON
    print("Generating JSON data...")
    generator = JSONGenerator()
    json_data = generator.generate_json(digest_data)

    # Save JSON
    filepath = generator.save_json(
        json_data, 
        CONFIG['output_dir'],
        CONFIG['days_to_keep']
    )

    print()
    print("=" * 70)
    print("DATA READY!")
    print("=" * 70)
    print()
    print("JSON file: " + os.path.abspath(filepath))
    print()
    print("Open website: " + os.path.abspath(os.path.join(CONFIG['output_dir'], '../index.html')))
    print()
    print("The smart template will automatically load and display this data!")
    print("=" * 70)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped")
    except Exception as e:
        print("\nError: " + str(e))
        import traceback
        traceback.print_exc()
