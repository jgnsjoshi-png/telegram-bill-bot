import io
import os
import requests
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from PyPDF2 import PdfReader, PdfWriter

# ================== CONFIG ==================
# Telegram Bot Token - LOADS FROM RAILWAY ENV VAR
TOKEN = os.getenv("TOKEN")

# CSV file (consumer,page)
CSV_FILE = "consumers.csv"

# PDF config - YOUR NEW LIMEWIRE LINK
PDF_FILE = "bills.pdf"
PDF_URL = "https://limewire.com/d/zpbkv#3z348wSYbx"

# ============================================

# --------- Download PDF once at startup ----------
def download_pdf():
    if not os.path.exists(PDF_FILE):
        print("Downloading PDF from LimeWire...")
        try:
            r = requests.get(PDF_URL, timeout=120)  # 2min timeout for large file
            r.raise_for_status()
            with open(PDF_FILE, "wb") as f:
                f.write(r.content)
            print("PDF downloaded successfully.")
        except Exception as e:
            print(f"PDF download failed: {e}")
    else:
        print("PDF already exists. Skipping download.")

# --------- Load CSV mapping ----------
mapping = {}
try:
    with open(CSV_FILE, "r") as f:
        first = True
        for line in f:
            line = line.strip()
            if not line:
                continue
            if first:
                first = False
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                consumer = parts[0].strip()
                page = int(parts[1].strip())
                mapping[consumer] = page
    print(f"Loaded {len(mapping)} consumers from CSV")
except Exception as e:
    print(f"CSV load error: {e}")

# --------- Bot handlers ----------
async def start(update, context):
    await update.message.reply_text(
        "🔌 PGVCL Bill Bot

"
        "Send consumer number (example: 85901016297)

"
        "PDF processing live!"
    )

async def get_bill(update, context):
    consumer = update.message.text.strip()
    
    # Check consumer exists
    if consumer not in mapping:
        await update.message.reply_text("❌ Consumer number not found in list.")
        return
    
    # Check PDF exists
    if not os.path.exists(PDF_FILE):
        await update.message.reply_text("⏳ PDF is downloading... Please wait 2 minutes.")
        return
    
    # BULLETPROOF PDF VALIDATION
    try:
        reader = PdfReader(PDF_FILE)
        if len(reader.pages) == 0:
            await update.message.reply_text("❌ PDF is empty. Contact admin.")
            return
    except Exception as e:
        await update.message.reply_text(
            "❌ PDF file is corrupted.
"
            "Try again later or contact admin.

"
            "Error: PDF read failed"
        )
        print(f"PDF Error: {e}")
        return
    
    # Validate page number
    page_num = mapping[consumer]
    if page_num < 1 or page_num > len(reader.pages):
        await update.message.reply_text("❌ Invalid page number.")
        return
    
    # Extract single page
    try:
        writer = PdfWriter()
        writer.add_page(reader.pages[page_num - 1])
        
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        
        await update.message.reply_document(
            document=buf,
            filename=f"PGVCL_bill_{consumer}.pdf",
            caption=f"✅ PGVCL Bill for Consumer: {consumer}
Page: {page_num}"
        )
        print(f"✅ Bill sent for consumer {consumer}, page {page_num}")
        
    except Exception as e:
        await update.message.reply_text("❌ PDF extraction failed. Contact admin.")
        print(f"PDF extraction error: {e}")

# --------- Main ----------
if __name__ == "__main__":
    print("🚀 Starting PGVCL Bill Bot...")
    
    # Download PDF and load CSV
    download_pdf()
    
    # Validate token
    if not TOKEN:
        print("❌ ERROR: TOKEN environment variable missing!")
        print("Railway.app → Variables → Add TOKEN=your_bot_token")
        exit(1)
    
    # Start bot
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_bill))
    
    print("✅ Bot started successfully! Polling active...")
    print(f"📊 Serving {len(mapping)} consumers")
    app.run_polling(drop_pending_updates=True)  # Fixes polling conflicts
