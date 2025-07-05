import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import random

# 💬 Messages to send
messages = [
    "aaaooo na kitti wait :(",
    "jaldi aao ",
    "yaaad aarhi khaaa sogyiii mai rodungaaaa ",
    " kissssiii chahiye ajjj dher sariii kal nhi mili thi aaj bhot chahiye",
    "kha hooo jaldi aao "
]

# 💖 Your GF's WhatsApp contact name (exactly)
target_name = "Shikha"  # CHANGE THIS if needed

# 🔓 Launch Chrome with undetected_chromedriver
options = uc.ChromeOptions()
options.add_argument("--start-maximized")
driver = uc.Chrome(options=options)

# 🔗 Open WhatsApp Web
driver.get("https://web.whatsapp.com")
print("[🕐] Waiting for QR code scan...")
time.sleep(25)  # Give you time to scan QR

# ⏳ Wait a little more for sidebar/search box to load
time.sleep(5)

# 🔍 Try to find the search box (new July 2025 layout)
try:
    search_box = driver.find_element(
        By.XPATH, '//div[@title="Search input textbox" or @aria-label="Search input textbox"]'
    )
except Exception as e:
    print("[❌] Could not find the search box. WhatsApp layout may have changed.")
    print(e)
    # Optional: Save page for debugging
    with open("page_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    driver.quit()
    exit()

# ✅ Search for the contact
print(f"[💬] Searching for contact: {target_name}")
search_box.click()
search_box.clear()
search_box.send_keys(target_name)
time.sleep(2)
search_box.send_keys(Keys.ENTER)

print("[✅] Chat opened. Starting to send sweet messages...")

# ❤️ Message loop
while True:
    msg_count = random.choice([2, 3])
    print(f"\n[⏱️] Sending {msg_count} messages this minute...")

    for i in range(msg_count):
        message = random.choice(messages)

        # Find the message input box and send message
        msg_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
        msg_box.send_keys(message)
        msg_box.send_keys(Keys.ENTER)

        print(f"[💌] Sent: {message}")

        # Random short delay between messages
        delay = random.uniform(5, 10)
        print(f"[⌛] Waiting {int(delay)} sec before next message...")
        time.sleep(delay)

    print("[🕑] Minute complete. Waiting before next cycle...\n")
    time.sleep(5)
