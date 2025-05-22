import sys
import subprocess
import pkg_resources
import os

# Auto-install missing dependencies
required = {'python-telegram-bot', 'requests', 'aiogram', 'aiohttp', 'beautifulsoup4', 'nest_asyncio', 'python-dotenv', 'emoji'}
installed = {pkg.key for pkg in pkg_resources.working_set}
missing = required - installed
if missing:
    print(f"Installing missing packages: {missing}")
    python = sys.executable
    subprocess.check_call([python, '-m', 'pip', 'install', *missing])

import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from datetime import datetime
from collections import defaultdict
import nest_asyncio
from dotenv import load_dotenv
import emoji

# --- CONFIG ---
DEVELOPER_CREDIT = '🤖 Bot by CRAVE | Telegram: @cravify'
CHECK_INTERVAL = 120  # seconds
LOG_FILE = 'monitor.log'

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)

# --- DATA STRUCTURES ---
# user_id -> {username: monitor_task}
user_monitors = defaultdict(dict)
# username -> set(user_ids)
username_watchers = defaultdict(set)

# --- UTILS ---
def get_instagram_status(username):
    url = f'https://instagram.com/{username}'
    try:
        resp = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        if resp.status_code == 404 or 'Page Not Found' in resp.text:
            return 'banned'
        elif resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            if soup.find('h2', string='Sorry, this page isn\'t available.'):
                return 'banned'
            return 'unbanned'
        else:
            return 'unknown'
    except Exception as e:
        logging.warning(f"Error checking {username}: {e}")
        return 'error'

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('➕ Add Monitor', callback_data='add_monitor')],
        [InlineKeyboardButton('👀 Status', callback_data='status')],
        [InlineKeyboardButton('❓ Help', callback_data='help')]
    ])

def back_to_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🔙 Back to Menu', callback_data='menu')]
    ])

def status_keyboard(user_id):
    buttons = []
    for username in user_monitors[user_id]:
        buttons.append([
            InlineKeyboardButton(f'🛑 Stop @{username}', callback_data=f'stop_{username}')
        ])
    if not buttons:
        buttons = [[InlineKeyboardButton('🔙 Back to Menu', callback_data='menu')]]
    else:
        buttons.append([InlineKeyboardButton('🔙 Back to Menu', callback_data='menu')])
    return InlineKeyboardMarkup(buttons)

# Add a function to generate action buttons for a username
def action_keyboard(username):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('🛑 Stop', callback_data=f'stop_{username}'),
            InlineKeyboardButton('🔙 Back to Menu', callback_data='menu')
        ]
    ])

# --- MONITORING TASKS ---
async def monitor_unban(context, user_id, username):
    logging.info(f"[UNBAN] Monitoring {username} for user {user_id}")
    while True:
        status = get_instagram_status(username)
        if status == 'unbanned':
            await context.bot.send_message(
                chat_id=user_id,
                text=f'🎉 Yay! <b>@{username}</b> is <b>UNBANNED</b>!\n{DEVELOPER_CREDIT}',
                parse_mode='HTML',
                reply_markup=action_keyboard(username)
            )
            break
        elif status == 'banned':
            await asyncio.sleep(CHECK_INTERVAL)
        elif status == 'error':
            await asyncio.sleep(30)
        else:
            await asyncio.sleep(CHECK_INTERVAL)
    user_monitors[user_id].pop(username, None)
    username_watchers[username].discard(user_id)

async def monitor_ban(context, user_id, username):
    logging.info(f"[BAN] Monitoring {username} for user {user_id}")
    while True:
        status = get_instagram_status(username)
        if status == 'banned':
            await context.bot.send_message(
                chat_id=user_id,
                text=f'🚫 <b>@{username}</b> is <b>BANNED/REMOVED</b>!\n{DEVELOPER_CREDIT}',
                parse_mode='HTML',
                reply_markup=action_keyboard(username)
            )
            break
        elif status == 'unbanned':
            await asyncio.sleep(CHECK_INTERVAL)
        elif status == 'error':
            await asyncio.sleep(30)
        else:
            await asyncio.sleep(CHECK_INTERVAL)
    user_monitors[user_id].pop(username, None)
    username_watchers[username].discard(user_id)

# --- COMMAND HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '👋 Welcome, friend!\nI can monitor Instagram ban/unban status for you.\nUse /unban <code>&lt;username&gt;</code> or /ban <code>&lt;username&gt;</code> to start monitoring, or use the buttons below!\n\n{credit}'.format(credit=DEVELOPER_CREDIT),
        parse_mode='HTML',
        reply_markup=main_menu_keyboard()
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'ℹ️ <b>How to use me:</b>\n'
        '• /unban <code>&lt;username&gt;</code> — Notify when account is unbanned 🟢\n'
        '• /ban <code>&lt;username&gt;</code> — Notify when account is banned 🔴\n'
        '• /stop <code>&lt;username&gt;</code> — Stop monitoring 🛑\n'
        '• /status — List your monitored accounts 👀\n\n'
        'Use the menu below for quick actions!\n{credit}'.format(credit=DEVELOPER_CREDIT),
        parse_mode='HTML',
        reply_markup=main_menu_keyboard()
    )

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text('❗ Usage: <code>/unban &lt;username&gt;</code>', parse_mode='HTML', reply_markup=back_to_menu_keyboard())
        return
    username = args[0].lstrip('@')
    if username in user_monitors[user_id]:
        await update.message.reply_text(f'🔄 Already monitoring <b>@{username}</b> for unban.', parse_mode='HTML', reply_markup=action_keyboard(username))
        return
    logging.info(f"User {user_id} started UNBAN monitor for {username}")
    username_watchers[username].add(user_id)
    task = asyncio.create_task(monitor_unban(context, user_id, username))
    user_monitors[user_id][username] = task
    await update.message.reply_text(
        f'🟢 Monitoring <b>@{username}</b> for <b>UNBAN</b>...\nYou will be notified when the account is back!\n{DEVELOPER_CREDIT}',
        parse_mode='HTML',
        reply_markup=action_keyboard(username)
    )

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text('❗ Usage: <code>/ban &lt;username&gt;</code>', parse_mode='HTML', reply_markup=back_to_menu_keyboard())
        return
    username = args[0].lstrip('@')
    if username in user_monitors[user_id]:
        await update.message.reply_text(f'🔄 Already monitoring <b>@{username}</b> for ban.', parse_mode='HTML', reply_markup=action_keyboard(username))
        return
    logging.info(f"User {user_id} started BAN monitor for {username}")
    username_watchers[username].add(user_id)
    task = asyncio.create_task(monitor_ban(context, user_id, username))
    user_monitors[user_id][username] = task
    await update.message.reply_text(
        f'🔴 Monitoring <b>@{username}</b> for <b>BAN/REMOVAL</b>...\nYou will be notified if the account is banned or removed!\n{DEVELOPER_CREDIT}',
        parse_mode='HTML',
        reply_markup=action_keyboard(username)
    )

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text('❗ Usage: <code>/stop &lt;username&gt;</code>', parse_mode='HTML', reply_markup=back_to_menu_keyboard())
        return
    username = args[0].lstrip('@')
    task = user_monitors[user_id].pop(username, None)
    username_watchers[username].discard(user_id)
    if task:
        task.cancel()
        await update.message.reply_text(f'🛑 Stopped monitoring <b>@{username}</b>.', parse_mode='HTML', reply_markup=back_to_menu_keyboard())
    else:
        await update.message.reply_text(f'⚠️ Not monitoring <b>@{username}</b>.', parse_mode='HTML', reply_markup=back_to_menu_keyboard())

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_monitors[user_id]:
        await update.message.reply_text('ℹ️ You are not monitoring any accounts.', reply_markup=back_to_menu_keyboard())
        return
    msg = '👁️ <b>Accounts you are monitoring:</b>\n'
    for username in user_monitors[user_id]:
        msg += f'• <b>@{username}</b>\n'
    await update.message.reply_text(msg, parse_mode='HTML', reply_markup=status_keyboard(user_id))

# --- CALLBACK QUERY HANDLER ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    data = query.data
    if data == 'menu':
        await query.edit_message_text(
            '🏠 <b>Main Menu</b>\nChoose an action below:',
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )
    elif data == 'add_monitor':
        await query.edit_message_text(
            '➕ <b>Add Monitor</b>\nUse /unban <code>&lt;username&gt;</code> or /ban <code>&lt;username&gt;</code> to start monitoring an account!',
            parse_mode='HTML',
            reply_markup=back_to_menu_keyboard()
        )
    elif data == 'status':
        if not user_monitors[user_id]:
            await query.edit_message_text('ℹ️ You are not monitoring any accounts.', reply_markup=back_to_menu_keyboard())
        else:
            msg = '👁️ <b>Accounts you are monitoring:</b>\n'
            for username in user_monitors[user_id]:
                msg += f'• <b>@{username}</b>\n'
            await query.edit_message_text(msg, parse_mode='HTML', reply_markup=status_keyboard(user_id))
    elif data == 'help':
        await query.edit_message_text(
            'ℹ️ <b>How to use me:</b>\n'
            '• /unban <code>&lt;username&gt;</code> — Notify when account is unbanned 🟢\n'
            '• /ban <code>&lt;username&gt;</code> — Notify when account is banned 🔴\n'
            '• /stop <code>&lt;username&gt;</code> — Stop monitoring 🛑\n'
            '• /status — List your monitored accounts 👀\n\n'
            'Use the menu below for quick actions!\n{credit}'.format(credit=DEVELOPER_CREDIT),
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )
    elif data.startswith('stop_'):
        username = data[5:]
        task = user_monitors[user_id].pop(username, None)
        username_watchers[username].discard(user_id)
        if task:
            task.cancel()
            await query.edit_message_text(f'🛑 Stopped monitoring <b>@{username}</b>.', parse_mode='HTML', reply_markup=back_to_menu_keyboard())
        else:
            await query.edit_message_text(f'⚠️ Not monitoring <b>@{username}</b>.', parse_mode='HTML', reply_markup=back_to_menu_keyboard())

# --- MAIN ---
async def main():
    load_dotenv()
    token = "7262384264:AAHi5bqjVEk4OQ87yqqHjtZo9mdEVUnxz60"
    if not token:
        print('Please set your Telegram bot token in the TELEGRAM_BOT_TOKEN environment variable or .env file.')
        return
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('unban', unban_cmd))
    app.add_handler(CommandHandler('ban', ban_cmd))
    app.add_handler(CommandHandler('stop', stop_cmd))
    app.add_handler(CommandHandler('status', status_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    print(f"Bot running. {DEVELOPER_CREDIT}")
    await app.run_polling()

if __name__ == '__main__':
    try:
        try:
            asyncio.run(main())
        except RuntimeError as e:
            if 'cannot be called from a running event loop' in str(e).lower() or 'cannot close a running event loop' in str(e).lower():
                nest_asyncio.apply()
                loop = asyncio.get_event_loop()
                loop.run_until_complete(main())
            else:
                raise
    except (KeyboardInterrupt, SystemExit):
        print('Bot stopped.') 