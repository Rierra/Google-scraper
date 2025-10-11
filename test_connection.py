#!/usr/bin/env python3
"""
Test script to verify connection to deployed backend
"""

import requests

def test_connection():
    api_url = "https://google-scraper-1.onrender.com"
    
    print("🔍 Testing connection to backend...")
    print(f"📡 URL: {api_url}")
    print("-" * 50)
    
    try:
        # Test basic connection
        response = requests.get(f"{api_url}/api/keywords", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            keywords = data.get("keywords", [])
            print("✅ Connection successful!")
            print(f"📋 Found {len(keywords)} keywords in database")
            
            if keywords:
                print("\n📝 Current keywords:")
                for kw in keywords:
                    print(f"  - {kw['keyword']} → {kw['url']}")
            else:
                print("📝 No keywords found (database is empty)")
                
            return True
        else:
            print(f"❌ Connection failed: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Connection timeout - backend might be sleeping")
        print("💡 Try again in a few seconds")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - check your internet connection")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 GOOGLE RANK TRACKER - CONNECTION TEST")
    print("=" * 60)
    
    success = test_connection()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 READY TO START LOCAL SCRAPER!")
        print("Run: python start_local_scraper.py")
        print("Or: start_scraper.bat")
    else:
        print("⚠️  CONNECTION ISSUES DETECTED")
        print("Make sure your backend is deployed and running")
    print("=" * 60)
