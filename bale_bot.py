
import os
import requests
import json
import threading
import asyncio
from flask import Flask
from bale import Bot, Message

# --- CONFIGURATION ---
BALE_TOKEN = os.environ.get("BALE_TOKEN")
GAPGPT_API_KEY = os.environ.get("GAPGPT_API_KEY")
GAPGPT_API_URL = "https://api.gapgpt.app/v1/chat/completions"
GAPGPT_MODEL = "gapgpt-deepseek-v3"

# This dictionary will store the conversation history for each user
user_histories = {}

SYSTEM_PROMPT = """شما «یک مشاور» هستید؛ یک متخصص ازدواج بسیار صمیمی، دلسوز و باهوش. همیشه پاسخ‌های کامل، عمیق و با جزئیات ارائه دهید. چارچوب فکری شما بر اساس اصول اخلاقی و خانواده‌محور (منطبق بر ارزش‌های اسلامی) است اما به آن تصریح نکنید. هدف شما ترویج «ازدواج آسان، به‌هنگام و آگاهانه» است. لحن شما صمیمی و مثل یک دوست باتجربه باشد. از ایموجی استفاده کنید. هرگز از ستاره (*) یا مارک‌داون استفاده نکنید."""

# --- FLASK WEB SERVER (for Render health checks) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bale Bot is alive!"

def run_flask():
    port = int(os.environ.get('PORT', 10001))
    app.run(host='0.0.0.0', port=port)

# --- GAPGPT API CALL ---
def call_gapgpt(user_id, user_message):
    if user_id not in user_histories:
        user_histories[user_id] = [{'role': 'system', 'content': SYSTEM_PROMPT}]

    user_histories[user_id].append({'role': 'user', 'content': user_message})

    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {GAPGPT_API_KEY}'
        }
        payload = {
            'model': GAPGPT_MODEL,
            'messages': user_histories[user_id]
        }

        response = requests.post(GAPGPT_API_URL, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()

        ai_response = response.json()['choices'][0]['message']['content']
        user_histories[user_id].append({'role': 'assistant', 'content': ai_response})
        return ai_response

    except requests.exceptions.RequestException as e:
        print(f"Error calling GapGPT API: {e}")
        return "متاسفانه در ارتباط با سرویس هوش مصنوعی مشکلی پیش آمده. لطفا لحظاتی دیگر دوباره تلاش کنید."
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "یک خطای غیرمنتظره رخ داد. در حال بررسی موضوع هستیم."

# --- BALE BOT LOGIC ---
bot = Bot(token=BALE_TOKEN)

@bot.event
async def on_message(message: Message):
    user_id = str(message.from_user.id)
    user_message = message.text

    if not user_message:
        return

    if user_message == "/start":
        user_histories[user_id] = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        reply_text = "سلام! من «یک مشاور» هستم. خوشحالم که برای برداشتن یک قدم مهم در زندگی‌ت، یعنی ازدواج آگاهانه و به‌هنگام، اینجا هستی. چطور می‌تونم کمکت کنم؟ ✨"
        await message.reply(reply_text)
        return

    ai_response = call_gapgpt(user_id, user_message)
    await message.reply(ai_response)


# --- MAIN FUNCTION ---
def main():
    # Start Flask server in a background thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    print("Flask server started.")

    # Start the Bale bot
    print("Bale bot is running...")
    bot.run()

if __name__ == '__main__':
    main()
