import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/nedo_english")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))
PORT = int(os.getenv("PORT", 8080))
