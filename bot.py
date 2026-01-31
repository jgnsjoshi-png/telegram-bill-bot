import io
import os
import requests
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from PyPDF2 import PdfReader, PdfWriter

# ================== CONFIG ==================

# Telegram Bot Token
# Termux ke liye direct rakha hai
# Cloud pe jaate time env variable bana dena
TOKEN = os.getenv("TOKEN")

# CSV file (consumer,page)
CSV_FILE = "consumers.csv"

# PDF config
PDF_FILE = "bills.pdf"
PDF_URL = "https://limewire.com/d/zpbkv#3z348wSYbx"

# ============================================

# --------- Download PDF once at startup ----------
def download_pdf():
    if not os.path.exists(PDF_FILE):
        print("Downloading PDF from Google Drive...")
        r = requests.get(PDF_URL)
        with open(PDF_FILE, "wb") as f:
            f.write(r.content)
        print("PDF downloaded successfully.")
    else:
        print("PDF already exists. Skipping download.")


# --------- Load CSV mapping ----------
mapping = {}
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


# --------- Bot handlers ----------
async def start(update, context):
    await update.message.reply_text(
        "Send Consumer number (example: 85901016297)"
    )


async def get_bill(update, context):
    consumer = update.message.text.strip()

    if consumer not in mapping:
        await update.message.reply_text("Consumer number list mein nahi mila.")
        return

    if not os.path.exists(PDF_FILE):
        await update.message.reply_text("PDF abhi available nahi hai.")
        return

    page_num = mapping[consumer]

    reader = PdfReader(PDF_FILE)

    if page_num < 1 or page_num > len(reader.pages):
        await update.message.reply_text("Page number invalid hai.")
        return

    writer = PdfWriter()
    writer.add_page(reader.pages[page_num - 1])

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)

    await update.message.reply_document(
        document=buf,
        filename=f"bill_{consumer}.pdf",
        caption=f"Bill for {consumer}"
    )


# --------- Main ----------
if __name__ == "__main__":
    download_pdf()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_bill))

    print("Bot started...")
    app.run_polling()
