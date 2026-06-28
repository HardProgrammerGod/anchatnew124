from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import database as db
from keyboards.inline import get_main_menu_keyboard

router = Router()

LOCATIONS = {
    "europe_east": {
        "text": "Eastern Europe",
        "countries": {
            "EU_E_UA": "Ukraine", "EU_E_PL": "Poland", "EU_E_RO": "Romania", 
            "EU_E_CZ": "Czechia", "EU_E_HU": "Hungary", "EU_E_SK": "Slovakia", 
            "EU_E_BG": "Bulgaria", "EU_E_MD": "Moldova"
        }
    },
    "europe_west": {
        "text": "Western & North Europe",
        "countries": {
            "EU_W_UK": "United Kingdom", "EU_W_FR": "France", "EU_W_DE": "Germany", 
            "EU_W_IT": "Italy", "EU_W_ES": "Spain", "EU_W_NL": "Netherlands",
            "EU_W_BE": "Belgium", "EU_W_SE": "Sweden", "EU_W_NO": "Norway", "EU_W_FI": "Finland"
        }
    },
    "asia": {
        "text": "Asia & Central Asia",
        "countries": {
            "AS_JP": "Japan", "AS_KR": "South Korea", "AS_CN": "China", 
            "AS_IN": "India", "AS_KZ": "Kazakhstan", "AS_UZ": "Uzbekistan",
            "AS_KG": "Kyrgyzstan", "AS_SG": "Singapore", "AS_MY": "Malaysia"
        }
    },
    "middle_east": {
        "text": "Middle East",
        "countries": {
            "ME_IL": "Israel", "ME_TR": "Turkey", "ME_AE": "UAE", 
            "ME_SA": "Saudi Arabia", "ME_QA": "Qatar", "ME_GE": "Georgia", "ME_AM": "Armenia"
        }
    },
    "americas": {
        "text": "Americas",
        "countries": {
            "AM_US": "USA", "AM_CA": "Canada", "AM_MX": "Mexico", 
            "AM_BR": "Brazil", "AM_AR": "Argentina", "AM_CL": "Chile", 
            "AM_CO": "Colombia", "AM_PE": "Peru"
        }
    }
}

def get_country_name_by_code(code: str) -> str:
    for reg_data in LOCATIONS.values():
        if code in reg_data["countries"]:
            return reg_data["countries"][code]
    return "Unknown Country"

@router.callback_query(F.data == "open_regions")
async def select_region(callback: CallbackQuery):
    buttons = []
    for key, data in LOCATIONS.items():
        buttons.append([InlineKeyboardButton(text=data["text"], callback_data=f"reg_{key}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_to_menu")])
    
    await callback.message.edit_text(
        "📍 <b>Select your region:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("reg_"))
async def select_country(callback: CallbackQuery):
    reg_key = callback.data.replace("reg_", "")
    if reg_key not in LOCATIONS:
        return await callback.answer("Error: Region not found.", show_alert=True)
        
    countries = LOCATIONS[reg_key]["countries"]
    
    buttons = []
    row = []
    for code, name in countries.items():
        row.append(InlineKeyboardButton(text=name, callback_data=f"setloc_{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="open_regions")])
    
    await callback.message.edit_text(
        f"📍 <b>Select your country in {LOCATIONS[reg_key]['text']}:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("setloc_"))
async def save_location(callback: CallbackQuery):
    loc_code = callback.data.replace("setloc_", "")
    db.update_user_location(callback.from_user.id, loc_code)
    
    country_name = get_country_name_by_code(loc_code)
    await callback.answer("📍 Location updated!", show_alert=False)
    await callback.message.edit_text(
        f"Success! Your location is now set to <b>{country_name}</b>.",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(has_location=True)
    )
