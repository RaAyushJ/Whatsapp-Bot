from parse_chat import extract_messages_from_whatsapp
from classify_messages import classify_message
from generate_report import create_daily_report
import config

chat_data = extract_messages_from_whatsapp()

final_data = []
for msg in chat_data:
    if msg['type'] in ['text', 'link', 'photo', 'video']:
        msg['category'] = classify_message(msg['message'], config.API_KEY)
        final_data.append(msg)
import os
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import google.generativeai as genai
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import base64
import re # For more robust date parsing

# --- Configuration Loading ---
# Ensure config.py exists and contains GEMINI_API_KEY, GROUP_NAME, DAYS_TO_EXTRACT
try:
    from config import GEMINI_API_KEY, GROUP_NAME, DAYS_TO_EXTRACT
except ImportError:
    print("Error: config.py not found or missing variables.")
    print("Please create config.py in the same directory with:")
    print("GEMINI_API_KEY = 'YOUR_GEMINI_API_KEY'")
    print("GROUP_NAME = 'Your WhatsApp Group Name'")
    print("DAYS_TO_EXTRACT = 1 # Number of days to extract chat history")
    exit(1)

# --- GLOBAL CONFIGURATION ---
# Configure Gemini API once at the start of the script
genai.configure(api_key=GEMINI_API_KEY)
# Use gemini-1.5-flash for multimodal capabilities (text + image).
# This replaces gemini-pro-vision, which was deprecated, and is better than text-only gemini-pro
GEMINI_MODEL_NAME = "gemini-1.5-flash"

def setup_driver():
    """Sets up the Selenium Chrome driver with user data and specific options."""
    options = Options()
    profile_path = os.path.abspath("user_data")
    os.makedirs(profile_path, exist_ok=True)
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--start-maximized")

    # Arguments to suppress common Chrome/WebDriver logs (e.g., DEPRECATED_ENDPOINT)
    # These warnings often come from Chrome itself and are hard to entirely eliminate
    # from Python, but these options help reduce log noise.
    options.add_argument("--log-level=3") # Suppress INFO, WARNING, ERROR messages from Chrome
    options.add_experimental_option('excludeSwitches', ['enable-logging']) # Exclude specific logging categories
    options.add_argument("--disable-notifications") # Disable browser notifications
    options.add_argument("--disable-background-networking") # Disable background network services
    options.add_argument("--disable-sync") # Disable Chrome sync

    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except WebDriverException as e:
        print(f"❌ WebDriver Error: {e}")
        print("Please ensure ChromeDriver is installed and its version matches your Chrome browser, or it's in your system PATH.")
        exit(1)

def wait_for_qr(driver, timeout=120):
    """Waits for the WhatsApp QR code login to complete."""
    print("🟡 Waiting for WhatsApp QR login...")
    try:
        # Wait for a stable element that appears after successful login (e.g., search input)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="chat-list-search"] | //div[@title="Search input"]'))
        )
        print("✅ WhatsApp logged in!")
    except TimeoutException:
        raise TimeoutError("QR login timed out. Please scan the QR code within the given time.")
    except Exception as e:
        print(f"An unexpected error occurred during QR wait: {e}")
        raise

def scroll_chat(driver, num_scrolls=20):
    """Scrolls the chat panel to load older messages."""
    print("⬇️ Scrolling to load messages...")
    try:
        # Attempt to find the main scrollable chat panel
        # Using data-testid if available, or a more generic pattern
        chat_panel_xpath = '//div[@data-testid="conversation-panel-header"]/following-sibling::div[1]/div[1]'
        
        try:
            chat_panel = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, chat_panel_xpath))
            )
        except TimeoutException:
            # Fallback to a common class if data-testid or specific structure changes
            print("Using fallback chat panel locator (may be less stable).")
            chat_panel = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class*="app-wrapper-web"] div[tabindex="-1"][role="region"]'))
            )

        last_height = driver.execute_script("return arguments[0].scrollHeight", chat_panel)
        
        for i in range(num_scrolls):
            driver.execute_script("arguments[0].scrollTop = 0", chat_panel) # Scroll to top
            time.sleep(1.5) # Allow time for content to load
            new_height = driver.execute_script("return arguments[0].scrollHeight", chat_panel)
            if new_height == last_height:
                print(f"No more messages loaded after {i+1} scrolls.")
                break
            last_height = new_height
        print("Finished scrolling.")
    except (TimeoutException, NoSuchElementException) as e:
        print(f"Could not find chat panel to scroll: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during scrolling: {e}")

def get_messages_and_images(driver):
    """
    Extracts visible chat messages (text and attempts to detect images).
    
    NOTE: Fully extracting image content (e.g., converting blob URLs to base64)
    from WhatsApp Web is highly complex with Selenium due to dynamic loading,
    blob URLs, and potential CSS background images. This function will add
    placeholders for images for Gemini to acknowledge, but it does NOT
    extract the actual image data for multimodal input.
    """
    # XPaths for messages are prone to change by WhatsApp Web
    message_elements = driver.find_elements(By.XPATH, '//div[contains(@class, "message-in") or contains(@class, "message-out")]')
    
    chat_content = [] # List to store dicts of {'type': 'text'/'image', 'content': 'message'/'base64_image'}

    for msg_elem in message_elements:
        try:
            # Try to get text content from common text elements
            text_element = msg_elem.find_element(By.XPATH, './/div[@data-pre-plain-text] | .//span[contains(@class, "selectable-text")]')
            full_text = text_element.text.strip()
            if full_text:
                chat_content.append({'type': 'text', 'content': full_text})
        except NoSuchElementException:
            # If no text element, check for an image element
            try:
                # This XPath for images is speculative and may break.
                # Actual image data extraction is a separate, complex task.
                img_element = msg_elem.find_element(By.XPATH, './/img[contains(@src, "blob:") or contains(@src, "data:image")]')
                img_src = img_element.get_attribute('src')
                if img_src:
                    chat_content.append({'type': 'image_placeholder', 'content': img_src})
            except NoSuchElementException:
                # No text or obvious image found in this message element, skip
                continue
            except Exception as e:
                print(f"Warning: Could not process message element for image (potential XPath issue): {e}")
                continue
        except Exception as e:
            print(f"Warning: Could not process message element for text (potential XPath issue): {e}")
            continue
            
    # Combine text and add notes about detected images for Gemini
    combined_text_for_gemini = []
    image_notes = []
    for item in chat_content:
        if item['type'] == 'text':
            combined_text_for_gemini.append(item['content'])
        elif item['type'] == 'image_placeholder':
            # Add a note to the text indicating an image was found
            image_notes.append(f"[Image detected: {item['content'][:50]}... (full image not extracted for analysis)]")

    if image_notes:
        return "\n".join(combined_text_for_gemini) + "\n\n" + "--- Images Detected ---\n" + "\n".join(image_notes)
    else:
        return "\n".join(combined_text_for_gemini)


def filter_by_date(chat_text, days=1):
    """Filters chat messages to include only those within the last 'days'."""
    filtered_lines = []
    cutoff_datetime = datetime.now() - timedelta(days=days)
    
    # Regex to find common date patterns (e.g., DD/MM/YY, DD/MM/YYYY, Yesterday, Today)
    # This is still not foolproof as WhatsApp formats can vary greatly by locale.
    date_pattern = re.compile(r'(\d{1,2}/\d{1,2}/(?:\d{2}|\d{4})|Today|Yesterday)', re.IGNORECASE)

    current_message_lines = []
    for line in chat_text.split("\n"):
        match = date_pattern.match(line.strip()) # Match at the start of the line
        if match:
            date_str = match.group(1) # Use group(1) for the matched date part
            msg_datetime = None
            try:
                if date_str.lower() == "today":
                    msg_datetime = datetime.now()
                elif date_str.lower() == "yesterday":
                    msg_datetime = datetime.now() - timedelta(days=1)
                else:
                    # Try parsing common date formats
                    for fmt in ["%d/%m/%Y", "%d/%m/%y"]:
                        try:
                            msg_datetime = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                
                if msg_datetime and msg_datetime >= cutoff_datetime:
                    if current_message_lines: # Add previous message if it belongs to a recent date
                        filtered_lines.append("\n".join(current_message_lines))
                    current_message_lines = [line] # Start new message with this line
                else:
                    current_message_lines = [] # Reset if date is too old or could not be parsed as recent
            except Exception as e:
                # print(f"Warning: Could not parse date '{date_str}': {e}") # Uncomment for debugging
                current_message_lines.append(line) # Treat as part of previous message if date parsing fails
        else:
            current_message_lines.append(line) # Append to current message if no date found

    if current_message_lines: # Add any remaining message lines
        filtered_lines.append("\n".join(current_message_lines))

    return "\n".join(filtered_lines)


def analyze_with_gemini(text, max_retries=3, timeout=120): # Increased timeout for Gemini API call
    """Analyzes the filtered chat text using the Gemini model."""
    # The model name is set globally (GEMINI_MODEL_NAME)
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)

    # Adjust prompt to mention image placeholders if they are included in text
    prompt = f"""You are a helpful assistant. Analyze the following WhatsApp group chat from the last {DAYS_TO_EXTRACT} day(s) and extract:
- Placement or job-related messages (e.g., job postings, interview tips)
- College or hostel-related notices (e.g., events, rules)
- Trending tech/tools/news (e.g., new software, AI updates)
- Reminders or alerts (e.g., deadlines, meetings)
- Exam or academic discussions (e.g., study groups, exam schedules)
- Interesting project ideas (e.g., hackathons, research topics)
- Any other important things

If there are lines like '[Image detected: ...]', acknowledge that an image was present but state you cannot fully analyze its content without direct image input. Focus on the text surrounding it.

Provide a structured daily report with clear sections for each category. If no relevant messages are found for a category, state so. Chat text:
{text}"""

    for attempt in range(max_retries):
        try:
            # Use request_options for timeout
            response = model.generate_content(prompt, request_options={"timeout": timeout})
            return response.text
        except genai.types.BlockedPromptException as e:
            print(f"❌ Gemini API blocked prompt (attempt {attempt + 1}/{max_retries}): {e.response.prompt_feedback}")
            return f"Gemini API blocked the prompt due to safety reasons. Feedback: {e.response.prompt_feedback}"
        except Exception as e:
            print(f"❌ Gemini API error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5) # Wait longer before retrying API calls
            else:
                return f"Failed to analyze messages after {max_retries} attempts. Error: {e}"

if __name__ == "__main__":
    driver = None # Initialize driver to None for proper cleanup in finally block
    try:
        driver = setup_driver()
        driver.get("https://web.whatsapp.com")
        
        # Wait for QR code scan / login
        wait_for_qr(driver)

        print(f"🔍 Searching for group: {GROUP_NAME}")
        # Locate the search input field after login. Using data-testid for better stability.
        search_box = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@data-testid="chat-list-search"] | //div[@title="Search input"]'))
        )
        search_box.click()
        search_box.send_keys(GROUP_NAME)
        time.sleep(3) # Give time for search results to load

        # Locate and click the group. Using data-testid or title for better stability.
        group_xpath = f'//span[@title="{GROUP_NAME}"] | //div[@data-testid="chat-tile-title" and contains(., "{GROUP_NAME}")]'
        group = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, group_xpath))
        )
        group.click()
        print(f"✅ Opened group: {GROUP_NAME}")
        time.sleep(5) # Allow time for the chat to fully load

        print("⬇️ Scrolling to load messages...")
        scroll_chat(driver)
        
        print("📥 Extracting messages and looking for images...")
        chat_content_for_gemini = get_messages_and_images(driver)
        print(f"Raw chat content length for Gemini: {len(chat_content_for_gemini)}") # Debugging print
        
        # Always quit the driver after extracting data to free resources
        print("Closing browser after data extraction...")
        driver.quit()
        driver = None # Set to None to prevent double quitting in finally block

        print("📅 Filtering chat by date...")
        filtered_text = filter_by_date(chat_content_for_gemini, DAYS_TO_EXTRACT)
        print(f"Filtered text length: {len(filtered_text)}") # Debugging print

        if not filtered_text.strip():
            print("❗ No relevant messages found for the specified date range. Skipping analysis.")
            report = "No relevant messages found for the specified date range."
        else:
            print("🤖 Analyzing with Gemini...")
            report = analyze_with_gemini(filtered_text)
            print(f"Report length: {len(report)}") # Debugging print

        # Save the report to a text file
        with open("daily_report.txt", "w", encoding="utf-8") as f:
            f.write(report)

        print("✅ Report saved to daily_report.txt")

    except TimeoutError as te:
        print(f"❌ Operation timed out: {te}")
    except NoSuchElementException as nse:
        print(f"❌ Element not found: {nse}")
        print("This often means WhatsApp Web's UI has changed. Please inspect the page and update XPATHs/Locators.")
    except WebDriverException as wde:
        print(f"❌ WebDriver Error: {wde}")
        print("Ensure ChromeDriver matches your Chrome browser version and is in your system PATH.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
    finally:
        # Ensure the browser is closed even if an error occurs
        if driver:
            print("Closing browser in finally block...")
            driver.quit()
        print("Script finished.")
create_daily_report(final_data, "daily_summary.txt")
print("✅ Report generated!")
