import os
import telebot
from services.ai_support_service import ai_support
from database.connection import SessionLocal
from database.models import User
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(TOKEN)

# --- Handlers ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 Welcome to **GrowthQuantix AI Support**!

"
        "I can help you with:
"
        "1. 📈 **Strategies:** Ask about Fibonacci or EMA logic.
"
        "2. 🛡️ **Trades:** 'Why did my last trade close?'
"
        "3. 🔧 **Setup:** 'How do I link Upstox?'

"
        "Just type your question below!"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_support_query(message):
    chat_id = str(message.chat.id)
    
    # 1. Look up user by Telegram Chat ID
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_chat_id == chat_id).first()
    user_email = user.email if user else None
    db.close()
    
    # 2. Process query with AI
    print(f"📬 Message from {user_email or 'Unknown'}: {message.text}")
    
    try:
        response = ai_support.answer_query(message.text, user_email)
        bot.reply_to(message, response, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Error in Support Bot: {e}")
        bot.reply_to(message, "⚠️ Sorry, I'm having trouble connecting to my brain right now. Please try again later.")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN is missing!")
    else:
        print("🤖 GrowthQuantix AI Support Bot is running...")
        bot.infinity_polling()
