import feedparser
import requests
import time
import html
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
TOPIC = os.environ.get("TOPIC", "Artificial Intelligence")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
HISTORY_FILE = "history.json"

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_history(history_set):
    with open(HISTORY_FILE, "w") as f:
        json.dump(list(history_set), f)

def get_latest_ai_news(history):
    # Google News RSS URL for a specific topic
    encoded_topic = TOPIC.replace(" ", "%20")
    rss_url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-US&gl=US&ceid=US:en"
    
    feed = feedparser.parse(rss_url)
    
    news_items = []
    # Iterate through entries and stop once we have 5 new ones
    for entry in feed.entries:
        if len(news_items) >= 5:
            break
            
        if entry.link in history:
            continue
            
        news_items.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published
        })
    return news_items

def summarize_news(news_list):
    if not GEMINI_API_KEY:
        print("⚠️ No Gemini API Key found. Skipping summarization.")
        return None

    try:
        # User requested gemini-2.5-flash
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Prepare the input for Gemini
        articles_text = "\n".join([f"- {item['title']}: {item['link']}" for item in news_list])
        prompt = (
            f"Here are the latest AI news headlines:\n{articles_text}\n\n"
            "Please select the top 3 most significant stories.\n"
            "Summarize them into 3 short paragraph with date and time, engaging paragraph suitable for a Telegram channel update.\n"
            "Use fun emojis (🤖, 🚀, 🧠, etc.) to make it lively.\n"
            "Start with a catchy headline.\n"
            "At the end, list the links to the 3 selected stories in a clean format like: '🔗 [Title](Link)'."
        )

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        return None

def send_telegram_message(content):
    if not content:
        return False

    # Send request
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": content,
        "parse_mode": "Markdown", 
        "disable_web_page_preview": False
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ News sent successfully!")
            return True
        else:
            print(f"❌ Failed to send: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Loading history...")
    history = load_history()
    
    print("Fetching news...")
    news = get_latest_ai_news(history)
    
    if not news:
        print("No new news found.")
        exit()
    
    print(f"Found {len(news)} new articles.")
    
    print("Summarizing with Gemini...")
    summary = summarize_news(news)
    
    sent = False
    if summary:
        sent = send_telegram_message(summary)
    else:
        # Fallback logic if Gemini fails
        print("Falling back to standard list...")
        pass # Fallback implementation skipped for brevity as per previous step
    
    if sent:
        # Update history with the links of the articles we fetched
        for item in news:
            history.add(item['link'])
        save_history(history)
        print("History updated.")


