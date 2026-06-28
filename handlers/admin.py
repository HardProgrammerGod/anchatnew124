from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

import database as db
from config import ADMIN_ID

router = Router()

# Фильтр для проверки прав администратора
def is_admin_filter(message: Message) -> bool:
    return message.from_user.id == ADMIN_ID

# --- ПАНЕЛЬ АДМИНИСТРАТОРА И СТАТИСТИКА ---
@router.message(Command("admin"), is_admin_filter)
async def cmd_admin(message: Message):
    stats = db.get_admin_stats()
    
    stats_text = (
        "⚙️ <b>ADMIN CONTROL PANEL</b>\n\n"
        f"▫️ <b>Total Registered:</b> {stats['total_users']}\n"
        f"▫️ <b>Premium Users:</b> {stats['premium_users']} ⭐\n"
        f"▫️ <b>Banned Users:</b> {stats['banned_users']} 🚫\n"
        "---------------------------\n"
        f"▫️ <b>Active Chats:</b> {stats['active_chats']}\n"
        f"▫️ <b>Users in Queue:</b> {stats['in_queue']}\n"
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ View Active Reports", callback_data="admin_reports")],
        [InlineKeyboardButton(text="🔄 Refresh Stats", callback_data="admin_refresh")]
    ])
    
    await message.answer(stats_text, parse_mode="HTML", reply_markup=markup)

# Обновление статистики по кнопке
@router.callback_query(F.data == "admin_refresh")
async def refresh_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Access denied.", show_alert=True)
        
    stats = db.get_admin_stats()
    stats_text = (
        "⚙️ <b>ADMIN CONTROL PANEL</b>\n\n"
        f"▫️ <b>Total Registered:</b> {stats['total_users']}\n"
        f"▫️ <b>Premium Users:</b> {stats['premium_users']} ⭐\n"
        f"▫️ <b>Banned Users:</b> {stats['banned_users']} 🚫\n"
        "---------------------------\n"
        f"▫️ <b>Active Chats:</b> {stats['active_chats']}\n"
        f"▫️ <b>Users in Queue:</b> {stats['in_queue']}\n"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ View Active Reports", callback_data="admin_reports")],
        [InlineKeyboardButton(text="🔄 Refresh Stats", callback_data="admin_refresh")]
    ])
    await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=markup)

# --- УПРАВЛЕНИЕ ЖАЛОБАМИ ---
@router.callback_query(F.data == "admin_reports")
async def show_reports(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Access denied.", show_alert=True)
        
    reports = db.get_open_reports(limit=5)
    if not reports:
        return await callback.answer("No active reports found! Everything is clean.", show_alert=True)
        
    report = reports[0] # Берем первую открытую жалобу
    
    report_text = (
        f"⚠️ <b>REPORT NOTIFICATION (ID: {report['id']})</b>\n\n"
        f"▫️ <b>Reporter ID:</b> <code>{report['reporter_id']}</code>\n"
        f"▫️ <b>Offender ID:</b> <code>{report['reported_id']}</code>\n"
        f"▫️ <b>Reason:</b> <i>{report['reason']}</i>\n"
    )
    
    # Кнопки принятия мер
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚫 Ban Offender", callback_data=f"adm_ban_{report['reported_id']}_{report['id']}"),
            InlineKeyboardButton(text="✅ Dismiss", callback_data=f"adm_dismiss_{report['id']}")
        ],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="admin_refresh")]
    ])
    
    await callback.message.edit_text(report_text, parse_mode="HTML", reply_markup=markup)

# Обработка Бана
@router.callback_query(F.data.startswith("adm_ban_"))
async def admin_ban_action(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        return
        
    data_parts = callback.data.split("_")
    offender_id = int(data_parts[2])
    report_id = int(data_parts[3])
    
    # Бан в базе и закрытие жалобы
    db.set_ban_status(offender_id, True)
    db.resolve_report(report_id)
    db.close_chat_session(offender_id) # На всякий случай выкидываем из чата
    
    try:
        await bot.send_message(offender_id, "You have been permanently banned by an administrator for violating chat rules.")
    except Exception:
        pass
        
    await callback.answer("User permanently banned.", show_alert=True)
    # Показываем следующую жалобу
    await show_reports(callback)

# Обработка Отклонения Жалобы
@router.callback_query(F.data.startswith("adm_dismiss_"))
async def admin_dismiss_action(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
        
    report_id = int(callback.data.split("_")[2])
    db.resolve_report(report_id)
    
    await callback.answer("Report dismissed.", show_alert=False)
    # Показываем следующую жалобу
    await show_reports(callback)
