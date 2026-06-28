import asyncio
import logging
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError

import database as db
from config import ADMIN_ID

router = Router()

# Стейты для безопасного ожидания текста рассылки
class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()

def is_admin_filter(message: Message) -> bool:
    return message.from_user.id == ADMIN_ID

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
        [InlineKeyboardButton(text="📢 Create Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⚠️ View Active Reports", callback_data="admin_reports")],
        [InlineKeyboardButton(text="🔄 Refresh Stats", callback_data="admin_refresh")]
    ])
    await message.answer(stats_text, parse_mode="HTML", reply_markup=markup)

@router.callback_query(F.data == "admin_refresh")
async def refresh_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
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
        [InlineKeyboardButton(text="📢 Create Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⚠️ View Active Reports", callback_data="admin_reports")],
        [InlineKeyboardButton(text="🔄 Refresh Stats", callback_data="admin_refresh")]
    ])
    await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=markup)

# --- ИНИЦИАЛИЗАЦИЯ РАССЫЛКИ ---
@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    await callback.message.edit_text(
        "📝 <b>Enter the text for global broadcast:</b>\n\n"
        "You can use HTML tags (<b>, <i>, <code>). To cancel, type /cancel.",
        parse_mode="HTML"
    )

# --- ПРОЦЕСС БЕЗОПАСНОЙ РАССЫЛКИ (АНТИ-СПАМ БЛОК) ---
@router.message(AdminStates.waiting_for_broadcast_text, is_admin_filter)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("Broadcast cancelled.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Back to Admin Panel", callback_data="admin_refresh")]
        ]))

    broadcast_text = message.text
    await state.clear()
    
    status_msg = await message.answer("🚀 <b>Broadcast started. Please wait...</b>", parse_mode="HTML")
    
    offset = 0
    limit = 100
    success_count = 0
    fail_count = 0

    while True:
        # Выгружаем юзеров порциями по 100 человек (ОЗУ в безопасности)
        users = db.get_users_chunk(offset, limit)
        if not users:
            break
            
        for user_id in users:
            try:
                await bot.send_message(chat_id=user_id, text=broadcast_text, parse_mode="HTML")
                success_count += 1
                # Спим 0.05 сек между отправками, чтобы выдерживать стабильные ~20 сообщений/сек (Ниже лимита TG)
                await asyncio.sleep(0.05)
            except TelegramRetryAfter as e:
                # Если всё же поймали FloodWait — спим столько, сколько требует API
                await asyncio.sleep(e.retry_after)
                try:
                    await bot.send_message(chat_id=user_id, text=broadcast_text, parse_mode="HTML")
                    success_count += 1
                except Exception:
                    fail_count += 1
            except TelegramAPIError:
                # Бот заблокирован пользователем или ID неактивен
                fail_count += 1
            except Exception as e:
                logging.error(f"Unexpected broadcast error for {user_id}: {e}")
                fail_count += 1
                
        offset += limit

    await status_msg.edit_text(
        f"✅ <b>Broadcast Completed!</b>\n\n"
        f"▫️ <b>Sent successfully:</b> {success_count}\n"
        f"▫️ <b>Failed / Blocked:</b> {fail_count}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Return to Admin Panel", callback_data="admin_refresh")]
        ])
    )

# --- ЖАЛОБЫ ---
@router.callback_query(F.data == "admin_reports")
async def show_reports(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    reports = db.get_open_reports(limit=5)
    if not reports:
        return await callback.answer("No active reports found! Everything is clean.", show_alert=True)
        
    report = reports[0]
    report_text = (
        f"⚠️ <b>REPORT NOTIFICATION (ID: {report['id']})</b>\n\n"
        f"▫️ <b>Reporter ID:</b> <code>{report['reporter_id']}</code>\n"
        f"▫️ <b>Offender ID:</b> <code>{report['reported_id']}</code>\n"
        f"▫️ <b>Reason:</b> <i>{report['reason']}</i>\n"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚫 Ban Offender", callback_data=f"adm_ban_{report['reported_id']}_{report['id']}"),
            InlineKeyboardButton(text="✅ Dismiss", callback_data=f"adm_dismiss_{report['id']}")
        ],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="admin_refresh")]
    ])
    await callback.message.edit_text(report_text, parse_mode="HTML", reply_markup=markup)

@router.callback_query(F.data.startswith("adm_ban_"))
async def admin_ban_action(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID: return
    data_parts = callback.data.split("_")
    offender_id = int(data_parts[2])
    report_id = int(data_parts[3])
    
    db.set_ban_status(offender_id, True)
    db.resolve_report(report_id)
    db.close_chat_session(offender_id)
    
    try:
        await bot.send_message(offender_id, "You have been permanently banned by an administrator for violating chat rules.")
    except Exception: pass
        
    await callback.answer("User permanently banned.", show_alert=True)
    await show_reports(callback)

@router.callback_query(F.data.startswith("adm_dismiss_"))
async def admin_dismiss_action(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    report_id = int(callback.data.split("_")[2])
    db.resolve_report(report_id)
    await callback.answer("Report dismissed.", show_alert=False)
    await show_reports(callback)
