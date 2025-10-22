import sys
import asyncio
import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from passlib.context import CryptContext
from jose import JWTError, jwt

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

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional, List

from scraper import GoogleRankScraper
from database import Database

# --- Authentication Configuration ---
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

if not SECRET_KEY:
    logger.error("SECRET_KEY environment variable not set. Authentication will not work.")
    # For development, you might want to set a default or raise an error
    # For production, this should always be set.
    SECRET_KEY = "super-secret-key" # Fallback for development, DO NOT USE IN PRODUCTION

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")

if not ADMIN_PASSWORD_HASH:
    logger.warning("ADMIN_PASSWORD_HASH not set. Please set it in .env for secure authentication.")
    # For development, you might want to generate one or use a default
    # For production, this should always be set.
    # Example: python -c "import bcrypt; print(bcrypt.hashpw(b'your_dev_password', bcrypt.gensalt()).decode('utf-8'))"
    ADMIN_PASSWORD_HASH = pwd_context.hash("dev_password") # Fallback for development, DO NOT USE IN PRODUCTION
# --- End Authentication Configuration ---

app = FastAPI(title="Google Rank Tracker API")

# CORS middleware for frontend
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,https://google-scraper-frontend.onrender.com').split(',')
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
    country: Optional[str] = None
    proxy: Optional[str] = None

class KeywordResponse(BaseModel):
    id: int
    keyword: str
    url: str
    country: Optional[str]
    proxy: Optional[str]
    position: Optional[int]
    checked_at: Optional[str]
    created_at: str

class CheckRequest(BaseModel):
    keyword_id: Optional[int] = None  # If None, check all

# --- Authentication Models ---
class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    username: str
    password: str
# --- End Authentication Models ---

# --- Authentication Functions ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def authenticate_user(username: str, password: str):
    if username == ADMIN_USERNAME and verify_password(password, ADMIN_PASSWORD_HASH):
        return {"username": ADMIN_USERNAME}
    return None

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return {"username": username}
    except JWTError:
        raise credentials_exception
# --- End Authentication Functions ---

@app.get("/")
async def root():
    return {"message": "Google Rank Tracker API", "status": "running"}

@app.on_event("startup")
async def startup_event():
    print("Registered routes:")
    for route in app.routes:
        print(f"  {route.methods if hasattr(route, 'methods') else 'N/A'} {route.path}")

@app.post("/api/login", response_model=Token)
async def login_for_access_token(form_data: LoginRequest):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/track")
async def add_tracking(data: KeywordCreate, current_user: dict = Depends(get_current_user)):
    """Add new keyword to track"""
    keyword_id = db.add_keyword(data.keyword, data.url, data.country, data.proxy)
    if keyword_id is None:
        raise HTTPException(status_code=400, detail="Keyword with this URL and country is already being tracked")
    
    return {"id": keyword_id, "message": "Keyword added successfully"}

@app.get("/api/keywords")
async def get_keywords(current_user: dict = Depends(get_current_user)):
    """Get all tracked keywords with latest position"""
    keywords = db.get_all_keywords()
    return {"keywords": keywords}

# Global variable to store keywords that need processing
pending_keywords = []

@app.get("/api/check")
async def get_pending_keywords(current_user: dict = Depends(get_current_user)):
    """Get keywords that need to be processed by local scraper"""
    global pending_keywords
    if pending_keywords:
        keywords = pending_keywords.copy()
        pending_keywords.clear()  # Clear after returning
        return {"keywords": keywords}
    else:
        raise HTTPException(status_code=404, detail="No keywords pending")

@app.post("/api/check")
async def check_rankings(data: CheckRequest = CheckRequest(), current_user: dict = Depends(get_current_user)):
    """Queue keywords for local scraping (visible browser)"""
    global pending_keywords
    logger.info(f"Received check request: {data}")
    
    if data.keyword_id:
        keywords = [kw for kw in db.get_all_keywords() if kw['id'] == data.keyword_id]
    else:
        keywords = db.get_all_keywords()
    
    if not keywords:
        logger.warning("No keywords found to check")
        raise HTTPException(status_code=404, detail="No keywords found")
    
    # Add keywords to pending list for local scraper to pick up
    pending_keywords = keywords
    
    logger.info(f"Queued {len(keywords)} keyword(s) for local processing...")
    
    return {
        "message": "Keywords queued for local processing with visible browser",
        "status": "queued",
        "total_keywords": len(keywords)
    }

@app.post("/api/update-position")
async def update_position(data: dict, current_user: dict = Depends(get_current_user)):
    """Update position from local scraper"""
    keyword_id = data.get('keyword_id')
    position = data.get('position')
    
    if not keyword_id:
        raise HTTPException(status_code=400, detail="keyword_id is required")
    
    db.add_position_check(keyword_id, position)
    logger.info(f"Updated position for keyword {keyword_id}: {position}")
    
    return {"status": "updated", "keyword_id": keyword_id, "position": position}

@app.get("/api/history/{keyword_id}")
async def get_history(keyword_id: int, current_user: dict = Depends(get_current_user)):
    """Get position history for a keyword"""
    history = db.get_position_history(keyword_id)
    return {"keyword_id": keyword_id, "history": history}

@app.delete("/api/keyword/{keyword_id}")
async def delete_keyword(keyword_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a tracked keyword"""
    db.delete_keyword(keyword_id)
    return {"message": "Keyword deleted successfully"}