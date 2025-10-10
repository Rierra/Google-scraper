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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleRankScraper:
    def __init__(self, proxy=None):
        self.proxy = proxy
        self.proxy_extension_path = None
        
    async def _handle_captcha(self, driver):
        """
        Attempt to solve reCAPTCHA by clicking the checkbox.
        Returns True if successful, False otherwise.
        """
        try:
            # Wait a bit for CAPTCHA to fully load
            time.sleep(2)
            
            # Try to find and click the reCAPTCHA checkbox
            # reCAPTCHA v2 checkbox selectors
            checkbox_selectors = [
                'iframe[src*="recaptcha"]',
                'iframe[title*="reCAPTCHA"]',
                'div.g-recaptcha',
            ]
            
            for selector in checkbox_selectors:
                try:
                    logger.info(f"Looking for CAPTCHA with selector: {selector}")
                    
                    if 'iframe' in selector:
                        # Switch to reCAPTCHA iframe
                        iframes = driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for iframe in iframes:
                            logger.info(f"Found iframe: {iframe.get_attribute('src')}")
                            driver.switch_to.frame(iframe)
                            
                            # Look for the checkbox inside iframe
                            try:
                                checkbox = driver.find_element(By.CSS_SELECTOR, '.recaptcha-checkbox-border')
                                logger.info("Found reCAPTCHA checkbox!")
                                
                                # Click it
                                checkbox.click()
                                logger.info("Clicked checkbox!")
                                
                                # Switch back to main content
                                driver.switch_to.default_content()
                                
                                # Wait to see if it was successful
                                time.sleep(5)
                                
                                # Check if we're past the CAPTCHA
                                if "unusual traffic" not in driver.page_source.lower():
                                    logger.info("✓ CAPTCHA appears to be solved!")
                                    return True
                                else:
                                    logger.warning("Checkbox clicked but CAPTCHA still present")
                                    
                                    # Check if image challenge appeared
                                    driver.switch_to.default_content()
                                    if self._has_image_challenge(driver):
                                        logger.warning("⚠️  Image challenge detected - cannot auto-solve")
                                        logger.warning("Please solve manually or integrate 2Captcha service")
                                        # Wait 60 seconds for manual solving
                                        logger.info("Waiting 60 seconds for manual intervention...")
                                        time.sleep(60)
                                        return "unusual traffic" not in driver.page_source.lower()
                                    
                            except Exception as e:
                                logger.debug(f"Checkbox not found in this iframe: {e}")
                                driver.switch_to.default_content()
                                continue
                                
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            logger.warning("Could not find or click CAPTCHA checkbox")
            return False
            
        except Exception as e:
            logger.error(f"Error handling CAPTCHA: {e}")
            return False
    
    def _has_image_challenge(self, driver):
        """Check if image-based CAPTCHA challenge is present"""
        try:
            image_challenge_indicators = [
                'iframe[title*="challenge"]',
                'div.rc-imageselect',
                'div.recaptcha-challenge-image',
            ]
            
            for indicator in image_challenge_indicators:
                elements = driver.find_elements(By.CSS_SELECTOR, indicator)
                if elements:
                    return True
            return False
        except:
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
    
    def _is_organic_result(self, element, driver):
        """Check if an element is an organic search result"""
        try:
            # Check if parent is a standard search result container
            parent = element.find_element(By.XPATH, './ancestor::div[contains(@class, "g")]')
            
            # Exclude ads - check for ad indicators
            try:
                ad_indicators = parent.find_elements(By.XPATH, './/span[contains(text(), "Ad") or contains(text, "Sponsored")]')
                if ad_indicators:
                    return False
            except:
                pass
            
            # Exclude knowledge panel, featured snippets, etc.
            excluded_classes = ['kp-', 'knowledge', 'card-section', 'related-question']
            parent_classes = parent.get_attribute('class') or ''
            for excluded in excluded_classes:
                if excluded in parent_classes:
                    return False
            
            return True
        except:
            # If we can't find standard parent, it might not be organic
            return False
        
    async def get_ranking(self, keyword, target_url, max_results=30):
        """
        Search Google for keyword and find position of target_url
        Returns: position (1-30) or None if not found
        """
        logger.info(f"Starting rank check for keyword: '{keyword}', URL: '{target_url}'")
        
        driver = None
        try:
            # Setup undetected Chrome
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
            options.add_argument('--disable-images')
            # options.add_argument('--disable-javascript')  # We need JS for Google, so keeping enabled
            
            # Handle proxy with extension for authentication
            if self.proxy:
                logger.info("Setting up proxy with authentication extension...")
                self.proxy_extension_path = self._create_proxy_extension(self.proxy)
                if self.proxy_extension_path:
                    options.add_argument(f'--load-extension={self.proxy_extension_path}')
                    logger.info("Proxy extension loaded")
            
            logger.info("Starting undetected Chrome browser...")
            driver = uc.Chrome(options=options, version_main=None)
            
            # Navigate to Google
            search_url = f'https://www.google.com/search?q={quote_plus(keyword)}&num=30'
            logger.info(f"Navigating to: {search_url}")
            driver.get(search_url)
            
            # Wait for page to load and JavaScript to execute
            logger.info("Waiting for search results to load...")
            
            # Wait for the search input to be present (indicates page loaded)
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
            
            # Check for CAPTCHA and try to solve it
            if "unusual traffic" in driver.page_source.lower() or "recaptcha" in driver.page_source.lower():
                logger.warning("⚠️  CAPTCHA detected! Attempting to solve...")
                driver.save_screenshot('captcha_detected.png')
                
                if await self._handle_captcha(driver):
                    logger.info("✓ CAPTCHA solved! Continuing...")
                    time.sleep(3)
                else:
                    logger.error("✗ Failed to solve CAPTCHA")
                    return None
            
            # Find all search result links - IMPROVED METHOD
            logger.info("Extracting search results...")
            
            links = []
            seen_domains = {}  # Track domain occurrences to avoid duplicates
            
            # Wait for search results to be present
            try:
                logger.info("Waiting for result containers to appear...")
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div#search'))
                )
                logger.info("Search container found")
                
                # Give extra time for all results to render
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Timeout waiting for results: {e}")
            
            # Try multiple selectors for result containers
            result_containers = []
            container_selectors = [
                'div.g',  # Standard desktop results
                'div[data-sokoban-container]',  # Alternative container
                'div.Gx5Zad',  # Mobile-style results sometimes appear
            ]
            
            for selector in container_selectors:
                try:
                    containers = driver.find_elements(By.CSS_SELECTOR, selector)
                    if containers:
                        result_containers = containers
                        logger.info(f"Found {len(containers)} result containers with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
            
            if not result_containers:
                logger.warning("No result containers found with any selector")
                # Try to find ANY links in the search section as fallback
                try:
                    search_div = driver.find_element(By.CSS_SELECTOR, 'div#search')
                    all_links = search_div.find_elements(By.CSS_SELECTOR, 'a[href]')
                    logger.info(f"Fallback: Found {len(all_links)} total links in search div")
                    
                    # Filter these links
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
                                    # Check if parent has ad indicator
                                    parent_text = link.find_element(By.XPATH, './ancestor::div[1]').text
                                    if 'Ad' not in parent_text and 'Sponsored' not in parent_text:
                                        links.append(href)
                                        seen_domains[domain] = len(links)
                                        logger.debug(f"Fallback position {len(links)}: {href}")
                        except:
                            continue
                except Exception as e:
                    logger.error(f"Fallback extraction failed: {e}")
            else:
                # Process containers normally
                for container in result_containers:
                    try:
                        # Check if this is "People also ask" or other non-organic result
                        try:
                            # Check for People Also Ask section
                            if container.find_elements(By.CSS_SELECTOR, 'div[jsname="yEVEwb"]'):
                                logger.debug("Skipping 'People also ask' section")
                                continue
                            
                            # Check for related searches, knowledge panels, etc.
                            container_classes = container.get_attribute('class') or ''
                            excluded_patterns = ['related-question', 'kp-blk', 'knowledge', 'osrp-blk']
                            if any(pattern in container_classes for pattern in excluded_patterns):
                                logger.debug(f"Skipping non-organic section: {container_classes}")
                                continue
                        except:
                            pass
                        
                        # Check if this is an ad
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
                        
                        # Get the main link from this container
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
                        
                        # Skip if no proper link found (might be a PAA or other element)
                        if not link_elem:
                            logger.debug("No link found in container, skipping")
                            continue
                        
                        if link_elem:
                            href = link_elem.get_attribute('href')
                            
                            # Filter out Google's own URLs and invalid links
                            if (href and 
                                href.startswith('http') and 
                                'google.com' not in href and
                                'google.co.' not in href and
                                'webcache.googleusercontent.com' not in href):
                                
                                # Extract domain for duplicate checking
                                try:
                                    domain = urlparse(href).netloc
                                    
                                    # Only add first occurrence of each domain (avoids sitelinks)
                                    if domain not in seen_domains:
                                        links.append(href)
                                        seen_domains[domain] = len(links)
                                        logger.debug(f"Position {len(links)}: {href}")
                                    else:
                                        logger.debug(f"Skipping duplicate domain: {domain}")
                                        
                                except Exception as e:
                                    logger.debug(f"Error parsing URL {href}: {e}")
                                    
                    except Exception as e:
                        logger.debug(f"Error processing container: {e}")
                        continue
            
            if not links:
                logger.warning("No links found - saving debug files...")
                driver.save_screenshot('no_results.png')
                with open('no_results.html', 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                
                # Check if it's actually a Google page
                if 'google' not in driver.title.lower():
                    logger.error(f"Not on Google! Page title: {driver.title}")
                    return None
            
            logger.info(f"Found {len(links)} unique organic results")
            
            # Check for target URL
            position = None
            target_domain = urlparse(target_url).netloc
            logger.info(f"Looking for domain: {target_domain}")
            
            for idx, href in enumerate(links[:max_results], 1):
                try:
                    link_domain = urlparse(href).netloc
                    
                    # Match by full URL or domain
                    if target_url in href or target_domain == link_domain or target_domain in link_domain:
                        position = idx
                        logger.info(f"✓ FOUND at position {position}!")
                        logger.info(f"   Matched URL: {href}")
                        break
                except:
                    continue
            
            if position is None:
                logger.info(f"✗ Not found in top {max_results} results")
                if links:
                    logger.info(f"All results found:")
                    for idx, link in enumerate(links[:10], 1):
                        logger.info(f"  {idx}. {link}")
            
            return position
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}", exc_info=True)
            return None
            
        finally:
            if driver:
                logger.info("Closing browser...")
                driver.quit()
                logger.info("Browser closed")
            
            # Cleanup proxy extension
            if self.proxy_extension_path and os.path.exists(self.proxy_extension_path):
                try:
                    import shutil
                    shutil.rmtree(os.path.dirname(self.proxy_extension_path))
                except:
                    pass