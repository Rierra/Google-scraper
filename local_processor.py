#!/usr/bin/env python3
"""
Local processor for Google Rank Tracker
Runs on your PC with visible browser to handle scraping
"""

import requests
import asyncio
import time
import json
from scraper import GoogleRankScraper

class LocalRankProcessor:
    def __init__(self, api_url):
        """
        Initialize the local processor
        
        Args:
            api_url: URL of your deployed Render app (e.g., "https://your-app.onrender.com")
        """
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
        
    def get_pending_keywords(self):
        """Get keywords that need to be scraped from the Render API"""
        try:
            response = self.session.get(f"{self.api_url}/api/keywords")
            if response.status_code == 200:
                data = response.json()
                return data.get("keywords", [])
            else:
                print(f"Error fetching keywords: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error connecting to API: {e}")
            return []
    
    def update_position(self, keyword_id, position):
        """Send scraping results back to Render API"""
        try:
            data = {
                "keyword_id": keyword_id,
                "position": position
            }
            response = self.session.post(f"{self.api_url}/api/update-position", json=data)
            if response.status_code == 200:
                print(f"✅ Updated keyword {keyword_id}: Position {position}")
                return True
            else:
                print(f"❌ Failed to update keyword {keyword_id}: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error updating position: {e}")
            return False
    
    async def process_keyword(self, keyword_data):
        """Process a single keyword with visible browser"""
        keyword_id = keyword_data['id']
        keyword = keyword_data['keyword']
        url = keyword_data['url']
        proxy = keyword_data.get('proxy')
        
        print(f"\n🔍 Processing: '{keyword}' for URL: {url}")
        
        try:
            # Use your existing scraper with visible browser
            scraper = GoogleRankScraper(proxy=proxy)
            position = await scraper.get_ranking(keyword, url)
            
            # Send result back to Render
            success = self.update_position(keyword_id, position)
            
            if position:
                print(f"🎯 Found at position: {position}")
            else:
                print(f"❌ Not found in top 30")
            
            return success
            
        except Exception as e:
            print(f"❌ Error processing keyword: {e}")
            return False
    
    async def run_continuous(self, check_interval=60):
        """Run continuous processing of keywords"""
        print(f"🚀 Starting local rank processor...")
        print(f"📡 Connected to: {self.api_url}")
        print(f"⏱️  Check interval: {check_interval} seconds")
        print(f"🌐 Using visible browser for scraping")
        print("-" * 50)
        
        while True:
            try:
                # Get keywords from Render API
                keywords = self.get_pending_keywords()
                
                if keywords:
                    print(f"\n📋 Found {len(keywords)} keyword(s) to process")
                    
                    # Process each keyword
                    for i, keyword_data in enumerate(keywords, 1):
                        print(f"\n[{i}/{len(keywords)}] Processing keyword...")
                        await self.process_keyword(keyword_data)
                        
                        # Delay between keywords to avoid rate limiting
                        if i < len(keywords):
                            print("⏳ Waiting 5 seconds before next keyword...")
                            await asyncio.sleep(5)
                    
                    print(f"\n✅ Completed batch of {len(keywords)} keywords")
                else:
                    print("💤 No keywords to process, waiting...")
                
                # Wait before next check
                print(f"⏰ Waiting {check_interval} seconds before next check...")
                await asyncio.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Stopping processor...")
                break
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                print("⏳ Waiting 30 seconds before retry...")
                await asyncio.sleep(30)

def main():
    """Main function to run the local processor"""
    
    # Get API URL from user or use default
    api_url = input("Enter your Render app URL (e.g., https://your-app.onrender.com): ").strip()
    
    if not api_url:
        print("❌ API URL is required!")
        return
    
    # Create and run processor
    processor = LocalRankProcessor(api_url)
    
    try:
        # Run continuous processing
        asyncio.run(processor.run_continuous(check_interval=60))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()
