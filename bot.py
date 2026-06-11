import os
import re
import logging
import urllib.parse
import html
from dotenv import load_dotenv
import pypdf
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Retrieve configuration details
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "5922324299:AAExCoiqMuDNyx0MNl1TM4i0R9tLOBDjwis")
CURRENCY_SYMBOL = os.getenv("CURRENCY_SYMBOL", "₹")
UPI_ID = os.getenv("UPI_ID", "your-upi-id@upi")
PAYEE_NAME = os.getenv("PAYEE_NAME", "PDF Calculator Bot")

try:
    PRICE_PER_PAGE_BW = float(os.getenv("PRICE_PER_PAGE_BW", os.getenv("PRICE_PER_PAGE", "2.00")))
except (ValueError, TypeError):
    logger.warning("Invalid PRICE_PER_PAGE_BW config. Defaulting to 2.00.")
    PRICE_PER_PAGE_BW = 2.00

try:
    PRICE_PER_PAGE_COLOR = float(os.getenv("PRICE_PER_PAGE_COLOR", "10.00"))
except (ValueError, TypeError):
    logger.warning("Invalid PRICE_PER_PAGE_COLOR config. Defaulting to 10.00.")
    PRICE_PER_PAGE_COLOR = 10.00


def parse_message_text(text: str) -> dict:
    """Parses message text to extract document details."""
    details = {
        "file_name": "Unknown",
        "page_count": 0,
        "print_type": "Unknown",
        "rate": "0.00",
        "total_price": "0.00"
    }
    if not text:
        return details

    # Clean HTML tags (e.g., <b>, <code>, etc.) to handle both mock and real environments
    clean_text = re.sub(r'<[^>]+>', '', text)

    for line in clean_text.split("\n"):
        if "File Name:" in line:
            details["file_name"] = line.split("File Name:", 1)[1].strip()
        elif "Total Pages:" in line:
            try:
                details["page_count"] = int(line.split("Total Pages:", 1)[1].strip())
            except ValueError:
                details["page_count"] = 0
        elif "Print Type:" in line:
            details["print_type"] = line.split("Print Type:", 1)[1].strip()
        elif "Rate per Page:" in line:
            details["rate"] = line.split("Rate per Page:", 1)[1].strip()
        elif "Total Price:" in line:
            details["total_price"] = line.split("Total Price:", 1)[1].strip()

    return details


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a greeting message when /start is issued."""
    welcome_text = (
        "👋 Hello! Welcome to the PDF Page Counter & Price Calculator Bot.\n\n"
        "📄 **How to use:**\n"
        "Simply send or upload any **PDF document** here, and I will:\n"
        "1. Count the number of pages in your document.\n"
        "2. Let you choose between black and white or colour printing.\n"
        f"   • Black & White: **{CURRENCY_SYMBOL}{PRICE_PER_PAGE_BW:.2f} per page**\n"
        f"   • Colour: **{CURRENCY_SYMBOL}{PRICE_PER_PAGE_COLOR:.2f} per page**\n\n"
        "Send me a PDF to get started!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message when /help is issued."""
    help_text = (
        "ℹ️ **Help & Instructions**\n\n"
        "• Send me any PDF document as a file attachment.\n"
        "• I will parse the document and extract the page count.\n"
        "• The cost is computed based on your print selection:\n"
        f"  - Black & White: `Pages × {CURRENCY_SYMBOL}{PRICE_PER_PAGE_BW:.2f}`\n"
        f"  - Colour: `Pages × {CURRENCY_SYMBOL}{PRICE_PER_PAGE_COLOR:.2f}`\n\n"
        "⚠️ *Note: Your files are processed securely and deleted immediately after the calculation is complete to protect your privacy.*"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancels any pending PDF processing."""
    pending = context.user_data.get("pending_pdf")
    if pending:
        file_path = pending.get("file_path")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up pending file on cancel: {file_path}")
            except Exception as err:
                logger.error(f"Failed to delete pending file on cancel: {err}")
        context.user_data.pop("pending_pdf", None)
        await update.message.reply_text("❌ PDF processing cancelled.")
    else:
        await update.message.reply_text("There is no active PDF processing to cancel.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes incoming messages, verifies and processes PDF documents, and rejects non-PDFs."""
    if not update.message:
        return

    # Check if there is a pending encrypted PDF for this user
    pending = context.user_data.get("pending_pdf")

    # If there is a pending PDF and they sent a document, clean up the old pending PDF
    if pending and update.message.document:
        old_path = pending.get("file_path")
        if old_path and os.path.exists(old_path):
            try:
                os.remove(old_path)
                logger.info(f"Cleaned up old pending file: {old_path}")
            except Exception as err:
                logger.error(f"Failed to delete old pending file: {err}")
        context.user_data.pop("pending_pdf", None)
        pending = None

    # If there is a pending PDF, process the text message as a password
    if pending:
        password = update.message.text
        if not password:
            await update.message.reply_text(
                "❌ **Error:** Please enter the password as a text message, or send `/cancel` to abort.",
                parse_mode="Markdown"
            )
            return

        temp_file_path = pending["file_path"]
        file_name = pending["file_name"]
        status_message_id = pending["status_message_id"]
        chat_id = update.effective_chat.id

        # Delete user's password message for privacy/security
        try:
            await update.message.delete()
        except Exception as e:
            logger.warning(f"Could not delete password message: {e}")

        try:
            reader = pypdf.PdfReader(temp_file_path)
            
            # Attempt decryption
            decrypt_result = reader.decrypt(password)
            if decrypt_result == 0:  # PasswordType.NOT_DECRYPTED
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_message_id,
                    text="❌ **Incorrect password.**\n\nPlease reply with the correct password, or send `/cancel` to abort:",
                    parse_mode="Markdown"
                )
                return

            # Decryption succeeded, count pages
            page_count = len(reader.pages)
            if page_count <= 0:
                raise ValueError("The PDF has zero pages or is unreadable.")

            escaped_file_name = html.escape(file_name)
            response_text = (
                "📊 <b>PDF Processed!</b>\n\n"
                f"📁 <b>File Name:</b> <code>{escaped_file_name}</code>\n"
                f"📄 <b>Total Pages:</b> <code>{page_count}</code>\n\n"
                "Please select the print type to continue:"
            )

            keyboard = [
                [
                    InlineKeyboardButton(f"⚫ Black & White ({CURRENCY_SYMBOL}{PRICE_PER_PAGE_BW:.2f}/page)", callback_data="print_bw"),
                    InlineKeyboardButton(f"🔴 Colour ({CURRENCY_SYMBOL}{PRICE_PER_PAGE_COLOR:.2f}/page)", callback_data="print_color")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Update status message with the results
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_message_id,
                text=response_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )

            # Success, clean up file and state
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            context.user_data.pop("pending_pdf", None)

        except Exception as err:
            logger.error(f"Error reading decrypted PDF: {err}", exc_info=True)
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_message_id,
                text="❌ **Error:** Failed to read the PDF. The file may be corrupted.",
                parse_mode="Markdown"
            )
            # Clean up on fatal error
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            context.user_data.pop("pending_pdf", None)

        return

    # Otherwise, handle regular document upload
    document = update.message.document

    # Reject non-document messages (text, photos, etc.)
    if not document:
        await update.message.reply_text("❌ *Error:* GANDU HAI KY PDF UPLOAF KR YE KY KR DIYA.", parse_mode="Markdown")
        return

    file_name = document.file_name or ""
    is_pdf = file_name.lower().endswith(".pdf") or document.mime_type == "application/pdf"

    # Reject non-PDF documents
    if not is_pdf:
        await update.message.reply_text("❌ *Error:* Please upload a valid PDF document.", parse_mode="Markdown")
        return

    # Notify user that processing has started
    status_message = await update.message.reply_text(
        "⏳ Processing your PDF... Please wait."
    )

    # Temporary local path to download the PDF to
    temp_file_path = f"temp_{document.file_id}.pdf"
    is_pending_encrypted = False

    try:
        # Fetch file object from Telegram
        tg_file = await context.bot.get_file(document.file_id)
        
        # Download file
        await tg_file.download_to_drive(custom_path=temp_file_path)

        # Open and count pages using pypdf, checking for encryption/corruption
        try:
            reader = pypdf.PdfReader(temp_file_path)
            
            # Check if encrypted
            if reader.is_encrypted:
                context.user_data["pending_pdf"] = {
                    "file_path": temp_file_path,
                    "file_name": file_name,
                    "status_message_id": status_message.message_id,
                }
                is_pending_encrypted = True
                
                await status_message.edit_text(
                    "🔑 **This PDF is password-protected (encrypted).**\n\n"
                    "Please reply with the password to decrypt and calculate the price, or send `/cancel` to abort.",
                    parse_mode="Markdown"
                )
                return

            page_count = len(reader.pages)
            if page_count <= 0:
                raise ValueError("The PDF has zero pages or is unreadable.")
        except Exception as parse_err:
            if not is_pending_encrypted:
                logger.error(f"Failed to read/parse PDF (possibly corrupted): {parse_err}")
                await status_message.edit_text(
                    "❌ **Error:** Failed to read the PDF. The file appears to be corrupted or not a valid PDF."
                )
                return

        escaped_file_name = html.escape(file_name)
        response_text = (
            "📊 <b>PDF Processed!</b>\n\n"
            f"📁 <b>File Name:</b> <code>{escaped_file_name}</code>\n"
            f"📄 <b>Total Pages:</b> <code>{page_count}</code>\n\n"
            "Please select the print type to continue:"
        )

        keyboard = [
            [
                InlineKeyboardButton(f"⚫ Black & White ({CURRENCY_SYMBOL}{PRICE_PER_PAGE_BW:.2f}/page)", callback_data="print_bw"),
                InlineKeyboardButton(f"🔴 Colour ({CURRENCY_SYMBOL}{PRICE_PER_PAGE_COLOR:.2f}/page)", callback_data="print_color")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Update status message with calculation results
        await status_message.edit_text(
            response_text, parse_mode="HTML", reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Unexpected error processing document: {e}", exc_info=True)
        await status_message.edit_text(
            "❌ **Error:** An unexpected error occurred while processing your file. Please try again."
        )
    finally:
        # Clean up temp file immediately unless waiting for a password
        if not is_pending_encrypted and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logger.error(f"Failed to delete temp file {temp_file_path}: {e}")


async def handle_print_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the print type selection button click (Colour or Black & White)."""
    query = update.callback_query
    await query.answer()

    data = query.data
    is_color = (data == "print_color")
    print_type_str = "Colour" if is_color else "Black & White"
    rate = PRICE_PER_PAGE_COLOR if is_color else PRICE_PER_PAGE_BW

    # Parse details from current message
    details = parse_message_text(query.message.text)
    file_name = details["file_name"]
    page_count = details["page_count"]

    # Calculate total price
    total_price = page_count * rate

    # Generate UPI link
    encoded_payee = urllib.parse.quote(PAYEE_NAME)
    note = f"PDF_{page_count}_pages_{print_type_str.replace(' ', '_')}"
    encoded_note = urllib.parse.quote(note)
    upi_url = f"upi://pay?pa={UPI_ID}&pn={encoded_payee}&am={total_price:.2f}&cu=INR&tn={encoded_note}"

    # Reconstruct display
    escaped_file_name = html.escape(file_name)
    escaped_upi_id = html.escape(UPI_ID)
    escaped_upi_url = html.escape(upi_url)

    response_text = (
        "✅ <b>Calculation Complete!</b>\n\n"
        f"📁 <b>File Name:</b> <code>{escaped_file_name}</code>\n"
        f"📄 <b>Total Pages:</b> <code>{page_count}</code>\n"
        f"🖨️ <b>Print Type:</b> <code>{print_type_str}</code>\n"
        f"💵 <b>Rate per Page:</b> <code>{CURRENCY_SYMBOL}{rate:.2f}</code>\n"
        f"🏷️ <b>Total Price:</b> <code>{CURRENCY_SYMBOL}{total_price:.2f}</code>\n\n"
        f"📌 <b>UPI ID:</b> <code>{escaped_upi_id}</code>\n\n"
        f"📱 <b>Pay Link:</b> <a href=\"{escaped_upi_url}\">Click to Pay</a>"
    )

    keyboard = [
        [
            InlineKeyboardButton("💳 Confirm Payment", callback_data="confirm_payment")
        ],
        [
            InlineKeyboardButton("⬅️ Change Print Type", callback_data="change_print_type")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=response_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )


async def handle_change_print_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the change print type button click."""
    query = update.callback_query
    await query.answer()

    details = parse_message_text(query.message.text)
    file_name = details["file_name"]
    page_count = details["page_count"]

    escaped_file_name = html.escape(file_name)
    response_text = (
        "📊 <b>PDF Processed!</b>\n\n"
        f"📁 <b>File Name:</b> <code>{escaped_file_name}</code>\n"
        f"📄 <b>Total Pages:</b> <code>{page_count}</code>\n\n"
        "Please select the print type to continue:"
    )
    keyboard = [
        [
            InlineKeyboardButton(f"⚫ Black & White ({CURRENCY_SYMBOL}{PRICE_PER_PAGE_BW:.2f}/page)", callback_data="print_bw"),
            InlineKeyboardButton(f"🔴 Colour ({CURRENCY_SYMBOL}{PRICE_PER_PAGE_COLOR:.2f}/page)", callback_data="print_color")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=response_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )


async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the payment confirmation button click."""
    query = update.callback_query
    await query.answer()

    details = parse_message_text(query.message.text)
    file_name = details["file_name"]
    page_count = details["page_count"]
    print_type = details["print_type"]
    rate = details["rate"]
    total_price = details["total_price"]

    escaped_file_name = html.escape(file_name)
    escaped_print_type = html.escape(print_type)
    escaped_rate = html.escape(rate)
    escaped_total_price = html.escape(total_price)

    # Reconstruct with confirmation HTML
    confirmation_text = (
        "✅ <b>Payment Confirmed!</b>\n\n"
        f"📁 <b>File Name:</b> <code>{escaped_file_name}</code>\n"
        f"📄 <b>Total Pages:</b> <code>{page_count}</code>\n"
        f"🖨️ <b>Print Type:</b> <code>{escaped_print_type}</code>\n"
        f"💵 <b>Rate per Page:</b> <code>{escaped_rate}</code>\n"
        f"🏷️ <b>Total Price:</b> <code>{escaped_total_price}</code>\n\n"
        "Thank you! Your payment has been successfully received and confirmed. 🚀"
    )

    await query.edit_message_text(
        text=confirmation_text,
        parse_mode="HTML",
        reply_markup=None
    )


def main() -> None:
    """Starts the Telegram bot."""
    if not BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN environment variable not set. Exiting.")
        print("Error: TELEGRAM_BOT_TOKEN is missing in the environment or .env file.")
        return

    # Create the application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_command))

    # Add message handler for everything except command messages
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    # Add callback query handlers for print selection, print type change, and payment confirmation
    application.add_handler(CallbackQueryHandler(handle_print_selection, pattern="^print_(bw|color)$"))
    application.add_handler(CallbackQueryHandler(handle_change_print_type, pattern="^change_print_type$"))
    application.add_handler(CallbackQueryHandler(handle_payment_confirmation, pattern="^confirm_payment$"))

    # Run the bot
    logger.info("Starting bot... Press Ctrl+C to stop.")
    application.run_polling()


if __name__ == "__main__":
    main()
