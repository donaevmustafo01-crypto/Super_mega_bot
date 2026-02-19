import telebot
from telebot import types
import google.generativeai as genai
import sqlite3
import secrets
import string
import os
import requests
from flask import Flask
from threading import Thread

# --- ТАНЗИМОТ ВА КАЛИДҲО ---
TOKEN = '8126192450:AAHuuv9o8fSFW9P96OfXrSNYdcJMONM58zQ'
GEMINI_KEY = 'AIzaSyBMtb30V4UkMw_XbDyytHdthDGic7AWP_8'
ADMIN_ID = 684347209 # ID-и ту (Аз @userinfobot гирифтаӣ)
DC_NUMBER = "+992904104860"

bot = telebot.TeleBot(TOKEN)
app = Flask('')

# Танзими AI (Gemini 1.5 Flash)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- БАЗАИ МАЪЛУМОТ ---
conn = sqlite3.connect('empire_final.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, img_count INTEGER DEFAULT 0, status TEXT DEFAULT "free")')
cursor.execute('CREATE TABLE IF NOT EXISTS promo_codes (code TEXT PRIMARY KEY, used INTEGER DEFAULT 0)')
conn.commit()

@app.route('/')
def home(): return "Empire AI Global System is Live! 💎"

def run_web(): app.run(host='0.0.0.0', port=8080)

# --- МЕНЮҲО ---
def get_main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🧠 Пурсиш аз AI", "🖼 Сохтани Сурат (AI)")
    m.add("🔑 Фаъолсозии VIP", "📊 Профил ва Лимит")
    m.add("💳 Харидани Код", "📢 Реклама")
    return m

# --- ФУНКСИЯҲОИ АДМИН (СОХТАНИ КОДҲО) ---
def generate_random_code():
    chars = string.ascii_uppercase + string.digits
    return "VIP-" + "".join(secrets.choice(chars) for _ in range(12))

@bot.message_handler(commands=['gen'])
def cmd_gen(m):
    if m.from_user.id != ADMIN_ID: return
    try:
        num = int(m.text.split()[1])
        codes = []
        for _ in range(num):
            new_code = generate_random_code()
            cursor.execute('INSERT INTO promo_codes (code) VALUES (?)', (new_code,))
            codes.append(f"`{new_code}`")
        conn.commit()
        bot.send_message(m.chat.id, f"✅ **{num} коди нав сохта шуд:**\n\n" + "\n".join(codes), parse_mode="Markdown")
    except:
        bot.send_message(m.chat.id, "Истифода: `/gen 5`", parse_mode="Markdown")

# --- СИСТЕМАИ ЛИМИТ ВА AI ---
@bot.message_handler(commands=['start'])
def start(m):
    cursor.execute('INSERT OR IGNORE INTO users (id) VALUES (?)', (m.chat.id,))
    conn.commit()
    bot.send_message(m.chat.id, "💎 **Ба Империяи AI хуш омадед!**\n\nШумо 10 имконияти ройгон доред.", reply_markup=get_main_menu())

@bot.message_handler(func=lambda m: m.text == "🖼 Сохтани Сурат (AI)")
def check_limit_img(m):
    user = cursor.execute('SELECT img_count, status FROM users WHERE id = ?', (m.chat.id,)).fetchone()
    if user and user[1] == "free" and user[0] >= 10:
        bot.send_message(m.chat.id, "🚫 **Лимити ройгон тамом шуд!**\nЛутфан тугмаи 💳 **Харидани Код**-ро пахш кунед.")
        return
    msg = bot.send_message(m.chat.id, "🎨 Чиро расм кашам? (Текст фиристед)")
    bot.register_next_step_handler(msg, process_image)

def process_image(m):
    try:
        status = bot.send_message(m.chat.id, "⏳ AI расм кашида истодааст...")
        url = f"https://pollinations.ai/p/{m.text.replace(' ', '%20')}?width=1024&height=1024"
        bot.send_photo(m.chat.id, url, caption=f"✨ {m.text}\n💎 @Empire_Bot")
        cursor.execute('UPDATE users SET img_count = img_count + 1 WHERE id = ?', (m.chat.id,))
        conn.commit()
        bot.delete_message(m.chat.id, status.message_id)
    except: bot.send_message(m.chat.id, "❌ Хатогӣ дар сохтани расм.")

# --- ФАЪОЛСОЗИИ КОД ВА ХАБАР БА АДМИН ---
@bot.message_handler(func=lambda m: m.text == "🔑 Фаъолсозии VIP")
def ask_voucher(m):
    msg = bot.send_message(m.chat.id, "🔑 Коди харидаатонро ворид кунед:")
    bot.register_next_step_handler(msg, use_voucher)

def use_voucher(m):
    code = m.text.strip()
    cursor.execute('SELECT used FROM promo_codes WHERE code = ?', (code,))
    res = cursor.fetchone()
    if res and res[0] == 0:
        cursor.execute('UPDATE promo_codes SET used = 1 WHERE code = ?', (code,))
        cursor.execute('UPDATE users SET img_count = 0, status = "vip" WHERE id = ?', (m.chat.id,))
        conn.commit()
        bot.send_message(m.chat.id, "🎉 **VIP фаъол шуд!** Лимити шумо аз нав шуд.")
        # Хабар ба Админ
        bot.send_message(ADMIN_ID, f"🔔 **ХАБАР:** Юзер @{m.from_user.username} (ID: {m.chat.id}) кодро истифода бурд:\n`{code}`", parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "❌ Код нодуруст аст ё аллакай истифода шудааст.")

# --- ДИГАР ФУНКСИЯҲО ---
@bot.message_handler(func=lambda m: m.text == "🧠 Пурсиш аз AI")
def ai_ask(m):
    msg = bot.send_message(m.chat.id, "🤖 Саволи худро нависед:")
    bot.register_next_step_handler(msg, lambda ms: bot.reply_to(ms, model.generate_content(ms.text).text))

@bot.message_handler(func=lambda m: m.text == "💳 Харидани Код")
def pay_info(m):
    bot.send_message(m.chat.id, f"💳 **Пардохт ба DC Wallet**\n\nРақам: `{DC_NUMBER}`\nМаблағ: **30 сомон**\n\nПас аз пардохт чекро ба @Bot_creator_tj фиристед ва коди VIP-ро гиред.")

@bot.message_handler(func=lambda m: m.text == "📊 Профил ва Лимит")
def my_stats(m):
    u = cursor.execute('SELECT img_count, status FROM users WHERE id = ?', (m.chat.id,)).fetchone()
    bot.send_message(m.chat.id, f"👤 **Профил:**\nСтатус: {u[1].upper()}\nРасмҳо: {u[0]}/10")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.infinity_polling()
