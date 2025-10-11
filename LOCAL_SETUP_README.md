# 🎯 Google Rank Tracker - Local Setup

Your hybrid setup is ready! This guide will help you run the local scraper on your PC.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Run the setup script
setup_local.bat
```

### 2. Start Local Scraper
```bash
# Double-click or run
start_scraper.bat
```

## 📋 What This Does

- **Connects to your deployed backend**: `https://google-scraper-1.onrender.com`
- **Runs visible browser**: Chrome will open on your PC for scraping
- **Processes keywords**: Scrapes all pending keywords in one run
- **Updates results**: Sends results back to the deployed backend
- **Runs once**: Processes all keywords and exits (no continuous polling)

## 🌐 Your URLs

- **Frontend (for your boss)**: `https://google-scraper-frontend.onrender.com`
- **Backend**: `https://google-scraper-1.onrender.com`

## 🔄 How It Works

1. **Your boss opens the frontend** and adds keywords
2. **Boss clicks "Check All"** → backend queues the tasks
3. **You run the local scraper** when you want to check rankings (once per day)
4. **Chrome opens on your PC** and scrapes Google search results
5. **Results are sent back** to the backend automatically
6. **Frontend updates** with the new rankings
7. **Script exits** after processing all keywords

## ⚙️ Manual Setup (if needed)

If the batch files don't work, run these commands manually:

```bash
# Install dependencies
pip install requests undetected-chromedriver selenium

# Start scraper
python start_local_scraper.py
```

## 🛑 Stopping the Scraper

- The script runs once and exits automatically
- Press `Ctrl+C` if you need to stop mid-processing

## 🔧 Troubleshooting

- **"Module not found"**: Run `setup_local.bat` first
- **"Connection failed"**: Check if your backend is deployed and running
- **Chrome issues**: Make sure Chrome is installed on your PC

## 📝 Notes

- The scraper runs with a **visible browser** (headless=False)
- It processes **all keywords once** and then exits
- **5-second delay** between keywords to avoid rate limiting
- Results are automatically sent to your deployed backend
- **Perfect for daily rank checks** - run once per day manually
