from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.deep_linking import create_start_link

import database as db
from config import CHANNEL_ID, ADMIN_ID
from keyboards import inline
from handlers.location import get_country_name_by_code

router = Router()

# Функция быстрой проверки подписки
async def is_subscribed(bot: Bot, user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

# --- КОМАНДА /START (С ОБРАБОТКОЙ РЕФЕРАЛА) ---
@router.message(Command("start"))
async def cmd_start(message: Message, bot: Bot):
    user_id = message.from_user.id
    
    # Проверяем, пришел ли пользователь по реферальной ссылке (/start 123456789)
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])

    # Передаем referrer_id в базу данных
    user = db.get_or_create_user(user_id, message.from_user.username, referrer_id)
    
    if user and user.get("is_banned"):
        return await message.answer("You are banned from using this bot.")

    if not await is_subscribed(bot, user_id):
        return await message.answer(
            "Welcome!\n\nTo use this anonymous chat, please subscribe to our channel first.",
            reply_markup=inline.get_subscription_keyboard()
        )
    
    # Если реферал успешно зарегистрировался и у пригласившего активировался премиум,
    # мы можем отправить скрытое уведомление пригласившему (опционально, сработает при его активности)
    if referrer_id and referrer_id != user_id:
        try:
            await bot.send_message(
                chat_id=referrer_id, 
                text="🎉 A friend joined via your link! Your <b>Premium Status</b> has been activated!", 
                parse_mode="HTML"
            )
        except Exception:
            pass

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

# --- СЕКЦИЯ ПРОФИЛЯ ---
@router.callback_query(F.data == "my_profile")
async def view_profile(callback: CallbackQuery):
    user = db.get_or_create_user(callback.from_user.id)
    
    if user and user.get("is_banned"):
        return await callback.answer("You are banned.", show_alert=True)
        
    loc = user.get("location_code")
    loc_text = get_country_name_by_code(loc) if loc else "Not selected"
    status = "⭐️ Premium Member" if user.get("is_premium") else "Regular Member"
    
    profile_text = (
        f"👤 <b>YOUR PROFILE</b>\n\n"
        f"▫️ <b>ID:</b> <code>{user['id']}</code>\n"
        f"▫️ <b>Status:</b> {status}\n"
        f"▫️ <b>Location:</b> {loc_text}\n"
    )
    await callback.message.edit_text(profile_text, parse_mode="HTML", reply_markup=inline.get_back_to_menu_keyboard())

# --- СЕКЦИЯ ПРЕМИУМА (БЕСПЛАТНО ЗА ДРУГА) ---
@router.callback_query(F.data == "buy_premium")
async def view_premium(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    user = db.get_or_create_user(user_id)
    
    if user.get("is_premium"):
        return await callback.answer("You already have Premium status!", show_alert=True)
        
    # Генерируем красивую реферальную ссылку через утилиту aiogram
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        
    premium_info = (
        "⭐ <b>FREE PREMIUM STATUS</b>\n\n"
        "Unlock the full power of anonymous communication entirely for free! "
        "Simply invite <b>1 friend</b> to our bot using your personal link.\n\n"
        "<b>Premium Perks:</b>\n"
        "• <b>Priority Matching:</b> Find partners 2x faster.\n"
        "• <b>Media Capabilities:</b> Extra server resource priority.\n"
        "• <b>Visual Status:</b> Unique look in your profile.\n\n"
        f"🔗 <b>Your Invite Link:</b>\n<code>{ref_link}</code>\n\n"
        "<i>Share this link with a friend. Once they start the bot, your Premium status activates instantly!</i>"
    )
    
    # Кнопку оплаты заменяем на обычный возврат, так как ссылка уже на экране
    await callback.message.edit_text(
        premium_info, 
        parse_mode="HTML", 
        disable_web_page_preview=True, 
        reply_markup=inline.get_back_to_menu_keyboard()
    )
