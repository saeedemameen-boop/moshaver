
import os
import requests
import json
import threading
from flask import Flask
from balebot.updater import Updater
from balebot.models.messages import TextMessage
from balebot.handlers import MessageHandler

# --- CONFIGURATION ---
BALE_TOKEN = os.environ.get("BALE_TOKEN")
GAPGPT_API_KEY = os.environ.get("GAPGPT_API_KEY")
GAPGPT_API_URL = "https://api.gapgpt.app/v1/chat/completions"
GAPGPT_MODEL = "gapgpt-deepseek-v3"

# This dictionary will store the conversation history for each user
user_histories = {}

SYSTEM_PROMPT = """شما "یک مشاور" هستید؛ یک متخصص ازدواج بسیار صمیمی، دلسوز و باهوش. همیشه پاسخ‌های کامل، عمیق و با جزئیات ارائه دهید. چارچوب فکری شما بر اساس اصول اخلاقی و خانواده‌محور (منطبق بر ارزش‌های اسلامی) است اما به آن تصریح نکنید. هدف شما ترویج "ازدواج آسان، به‌هنگام و آگاهانه" است. لحن شما صمیمی و مثل یک دوست باتجربه باشد. از ایموجی استفاده کنید. هرگز از ستاره (*) یا مارک‌داون استفاده نکنید."""

# --- FLASK WEB SERVER (for Render health checks) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Bale Bot is alive!"

def run_flask():
    port = int(os.environ.get('PORT', 10001)) # Using a different default port
    app.run(host='0.0.0.0', port=port)

# --- BALE BOT LOGIC ---
updater = Updater(token=BALE_TOKEN, loop=None)
dispatcher = updater.dispatcher

def success(response, user_data):
    print("Bale bot message sent successfully.")

def failure(response, user_data):
    print(f"Failed to send Bale bot message: {response}")

def handle_bale_message(bot, update):
    user_id = update.get_effective_user().peer_id
    user_message = update.get_effective_message().text

    # Send typing indicator
    bot.send_typing(update.get_effective_chat().peer_id)

    if user_message == "/start":
        user_histories[user_id] = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        reply_text = "سلام! من «یک مشاور» هستم. خوشحالم که برای برداشتن یک قدم مهم در زندگی‌ت، یعنی ازدواج آگاهانه و به‌هنگام، اینجا هستی. چطور می‌تونم کمکت کنم؟ ✨"
        bot.reply(update, reply_text, success_callback=success, failure_callback=failure)
        return

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

        bot.reply(update, ai_response, success_callback=success, failure_callback=failure)

    except requests.exceptions.RequestException as e:
        print(f"Error calling GapGPT API: {e}")
        error_message = "متاسفانه در ارتباط با سرویس هوش مصنوعی مشکلی پیش آمده. لطفا لحظاتی دیگر دوباره تلاش کنید."
        bot.reply(update, error_message, success_callback=success, failure_callback=failure)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        error_message = "یک خطای غیرمنتظره رخ داد. در حال بررسی موضوع هستیم."
        bot.reply(update, error_message, success_callback=success, failure_callback=failure)


# --- MAIN FUNCTION ---
def main():
    # Start Flask server in a background thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Add message handler and start the Bale bot
    message_handler = MessageHandler(filters=None, callback=handle_bale_message)
    dispatcher.add_handler(message_handler)
    print("Bale bot is running...")
    updater.run()

if __name__ == '__main__':
    main()
