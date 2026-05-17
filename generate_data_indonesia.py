#!/usr/bin/env python3
"""
Data Generator for Indonesia
Reads categorized digest from Google Sheets and generates JSON for website
"""

import json
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
from datetime import datetime, timezone

# Google Sheets setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

SHEET_NAME = 'News Scraper Database'  # Same as Vietnam/Brazil
DIGEST_WORKSHEET = 'Indonesia Daily Digest'
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

def get_digest_from_sheet(client):
    """Get categorized digest from Google Sheets"""
    try:
        spreadsheet = client.open(SHEET_NAME)
        worksheet = spreadsheet.worksheet(DIGEST_WORKSHEET)
        
        records = worksheet.get_all_records()
        
        digest = {
            'high': [],
            'medium': [],
            'not_relevant': []
        }
        
        for record in records:
            priority = record.get('Priority', '').upper()
            
            article = {
                'title': record.get('Title', ''),
                'url': record.get('URL', ''),
                'summary': record.get('Summary', ''),
                'source': record.get('Source', 'CNN Indonesia'),
                'date': record.get('Date', '')
            }
            
            if priority == 'HIGH':
                digest['high'].append(article)
            elif priority == 'MEDIUM':
                digest['medium'].append(article)
        
        return digest
        
    except Exception as e:
        print(f"Error reading from Google Sheets: {e}")
        return {'high': [], 'medium': [], 'not_relevant': []}

def generate_json_output(digest):
    """Generate JSON file for website"""
    
    output_data = {
        'update_time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'country': 'Indonesia',
        'source': 'CNN Indonesia',
        'total_articles': len(digest['high']) + len(digest['medium']),
        'high': digest['high'],
        'medium': digest['medium'],
        'not_relevant': []
    }
    
    # Save to JSON file
    output_file = './data/indonesia-news.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Generated {output_file}")
    print(f"  HIGH: {len(digest['high'])} articles")
    print(f"  MEDIUM: {len(digest['medium'])} articles")
    print(f"  Total: {output_data['total_articles']} articles")
    
    return output_file

def main():
    print("=" * 70)
    print("INDONESIA DATA GENERATOR")
    print(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'))
    print("=" * 70)
    print()
    
    try:
        # Setup Google Sheets
        print("Connecting to Google Sheets...")
        client = setup_google_sheets()
        
        # Get digest
        print("Reading digest from Google Sheets...")
        digest = get_digest_from_sheet(client)
        
        if not digest['high'] and not digest['medium']:
            print("⚠ No articles found in digest!")
            print("Creating empty JSON file...")
        
        # Generate JSON
        print()
        print("Generating JSON file...")
        output_file = generate_json_output(digest)
        
        print()
        print("=" * 70)
        print("DATA GENERATION COMPLETE")
        print("=" * 70)
        print(f"Output: {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
