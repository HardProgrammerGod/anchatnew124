from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_URL

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Subscribe to Channel", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="🔄 Check Subscription", callback_data="check_sub")]
    ])

def get_main_menu_keyboard(has_location: bool) -> InlineKeyboardMarkup:
    loc_text = "📍 Change Location" if has_location else "📍 Select Location"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Find a Partner", callback_data="start_search")],
        [InlineKeyboardButton(text=loc_text, callback_data="open_regions")],
        [InlineKeyboardButton(text="👤 My Profile", callback_data="my_profile"),
         InlineKeyboardButton(text="⭐ Premium", callback_data="buy_premium")]
    ])

def get_premium_payment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Buy Premium for 100 ⭐️", callback_data="pay_stars")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_menu")]
    ])

def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_to_menu")]
    ])
