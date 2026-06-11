# 🖨️ PDF Page Counter & Price Calculator Telegram Bot

A Python-based Telegram bot that allows users to upload PDF documents, automatically calculates page counts using the lightweight `pypdf` library, computes black-and-white vs. colour print costs, and generates UPI payment deep-links for seamless checkout.

---

## 🚀 Features

- **Automated PDF Parsing**: Detects and parses incoming `.pdf` attachments securely.
- **Dynamic Pricing**: Custom rates for both Black & White and Colour prints configured via env variables.
- **Interactive UI**: Standard Telegram inline keyboard buttons to change options and confirm payments.
- **UPI Deep-Linking**: Generates a functional UPI QR/payment URL for instant mobile checkout in India (BHIM, Google Pay, PhonePe, Paytm, etc.).
- **Automatic Cleanup**: Downloaded PDFs are processed, and immediately deleted from the server to guarantee privacy and save disk space.
- **Robust Error Handling**: Rigid checks for missing, corrupt, or encrypted PDF files, as well as configuration verification.
- **Fully Async**: Powered by `python-telegram-bot` v20+ with async/await.

---

## 🛠️ Project Structure

```text
bot/
├── bot.py             # Main application and handler logic
├── test_handler.py    # Mock test suite for verifying flow
├── requirements.txt   # Python dependency manifest
├── .env.example       # Template for configuration environment variables
└── README.md          # Project documentation
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- **Python 3.8+**
- A **Telegram Bot Token** (obtainable from [@BotFather](https://t.me/BotFather) on Telegram)
- A **UPI ID** (if configuring the payment functionality, e.g., `yourname@upi`)

### 2. Set Up a Virtual Environment (Recommended)
Isolate dependencies using `venv`:

```bash
# On Linux/macOS
python3 -m venv .venv
source .venv/bin/activate

# On Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies
Install all required libraries:

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to create a local `.env` configuration file:

```bash
cp .env.example .env
```

Open `.env` and fill out your details:

| Variable Name | Description | Example Value | Required? |
| :--- | :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | The unique API token obtained from `@BotFather`. | `5922324299:AAExCo...` | **Yes** |
| `CURRENCY_SYMBOL` | The currency symbol to display to the user (e.g. `$`, `₹`, `€`). | `₹` | **Yes** |
| `UPI_ID` | The UPI ID to receive payments. | `payee@upi` | **Yes** |
| `PAYEE_NAME` | The name associated with the UPI payee. | `PDF Calculator Bot` | **Yes** |
| `PRICE_PER_PAGE_BW` | Cost per page for a Black & White printout. | `2.00` | **Yes** |
| `PRICE_PER_PAGE_COLOR` | Cost per page for a Colour printout. | `10.00` | **Yes** |

> [!WARNING]
> Do not commit the `.env` file to your source control. The `.gitignore` file is pre-configured to keep it safe.

---

## 🏃 Running the Bot

Run the main bot script:

```bash
python bot.py
```

Open Telegram, search for your bot, send `/start`, and upload a PDF to test the pricing and UPI payment generation flow.

---

## 🧪 Testing

The codebase includes an offline mock test suite to verify handlers without calling external APIs:

```bash
python test_handler.py
```
