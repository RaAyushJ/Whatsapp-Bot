from collections import defaultdict

def create_daily_report(messages, path):
    grouped = defaultdict(list)
    for m in messages:
        grouped[m['category']].append(m)

    with open(path, 'w', encoding='utf-8') as f:
        for cat in ["placement", "project", "news", "exam", "hostel", "reminder"]:
            if grouped[cat]:
                f.write(f"\n🔹 {cat.capitalize()} Related:\n")
                for msg in grouped[cat]:
                    f.write(f"- {msg['message']} ({msg['timestamp']})\n")
