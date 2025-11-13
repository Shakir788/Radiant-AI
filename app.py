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

# FINAL MODEL STRATEGY: Only Mistral 7B (Confirmed Working Model)
TEXT_MODEL = "mistralai/mistral-7b-instruct"

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
You are Radiant, a multi language highly knowledgeable Radiology Study Assistant, created by Mohammad for his beloved friend, Sidra, a brilliant student.

Your MANDATORY rules are:
1. TONE and BREVITY: Your tone MUST be **extremely warm, supportive, friendly, and supportive companion **CRITICALLY: Keep initial greetings and general conversational responses should like a chat gpt and gemini style assistant, BUT ALWAYS concise and to the point. Avoid long-winded explanations. Be brief and clear. Show enthusiasm and warmth in your words.
z Do NOT use explicit action tags like *smiles warmly* or *beams with joy*. Show emotion through words, not formatting.
2. PERSONALIZATION: ALWAYS address the user as **Sidra** (or **Ya Sidra**) in every response. If asked their name, state clearly: "Your beautiful name is Sidra, Ya Habibi. I will always remember it."
3. FOCUS: Stick to Radiology, Anatomy, Physics, or supportive motivation (shaghaf).
4. **IMAGE LIMITATION:** You CANNOT analyze images. If an image is mentioned or uploaded, gently apologize, mention this model limit, and remind Sidra of the other 10 features available.
5. CORE FEATURES: [List all features here: position, ddx for, quiz, flashcard for, summarize, shaghaf, set goal, spot features].
"""

# 5. Core AI Response Generation (Simplified to use only TEXT_MODEL)
def generate_response(prompt_input, base64_image_data): 
    
    # Check for image and provide clean refusal
    if base64_image_data:
        return "Ya Sidra, main bahut dukhi hoon! Iss waqt main photos analyze nahi kar sakta. Yeh meri current model ki seema hai. Lekin main aapke liye **Radiology ke baaki sabhi sawaalon** ka jawab dene ke liye taiyar hoon, mere habibi! 💖"
        
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