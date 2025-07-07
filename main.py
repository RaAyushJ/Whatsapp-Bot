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

create_daily_report(final_data, "daily_summary.txt")
print("✅ Report generated!")
