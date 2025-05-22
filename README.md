# Instagram Status Monitor Bot

A Telegram bot to monitor the ban/unban status of Instagram accounts in real-time.

## Features
- Monitor Instagram accounts for ban/unban status
- Commands: `/unban <username>`, `/ban <username>`, `/stop <username>`, `/status`, `/help`
- **Beautiful inline buttons** for all actions (add monitor, status, help, stop monitoring, back to menu)
- **Cute and playful emojis** throughout the interface
- Handles multiple users and accounts concurrently
- Persistent, self-healing, and logs actions
- Auto-installs dependencies
- **Environment variable or `.env` file** for token management
- Developer credit: Bot by CRAVE | Telegram: [@cravify](https://t.me/cravify)

## Setup
1. Clone or download this folder to your device.
2. Create a `.env` file in this folder with your Telegram bot token:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```
3. Run the bot script. The script will auto-install any missing dependencies.
4. Start chatting with your bot on Telegram!

## Usage
- `/unban <username>` — Monitor until the account is unbanned (profile page is accessible)
- `/ban <username>` — Monitor until the account is banned/removed (profile page is 404 or not found)
- `/stop <username>` — Stop monitoring that username
- `/status` — List all accounts you are monitoring (with stop buttons)
- `/help` — Show help and usage instructions
- Use the **inline buttons** for quick actions and navigation (including "Back to Menu" after every action)

## Requirements
- Python 3.8+
- Telegram bot token (from @BotFather)
- See `requirements.txt` for dependencies (auto-installed)

## Cross-Platform
Works on Termux, Pydroid3, Linux, Windows, and VS Code.

---

**Bot by CRAVE | Telegram: [@cravify](https://t.me/cravify)** 