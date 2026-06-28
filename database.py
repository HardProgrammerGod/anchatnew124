import logging
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Инициализация клиента Supabase с приватным ключом (bypass RLS)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ---

def get_or_create_user(user_id: int, username: str = None) -> dict:
    try:
        # Проверяем, есть ли пользователь
        res = supabase.table("users").select("*").eq("id", user_id).execute()
        if res.data:
            return res.data[0]
        
        # Если нет — создаем
        new_user = {
            "id": user_id,
            "username": username,
            "location_code": None,
            "is_premium": False,
            "is_banned": False
        }
        res = supabase.table("users").insert(new_user).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logging.error(f"Error in get_or_create_user: {e}")
        return None

def update_user_location(user_id: int, location_code: str):
    try:
        supabase.table("users").update({"location_code": location_code}).eq("id", user_id).execute()
    except Exception as e:
        logging.error(f"Error in update_user_location: {e}")

def set_premium_status(user_id: int, status: bool = True):
    try:
        supabase.table("users").update({"is_premium": status}).eq("id", user_id).execute()
    except Exception as e:
        logging.error(f"Error in set_premium_status: {e}")

def set_ban_status(user_id: int, status: bool = True):
    try:
        supabase.table("users").update({"is_banned": status}).eq("id", user_id).execute()
    except Exception as e:
        logging.error(f"Error in set_ban_status: {e}")

# --- СТАТИСТИКА ДЛЯ АДМИНА ---

def get_admin_stats() -> dict:
    try:
        # Подсчет общего количества пользователей (минимальный трафик через count)
        users_res = supabase.table("users").select("id", count="exact").execute()
        total_users = users_res.count if users_res.count is not None else len(users_res.data)
        
        # Премиум пользователи
        prem_res = supabase.table("users").select("id", count="exact").eq("is_premium", True).execute()
        premium_users = prem_res.count if prem_res.count is not None else len(prem_res.data)
        
        # Забаненные
        ban_res = supabase.table("users").select("id", count="exact").eq("is_banned", True).execute()
        banned_users = ban_res.count if ban_res.count is not None else len(ban_res.data)
        
        # Активные чаты прямо сейчас
        chats_res = supabase.table("active_chats").select("id", count="exact").not_.is_("user_two", "null").execute()
        active_chats = chats_res.count if chats_res.count is not None else len(chats_res.data)
        
        # Люди в очереди поиска
        queue_res = supabase.table("active_chats").select("id", count="exact").is_("user_two", "null").execute()
        in_queue = queue_res.count if queue_res.count is not None else len(queue_res.data)

        return {
            "total_users": total_users,
            "premium_users": premium_users,
            "banned_users": banned_users,
            "active_chats": active_chats,
            "in_queue": in_queue
        }
    except Exception as e:
        logging.error(f"Error in get_admin_stats: {e}")
        return {"total_users": 0, "premium_users": 0, "banned_users": 0, "active_chats": 0, "in_queue": 0}
