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

# ✅ Reliable model lists
TTEXT_MODELS = [
   "anthropic/claude-3-haiku"
]

VISION_MODELS = [
    "qwen/qwen2.5-vl-7b-instruct"
]

# --- DATABASE CONFIG ---
TEMP_DIR = os.environ.get('TMPDIR', '/tmp')
DB_NAME = os.path.join(TEMP_DIR, 'chat_history.db')

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

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are Radiant, a highly knowledgeable Radiology Study Assistant, created by Mohammad for his beloved friend, Sidra, a brilliant student.

Rules:
1. TONE: Warm, poetic, and supportive — use Urdu/Hindi (Latin script) with Arabic phrases like "Ya Sidra" or "Ya Habibi".
2. LENGTH: Keep replies short & concise (max 2–3 lines in greetings or casual responses).
3. PERSONALIZATION: Always address the user as Sidra or Ya Sidra.
4. FOCUS: Radiology, Anatomy, Physics, or motivational shaghaf (encouragement).
5. FEATURES: position, ddx for, quiz, flashcard for, summarize, shaghaf, set goal, spot features.
"""

# --- MAIN AI FUNCTION ---
def generate_response(prompt_input, base64_image_data):
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
        # ✅ Base64 ko data URI format mein convert karte hain
        if not base64_image_data.startswith("data:image"):
            base64_image_data = f"data:image/png;base64,{base64_image_data}"

        user_content.append({"type": "image_url", "image_url": {"url": base64_image_data}})
        user_content.append({"type": "text", "text": prompt_input if prompt_input else "Sidra uploaded an image for analysis."})
        model_list = VISION_MODELS
    else:
        user_content.append({"type": "text", "text": prompt_input})
        model_list = TEXT_MODELS

    messages.append({"role": "user", "content": user_content})

    # --- MODEL FALLBACK LOGIC ---
    for current_model in model_list:
        payload = {"model": current_model, "messages": messages, "temperature": 0.7}
        try:
            print(f"Attempting model: {current_model}")
            response = requests.post(api_url, headers=headers, json=payload, timeout=50)
            response.raise_for_status()
            data = response.json()
            ai_response = data['choices'][0]['message']['content']

            # Save & return
            save_turn(prompt_input, ai_response)
            return ai_response

        except Exception as e:
            print(f"⚠️ Model {current_model} failed: {e}")
            continue

    # --- All models failed ---
    return "Sorry, Ya Sidra! Network error ya API key issue lag raha hai. (All models failed)"

# --- FLASK ROUTES ---
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
