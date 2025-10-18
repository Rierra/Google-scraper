import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse, quote_plus
import time
import random
import logging
import os
import tempfile
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleRankScraper:
    def __init__(self, proxy=None):
        self.proxy = proxy
        self.proxy_extension_path = None
    
    def _create_chrome_options(self):
        """Create a fresh ChromeOptions object for each scraping session"""
        options = uc.ChromeOptions()
        
        # Use headless mode in production if configured
        if os.getenv('CHROME_HEADLESS', 'false').lower() == 'true':
            options.add_argument('--headless=new')
        
        # Essential arguments for deployment
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-gpu')
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        
        # DON'T disable images for CAPTCHA solving - we need to see the audio button
        # options.add_argument('--disable-images')  # REMOVED
        
        # Handle proxy with extension for authentication
        if self.proxy:
            logger.info("Setting up proxy with authentication extension...")
            self.proxy_extension_path = self._create_proxy_extension(self.proxy)
            if self.proxy_extension_path:
                options.add_argument(f'--load-extension={self.proxy_extension_path}')
                logger.info("Proxy extension loaded")
        
        return options
    
    def _transcribe_with_whisper(self, audio_path):
        """
        Transcribe audio using OpenAI Whisper API or local model
        """
        # Try API first if key is available
        whisper_api_key = os.getenv('OPENAI_API_KEY')
        
        if whisper_api_key:
            try:
                logger.info("Using OpenAI Whisper API...")
                url = "https://api.openai.com/v1/audio/transcriptions"
                headers = {
                    "Authorization": f"Bearer {whisper_api_key}"
                }
                
                with open(audio_path, 'rb') as audio_file:
                    files = {
                        'file': ('audio.mp3', audio_file, 'audio/mpeg'),
                    }
                    data = {
                        'model': 'whisper-1'
                    }
                    
                    response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        text = result.get('text', '').strip()
                        return text
                    else:
                        logger.warning(f"Whisper API error: {response.status_code}, falling back to local")
                        
            except Exception as e:
                logger.warning(f"Whisper API failed: {e}, falling back to local")
        
        # Fall back to local Whisper
        try:
            import whisper
            
            logger.info("Using local Whisper model...")
            model = whisper.load_model("base")
            result = model.transcribe(audio_path)
            text = result["text"].strip()
            return text
            
        except ImportError:
            logger.error("⚠️ Whisper not available!")
            logger.error("Install with: pip install openai-whisper")
            logger.error("Or set OPENAI_API_KEY in environment")
            return None
        except Exception as e:
            logger.error(f"Error with local Whisper: {e}")
            return None
    
    async def _solve_audio_captcha(self, driver):
        """
        Solve reCAPTCHA using audio challenge method
        Returns True if successful, False otherwise
        """
        try:
            logger.info("=" * 60)
            logger.info("ATTEMPTING AUDIO CAPTCHA SOLVE")
            logger.info("=" * 60)
            
            # Give CAPTCHA time to fully load
            time.sleep(3)
            
            # ===== STEP 1: Click checkbox =====
            logger.info("STEP 1: Looking for reCAPTCHA checkbox...")
            
            checkbox_iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha'][src*='anchor']")
            
            if not checkbox_iframes:
                logger.warning("No reCAPTCHA checkbox iframe found")
                return False
            
            logger.info(f"Found {len(checkbox_iframes)} checkbox iframe(s)")
            driver.switch_to.frame(checkbox_iframes[0])
            
            try:
                checkbox = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "recaptcha-checkbox-border"))
                )
                checkbox.click()
                logger.info("✓ Clicked checkbox!")
                driver.switch_to.default_content()
            except Exception as e:
                logger.error(f"Failed to click checkbox: {e}")
                driver.switch_to.default_content()
                return False
            
            # ===== STEP 2: Wait for challenge iframe =====
            logger.info("STEP 2: Waiting for challenge iframe...")
            time.sleep(3)
            
            # Check if checkbox alone was enough (sometimes it is!)
            if "unusual traffic" not in driver.page_source.lower():
                logger.info("✓ Checkbox click was sufficient! No challenge needed.")
                return True
            
            # ===== STEP 3: Click audio button =====
            logger.info("STEP 3: Looking for audio button...")
            
            challenge_iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha'][src*='bframe']")
            
            if not challenge_iframes:
                logger.warning("No challenge iframe found")
                return False
            
            driver.switch_to.frame(challenge_iframes[0])
            
            try:
                audio_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "recaptcha-audio-button"))
                )
                audio_button.click()
                logger.info("✓ Clicked audio button!")
            except Exception as e:
                logger.error(f"Failed to click audio button: {e}")
                driver.switch_to.default_content()
                return False
            
            # ===== STEP 4: Download audio =====
            logger.info("STEP 4: Downloading audio challenge...")
            time.sleep(5)  # Wait for audio to load
            
            try:
                download_link = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.rc-audiochallenge-tdownload-link"))
                )
                audio_url = download_link.get_attribute('href')
                logger.info("✓ Found audio download link")
                
                # Download audio file
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                audio_response = requests.get(audio_url, headers=headers, timeout=20)
                
                if audio_response.status_code != 200:
                    logger.error(f"Failed to download audio: {audio_response.status_code}")
                    driver.switch_to.default_content()
                    return False
                
                audio_path = f"captcha_audio_{int(time.time())}.mp3"
                with open(audio_path, 'wb') as f:
                    f.write(audio_response.content)
                logger.info(f"✓ Audio downloaded ({len(audio_response.content)} bytes)")
                
            except Exception as e:
                logger.error(f"Failed to download audio: {e}")
                driver.switch_to.default_content()
                return False
            
            # ===== STEP 5: Transcribe audio =====
            logger.info("STEP 5: Transcribing audio...")
            
            transcription = self._transcribe_with_whisper(audio_path)
            
            # Cleanup audio file
            try:
                os.remove(audio_path)
            except:
                pass
            
            if not transcription:
                logger.error("Failed to transcribe audio")
                driver.switch_to.default_content()
                return False
            
            # Clean transcription - remove spaces, special characters
            transcription_clean = ''.join(c for c in transcription if c.isalnum()).strip()
            logger.info(f"✓ Transcription: '{transcription_clean}'")
            
            # ===== STEP 6: Enter transcription =====
            logger.info("STEP 6: Entering transcription...")
            
            try:
                input_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "audio-response"))
                )
                input_field.clear()
                time.sleep(0.5)
                
                # Type slowly like a human
                for char in transcription_clean.lower():
                    input_field.send_keys(char)
                    time.sleep(random.uniform(0.1, 0.3))
                
                logger.info("✓ Transcription entered")
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to enter transcription: {e}")
                driver.switch_to.default_content()
                return False
            
            # ===== STEP 7: Submit =====
            logger.info("STEP 7: Submitting answer...")
            
            try:
                verify_button = driver.find_element(By.ID, "recaptcha-verify-button")
                verify_button.click()
                logger.info("✓ Clicked verify button")
                
                # Wait for verification
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Failed to submit: {e}")
                driver.switch_to.default_content()
                return False
            
            # Switch back to main content
            driver.switch_to.default_content()
            
            # ===== STEP 8: Verify success =====
            logger.info("STEP 8: Checking if CAPTCHA was solved...")
            time.sleep(2)
            
            # Check if "unusual traffic" message is gone
            page_source = driver.page_source.lower()
            
            if "unusual traffic" not in page_source and "recaptcha" not in page_source:
                logger.info("🎉 SUCCESS! CAPTCHA SOLVED!")
                logger.info("=" * 60)
                return True
            else:
                logger.warning("⚠️ CAPTCHA still present - transcription may have been wrong")
                logger.info("Page will continue, but might need manual intervention")
                
                # Try one more time with a fresh attempt
                logger.info("Attempting audio challenge again...")
                driver.switch_to.frame(challenge_iframes[0])
                
                try:
                    # Click reload button for new audio
                    reload_button = driver.find_element(By.ID, "recaptcha-reload-button")
                    reload_button.click()
                    logger.info("Clicked reload for new audio challenge")
                    time.sleep(3)
                    
                    # Repeat the process once more
                    download_link = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a.rc-audiochallenge-tdownload-link"))
                    )
                    audio_url = download_link.get_attribute('href')
                    audio_response = requests.get(audio_url, headers=headers, timeout=20)
                    
                    audio_path = f"captcha_audio_{int(time.time())}_retry.mp3"
                    with open(audio_path, 'wb') as f:
                        f.write(audio_response.content)
                    
                    transcription = self._transcribe_with_whisper(audio_path)
                    
                    try:
                        os.remove(audio_path)
                    except:
                        pass
                    
                    if transcription:
                        transcription_clean = ''.join(c for c in transcription if c.isalnum()).strip()
                        logger.info(f"Retry transcription: '{transcription_clean}'")
                        
                        input_field = driver.find_element(By.ID, "audio-response")
                        input_field.clear()
                        time.sleep(0.5)
                        
                        for char in transcription_clean.lower():
                            input_field.send_keys(char)
                            time.sleep(random.uniform(0.1, 0.3))
                        
                        verify_button = driver.find_element(By.ID, "recaptcha-verify-button")
                        verify_button.click()
                        time.sleep(5)
                        
                        driver.switch_to.default_content()
                        
                        page_source = driver.page_source.lower()
                        if "unusual traffic" not in page_source:
                            logger.info("🎉 SUCCESS on retry!")
                            return True
                    
                except Exception as e:
                    logger.error(f"Retry attempt failed: {e}")
                
                driver.switch_to.default_content()
                return False
                
        except Exception as e:
            logger.error(f"Error during audio CAPTCHA solve: {e}", exc_info=True)
            try:
                driver.switch_to.default_content()
            except:
                pass
            return False
    
    async def _handle_captcha(self, driver):
        """
        Main CAPTCHA handler - attempts audio solve first
        Returns True if successful, False otherwise
        """
        try:
            logger.info("⚠️ CAPTCHA detected!")
            driver.save_screenshot('captcha_detected.png')
            
            # Try audio solve method
            if await self._solve_audio_captcha(driver):
                return True
            
            # If audio solve failed, wait for manual intervention
            logger.warning("⚠️ Audio solve failed")
            logger.warning("Waiting 60 seconds for manual intervention...")
            time.sleep(60)
            
            # Check if manually solved
            if "unusual traffic" not in driver.page_source.lower():
                logger.info("✓ CAPTCHA cleared (possibly manual)")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling CAPTCHA: {e}")
            return False
    
    def _create_proxy_extension(self, proxy_url):
        """
        Create a Chrome extension to handle proxy authentication.
        This bypasses Chrome's proxy auth limitations.
        """
        if not proxy_url or '@' not in proxy_url:
            return None
            
        try:
            # Parse proxy URL: http://username:password@host:port
            parts = proxy_url.replace('http://', '').replace('https://', '')
            auth, host_port = parts.split('@')
            username, password = auth.split(':')
            host, port = host_port.split(':')
            
            # Create extension files
            manifest_json = """
            {
                "version": "1.0.0",
                "manifest_version": 2,
                "name": "Chrome Proxy",
                "permissions": [
                    "proxy",
                    "tabs",
                    "unlimitedStorage",
                    "storage",
                    "<all_urls>",
                    "webRequest",
                    "webRequestBlocking"
                ],
                "background": {
                    "scripts": ["background.js"]
                },
                "minimum_chrome_version":"22.0.0"
            }
            """
            
            background_js = """
            var config = {
                mode: "fixed_servers",
                rules: {
                  singleProxy: {
                    scheme: "http",
                    host: "%s",
                    port: parseInt(%s)
                  },
                  bypassList: ["localhost"]
                }
              };
            
            chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
            
            function callbackFn(details) {
                return {
                    authCredentials: {
                        username: "%s",
                        password: "%s"
                    }
                };
            }
            
            chrome.webRequest.onAuthRequired.addListener(
                        callbackFn,
                        {urls: ["<all_urls>"]},
                        ['blocking']
            );
            """ % (host, port, username, password)
            
            # Create temp directory for extension
            temp_dir = tempfile.mkdtemp()
            extension_dir = os.path.join(temp_dir, 'proxy_extension')
            os.makedirs(extension_dir, exist_ok=True)
            
            # Write manifest
            with open(os.path.join(extension_dir, 'manifest.json'), 'w') as f:
                f.write(manifest_json)
            
            # Write background script
            with open(os.path.join(extension_dir, 'background.js'), 'w') as f:
                f.write(background_js)
            
            logger.info(f"Created proxy extension at: {extension_dir}")
            return extension_dir
            
        except Exception as e:
            logger.error(f"Error creating proxy extension: {e}")
            return None
    
    def _extract_results_from_page(self, driver, seen_domains, current_position):
        """
        Extract organic search results from the current page.
        Returns: list of URLs found on this page
        """
        links = []
        
        logger.info("Extracting search results from current page...")
        
        # Wait for search results to be present
        try:
            logger.info("Waiting for result containers to appear...")
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div#search'))
            )
            logger.info("Search container found")
            time.sleep(2)
            
        except Exception as e:
            logger.warning(f"Timeout waiting for results: {e}")
        
        # Try multiple selectors for result containers
        result_containers = []
        container_selectors = [
            'div.g:not(.related-question-pair):not(.kp-blk)',
            'div[data-sokoban-container]',
            'div.Gx5Zad.fP1Qef',
            'div[jscontroller][data-hveid]',
        ]
        
        for selector in container_selectors:
            try:
                containers = driver.find_elements(By.CSS_SELECTOR, selector)
                valid_containers = [c for c in containers if c.text.strip()]
                if valid_containers:
                    result_containers = valid_containers
                    logger.info(f"Found {len(valid_containers)} result containers with selector: {selector}")
                    break
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
        
        if not result_containers:
            logger.warning("No result containers found with any selector")
            try:
                search_div = driver.find_element(By.CSS_SELECTOR, 'div#search')
                all_links = search_div.find_elements(By.CSS_SELECTOR, 'a[href]')
                logger.info(f"Fallback: Found {len(all_links)} total links in search div")
                
                for link in all_links:
                    try:
                        href = link.get_attribute('href')
                        if (href and 
                            href.startswith('http') and 
                            'google.com' not in href and
                            'google.co.' not in href and
                            'webcache' not in href):
                            
                            domain = urlparse(href).netloc
                            if domain not in seen_domains:
                                parent_text = link.find_element(By.XPATH, './ancestor::div[1]').text
                                if 'Ad' not in parent_text and 'Sponsored' not in parent_text:
                                    links.append(href)
                                    seen_domains[domain] = current_position + len(links)
                                    logger.debug(f"Fallback position {current_position + len(links)}: {href}")
                    except:
                        continue
            except Exception as e:
                logger.error(f"Fallback extraction failed: {e}")
        else:
            for container in result_containers:
                try:
                    # Skip "People also ask" sections
                    try:
                        if container.find_elements(By.CSS_SELECTOR, 'div[jsname="yEVEwb"]'):
                            logger.debug("Skipping 'People also ask' section")
                            continue
                        
                        container_classes = container.get_attribute('class') or ''
                        excluded_patterns = ['related-question', 'kp-blk', 'knowledge', 'osrp-blk']
                        if any(pattern in container_classes for pattern in excluded_patterns):
                            logger.debug(f"Skipping non-organic section: {container_classes}")
                            continue
                    except:
                        pass
                    
                    # Check for ads
                    is_ad = False
                    try:
                        container_text = container.text
                        if 'Ad' in container_text or 'Sponsored' in container_text:
                            logger.debug("Skipping ad result")
                            is_ad = True
                    except:
                        pass
                    
                    if is_ad:
                        continue
                    
                    # Find the main link
                    link_elem = None
                    link_selectors = [
                        'div.yuRUbf > a',
                        'a[jsname="UWckNb"]',
                        'h3 > a',
                        'a[href^="http"]',
                    ]
                    
                    for link_selector in link_selectors:
                        try:
                            link_elem = container.find_element(By.CSS_SELECTOR, link_selector)
                            if link_elem:
                                break
                        except:
                            continue
                    
                    if not link_elem:
                        logger.debug("No link found in container, skipping")
                        continue
                    
                    if link_elem:
                        href = link_elem.get_attribute('href')
                        
                        if (href and 
                            href.startswith('http') and 
                            'google.com' not in href and
                            'google.co.' not in href and
                            'webcache.googleusercontent.com' not in href):
                            
                            try:
                                domain = urlparse(href).netloc
                                
                                if domain not in seen_domains:
                                    links.append(href)
                                    seen_domains[domain] = current_position + len(links)
                                    logger.debug(f"Position {current_position + len(links)}: {href}")
                                else:
                                    logger.debug(f"Skipping duplicate domain: {domain}")
                                    
                            except Exception as e:
                                logger.debug(f"Error parsing URL {href}: {e}")
                                
                except Exception as e:
                    logger.debug(f"Error processing container: {e}")
                    continue
        
        logger.info(f"Extracted {len(links)} new results from this page")
        return links
    
    def _click_next_page(self, driver):
        """
        Click the 'Next' button to go to the next page of results.
        Returns True if successful, False if no next button found.
        """
        try:
            # Add random delay to appear more human-like
            time.sleep(random.uniform(2, 4))
            
            # Try multiple selectors for the Next button
            next_selectors = [
                'a#pnnext',  # Standard Next button ID
                'a[aria-label="Next page"]',
                'a span:contains("Next")',
                'td.d6cvqb a[id="pnnext"]',
            ]
            
            next_button = None
            for selector in next_selectors:
                try:
                    if ':contains' in selector:
                        # For text-based search, use XPath
                        next_button = driver.find_element(By.XPATH, "//a[contains(@id, 'pnnext') or contains(., 'Next')]")
                    else:
                        next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if next_button and next_button.is_displayed():
                        logger.info(f"Found Next button with selector: {selector}")
                        break
                except:
                    continue
            
            if not next_button:
                logger.info("No 'Next' button found - reached end of results")
                return False
            
            # Scroll to button to make sure it's in view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            time.sleep(1)
            
            # Click the next button
            next_button.click()
            logger.info("✓ Clicked 'Next' button")
            
            # Wait for new page to load
            time.sleep(random.uniform(3, 5))
            
            # Wait for search results to appear
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div#search'))
                )
                logger.info("Next page loaded successfully")
                return True
            except:
                logger.warning("Timeout waiting for next page to load")
                return False
                
        except Exception as e:
            logger.warning(f"Could not navigate to next page: {e}")
            return False
    
    async def get_ranking(self, keyword, target_url, country=None, max_results=100, max_pages=10):
        """
        Search Google for keyword and find position of target_url across multiple pages.
        
        Args:
            keyword: Search term
            target_url: URL to find
            country: Two-letter country code for search (e.g., 'us', 'ca')
            max_results: Maximum number of results to check (default: 100)
            max_pages: Maximum number of pages to scrape (default: 10)
        
        Returns: position (1-max_results) or None if not found
        """
        if country:
            logger.info(f"Starting rank check for keyword: '{keyword}', URL: '{target_url}', Country: '{country.upper()}'")
        else:
            logger.info(f"Starting rank check for keyword: '{keyword}', URL: '{target_url}'")
        logger.info(f"Will check up to {max_pages} pages or {max_results} results")
        
        driver = None
        try:
            # Create fresh options for this scraping session
            options = self._create_chrome_options()
            
            logger.info("Starting undetected Chrome browser...")
            driver = uc.Chrome(options=options, version_main=None)
            
            # Navigate to Google (start with first page)
            search_url = f'https://www.google.com/search?q={quote_plus(keyword)}'
            if country:
                search_url += f'&gl={country}'
            logger.info(f"Navigating to: {search_url}")
            driver.get(search_url)
            
            # Wait for page to load
            logger.info("Waiting for search results to load...")
            
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "q"))
                )
                logger.info("Search page loaded")
            except:
                logger.warning("Search input not found, but continuing...")
            
            # Additional wait for results to render
            time.sleep(random.uniform(3, 5))
            
            # Log page title to verify page loaded
            logger.info(f"Page title: {driver.title}")
            
            # Check for CAPTCHA on first page
            if "unusual traffic" in driver.page_source.lower() or "recaptcha" in driver.page_source.lower():
                if await self._handle_captcha(driver):
                    logger.info("✓ CAPTCHA solved! Continuing...")
                    time.sleep(3)
                else:
                    logger.error("✗ Failed to solve CAPTCHA")
                    return None
            
            # Track all links across pages
            all_links = []
            seen_domains = {}
            target_domain = urlparse(target_url).netloc
            logger.info(f"Looking for domain: {target_domain}")
            
            # Scrape multiple pages
            page_num = 1
            position = None
            
            while page_num <= max_pages and len(all_links) < max_results:
                logger.info(f"\n{'='*60}")
                logger.info(f"SCRAPING PAGE {page_num}")
                logger.info(f"{'='*60}")
                
                # Extract results from current page
                current_position = len(all_links)
                page_links = self._extract_results_from_page(driver, seen_domains, current_position)
                
                if not page_links:
                    logger.warning(f"No results found on page {page_num}")
                    
                    if page_num == 1:
                        # Save debug info for first page
                        driver.save_screenshot('no_results.png')
                        with open('no_results.html', 'w', encoding='utf-8') as f:
                            f.write(driver.page_source)
                        
                        if 'google' not in driver.title.lower():
                            logger.error(f"Not on Google! Page title: {driver.title}")
                            return None
                    
                    break
                
                # Add to all links
                all_links.extend(page_links)
                
                # Check if target is in this page's results
                for idx, href in enumerate(page_links, current_position + 1):
                    try:
                        link_domain = urlparse(href).netloc
                        
                        if target_url in href or target_domain == link_domain or target_domain in link_domain:
                            position = idx
                            logger.info(f"\n{'='*60}")
                            logger.info(f"✓ FOUND at position {position} (Page {page_num})!")
                            logger.info(f"   Matched URL: {href}")
                            logger.info(f"{'='*60}")
                            return position
                    except:
                        continue
                
                logger.info(f"Total results so far: {len(all_links)}")
                logger.info(f"Target not found yet, continuing to next page...")
                
                # Stop if we've checked enough results
                if len(all_links) >= max_results:
                    logger.info(f"Reached max_results limit ({max_results})")
                    break
                
                # Try to go to next page
                if not self._click_next_page(driver):
                    logger.info("No more pages available")
                    break
                
                page_num += 1
                
                # Check for CAPTCHA on subsequent pages
                if "unusual traffic" in driver.page_source.lower() or "recaptcha" in driver.page_source.lower():
                    logger.warning(f"CAPTCHA detected on page {page_num}")
                    if await self._handle_captcha(driver):
                        logger.info("✓ CAPTCHA solved! Continuing...")
                        time.sleep(3)
                    else:
                        logger.error("✗ Failed to solve CAPTCHA on subsequent page")
                        break
            
            # Target not found in any pages
            if position is None:
                logger.info(f"\n{'='*60}")
                logger.info(f"✗ Not found in top {len(all_links)} results ({page_num} pages)")
                logger.info(f"{'='*60}")
                if all_links:
                    logger.info(f"First 10 results found:")
                    for idx, link in enumerate(all_links[:10], 1):
                        logger.info(f"  {idx}. {link}")
            
            return position
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}", exc_info=True)
            return None
            
        finally:
            if driver:
                logger.info("Closing browser...")
                try:
                    driver.quit()
                    logger.info("Browser closed")
                except Exception as e:
                    logger.warning(f"Error during browser cleanup: {e}")
                    try:
                        driver.close()
                    except:
                        pass
                finally:
                    time.sleep(0.5)
                    driver = None
            
            # Cleanup proxy extension
            if self.proxy_extension_path and os.path.exists(self.proxy_extension_path):
                try:
                    import shutil
                    shutil.rmtree(os.path.dirname(self.proxy_extension_path))
                except:
                    pass