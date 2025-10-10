import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import requests
import random
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def transcribe_with_whisper(audio_path):
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
        logger.error("âš ï¸ Whisper not available!")
        logger.error("Install with: pip install openai-whisper")
        logger.error("Or set OPENAI_API_KEY in environment")
        return None
    except Exception as e:
        logger.error(f"Error with local Whisper: {e}")
        return None

def test_captcha_full_solve():
    """
    Test COMPLETE CAPTCHA solving with VISIBLE browser
    """
    driver = None
    try:
        logger.info("=" * 60)
        logger.info("CAPTCHA FULL SOLVE TEST - VISIBLE BROWSER MODE")
        logger.info("=" * 60)
        
        # Setup Chrome WITHOUT headless mode
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        logger.info("Starting Chrome browser (VISIBLE)...")
        driver = uc.Chrome(options=options)
        
        # Go to reCAPTCHA demo page
        demo_url = "https://www.google.com/recaptcha/api2/demo"
        logger.info(f"Navigating to: {demo_url}")
        driver.get(demo_url)
        
        time.sleep(2)
        logger.info(f"Page loaded: {driver.title}")
        
        # ===== STEP 1: Click checkbox =====
        logger.info("\n" + "=" * 60)
        logger.info("STEP 1: Clicking reCAPTCHA checkbox...")
        logger.info("=" * 60)
        
        checkbox_iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha'][src*='anchor']")
        logger.info(f"Found {len(checkbox_iframes)} checkbox iframes")
        
        driver.switch_to.frame(checkbox_iframes[0])
        checkbox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "recaptcha-checkbox-border"))
        )
        checkbox.click()
        logger.info("âœ“ Clicked checkbox!")
        driver.switch_to.default_content()
        
        # ===== STEP 2: Wait for challenge =====
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: Waiting for challenge...")
        logger.info("=" * 60)
        time.sleep(3)
        
        # ===== STEP 3: Click audio button =====
        logger.info("\n" + "=" * 60)
        logger.info("STEP 3: Clicking audio button...")
        logger.info("=" * 60)
        
        challenge_iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha'][src*='bframe']")
        driver.switch_to.frame(challenge_iframes[0])
        
        audio_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "recaptcha-audio-button"))
        )
        audio_button.click()
        logger.info("âœ“ Clicked audio button!")
        
        # ===== STEP 4: Download audio =====
        logger.info("\n" + "=" * 60)
        logger.info("STEP 4: Downloading audio...")
        logger.info("=" * 60)
        
        time.sleep(5)
        
        download_link = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.rc-audiochallenge-tdownload-link"))
        )
        audio_url = download_link.get_attribute('href')
        logger.info(f"âœ“ Found audio URL")
        
        # Download audio
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        audio_response = requests.get(audio_url, headers=headers, timeout=20)
        
        if audio_response.status_code != 200:
            logger.error(f"Failed to download audio: {audio_response.status_code}")
            input("Press Enter to close...")
            return
        
        audio_path = "captcha_audio_test.mp3"
        with open(audio_path, 'wb') as f:
            f.write(audio_response.content)
        logger.info(f"âœ“ Audio downloaded ({len(audio_response.content)} bytes)")
        
        # ===== STEP 5: Transcribe audio =====
        logger.info("\n" + "=" * 60)
        logger.info("STEP 5: Transcribing audio with Whisper...")
        logger.info("=" * 60)
        
        transcription = transcribe_with_whisper(audio_path)
        
        if not transcription:
            logger.error("Failed to transcribe audio")
            input("Press Enter to close...")
            return
        
        # Clean transcription
        transcription_clean = ''.join(c for c in transcription if c.isalnum()).strip()
        logger.info(f"âœ“ Transcription: '{transcription_clean}'")
        logger.info(f"   (Original: '{transcription}')")
        
        # ===== STEP 6: Enter transcription =====
        logger.info("\n" + "=" * 60)
        logger.info("STEP 6: Entering transcription...")
        logger.info("=" * 60)
        
        input_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "audio-response"))
        )
        input_field.clear()
        time.sleep(0.5)
        
        # Type slowly like a human
        logger.info("Typing answer...")
        for char in transcription_clean.lower():
            input_field.send_keys(char)
            time.sleep(random.uniform(0.15, 0.35))
        
        logger.info("âœ“ Transcription entered")
        time.sleep(1)
        
        # ===== STEP 7: Submit =====
        logger.info("\n" + "=" * 60)
        logger.info("STEP 7: Submitting answer...")
        logger.info("=" * 60)
        
        verify_button = driver.find_element(By.ID, "recaptcha-verify-button")
        verify_button.click()
        logger.info("âœ“ Clicked verify button")
        
        # Wait for result
        time.sleep(5)
        
        # Switch back to default content
        driver.switch_to.default_content()
        
        # ===== STEP 8: Check if solved =====
        logger.info("\n" + "=" * 60)
        logger.info("STEP 8: Checking if CAPTCHA was solved...")
        logger.info("=" * 60)
        
        # Check for success - look for the submit button being enabled
        try:
            submit_button = driver.find_element(By.ID, "recaptcha-demo-submit")
            is_disabled = submit_button.get_attribute("disabled")
            
            if is_disabled:
                logger.warning("âš ï¸ CAPTCHA still active - Submit button is disabled")
                logger.info("This might mean the transcription was wrong")
            else:
                logger.info("ðŸŽ‰ SUCCESS! CAPTCHA SOLVED!")
                logger.info("Submit button is now enabled!")
                
                # Optionally click submit to complete the demo
                logger.info("\nClicking submit button to complete demo...")
                submit_button.click()
                time.sleep(2)
                logger.info("âœ“ Demo form submitted!")
        except Exception as e:
            logger.error(f"Error checking submit button: {e}")
        
        # Keep browser open
        logger.info("\n" + "=" * 60)
        logger.info("Browser will stay open for inspection")
        logger.info("Check if the CAPTCHA shows a green checkmark!")
        logger.info("Press Enter to close the browser...")
        logger.info("=" * 60)
        input()
        
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        input("Press Enter to close...")
        
    finally:
        # Cleanup
        if os.path.exists("captcha_audio_test.mp3"):
            try:
                os.remove("captcha_audio_test.mp3")
            except:
                pass
        
        if driver:
            logger.info("Closing browser...")
            driver.quit()
            logger.info("Browser closed")

if __name__ == "__main__":
    test_captcha_full_solve()