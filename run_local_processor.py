#!/usr/bin/env python3
"""
Quick setup script for local processor
Run this on your PC to connect to Render backend
"""

import requests
import asyncio
from scraper import GoogleRankScraper

class LocalRankProcessor:
    def __init__(self, api_url):
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
        
    def get_keywords(self):
        """Get keywords from Render API"""
        try:
            response = self.session.get(f"{self.api_url}/api/keywords")
            if response.status_code == 200:
                data = response.json()
                return data.get("keywords", [])
            return []
        except Exception as e:
            print(f"Error fetching keywords: {e}")
            return []
    
    def update_position(self, keyword_id, position):
        """Send results back to Render"""
        try:
            data = {"keyword_id": keyword_id, "position": position}
            response = self.session.post(f"{self.api_url}/api/update-position", json=data)
            return response.status_code == 200
        except Exception as e:
            print(f"Error updating position: {e}")
            return False
    
    async def process_keyword(self, keyword_data):
        """Process single keyword with visible browser"""
        keyword_id = keyword_data['id']
        keyword = keyword_data['keyword']
        url = keyword_data['url']
        proxy = keyword_data.get('proxy')
        
        print(f"\n🔍 Processing: '{keyword}' for {url}")
        
        try:
            # Use your existing scraper with visible browser
            scraper = GoogleRankScraper(proxy=proxy)
            position = await scraper.get_ranking(keyword, url)
            
            # Send result back
            if self.update_position(keyword_id, position):
                print(f"✅ Updated: Position {position}")
            else:
                print(f"❌ Failed to update")
            
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    async def run(self):
        """Main processing loop"""
        print(f"🚀 Local Rank Processor Started")
        print(f"📡 Connected to: {self.api_url}")
        print(f"🌐 Using visible browser for scraping")
        print("-" * 50)
        
        while True:
            try:
                keywords = self.get_keywords()
                
                if keywords:
                    print(f"\n📋 Found {len(keywords)} keyword(s)")
                    
                    for i, kw in enumerate(keywords, 1):
                        print(f"\n[{i}/{len(keywords)}] Processing...")
                        await self.process_keyword(kw)
                        
                        if i < len(keywords):
                            print("⏳ Waiting 5 seconds...")
                            await asyncio.sleep(5)
                    
                    print(f"\n✅ Completed batch!")
                else:
                    print("💤 No keywords found, waiting...")
                
                print("⏰ Waiting 60 seconds for next check...")
                await asyncio.sleep(60)
                
            except KeyboardInterrupt:
                print("\n🛑 Stopping...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                await asyncio.sleep(30)

def main():
    # Get your Render backend URL
    api_url = input("Enter your Render backend URL (e.g., https://your-app.onrender.com): ").strip()
    
    if not api_url:
        print("❌ URL required!")
        return
    
    processor = LocalRankProcessor(api_url)
    
    try:
        asyncio.run(processor.run())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()
