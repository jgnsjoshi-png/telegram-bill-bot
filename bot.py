import io
import os
import requests
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from PyPDF2 import PdfReader, PdfWriter

TOKEN = os.getenv("TOKEN")
CSV_FILE = "consumers.csv"
PDF_FILE = "bills.pdf"
PDF_URL = "https://drive.google.com/file/d/1A2RNG8qc_JboJ7Y55uzDvIbbq1cF2zfS/view?usp=drivesdk

def download_pdf():
    if not os.path.exists(PDF_FILE):
        print("Downloading PDF...")
        try:
            r = requests.get(PDF_URL, timeout=120)
            r.raise_for_status()
            with open(PDF_FILE, "wb") as f:
                f.write(r.content)
            print("PDF downloaded.")
        except Exception as e:
            print(f"PDF download failed: {e}")
    else:
        print("PDF exists.")

mapping = {}
try:
    with open(CSV_FILE, "r") as f:
        first = True
        for line in f:
            line = line.strip()
            if not line or first:
                first = False
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                consumer = parts[0].strip()
                page = int(parts[1].strip())
                mapping[consumer] = page
    print(f"Loaded {len(mapping)} consumers")
except Exception as e:
    print(f"CSV error: {e}")

async def start(update, context):
    await update.message.reply_text("PGVCL Bill Bot. Send consumer number (ex: 85901016297)")

async def get_bill(update, context):
    consumer = update.message.text.strip()
    
    if consumer not in mapping:
        await update.message.reply_text("Consumer number not found.")
        return
    
    if not os.path.exists(PDF_FILE):
        await update.message.reply_text("PDF downloading. Wait 2 minutes.")
        return
    
    try:
        reader = PdfReader(PDF_FILE)
        if len(reader.pages) == 0:
            await update.message.reply_text("PDF empty. Contact admin.")
            return
    except:
        await update.message.reply_text("PDF corrupted. Try later.")
        return
    
    page_num = mapping[consumer]
    if page_num < 1 or page_num > len(reader.pages):
        await update.message.reply_text("Invalid page number.")
        return
    
    try:
        writer = PdfWriter()
        writer.add_page(reader.pages[page_num - 1])
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        
        await update.message.reply_document(
            document=buf,
            filename=f"PGVCL_bill_{consumer}.pdf",
            caption=f"PGVCL Bill - Consumer: {consumer}"
        )
        print(f"Bill sent: {consumer}")
    except:
        await update.message.reply_text("PDF extraction failed.")

if __name__ == "__main__":
    print("Starting bot...")
    download_pdf()
    
    if not TOKEN:
        print("ERROR: No TOKEN!")
        exit(1)
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_bill))
    
    print("Bot started!")
    app.run_polling(drop_pending_updates=True)
