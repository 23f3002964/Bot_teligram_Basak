# PDF Page Counter & Price Calculator Telegram Bot

A Python-based Telegram bot that allows users to upload PDF documents, automatically counts the number of pages in the PDF, and calculates a total price based on a configurable rate per page.

## Features

- **Document PDF Check**: Recognizes uploaded files ending with `.pdf` or with the correct MIME type.
- **Page Counting**: Uses the lightweight `pypdf` library to read PDF headers and count pages.
- **Configurable Pricing**: Rates and currency symbols can be configured via environment variables.
- **Automatic Clean Up**: Downloaded PDFs are processed and deleted immediately from disk to ensure privacy and efficiency.
- **Async Execution**: Built on `python-telegram-bot` v20+ with async/await handlers.

---

## Installation & Setup

### 1. Prerequisites
- Python 3.8 or higher
- A Telegram bot token (Create one using [@BotFather](https://t.me/BotFather) on Telegram)

### 2. Clone/Prepare Workspace
Ensure all project files are in place:
```bash
bot/
├── bot.py
├── requirements.txt
├── .env.example
└── README.md
```

### 3. Create a Virtual Environment (Recommended)
Set up a Python virtual environment and activate it:
```bash
# On Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
Install the required packages:
```bash
pip install -r requirements.txt
```

### 5. Configuration
Copy the sample environment file to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in your details:
- `TELEGRAM_BOT_TOKEN`: The API key you received from @BotFather.
- `PRICE_PER_PAGE`: The cost per page (e.g., `1.50`, `0.10`).
- `CURRENCY_SYMBOL`: The currency sign to show in the bot responses (e.g., `$`, `₹`, `€`).

---

## Running the Bot

Run the bot script:
```bash
python bot.py
```

Open Telegram, search for your bot, click **Start**, and send any PDF file to test the count and price calculation!
