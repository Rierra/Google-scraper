import requests
import asyncio
import time
import sys
import os
import warnings
import random # Added for random.uniform

# Suppress the Windows handle warning during cleanup
warnings.filterwarnings("ignore", category=ResourceWarning)

# Add backend directory to path so we can import scraper
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from scraper import GoogleRankScraper

# Monkey patch to suppress Windows handle errors during Chrome cleanup
import undetected_chromedriver as uc
_original_quit = uc.Chrome.quit

def patched_quit(self):
    """Patched quit method that suppresses Windows handle errors"""
    try:
        _original_quit(self)
    except OSError:
        pass  # Ignore Windows handle errors during cleanup

uc.Chrome.quit = patched_quit

class LocalRankProcessor:
    def __init__(self, api_url, username, password, proxy=None):
        """
        Initialize the local processor
        
        Args:
            api_url: URL of your deployed Render app
            username: Username for backend authentication
            password: Password for backend authentication
            proxy: Proxy URL in format: http://username:password@host:port
        """
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.default_proxy = proxy
        self.jwt_token = None

    def _authenticate(self):
        """Authenticates with the backend and stores the JWT token."""
        try:
            login_data = {"username": self.username, "password": self.password}
            response = self.session.post(f"{self.api_url}/api/login", json=login_data)
            response.raise_for_status()  # Raise an exception for HTTP errors
            token_data = response.json()
            self.jwt_token = token_data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.jwt_token}"})
            print("✅ Successfully authenticated with backend.")
            return True
        except requests.exceptions.HTTPError as e:
            print(f"❌ Authentication failed: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ Error during authentication: {e}")
            return False

    def get_pending_keywords(self):
        """Get keywords that need to be scraped from the Render API"""
        if not self.jwt_token:
            if not self._authenticate():
                return []
        try:
            response = self.session.get(f"{self.api_url}/api/check")
            if response.status_code == 200:
                data = response.json()
                return data.get("keywords", [])
            elif response.status_code == 404:
                # No keywords to check - this is normal
                return []
            elif response.status_code == 401:
                print("⚠️ JWT expired or invalid. Re-authenticating...")
                if self._authenticate():
                    # Retry request after re-authentication
                    response = self.session.get(f"{self.api_url}/api/check")
                    response.raise_for_status()
                    data = response.json()
                    return data.get("keywords", [])
                else:
                    print("❌ Failed to re-authenticate. Cannot fetch keywords.")
                    return []
            else:
                print(f"❌ Error fetching keywords: {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"❌ Error connecting to API: {e}")
            return []
    
    def update_position(self, keyword_id, position):
        """Send scraping results back to Render API"""
        if not self.jwt_token:
            if not self._authenticate():
                return False
        try:
            data = {
                "keyword_id": keyword_id,
                "position": position
            }
            response = self.session.post(f"{self.api_url}/api/update-position", json=data)
            if response.status_code == 200:
                print(f"✅ Updated keyword {keyword_id}: Position {position}")
                return True
            elif response.status_code == 401:
                print("⚠️ JWT expired or invalid. Re-authenticating...")
                if self._authenticate():
                    # Retry request after re-authentication
                    response = self.session.post(f"{self.api_url}/api/update-position", json=data)
                    response.raise_for_status()
                    print(f"✅ Updated keyword {keyword_id}: Position {position} after re-auth")
                    return True
                else:
                    print("❌ Failed to re-authenticate. Cannot update position.")
                    return False
            else:
                print(f"❌ Failed to update keyword {keyword_id}: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Error updating position: {e}")
            return False
    
    async def process_keyword(self, keyword_data):
        """Process a single keyword with headless browser + proxy"""
        keyword_id = keyword_data['id']
        keyword = keyword_data['keyword']
        url = keyword_data['url']
        country = keyword_data.get('country')

        # Use proxy from keyword data if provided, otherwise use default
        proxy = keyword_data.get('proxy') or self.default_proxy
        
        if country:
            print(f"\nðŸ” Processing: '{keyword}' for URL: {url} (Country: {country.upper()})")
        else:
            print(f"\nðŸ” Processing: '{keyword}' for URL: {url}")

        if proxy:
            # Hide password in logs
            proxy_display = proxy.split('@')[1] if '@' in proxy else proxy
            print(f"ðŸŒ Using proxy: {proxy_display}")
        
        try:
            # Use scraper in HEADLESS mode with proxy
            scraper = GoogleRankScraper(proxy=proxy)
            position = await scraper.get_ranking(keyword, url, country=country)
            
            # Send result back to Render
            success = self.update_position(keyword_id, position)
            
            if position:
                print(f"🎯 Found at position: {position}")
            else:
                print(f"❌ Not found in top 30")
            
            # Clear scraper reference to help with cleanup
            del scraper
            
            return success
            
        except Exception as e:
            print(f"❌ Error processing keyword: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_continuous(self, check_interval=10):
        """Run continuously, waiting for scraping triggers from website"""
        print(f"🚀 Starting local rank processor (CONTINUOUS MODE)...")
        print(f"📡 Connected to: {self.api_url}")
        print(f"🔒 Using HEADLESS browser mode")
        if self.default_proxy:
            proxy_display = self.default_proxy.split('@')[1] if '@' in self.default_proxy else self.default_proxy
            print(f"🌐 Default proxy: {proxy_display}")
        print(f"💡 You can add keywords via: https://google-scraper-frontend.onrender.com")
        print(f"⏱️  Checking for new requests every {check_interval} seconds")
        print(f"🔄 Script will stay running - close with Ctrl+C to stop")
        print("-" * 60)
        
        # Initial authentication
        if not self._authenticate():
            print("❌ Initial authentication failed. Exiting.")
            return

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
                            wait_time = random.uniform(8, 15)
                            print(f"⏳ Waiting {wait_time:.1f} seconds before next keyword...")
                            await asyncio.sleep(wait_time)
                    
                    print(f"\n✅ Completed batch of {len(keywords)} keywords")
                    print(f"🎉 Results sent to backend!")
                    print(f"💤 Waiting for next trigger...")
                else:
                    print("💤 No keywords to process, waiting...")
                
                # Wait before next check
                print(f"⏰ Checking again in {check_interval} seconds...")
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
    
    # --- Scraper Authentication Credentials ---
    # These should match your backend admin credentials
    # For security, consider loading these from environment variables
    scraper_username = os.getenv("SCRAPER_USERNAME", "Ronaldo") # Default to Ronaldo
    scraper_password = os.getenv("SCRAPER_PASSWORD", "test123") # Default to test123
    # ------------------------------------------

    # ============================================
    # CONFIGURE YOUR PROXY HERE
    # ============================================
    # Format: http://username:password@host:port
    # Example: http://QD2I98DOSq0h30C6:wifi;;;;@proxy.froxy.com:9000
    
    proxy = "http://QD2I98DOSq0h30C6:wifi;;;;@proxy.froxy.com:9000"
    
    # If no proxy needed, set to None:
    # proxy = None
    
    print("=" * 60)
    print("🎯 GOOGLE RANK TRACKER - LOCAL PROCESSOR")
    print("=" * 60)
    print(f"📡 Backend: {api_url}")
    print(f"🌐 Frontend: https://google-scraper-frontend.onrender.com")
    if proxy:
        proxy_display = proxy.split('@')[1] if '@' in proxy else proxy
        print(f"🔐 Proxy: {proxy_display}")
    print("=" * 60)
    
    # Create and run processor
    processor = LocalRankProcessor(api_url, scraper_username, scraper_password, proxy=proxy)
    
    try:
        # Test connection first (this will now include authentication)
        print("🔍 Testing connection to backend (and authenticating)...")
        # The first call to get_pending_keywords will trigger authentication
        keywords = processor.get_pending_keywords()
        if keywords is not None: # Check for None in case of auth failure
            print("✅ Connection and initial authentication successful!")
        else:
            print("❌ Initial connection or authentication failed. Exiting.")
            return
        
        # Run continuously, waiting for triggers
        asyncio.run(processor.run_continuous(check_interval=10))
            
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        print("Make sure your backend is deployed and running!")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()