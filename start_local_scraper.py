#!/usr/bin/env python3
"""
Pre-configured local scraper for your deployed backend
Just run this script to start scraping on your PC
"""

import requests
import asyncio
import time
import sys
import os

# Add backend directory to path so we can import scraper
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from scraper import GoogleRankScraper

class LocalRankProcessor:
    def __init__(self, api_url):
        """
        Initialize the local processor
        
        Args:
            api_url: URL of your deployed Render app
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
                print(f"❌ Error fetching keywords: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error connecting to API: {e}")
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
            # Use your existing scraper with visible browser (headless=False)
            scraper = GoogleRankScraper(proxy=proxy, headless=False)
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
        print(f"🌐 Using VISIBLE browser for scraping")
        print(f"💡 Your boss can now use: https://google-scraper-frontend.onrender.com")
        print("-" * 60)
        
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
    
    # Your deployed backend URL
    api_url = "https://google-scraper-1.onrender.com"
    
    print("=" * 60)
    print("🎯 GOOGLE RANK TRACKER - LOCAL PROCESSOR")
    print("=" * 60)
    print(f"📡 Backend: {api_url}")
    print(f"🌐 Frontend: https://google-scraper-frontend.onrender.com")
    print("=" * 60)
    
    # Create and run processor
    processor = LocalRankProcessor(api_url)
    
    try:
        # Test connection first
        print("🔍 Testing connection to backend...")
        keywords = processor.get_pending_keywords()
        print("✅ Connection successful!")
        
        # Run continuous processing
        asyncio.run(processor.run_continuous(check_interval=60))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        print("Make sure your backend is deployed and running!")

if __name__ == "__main__":
    main()
