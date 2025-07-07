#  Whatsapp-Bot

A Python-based intelligent automation system for WhatsApp Web using Selenium and Google Gemini.

---

##  Features

###  1. LoveBot
- Sends automated messages to a specific contact (e.g., "miss you") at random intervals.
- Mimics human typing using realistic delays.

###  2. Smart Group Chat Reader (In Progress)
- Reads group chat messages using Selenium or WhatsApp .txt exports.
- Detects and tags messages as:
  - Placement-related
  - Exam reminders
  - Project/tool suggestions
  - Hostel/food/water issues
  - News or trending info
- Uses Gemini API for accurate classification.
- Outputs a daily summary grouped by category.

---

## Tech Stack

- Python
- Selenium
- Gemini Pro (Google Generative AI)
- GitHub Actions (planned for automation)
- Streamlit (planned GUI support)

---

## Getting Started

```bash
git clone https://github.com/RaAyushJ/Whatsapp-Bot.git
cd Whatsapp-Bot
pip install -r requirements.txt
