from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import database as db
from keyboards.inline import get_main_menu_keyboard

router = Router()

# Структура данных для экономии памяти
LOCATIONS = {
    "europe": {
        "text": "Europe",
        "regions": {
            "eu_west": {
                "text": "Western Europe",
                "countries": {"EU_W_UK": "United Kingdom", "EU_W_FR": "France", "EU_W_DE": "Germany"}
            },
            "eu_east": {
                "text": "Eastern Europe",
                "countries": {"EU_E_UA": "Ukraine", "EU_E_PL": "Poland", "EU_E_RO": "Romania"}
            }
        }
    },
    "asia": {
        "text": "Asia",
        "regions": {
            "as_east": {
                "text": "East Asia",
                "countries": {"AS_E_JP": "Japan", "AS_E_KR": "South Korea", "AS_E_CN": "China"}
            },
            "as_south": {
                "text": "South Asia",
                "countries": {"AS_S_IN": "India", "AS_S_PK": "Pakistan", "AS_S_BD": "Bangladesh"}
            }
        }
    },
    "america": {
        "text": "America",
        "regions": {
            "am_north": {
                "text": "North America",
                "countries": {"AM_N_US": "USA", "AM_N_CA": "Canada", "AM_N_MX": "Mexico"}
            },
            "am_south": {
                "text": "South/Central America",
                "countries": {"AM_S_BR": "Brazil", "AM_S_AR": "Argentina", "AM_S_CL": "Chile"}
            }
        }
    }
}

# --- ВЫБОР КОНТИНЕНТА ---
@router.callback_query(F.data == "open_regions")
async def select_continent(callback: CallbackQuery):
    buttons = []
    for key, data in LOCATIONS.items():
        buttons.append([InlineKeyboardButton(text=data["text"], callback_data=f"cont_{key}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_to_menu")])
    
    await callback.message.edit_text(
        "📍 <b>Select your continent:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

# --- ВЫБОР ЧАСТИ КОНТИНЕНТА ---
@router.callback_query(F.data.startswith("cont_"))
async def select_region(callback: CallbackQuery):
    cont_key = callback.data.split("_")[1]
    regions = LOCATIONS[cont_key]["regions"]
    
    buttons = []
    for key, data in regions.items():
        buttons.append([InlineKeyboardButton(text=data["text"], callback_data=f"reg_{cont_key}_{key}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="open_regions")])
    
    await callback.message.edit_text(
        f"📍 <b>Select region in {LOCATIONS[cont_key]['text']}:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

# --- ВЫБОР СТРАНЫ ---
@router.callback_query(F.data.startswith("reg_"))
async def select_country(callback: CallbackQuery):
    _, cont_key, reg_key = callback.data.split("_")
    countries = LOCATIONS[cont_key]["regions"][reg_key]["countries"]
    
    buttons = []
    # Разносим по 2 страны в строку для красоты
    row = []
    for code, name in countries.items():
        row.append(InlineKeyboardButton(text=name, callback_data=f"setloc_{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"cont_{cont_key}")])
    
    await callback.message.edit_text(
        "📍 <b>Select your country:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

# --- СОХРАНЕНИЕ ЛОКАЦИИ ---
@router.callback_query(F.data.startswith("setloc_"))
async def save_location(callback: CallbackQuery):
    loc_code = callback.data.split("_")[1] + "_" + callback.data.split("_")[2] + "_" + callback.data.split("_")[3]
    db.update_user_location(callback.from_user.id, loc_code)
    
    await callback.answer("📍 Location saved!", show_alert=False)
    await callback.message.edit_text(
        f"Success! Your location is now set to <b>{loc_code.replace('_', ' ')}</b>.",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(has_location=True)
    )
