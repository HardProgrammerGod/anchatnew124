import re
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import database as db

router = Router()

# Регулярное выражение для обнаружения ссылок
LINK_PATTERN = re.compile(r'(https?://\S+|www\.\S+|\bt\.me\/\S+)')

# --- ОБЩИЙ Inline-Ответ для Премиума при нарушении ---
def get_premium_promo_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Get Premium (100 Stars)", callback_data="buy_premium")],
        [InlineKeyboardButton(text="🚫 Close Notice", callback_data="close_notice")]
    ])

# --- НАЧАТЬ ПОИСК ---
@router.callback_query(F.data == "start_search")
async def search_partner(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    user = db.get_or_create_user(user_id)
    
    if not user.get("location_code"):
        return await callback.answer("⚠️ Please select your location first!", show_alert=True)
        
    await callback.message.edit_text(
        "🔍 <b>Searching for a partner...</b>\n\nCommands during chat:\n/leave — end conversation\n/report — report partner",
        parse_mode="HTML"
    )
    
    session = db.start_search_session(user_id)
    if session and session.get("user_two"):
        # Чат успешно создан, уведомляем обоих
        p1 = session["user_one"]
        p2 = session["user_two"]
        
        p1_user = db.get_or_create_user(p1)
        p2_user = db.get_or_create_user(p2)
        
        m1 = f"🎉 <b>Partner found!</b>\nLocation: <code>{p2_user['location_code'].replace('_', ' ')}</code>\nSay hello!"
        m2 = f"🎉 <b>Partner found!</b>\nLocation: <code>{p1_user['location_code'].replace('_', ' ')}</code>\nSay hello!"
        
        await bot.send_message(p1, m1, parse_mode="HTML")
        await bot.send_message(p2, m2, parse_mode="HTML")

# --- КОМАНДА ВЫХОДА /LEAVE ---
@router.message(F.text == "/leave")
async def leave_chat(message: Message, bot: Bot):
    user_id = message.from_user.id
    partner_id = db.close_chat_session(user_id)
    
    user = db.get_or_create_user(user_id)
    from keyboards.inline import get_main_menu_keyboard
    
    if partner_id:
        await message.answer("You left the chat.", reply_markup=get_main_menu_keyboard(True))
        await bot.send_message(partner_id, "Your partner left the chat.", reply_markup=get_main_menu_keyboard(True))
    else:
        # Если пользователь был просто в очереди поиска
        await message.answer("Search cancelled.", reply_markup=get_main_menu_keyboard(True))

# --- КОМАНДА ЖАЛОБЫ /REPORT ---
@router.message(F.text.startswith("/report"))
async def report_user(message: Message):
    user_id = message.from_user.id
    partner_id = db.get_active_partner(user_id)
    
    if not partner_id:
        return await message.answer("You are not in an active chat.")
        
    reason = message.text.replace("/report", "").strip()
    if not reason:
        reason = "No reason provided by user"
        
    db.create_report(user_id, partner_id, reason)
    await message.answer("⚠️ <b>Your report has been submitted to administrators.</b>\nThank you for keeping our community safe.", parse_mode="HTML")

# --- ФИЛЬТРАЦИЯ И ПЕРЕСЫЛКА СООБЩЕНИЙ ---

# 1. Запрет на любые Медиафайлы (Фото, Голосовые, Кружки, Аудио, Видео, Документы)
@router.message(F.photo | F.voice | F.video_note | F.video | F.audio | F.document | F.sticker)
async def block_media(message: Message):
    user_id = message.from_user.id
    partner_id = db.get_active_partner(user_id)
    
    if not partner_id:
        return # Если не в чате, просто игнорируем
        
    await message.answer(
        "❌ <b>Sharing media (images, voice notes, video circles, stickers) is prohibited!</b>\n\n"
        "⭐ Upgrade to <b>Premium for 100 Stars</b> to get high-priority delivery and unlock visual status updates.",
        parse_mode="HTML",
        reply_markup=get_premium_promo_markup()
    )

# 2. Обработка Текста (Проверка на ссылки + пересылка)
@router.message(F.text)
async def handle_text_chat(message: Message, bot: Bot):
    user_id = message.from_user.id
    partner_id = db.get_active_partner(user_id)
    
    if not partner_id:
        return # Не в чате — ничего не делаем

    # Проверка на наличие ссылок в тексте
    if LINK_PATTERN.search(message.text):
        return await message.answer(
            "❌ <b>Sending links is prohibited to prevent spam!</b>\n\n"
            "⭐ Upgrade to <b>Premium for 100 Stars</b> to gain exclusive profile features and unlock special perks.",
            parse_mode="HTML",
            reply_markup=get_premium_promo_markup()
        )
        
    # Если всё чисто — пересылаем собеседнику обычный текст
    try:
        await bot.send_message(chat_id=partner_id, text=message.text)
    except Exception:
        # Если не удалось отправить (например, партнер заблокировал бота во время чата)
        db.close_chat_session(user_id)
        from keyboards.inline import get_main_menu_keyboard
        await message.answer("Connection lost. Your partner is unavailable.", reply_markup=get_main_menu_keyboard(True))

# Закрытие уведомления по кнопке
@router.callback_query(F.data == "close_notice")
async def close_notice(callback: CallbackQuery):
    await callback.message.delete()
