import asyncio
import json
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ================== SOZLAMALAR ==================
BOT_TOKEN = os.getenv("BOT_TOKEN", "BU_YERGA_TOKEN")      # @BotFather beradi
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))                 # sizning Telegram ID
CHANNEL = os.getenv("CHANNEL", "")                         # majburiy obuna: "@kanal" (bo'sh = o'chiq)
TOTAL = 36
DB_FILE = "videos.json"
CARTOON_NAME = "🐾 Hayvonlar olami"
# ================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(BOT_TOKEN)
dp = Dispatcher()


def load_db() -> dict:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_db(db: dict) -> None:
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


DB = load_db()

MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎬 Videolar")],
    ],
    resize_keyboard=True,
)


async def is_subscribed(user_id: int) -> bool:
    if not CHANNEL:
        return True
    try:
        m = await bot.get_chat_member(CHANNEL, user_id)
        return m.status in ("member", "administrator", "creator")
    except Exception:
        return True  # xatolik bo'lsa to'sib qo'ymaymiz


def sub_kb():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📢 Kanalga obuna bo'lish",
                               url=f"https://t.me/{CHANNEL.lstrip('@')}"))
    b.row(InlineKeyboardButton(text="✅ Tekshirish", callback_data="check"))
    return b.as_markup()


def episodes_kb():
    b = InlineKeyboardBuilder()
    for i in range(1, TOTAL + 1):
        mark = "" if str(i) in DB else "🔒"
        b.button(text=f"{i}{mark}", callback_data=f"ep:{i}")
    b.adjust(6)  # 6 x 6 setka
    return b.as_markup()


def nav_kb(n: int):
    b = InlineKeyboardBuilder()
    row = []
    if n > 1:
        row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"ep:{n-1}"))
    row.append(InlineKeyboardButton(text="📋 Qismlar", callback_data="list"))
    if n < TOTAL:
        row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"ep:{n+1}"))
    b.row(*row)
    return b.as_markup()


# ---------- Foydalanuvchi ----------
@dp.message(CommandStart())
async def start(m: Message):
    if not await is_subscribed(m.from_user.id):
        return await m.answer("Botdan foydalanish uchun kanalga obuna bo'ling 👇",
                              reply_markup=sub_kb())
    await m.answer(
        f"Salom, {m.from_user.first_name}! 👋\n\n"
        f"{CARTOON_NAME} multfilmiga xush kelibsiz!\n"
        f"Jami {TOTAL} qism. Boshlash uchun «🎬 Videolar» tugmasini bosing.",
        reply_markup=MAIN_KB,
    )


@dp.message(F.text == "🎬 Videolar")
async def videos(m: Message):
    if not await is_subscribed(m.from_user.id):
        return await m.answer("Avval kanalga obuna bo'ling 👇", reply_markup=sub_kb())
    await m.answer(f"{CARTOON_NAME}\nQismni tanlang 👇", reply_markup=episodes_kb())


@dp.callback_query(F.data == "check")
async def check(c: CallbackQuery):
    if await is_subscribed(c.from_user.id):
        await c.message.delete()
        await c.message.answer("✅ Rahmat! Endi «🎬 Videolar» ni bosing.",
                               reply_markup=MAIN_KB)
    else:
        await c.answer("Hali obuna bo'lmagansiz!", show_alert=True)


@dp.callback_query(F.data == "list")
async def show_list(c: CallbackQuery):
    await c.message.answer(f"{CARTOON_NAME}\nQismni tanlang 👇",
                           reply_markup=episodes_kb())
    await c.answer()


@dp.callback_query(F.data.startswith("ep:"))
async def send_episode(c: CallbackQuery):
    if not await is_subscribed(c.from_user.id):
        return await c.answer("Avval kanalga obuna bo'ling!", show_alert=True)
    n = int(c.data.split(":")[1])
    file_id = DB.get(str(n))
    if not file_id:
        return await c.answer(f"{n}-qism tez orada chiqadi ⏳", show_alert=True)
    await c.message.answer_video(
        file_id,
        caption=f"{CARTOON_NAME}\n🎞 {n}-qism / {TOTAL}",
        reply_markup=nav_kb(n),
        protect_content=False,
    )
    await c.answer()


# ---------- Admin ----------
def is_admin(m: Message) -> bool:
    return m.from_user.id == ADMIN_ID


@dp.message(F.video, F.func(is_admin))
async def admin_upload(m: Message):
    """Admin videoni yuboradi, izohga (caption) qism raqamini yozadi: 5"""
    cap = (m.caption or "").strip()
    if not cap.isdigit() or not (1 <= int(cap) <= TOTAL):
        return await m.reply(f"Izohga 1 dan {TOTAL} gacha qism raqamini yozing.")
    DB[cap] = m.video.file_id
    save_db(DB)
    await m.reply(f"✅ {cap}-qism saqlandi. Jami: {len(DB)}/{TOTAL}")


@dp.message(Command("stats"), F.func(is_admin))
async def stats(m: Message):
    missing = [str(i) for i in range(1, TOTAL + 1) if str(i) not in DB]
    await m.answer(f"Yuklangan: {len(DB)}/{TOTAL}\n"
                   f"Yo'q qismlar: {', '.join(missing) or 'yo`q'}")


@dp.message(Command("del"), F.func(is_admin))
async def delete_ep(m: Message):
    parts = m.text.split()
    if len(parts) == 2 and DB.pop(parts[1], None):
        save_db(DB)
        return await m.answer(f"{parts[1]}-qism o'chirildi.")
    await m.answer("Foydalanish: /del 5")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
