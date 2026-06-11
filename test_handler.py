import asyncio
import os
import shutil
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot import (
    handle_message,
    handle_print_selection,
    handle_change_print_type,
    handle_payment_confirmation
)

class MockDocument:
    def __init__(self, file_id="test_file_id", file_name="MAD1.pdf", mime_type="application/pdf"):
        self.file_id = file_id
        self.file_name = file_name
        self.mime_type = mime_type

class MockMessage:
    def __init__(self):
        self.document = MockDocument()
        self.text = None
        self.message_id = 999
        self.chat = MagicMock()
        self.chat.id = 123456
        self.status_msg = None
        
        # Mock reply_text to return another message
        self.reply_text = AsyncMock(side_effect=self.mock_reply_text)
        self.delete = AsyncMock()

    async def mock_reply_text(self, text, *args, **kwargs):
        print(f"[Bot reply_text] {text}")
        self.status_msg = MockStatusMessage()
        self.status_msg.text = text
        return self.status_msg

class MockStatusMessage:
    def __init__(self):
        self.message_id = 888
        self.text = ""

    async def edit_text(self, text, *args, **kwargs):
        print(f"[Bot edit_text] {text}")
        self.text = text
        return self

class MockFile:
    def __init__(self, file_id):
        self.file_id = file_id

    async def download_to_drive(self, custom_path):
        print(f"[Bot download_to_drive] Downloading to {custom_path}")
        # Touch the file to avoid FileNotFoundError
        with open(custom_path, 'wb') as f:
            f.write(b"%PDF-1.4 ... dummy content")

class MockBot:
    async def get_file(self, file_id):
        print(f"[Bot get_file] Fetching file_id={file_id}")
        return MockFile(file_id)

class MockCallbackQuery:
    def __init__(self, data, text):
        self.data = data
        self.message = MagicMock()
        self.message.text = text
        self.answer = AsyncMock()
        self.edit_message_text = AsyncMock(side_effect=self.mock_edit_message_text)

    async def mock_edit_message_text(self, text, *args, **kwargs):
        print(f"[Callback edit_message_text]\n{text}\n--------------------")
        self.message.text = text
        return self.message

class MockUpdate:
    def __init__(self, message=None, callback_query=None):
        self.message = message
        self.callback_query = callback_query
        self.effective_chat = MagicMock()
        self.effective_chat.id = 123456

class MockContext:
    def __init__(self):
        self.bot = MockBot()
        self.user_data = {}

async def main():
    # 1. Initialize update & context for document upload
    update = MockUpdate()
    msg = MockMessage()
    update.message = msg
    context = MockContext()
    
    # Patch pypdf.PdfReader to make testing independent of real PDFs
    with patch('pypdf.PdfReader') as mock_pdf_reader:
        mock_instance = MagicMock()
        mock_instance.is_encrypted = False
        mock_instance.pages = [MagicMock()] * 5  # Mock a 5-page PDF
        mock_pdf_reader.return_value = mock_instance
        
        print("--- 1. Running handle_message with valid PDF ---")
        await handle_message(update, context)
        
        # Ensure status message text is updated
        status_text = msg.status_msg.text
        
        # 2. Simulate User clicking 'Black & White'
        print("\n--- 2. Simulating print selection callback (Black & White) ---")
        update_cb = MockUpdate(callback_query=MockCallbackQuery("print_bw", status_text))
        await handle_print_selection(update_cb, context)
        
        # 3. Simulate User clicking 'Confirm Payment'
        print("\n--- 3. Simulating payment confirmation callback ---")
        last_text = update_cb.callback_query.message.text
        update_confirm = MockUpdate(callback_query=MockCallbackQuery("confirm_payment", last_text))
        await handle_payment_confirmation(update_confirm, context)
        
        # 4. Simulate User clicking 'Change Print Type'
        print("\n--- 4. Simulating change print type callback ---")
        update_change = MockUpdate(callback_query=MockCallbackQuery("change_print_type", last_text))
        await handle_change_print_type(update_change, context)
        
        # 5. Simulate User clicking 'Colour'
        print("\n--- 5. Simulating print selection callback (Colour) ---")
        changed_text = update_change.callback_query.message.text
        update_cb_color = MockUpdate(callback_query=MockCallbackQuery("print_color", changed_text))
        await handle_print_selection(update_cb_color, context)
        
        # 6. Simulate User clicking 'Confirm Payment' for Colour print
        print("\n--- 6. Simulating payment confirmation callback for Colour ---")
        last_text_color = update_cb_color.callback_query.message.text
        update_confirm_color = MockUpdate(callback_query=MockCallbackQuery("confirm_payment", last_text_color))
        await handle_payment_confirmation(update_confirm_color, context)

if __name__ == "__main__":
    asyncio.run(main())
