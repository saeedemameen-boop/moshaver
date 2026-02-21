import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import requests
import json
import os
import threading
from flask import Flask

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
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
    return "Bot is alive!"

def run_flask():
    # Render provides the PORT environment variable.
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# --- TELEGRAM BOT LOGIC ---

async def start(update, context):
    """Send a welcome message when the /start command is issued."""
    user_id = update.effective_user.id
    user_histories[user_id] = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    await update.message.reply_text("سلام! من «یک مشاور» هستم. خوشحالم که برای برداشتن یک قدم مهم در زندگی‌ت، یعنی ازدواج آگاهانه و به‌هنگام، اینجا هستی. چطور می‌تونم کمکت کنم؟ ✨")

async def handle_message(update, context):
    """Handle incoming text messages and get a response from the AI."""
    user_id = update.effective_user.id
    user_message = update.message.text

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

        await update.effective_chat.send_action(action='typing')
        
        response = requests.post(GAPGPT_API_URL, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status() 

        ai_response = response.json()['choices'][0]['message']['content']
        user_histories[user_id].append({'role': 'assistant', 'content': ai_response})

        await update.message.reply_text(ai_response)

    except requests.exceptions.RequestException as e:
        print(f"Error calling GapGPT API: {e}")
        await update.message.reply_text("متاسفانه در ارتباط با سرویس هوش مصنوعی مشکلی پیش آمده. لطفا لحظاتی دیگر دوباره تلاش کنید.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        await update.message.reply_text("یک خطای غیرمنتظره رخ داد. در حال بررسی موضوع هستیم.")

def main():
    """Main function to start the bot and the web server."""
    # Start Flask server in a background thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Start the Telegram bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
