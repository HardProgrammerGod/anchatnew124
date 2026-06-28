from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

import database as db
from config import CHANNEL_ID, ADMIN_ID
from keyboards import inline
# Импортируем функцию декодирования, чтобы не нагружать БД лишними строками
from handlers.location import get_country_name_by_code

router = Router()

# Функция быстрой проверки подписки
async def is_subscribed(bot: Bot, user_id: int) -> bool:
    if user_id == ADMIN_ID:  # Админу проверку можно пропустить
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

# --- КОМАНДА /START ---
@router.message(Command("start"))
async def cmd_start(message: Message, bot: Bot):
    user_id = message.from_user.id
    user = db.get_or_create_user(user_id, message.from_user.username)
    
    if user and user.get("is_banned"):
        return await message.answer("You are banned from using this bot.")

    if not await is_subscribed(bot, user_id):
        return await message.answer(
            "Welcome!\n\nTo use this anonymous chat, please subscribe to our channel first.",
            reply_markup=inline.get_subscription_keyboard()
        )
    
    has_location = user.get("location_code") is not None
    await message.answer(
        "Welcome to the Anonymous Chat!\n\nFind people from specific countries, chat safely, and enjoy a minimalist experience.",
        reply_markup=inline.get_main_menu_keyboard(has_location)
    )

# --- ПРОВЕРКА ПОДПИСКИ ПО КНОПКЕ ---
@router.callback_query(F.data == "check_sub")
async def check_subscription_callback(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    if await is_subscribed(bot, user_id):
        user = db.get_or_create_user(user_id, callback.from_user.username)
        has_location = user.get("location_code") is not None
        await callback.message.edit_text(
            "Thank you for subscribing! Welcome to the main menu:",
            reply_markup=inline.get_main_menu_keyboard(has_location)
        )
    else:
        await callback.answer("❌ You haven't subscribed yet. Please subscribe to the channel.", show_alert=True)

# --- ВОЗВРАТ В МЕНЮ ---
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_or_create_user(user_id)
    
    if user and user.get("is_banned"):
        return await callback.answer("You are banned.", show_alert=True)
        
    has_location = user.get("location_code") is not None
    await callback.message.edit_text(
        "Main Menu:",
        reply_markup=inline.get_main_menu_keyboard(has_location)
    )

# --- СЕКЦИЯ ПРОФИЛЯ (ОПТИМИЗИРОВАНО) ---
@router.callback_query(F.data == "my_profile")
async def view_profile(callback: CallbackQuery):
    user = db.get_or_create_user(callback.from_user.id)
    
    if user and user.get("is_banned"):
        return await callback.answer("You are banned.", show_alert=True)
        
    loc = user.get("location_code")
    # Превращаем короткий код "EU_E_UA" в красивое "Ukraine" прямо в ОЗУ
    loc_text = get_country_name_by_code(loc) if loc else "Not selected"
    status = "⭐️ Premium Member" if user.get("is_premium") else "Regular Member"
    
    profile_text = (
        f"👤 <b>YOUR PROFILE</b>\n\n"
        f"▫️ <b>ID:</b> <code>{user['id']}</code>\n"
        f"▫️ <b>Status:</b> {status}\n"
        f"▫️ <b>Location:</b> {loc_text}\n"
    )
    await callback.message.edit_text(profile_text, parse_mode="HTML", reply_markup=inline.get_back_to_menu_keyboard())

# --- СЕКЦИЯ ПРЕМИУМА ---
@router.callback_query(F.data == "buy_premium")
async def view_premium(callback: CallbackQuery):
    user = db.get_or_create_user(callback.from_user.id)
    if user.get("is_premium"):
        return await callback.answer("You already have Premium status!", show_alert=True)
        
    premium_info = (
        "⭐ <b>PREMIUM BENEFITS</b> (100 Stars)\n\n"
        "Unlock the full power of anonymous communication:\n"
        "• <b>Priority Matching:</b> Find partners 2x faster in the queue.\n"
        "• <b>Media Capabilities:</b> Send custom text formats and unlock premium server status.\n"
        "• <b>Visual Status:</b> Stand out with a unique look in statistics and system profile options.\n\n"
        "Get your Premium subscription right now safely via Telegram Stars."
    )
    await callback.message.edit_text(premium_info, parse_mode="HTML", reply_markup=inline.get_premium_payment_keyboard())

# --- ПОКУПКА ЗА ЗВЕЗДЫ ---
@router.callback_query(F.data == "pay_stars")
async def process_premium_payment(callback: CallbackQuery):
    db.set_premium_status(callback.from_user.id, True)
    await callback.answer("🎉 Premium activated successfully!", show_alert=True)
    
    user = db.get_or_create_user(callback.from_user.id)
    has_location = user.get("location_code") is not None
    await callback.message.edit_text(
        "Thank you for supporting us! Premium benefits are now active.",
        reply_markup=inline.get_main_menu_keyboard(has_location)
    )
