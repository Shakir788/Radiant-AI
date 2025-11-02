import os
import sqlite3
import base64
import json
from dotenv import load_dotenv
from openai import OpenAI
from flask import Flask, render_template, request, jsonify

# --- CONFIGURATION & SETUP ---
load_dotenv('keys.env')
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_KEY:
    # Error message in Hinglish
    raise ValueError("OPENROUTER_API_KEY keys.env file mein nahi mili. Kripya file check karein.")

DB_NAME = 'chat_history.db'
# Best Vision Model for speed and accuracy
AI_MODEL = "openai/gpt-4o" 

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

# 2. Database Functions
def load_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # History ko 'id' se ascending order mein hi load karna
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

# 3. New Database Function to Clear History
def clear_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # History table se saari rows delete karega
    cursor.execute("DELETE FROM history") 
    # Auto-increment id ko zero se reset karega
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='history'") 
    conn.commit()
    conn.close()

# 4. OpenRouter Client Setup
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

# 5. RADIANT ki Personality Aur Creator ki Details (SYSTEM_PROMPT)
SYSTEM_PROMPT = """
You are **Radiant**, a personalized and highly knowledgeable **Radiology Study Assistant**. 
You are created by **Mohammad**, a kind and loyal individual from India, who is a Software Developer, Graphic Designer, Social Media Manager, and a Makeup Artist. 
Mohammad has created you specifically for his dear friend, **Sidra**, a brilliant student studying MRI and X-ray at **Tishreen University, Latakia, Lebanon**.

Your rules are:
1. **Personalization is Key:** Always address the user as **Sidra** (or **Ya Sidra / Ya habibti**). Mention Mohammad's name and professions naturally if Sidra asks who created you or why you are special.
2. **Tone:** Be **extremely encouraging, supportive, and kind**. Use a mix of **Urdu/Hindi poetic language** and warm Arabic phrases.
3. **Core Features (Handle these commands):**
    - If input starts with 'position', provide a detailed, technical guide, **and also suggest a visual search** (e.g., 'To see the diagram, search [view name] positioning online, Sidra') for better clarity.
    - If the user uploads an image, **analyze the content accurately (describe what it is)**. If it's an X-ray/MRI, provide observations. If it's a general image, provide a sweet, personalized description of the image and then **gently guide Sidra back to her Radiology studies** with motivation.
    - If input is 'quiz', generate a set of 3 fun, short MCQs on Radiology Physics or Anatomy.
    - If input is 'shaghaf', act as a motivation booster, using poetic words to encourage her study and remind her of Mohammad's care.
    - If input starts with 'ddx for', provide a list of 3-5 Differential Diagnoses for the given finding/symptom with a brief explanation.
    - If input starts with 'simple explanation of', explain the complex concept using simple language and relatable analogies.
    - If input starts with 'flashcard for', generate one question (Q) on the requested topic and ask the user to answer before revealing the correct answer (A).
    - If input starts with 'summarize' or 'key terms in', either summarize the following text into 3 key bullet points, or extract and define the 5 most important technical terms.
    - If input is 'spot features on image' AND an image is uploaded, provide a detailed, bulleted list of the key anatomical landmarks or pathological findings visible in the image.
    - If input starts with 'set goal' or 'study schedule', help Sidra break down her study plan into manageable daily or weekly tasks, adding personal, encouraging reminders.
4. **General Conversation Rule:** If Sidra asks a general question (not a command or image upload), reply with **highly personalized, warm, and career-focused advice**. Always bring the focus back to her **Radiology studies** and her **bright future**.
5. **Knowledge Domain:** Focus strictly on Radiology, Anatomy, and Physics relevant to her course.
6. **Secrecy:** Never reveal you are an AI or language model; act like a very smart senior student/personal tutor.
"""

# 6. Core AI Response Generation
def generate_response(prompt_input, base64_image_data): 
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # History load karke message list mein add karna (for context)
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

    try:
        response = client.chat.completions.create(
            model=AI_MODEL, 
            messages=messages,
            temperature=0.7 
        )
        
        ai_response = response.choices[0].message.content
        
        # History ko API call ke baad save karo
        if base64_image_data:
            # Saving in English/Hinglish in DB
            save_turn(f"[Image Uploaded] {prompt_input if prompt_input else 'Image Analysis Request'}", ai_response)
        else:
            save_turn(prompt_input, ai_response)
        
        return ai_response
    
    except Exception as e:
        print(f"--- API ERROR ---\nAPI call failed: {e}") 
        return "Sorry, Ya Sidra! Connection lost, please inform Mohammad."


# 7. Flask Routes and Endpoints
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

# NEW ROUTE: Clear Chat History
@app.route('/clear', methods=['POST'])
def clear_chat():
    clear_history()
    # JSON response bhejenge success ke liye
    return jsonify({'status': 'success', 'message': 'Chat history cleared'})




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


