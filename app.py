import os
import sqlite3
import base64
import json
import requests # <--- NEW IMPORT
from dotenv import load_dotenv
from openai import OpenAI
from flask import Flask, render_template, request, jsonify

# --- CONFIGURATION & SETUP ---
load_dotenv('keys.env')
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_KEY:
    raise ValueError("OPENROUTER_API_KEY keys.env file mein nahi mili. Kripya file check karein.")

# FIX: DB_NAME ko Render ke temporary directory mein set karna.
TEMP_DIR = os.environ.get('TMPDIR', '/tmp')
DB_NAME = os.path.join(TEMP_DIR, 'chat_history.db')

# Best Vision Model for speed and accuracy
AI_MODEL = "mistralai/mistral-7b-instruct"


# Flask App Initialization
app = Flask(__name__)

# 1. Database Setup - CREATE TABLE
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

# 2. Setup Database call
setup_database()


# 3. Database Functions (No Change)
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

# 4. RADIANT ki Personality Aur Features (SYSTEM_PROMPT) - No Change
SYSTEM_PROMPT = """
You are **Radiant**, a personalized and highly knowledgeable **Radiology Study Assistant**...
(SAME SYSTEM PROMPT AS BEFORE)
"""

# 5. Core AI Response Generation (FIXED to use requests with explicit timeout)
def generate_response(prompt_input, base64_image_data): 
    # OpenRouter API URL and Headers
    api_url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
    "Authorization": f"Bearer {OPENROUTER_KEY}",
    "Content-Type": "application/json",
    "Referer": "https://radiant-54oy.onrender.com",  # FIXED header name
    "X-Title": "Radiant: Sidra's Personal Helper",
}

    
    # Message History Build (Same as before)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    full_history = load_history()
    for user_msg, ai_res in full_history:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": ai_res})
    
    # User Content (Same as before)
    user_content = []
    if base64_image_data:
        # Image part and text part
        user_content.append({"type": "image_url", "image_url": {"url": base64_image_data}})
        user_content.append({"type": "text", "text": prompt_input if prompt_input else "Sidra uploaded an image for analysis."})
    elif prompt_input:
        user_content.append({"type": "text", "text": prompt_input})
    messages.append({"role": "user", "content": user_content})

    # Request Payload
    payload = {
        "model": AI_MODEL,
        "messages": messages,
        "temperature": 0.7
    }

    try:
        # FIX: Explicit timeout of 50 seconds using requests library
        response = requests.post(api_url, headers=headers, json=payload, timeout=50)
        response.raise_for_status() # HTTP error codes check karega (4xx ya 5xx)
        
        data = response.json()
        ai_response = data['choices'][0]['message']['content']
        
        # Save response (Same as before)
        if base64_image_data:
            save_turn(f"[Image Uploaded] {prompt_input if prompt_input else 'Image Analysis Request'}", ai_response)
        else:
            save_turn(prompt_input, ai_response)
        
        return ai_response
    
    except requests.exceptions.Timeout:
        print("--- API TIMEOUT ERROR ---")
        return "Sorry, Ya Sidra! API ne 50 seconds mein jawab nahi diya. Connection lost."
    except requests.exceptions.RequestException as e:
        print(f"--- API REQUEST ERROR ---\nAPI call failed: {e}") 
        return "Sorry, Ya Sidra! Network error or API key issue. Connection lost."
    except Exception as e:
        print(f"--- GENERAL ERROR ---\n{e}")
        return "Sorry, Ya Sidra! There was an internal error processing the request."

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