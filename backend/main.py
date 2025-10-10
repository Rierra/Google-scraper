import sys
import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set Windows event loop policy for the main process
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logger.info("Set WindowsSelectorEventLoopPolicy for main process")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from scraper import GoogleRankScraper
from database import Database

app = FastAPI(title="Google Rank Tracker API")

# CORS middleware for frontend
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database()

# Pydantic models
class KeywordCreate(BaseModel):
    keyword: str
    url: str
    proxy: Optional[str] = None

class KeywordResponse(BaseModel):
    id: int
    keyword: str
    url: str
    proxy: Optional[str]
    position: Optional[int]
    checked_at: Optional[str]
    created_at: str

class CheckRequest(BaseModel):
    keyword_id: Optional[int] = None  # If None, check all

@app.get("/")
async def root():
    return {"message": "Google Rank Tracker API", "status": "running"}

@app.on_event("startup")
async def startup_event():
    print("Registered routes:")
    for route in app.routes:
        print(f"  {route.methods if hasattr(route, 'methods') else 'N/A'} {route.path}")

@app.post("/api/track")
async def add_tracking(data: KeywordCreate):
    """Add new keyword to track"""
    keyword_id = db.add_keyword(data.keyword, data.url, data.proxy)
    if keyword_id is None:
        raise HTTPException(status_code=400, detail="Keyword already being tracked")
    
    return {"id": keyword_id, "message": "Keyword added successfully"}

@app.get("/api/keywords")
async def get_keywords():
    """Get all tracked keywords with latest position"""
    keywords = db.get_all_keywords()
    return {"keywords": keywords}

@app.post("/api/check")
async def check_rankings(data: CheckRequest = CheckRequest()):
    """Check rankings for one or all keywords"""
    logger.info(f"Received check request: {data}")
    
    # Get default proxy from environment
    default_proxy = os.getenv('PROXY_URL')
    
    if data.keyword_id:
        keywords = [kw for kw in db.get_all_keywords() if kw['id'] == data.keyword_id]
    else:
        keywords = db.get_all_keywords()
    
    if not keywords:
        logger.warning("No keywords found to check")
        raise HTTPException(status_code=404, detail="No keywords found")
    
    logger.info(f"Checking {len(keywords)} keyword(s)...")
    results = []
    
    for i, kw in enumerate(keywords, 1):
        logger.info(f"[{i}/{len(keywords)}] Processing keyword: '{kw['keyword']}'")
        
        # Use keyword's proxy if set, otherwise use default from .env
        proxy = kw.get('proxy') or default_proxy
        if proxy:
            logger.info(f"Using proxy for this request")
        
        scraper = GoogleRankScraper(proxy=proxy)
        position = await scraper.get_ranking(kw['keyword'], kw['url'])
        
        logger.info(f"Result for '{kw['keyword']}': Position = {position}")
        
        db.add_position_check(kw['id'], position)
        
        results.append({
            "keyword_id": kw['id'],
            "keyword": kw['keyword'],
            "position": position,
            "status": "found" if position else "not_in_top_30"
        })
        
        # Add delay between checks to avoid rate limiting
        if i < len(keywords):  # Don't delay after the last one
            logger.info("Waiting 3 seconds before next check...")
            await asyncio.sleep(3)
    
    logger.info(f"Completed all checks. Total: {len(results)}")
    return {"results": results}

@app.get("/api/history/{keyword_id}")
async def get_history(keyword_id: int):
    """Get position history for a keyword"""
    history = db.get_position_history(keyword_id)
    return {"keyword_id": keyword_id, "history": history}

@app.delete("/api/keyword/{keyword_id}")
async def delete_keyword(keyword_id: int):
    """Delete a tracked keyword"""
    db.delete_keyword(keyword_id)
    return {"message": "Keyword deleted successfully"}