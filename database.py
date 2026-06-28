import logging
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Инициализация клиента Supabase с приватным ключом (bypass RLS)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ---

def get_or_create_user(user_id: int, username: str = None, referrer_id: int = None) -> dict:
    try:
        # Проверяем, есть ли пользователь
        res = supabase.table("users").select("*").eq("id", user_id).execute()
        if res.data:
            return res.data[0]
        
        # Если пользователя нет — создаем его
        new_user = {
            "id": user_id,
            "username": username,
            "location_code": None,
            "is_premium": False,
            "is_banned": False,
            "referred_by": referrer_id if referrer_id and referrer_id != user_id else None
        }
        res = supabase.table("users").insert(new_user).execute()
        
        # Если его пригласил друг, автоматически выдаем другу премиум!
        if referrer_id and referrer_id != user_id:
            # Проверяем, существует ли вообще пригласивший
            ref_check = supabase.table("users").select("id").eq("id", referrer_id).execute()
            if ref_check.data:
                set_premium_status(referrer_id, True)
                logging.info(f"User {referrer_id} got Premium because they invited {user_id}")
        
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

# --- СИСТЕМА ПОИСКА И ЧАТА ---

def start_search_session(user_id: int) -> dict:
    try:
        # Проверяем, нет ли уже сессии
        existing = supabase.table("active_chats").select("*").or_(f"user_one.eq.{user_id},user_two.eq.{user_id}").execute()
        if existing.data:
            return existing.data[0]
            
        # Получаем локацию пользователя
        user_data = supabase.table("users").select("location_code").eq("id", user_id).execute()
        user_loc = user_data.data[0]["location_code"] if user_data.data else None

        # Ищем свободного собеседника (у которого user_two ис NULL)
        # Сначала пробуем найти с такой же локацией
        query = supabase.table("active_chats").select("*").is_("user_two", "null").not_.eq("user_one", user_id)
        potentials = query.execute()
        
        partner_id = None
        session_id = None
        
        if potentials.data:
            # Оптимизация: берем первого свободного. При желании можно отфильтровать по локации в Python для экономии памяти бд
            for pot in potentials.data:
                p_id = pot["user_one"]
                p_data = supabase.table("users").select("location_code").eq("id", p_id).execute()
                p_loc = p_data.data[0]["location_code"] if p_data.data else None
                
                if user_loc and p_loc == user_loc:
                    partner_id = p_id
                    session_id = pot["id"]
                    break
            
            # Если по локации никого, берем просто самого первого из очереди
            if not partner_id:
                partner_id = potentials.data[0]["user_one"]
                session_id = potentials.data[0]["id"]
                
            # Соединяем пользователей
            res = supabase.table("active_chats").update({"user_two": user_id}).eq("id", session_id).execute()
            return res.data[0]
            
        else:
            # Если очереди нет, встаем в нее сами
            new_session = {"user_one": user_id, "user_two": None}
            res = supabase.table("active_chats").insert(new_session).execute()
            return res.data[0]
            
    except Exception as e:
        logging.error(f"Error in start_search_session: {e}")
        return None

def close_chat_session(user_id: int) -> int:
    """Удаляет сессию чата и возвращает ID собеседника, чтобы ему написать"""
    try:
        res = supabase.table("active_chats").select("*").or_(f"user_one.eq.{user_id},user_two.eq.{user_id}").execute()
        if not res.data:
            return None
            
        session = res.data[0]
        supabase.table("active_chats").delete().eq("id", session["id"]).execute()
        
        return session["user_two"] if session["user_one"] == user_id else session["user_one"]
    except Exception as e:
        logging.error(f"Error in close_chat_session: {e}")
        return None

def get_active_partner(user_id: int) -> int:
    try:
        res = supabase.table("active_chats").select("*").or_(f"user_one.eq.{user_id},user_two.eq.{user_id}").execute()
        if not res.data:
            return None
        session = res.data[0]
        if session["user_two"] is None:
            return None
        return session["user_two"] if session["user_one"] == user_id else session["user_one"]
    except Exception as e:
        logging.error(f"Error in get_active_partner: {e}")
        return None

def create_report(reporter_id: int, reported_id: int, reason: str):
    try:
        supabase.table("reports").insert({
            "reporter_id": reporter_id,
            "reported_id": reported_id,
            "reason": reason,
            "status": "open"
        }).execute()
    except Exception as e:
        logging.error(f"Error in create_report: {e}")

def get_open_reports(limit: int = 5) -> list:
    try:
        res = supabase.table("reports").select("*").eq("status", "open").limit(limit).execute()
        return res.data if res.data else []
    except Exception as e:
        logging.error(f"Error in get_open_reports: {e}")
        return []

def resolve_report(report_id: int):
    try:
        supabase.table("reports").update({"status": "resolved"}).eq("id", report_id).execute()
    except Exception as e:
        logging.error(f"Error in resolve_report: {e}")

def get_users_chunk(offset: int, limit: int = 100) -> list:
    """Выгружает только ID пользователей порциями для экономии ОЗУ"""
    try:
        res = supabase.table("users").select("id").range(offset, offset + limit - 1).execute()
        return [row["id"] for row in res.data] if res.data else []
    except Exception as e:
        logging.error(f"Error in get_users_chunk: {e}")
        return []
