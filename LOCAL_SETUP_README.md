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
- **Processes keywords**: Automatically scrapes keywords queued by your boss
- **Updates results**: Sends results back to the deployed backend
- **Runs continuously**: Checks for new keywords every 60 seconds

## 🌐 Your URLs

- **Frontend (for your boss)**: `https://google-scraper-frontend.onrender.com`
- **Backend**: `https://google-scraper-1.onrender.com`

## 🔄 How It Works

1. **Your boss opens the frontend** and adds keywords
2. **Boss clicks "Check All"** → backend queues the tasks
3. **Your local scraper** (this script) connects and processes the tasks
4. **Chrome opens on your PC** and scrapes Google search results
5. **Results are sent back** to the backend automatically
6. **Frontend updates** with the new rankings

## ⚙️ Manual Setup (if needed)

If the batch files don't work, run these commands manually:

```bash
# Install dependencies
pip install requests undetected-chromedriver selenium

# Start scraper
python start_local_scraper.py
```

## 🛑 Stopping the Scraper

- Press `Ctrl+C` in the terminal to stop
- Or close the terminal window

## 🔧 Troubleshooting

- **"Module not found"**: Run `setup_local.bat` first
- **"Connection failed"**: Check if your backend is deployed and running
- **Chrome issues**: Make sure Chrome is installed on your PC

## 📝 Notes

- The scraper runs with a **visible browser** (headless=False)
- It processes keywords every **60 seconds**
- **5-second delay** between keywords to avoid rate limiting
- Results are automatically sent to your deployed backend
