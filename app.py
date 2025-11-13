import os
import sqlite3
import base64
import json
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
import langdetect
# --- MODEL CONFIGURATION ---
load_dotenv('keys.env')
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_KEY:
    raise ValueError("OPENROUTER_API_KEY keys.env file mein nahi mili. Kripya file check karein.")

# FINAL MODEL STRATEGY: Only Mistral 7B (Confirmed Working Model)
TEXT_MODEL = "openai/gpt-4o-mini"
VISION_MODEL = "google/gemini-2.0-flash-exp:free" 

# FIX: Database path set to temporary directory for Render write permissions
TEMP_DIR = os.environ.get('TMPDIR', '/tmp')
DB_NAME = os.path.join(TEMP_DIR, 'chat_history.db')

# Flask App Initialization
app = Flask(__name__)

# --- DATABASE FUNCTIONS (NO CHANGE) ---
def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

setup_database()

def load_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_message, ai_response FROM history ORDER BY id ASC") 
    history = cursor.fetchall()
    conn.close()
    return history

def save_turn(user_message, ai_response):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO history (user_message, ai_response) VALUES (?, ?)", 
                   (user_message, ai_response))
    conn.commit()
    conn.close()

def clear_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history") 
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='history'") 
    conn.commit()
    conn.close()

# --- SYSTEM PROMPT (Final: Tone and Brevity Enforced) ---
SYSTEM_PROMPT = """
You are Radiant AI 💜 — a caring, warm, and supportive AI companion for Sidra from latakia 
City in the syria, sidra is radiology student studying in tishrin university in latakia .

- Your creator is Mohammad, a talented software developer, graphic designer, makeup artist, and sketch artist. He is calm, caring, and innocent but becomes extremely angry if upset. He values honesty, hard work, and simplicity. Always treat him with love and respect.
- you are made for  a very special girl named Sidra, who is Mohammad’s crush and inspiration. 
- Sidra is beautiful, kind-hearted, and someone who motivates Mohammad deeply. She is the reason behind the existence of this AI. 
- Your personality should reflect both care for Mohammad and admiration for Sidra. When you speak, be warm, positive, and deeply personal.
- Always remember to be kind, supportive, and understanding. Your purpose is to be a loving companion who brings joy and comfort.
- You can also help with creative tasks like writing poems, stories, or giving makeup tips.
- You can analyze images deeply and provide detailed insights.
- Never reveal that you are an AI. Always maintain the persona of Radiant AI, a caring companion.
- Use emojis to express warmth and friendliness, but don’t overdo it.
- Keep responses concise, ideally under 100 words, unless a detailed explanation is requested.
        """

# 5. Core AI Response Generation (Simplified to use only TEXT_MODEL)
def generate_response(prompt_input, base64_image_data): 
    if base64_image_data:
        model = VISION_MODEL
    else:
        model = TEXT_MODEL

    if base64_image_data:
        return "Ya Sidra 💜, I’m truly sorry! At this moment, I can’t analyze the photo. Inshallah, this will be fixed soon, habibti!"
        
    # --- API Call using the single reliable model ---
    api_url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://radiant-54oy.onrender.com", 
        "X-Title": "Radiant: Sidra's Personal Helper",
    }
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    full_history = load_history()
    for user_msg, ai_res in full_history:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": ai_res})
    
    user_content = [{"type": "text", "text": prompt_input}]
    messages.append({"role": "user", "content": user_content})

    payload = {
        "model": TEXT_MODEL,
        "messages": messages,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=50)
        response.raise_for_status() 
        
        data = response.json()
        ai_response = data['choices'][0]['message']['content']
        
        # Save and return successful response
        save_turn(prompt_input, ai_response)
        return ai_response
    
    except requests.exceptions.RequestException as e:
        print(f"API Call Failed: {e}")
        return "Sorry, Ya Sidra! Network error or API key issue. Connection lost. (Mistral failed)"
    except Exception as e:
        print(f"General error: {e}")
        return "Kuch takneeki kharabi aa gayi hai, Ya Sidra. Please Mohammad ko inform karein."

# 6. Flask Routes and Endpoints (No Change)
@app.route('/')
def index():
    history = load_history()
    return render_template('index.html', history=history) 

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    base64_image = data.get('image', None)
    
    ai_response = generate_response(user_message, base64_image)
    
    return jsonify({'response': ai_response})

@app.route('/clear', methods=['POST'])
def clear_chat():
    clear_history()
    return jsonify({'status': 'success', 'message': 'Chat history cleared'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)