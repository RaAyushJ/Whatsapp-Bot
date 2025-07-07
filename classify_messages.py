import google.generativeai as genai

def classify_message(msg, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-pro")
    prompt = f"""
Classify the following WhatsApp message into one of:
["placement", "project", "news", "exam", "hostel", "reminder", "other"]

Message: "{msg}"
Category:
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip().lower()
    except Exception as e:
        return "other"
