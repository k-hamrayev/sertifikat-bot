import io
import os
import random
import datetime
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import qrcode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ==========================================
# SOZLAMALAR
# ==========================================
ADMIN_ID = int(os.environ.get("ADMIN_ID", 5070261597))
TOKEN = os.environ.get("BOT_TOKEN", "8812256632:AAFU6i9q5el-RmQVj3olNBnFLYGxvtTZ4Ik")

# Database - Ma'lumotlar bazasi
def init_db():
    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT,
            score INTEGER,
            total INTEGER,
            cert_num TEXT,
            date_created TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_result(user_id, full_name, score, total, cert_num):
    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO results (user_id, full_name, score, total, cert_num, date_created)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, full_name, score, total, cert_num, now))
    conn.commit()
    conn.close()

# Render Health Check Server
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot ishlayapti!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_health_check_server():
    server_address = ('', 10000)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    httpd.serve_forever()

# 20 TA YANGI SAVOLLAR
QUESTIONS = [
    {"question": "O'zbekiston Respublikasi poytaxti qaysi shahar?", "options": ["Samarqand", "Toshkent", "Buxoro"], "correct": 1},
    {"question": "Dunyodagi eng katta okean qaysi?", "options": ["Atlantika okeani", "Tinch okeani", "Hind okeani"], "correct": 1},
    {"question": "O'zbekiston Mustaqillikka erishgan yil?", "options": ["1990-yil", "1991-yil", "1992-yil"], "correct": 1},
    {"question": "Amir Temur qachon tug'ilgan?", "options": ["1336-yil 9-aprel", "1340-yil 5-may", "1330-yil 1-yanvar"], "correct": 0},
    {"question": "O'zbekiston Respublikasining birinchi Prezidenti kim?", "options": ["Shavkat Mirziyoyev", "Islom Karimov", "Sharof Rashidov"], "correct": 1},
    {"question": "O'zbek tili davlat tili maqomini qachon olgan?", "options": ["1989-yil 21-oktyabr", "1991-yil 1-sentyabr", "1992-yil 8-dekabr"], "correct": 0},
    {"question": "Quyosh tizimidagi eng katta planeta qaysi?", "options": ["Mars", "Yupiter", "Saturn"], "correct": 1},
    {"question": "O'zbekiston Konstitutsiyasi qachon qabul qilingan?", "options": ["1992-yil 8-dekabr", "1991-yil 31-avgust", "1993-yil 1-yanvar"], "correct": 0},
    {"question": "Inson tanasida nechta suyak bor (kattalarda)?", "options": ["206 ta", "300 ta", "150 ta"], "correct": 0},
    {"question": "Alisher Navoiy qaysi asrda yashagan?", "options": ["XV asr", "XIV asr", "XVI asr"], "correct": 0},
    {"question": "O'zbekiston Respublikasi Bayrog'i qachon qabul qilingan?", "options": ["1991-yil 18-noyabr", "1992-yil 10-dekabr", "1990-yil 1-sentyabr"], "correct": 0},
    {"question": "O'zbekiston Respublikasi Gerbi qachon qabul qilingan?", "options": ["1992-yil 2-iyul", "1991-yil 18-noyabr", "1993-yil 10-dekabr"], "correct": 0},
    {"question": "O'zbekiston Respublikasi Madhiyasi muallifi (matni) kim?", "options": ["Abdulla Oripov", "Erkin Vohidov", "Muhammad Yusuf"], "correct": 0},
    {"question": "Dunyodagi eng uzun daryo qaysi?", "options": ["Nil", "Amazonka", "Yanszi"], "correct": 0},
    {"question": "O'zbekiston nechtaga viloyatga bo'lingan?", "options": ["12 ta viloyat, 1 ta respublika", "14 ta viloyat", "10 ta viloyat"], "correct": 0},
    {"question": "Sharq tusi va Tib qonunlari asari muallifi kim?", "options": ["Abu Ali ibn Sino", "Al-Xorazmiy", "Mirzo Ulug'bek"], "correct": 0},
    {"question": "Algebra faniga kim asos solgan?", "options": ["Al-Xorazmiy", "Abu Rayhon Beruniy", "Ahmad Farg'oniy"], "correct": 0},
    {"question": "O'zbekistonning eng baland tog' cho'qqisi qaysi?", "options": ["Hazrati Sulton cho'qqisi", "Katta Chimyon", "Adelunga"], "correct": 0},
    {"question": "Inson yuragi bir daqiqada o'rtacha necha marta uradi?", "options": ["60-80 marta", "100-120 marta", "40-50 marta"], "correct": 0},
    {"question": "Birlashgan Millatlar Tashkilotiga (BMT) O'zbekiston qachon a'zo bo'lgan?", "options": ["1992-yil 2-mart", "1991-yil 1-sentyabr", "1993-yil 5-may"], "correct": 0}
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("✨ Assalomu alaykum! Onlayn viktorina botiga xush kelibsiz.\n\nSertifikat olish uchun Ism va Familiyangizni yuboring (masalan: Kamol Hamrayev):")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text == "/stats":
        await stats(update, context)
        return

    if "full_name" not in context.user_data:
        context.user_data["full_name"] = text
        keyboard = [[InlineKeyboardButton("🚀 Testni boshlash", callback_data="start_quiz")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"Rahmat, {text}!\n\nTestni boshlashga tayyormisiz? (20 ta savol)", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if "full_name" not in context.user_data:
        await query.message.edit_text("⚠️ Xatolik yuz berdi. Iltimos, qaytadan /start bosib ism-familiyangizni kiriting.")
        return

    if data == "start_quiz":
        context.user_data["score"] = 0
        context.user_data["current_q"] = 0
        context.user_data["is_active"] = True
        await send_question(query, context)
    elif data.startswith("ans_"):
        if not context.user_data.get("is_active"):
            return
            
        selected_opt = int(data.split("_")[1])
        q_idx = context.user_data["current_q"]
        
        if selected_opt == QUESTIONS[q_idx]["correct"]:
            context.user_data["score"] += 1
            
        context.user_data["current_q"] += 1
        
        if context.user_data["current_q"] < len(QUESTIONS):
            await send_question(query, context)
        else:
            context.user_data["is_active"] = False
            await finish_quiz(query, context)

async def send_question(query, context):
    q_idx = context.user_data["current_q"]
    q_data = QUESTIONS[q_idx]
    
    keyboard = []
    for idx, opt in enumerate(q_data["options"]):
        keyboard.append([InlineKeyboardButton(opt, callback_data=f"ans_{idx}")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"❓ {q_idx + 1}/{len(QUESTIONS)}-savol:\n{q_data['question']}"
    
    if query.message:
        await query.message.edit_text(text, reply_markup=reply_markup)

async def finish_quiz(query, context):
    score = context.user_data.get("score", 0)
    total = len(QUESTIONS)
    full_name = context.user_data.get("full_name", "Foydalanuvchi")
    user_id = query.from_user.id
    
    cert_num = f"CERT-{random.randint(100000, 999999)}"
    save_result(user_id, full_name, score, total, cert_num)
    
    # ADMINGA BILDIRISHNOMA
    admin_msg = (
        f"🔔 **Yangi natija!**\n\n"
        f"👤 **Ism:** {full_name}\n"
        f"📊 **Natija:** {score}/{total}\n"
        f"📜 **Sertifikat No:** {cert_num}\n"
        f"🆔 **User ID:** `{user_id}`"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
    except Exception as e:
        print(f"Adminga xabar yuborishda xatolik: {e}")

    await query.message.edit_text(f"🏁 Test yakunlandi!\nSiz {total} ta savoldan {score} tasiga to'g'ri javob berdingiz.\n\nSertifikat tayyorlanmoqda...")
    
    pdf_buffer = generate_pdf_certificate(full_name, score, total, cert_num)
    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=pdf_buffer,
        filename=f"Sertifikat_{full_name}.pdf",
        caption=f"Tabriklaymiz, {full_name}! Mana sizning sertifikatingiz."
    )

def generate_pdf_certificate(full_name, score, total, cert_num):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CertTitle',
        parent=styles['Heading1'],
        fontSize=32,
        leading=38,
        textColor=colors.HexColor("#1A365D"),
        alignment=1,
        spaceAfter=15
    )
    name_style = ParagraphStyle(
        'CertName',
        parent=styles['Normal'],
        fontSize=26,
        leading=32,
        textColor=colors.HexColor("#2B6CB0"),
        alignment=1,
        spaceAfter=15
    )
    text_style = ParagraphStyle(
        'CertText',
        parent=styles['Normal'],
        fontSize=14,
        leading=20,
        textColor=colors.HexColor("#2D3748"),
        alignment=1,
        spaceAfter=10
    )
    
    elements = []
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("SERTIFIKAT", title_style))
    elements.append(Paragraph("Ushbu sertifikat egasi:", text_style))
    elements.append(Paragraph(f"<b>{full_name}</b>", name_style))
    elements.append(Paragraph(f"Onlayn viktorinada muvaffaqiyatli qatnashib, <b>{total}</b> ta savoldan <b>{score}</b> tasiga to'g'ri javob bergani uchun topshirildi.", text_style))
    
    qr_img = qrcode.make(f"Sertifikat №: {cert_num}\nEgasiga: {full_name}\nNatija: {score}/{total}")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    
    qr_image = Image(qr_buffer, width=80, height=80)
    elements.append(Spacer(1, 20))
    elements.append(qr_image)
    elements.append(Paragraph(f"<font size=9 color='#718096'>Sertifikat raqami: {cert_num}</font>", text_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Bu buyruq faqat admin uchun!")
        return

    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, score, total, cert_num, date_created FROM results ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📊 Hali hech kim test topshirmadi.")
        return

    text = "📊 **G'oliblar va qatnashchilar ro'yxati:**\n\n"
    for idx, row in enumerate(rows, 1):
        text += f"{idx}. **{row[0]}** - {row[1]}/{row[2]} ball\n   📜 {row[3]} | 📅 {row[4]}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")

def main():
    init_db()
    
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
