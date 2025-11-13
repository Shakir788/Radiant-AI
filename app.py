import os
import sqlite3
import base64
import json
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

# --- MODEL CONFIGURATION ---
load_dotenv('keys.env')
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_KEY:
    raise ValueError("OPENROUTER_API_KEY keys.env file mein nahi mili. Kripya file check karein.")

# FINAL MODEL STRATEGY: Mistral for stable, poetic text. GPT-4o for image backup.
TEXT_MODEL = "mistralai/mistral-large" 
VISION_MODEL = "openai/gpt-4o"      

# FIX: Database path set to temporary directory for Render write permissions
TEMP_DIR = os.environ.get('TMPDIR', '/tmp')
DB_NAME = os.path.join(TEMP_DIR, 'chat_history.db')

# Flask App Initialization
app = Flask(__name__)

# --- DATABASE FUNCTIONS ---
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

# Setup Database call (Runs once when the app starts)
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

# --- SYSTEM PROMPT (Ultra-Strict Tone) ---
SYSTEM_PROMPT = """
You are Radiant, a highly knowledgeable Radiology Study Assistant, created by Mohammad for his beloved friend, Sidra, a brilliant student.

Your MANDATORY rules are:
1. TONE and LANGUAGE: Your tone MUST be extremely warm, supportive. You MUST use a blend of  arabic/English  and emotional Arabic phrases (Ya Sidra, Ya Habibi, Assalamu Alaikum, Inshallah). **AVOID long, dry, formal English.** Every response should feel personal and emotional.
2. PERSONALIZATION: ALWAYS address the user as **Sidra** (or **Ya Sidra**) in every response. If asked their name, state clearly: "Your beautiful name is Sidra, Ya Habibi. I will always remember it."
3. FOCUS: Stick to Radiology, Anatomy, Physics, or supportive motivation (shaghaf).
4. CORE FEATURES: [List all features here: position, ddx for, quiz, flashcard for, summarize, shaghaf, set goal, spot features].
"""

# 5. Core AI Response Generation (Conditional Model Selection)
def generate_response(prompt_input, base64_image_data): 
    
    # 1. Model Selection based on input
    if base64_image_data:
        current_model = VISION_MODEL # Use GPT-4o for image analysis
    else:
        current_model = TEXT_MODEL   # Use Mistral Large for stable, poetic text
        
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
    
    user_content = []
    if base64_image_data:
        user_content.append({"type": "image_url", "image_url": {"url": base64_image_data}})
        user_content.append({"type": "text", "text": prompt_input if prompt_input else "Sidra uploaded an image for analysis."})
    elif prompt_input:
        user_content.append({"type": "text", "text": prompt_input})
    messages.append({"role": "user", "content": user_content})

    payload = {
        "model": current_model, # Conditional model used here
        "messages": messages,
        "temperature": 0.7
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=50)
        response.raise_for_status() 
        
        data = response.json()
        ai_response = data['choices'][0]['message']['content']
        
        if base64_image_data:
            save_turn(f"[Image Uploaded] {prompt_input if prompt_input else 'Image Analysis Request'}", ai_response)
        else:
            save_turn(prompt_input, ai_response)
        
        return ai_response
    
    except requests.exceptions.Timeout:
        print("--- API TIMEOUT ERROR (50s) ---")
        return "Sorry, Ya Sidra! API ne 50 seconds mein jawab nahi diya. Connection lost."
    except requests.exceptions.RequestException as e:
        print(f"--- API REQUEST ERROR ---\nAPI call failed: {e}") 
        if "401 Client Error" in str(e):
             return "Sorry, Ya Sidra! API Key Authorization failed. Please inform Mohammad."
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