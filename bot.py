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
# SOZLAMALAR: O'Z TELEGRAM ID-NGIZNI YOZING
# ==========================================
ADMIN_ID = 5070261597  # Telegram ID'ingizni shu yerga qo'ying (masalan: 123456789)
TOKEN = "8812256632:AAEp7G5xem6lWdIMrkdewpN9FCmm9kt8T30"

# Database - Ma'lumotlar bazasini yaratish va sozlash
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

QUESTIONS = [
    {"question": "O'zbekiston poytaxti qaysi?", "options": ["Samarqand", "Toshkent", "Buxoro"], "correct": 1},
    {"question": "Dunyodagi eng katta okean qaysi?", "options": ["Atlantika okeani", "Tinch okeani", "Hind okeani"], "correct": 1},
    {"question": "Yer yuzidagi eng uzun daryo qaysi?", "options": ["Nil", "Amazonka", "Misisipi"], "correct": 0},
    {"question": "Quyosh sistemasidagi eng katta sayyora qaysi?", "options": ["Zuxro", "Mars", "Yupiter"], "correct": 2},
    {"question": "Fransiya poytaxti qaysi shahar?", "options": ["Parij", "Berlin", "Rim"], "correct": 0},
    {"question": "Inson tanasidagi eng katta organ qaysi?", "options": ["Yurak", "Teri", "Jigar"], "correct": 1},
    {"question": "Dunyodagi eng baland cho'qqi qaysi?", "options": ["Kengur", "Chogori", "Jomolungma (Everest)"], "correct": 2},
    {"question": "Suvning kimyoviy formulasi qanday?", "options": ["H2O", "CO2", "NaCl"], "correct": 0},
    {"question": "Alisher Navoiy qaysi yilda tavallud topgan?", "options": ["1441-yil", "1500-yil", "1336-yil"], "correct": 0},
    {"question": "Yaponiya poytaxti qaysi shahar?", "options": ["Pekin", "Tokio", "Seul"], "correct": 1},
    {"question": "O'zbekiston Respublikasining davlat bayrog'i qachon qabul qilingan?", "options": ["1991-yil 1-sentyabr", "1992-yil 18-noyabr", "1993-yil 8-dekabr"], "correct": 1},
    {"question": "Dunyodagi eng kichik davlat qaysi?", "options": ["Monako", "Vatikan", "San-Marino"], "correct": 1},
    {"question": "Qaysi qit'a 'Qora qit'a' deb ataladi?", "options": ["Osiyo", "Afrika", "Janubiy Amerika"], "correct": 1},
    {"question": "Amir Temur qachon tavallud topgan?", "options": ["1336-yil", "1405-yil", "1226-yil"], "correct": 0},
    {"question": "Dunyodagi eng chuqur ko'l qaysi?", "options": ["Baykal", "Kaspiy", "Victoriya"], "correct": 0},
    {"question": "Matematikada pi (π) sonining taxminiy qiymati nechaga teng?", "options": ["3.14", "2.71", "1.41"], "correct": 0},
    {"question": "Italiya poytaxti qaysi shahar?", "options": ["Madrid", "Rim", "Afina"], "correct": 1},
    {"question": "Yorug'lik tezligi sekundiga taxminan necha kilometr?", "options": ["300 000 km/s", "150 000 km/s", "3 000 km/s"], "correct": 0},
    {"question": "Qaysi element Mendeleev jadvalida 'O' belgisi bilan belgilangan?", "options": ["Oltin", "Kislorod", "Vodorod"], "correct": 1},
    {"question": "Birlashgan Millatlar Tashkiloti (BMT) qachon tashkil etilgan?", "options": ["1945-yil", "1939-yil", "1950-yil"], "correct": 0}
]

user_scores = {}
user_current_q = {}
user_full_names = {}

def generate_certificate_pdf(user_name: str, score: int, total: int, cert_num: str) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=0, leftMargin=0, topMargin=0, bottomMargin=0
    )
    
    # QR kod yaratish
    qr_data = f"Sertifikat №: {cert_num}\nIsm: {user_name}\nNatija: {score}/{total}\nSana: {datetime.date.today().strftime('%d.%m.%Y')}"
    qr_img = qrcode.make(qr_data)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    
    styles = getSampleStyleSheet()
    
    # Ism uchun maxsus shrift va tekislash (Chiziq ustiga to'g'ri tushishi uchun)
    name_style = ParagraphStyle(
        'CertName',
        parent=styles['Normal'],
        fontName='Times-BoldItalic',
        fontSize=34,
        textColor=colors.HexColor('#2A1A08'),
        alignment=1
    )

    elements = [
        Spacer(1, 282), # Ismni aynan chiziq ustidagi ochiq joyga tushirish uchun aniq oraliq
        Paragraph(f"{user_name}", name_style)
    ]

    def draw_background(canvas, doc):
        canvas.saveState()
        template_path = "template.jpg"
        if os.path.exists(template_path):
            canvas.drawImage(template_path, 0, 0, width=landscape(A4)[0], height=landscape(A4)[1])
        
        # QR-kodni pastki chap tomondagi toza va mos bo'shliqqa chiroyli joylashtirish
        qr_image_obj = Image(qr_buffer, width=50, height=50)
        qr_image_obj.drawOn(canvas, 130, 85)
        
        # Sertifikat raqami va sanasini pastki burchakda ko'rsatish
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(colors.HexColor('#444444'))
        canvas.drawString(60, 45, f"№: {cert_num}")
        canvas.restoreState()
    
    doc.build(elements, onFirstPage=draw_background)
    buffer.seek(0)
    return buffer

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_scores[user_id] = 0
    user_current_q[user_id] = 0
    await update.message.reply_text(
        "✨ Assalomu alaykum! Viktorina botiga xush kelibsiz.\n\n"
        "Sertifikat olish uchun Ism va Familiyangizni yuboring (masalan: Kamol Hamrayev):"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ADMIN_ID != 0 and user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Siz adminga tegishli buyruqdan foydalana olmaysiz.")
        return
        
    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, score, total, cert_num, date_created FROM results ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📊 Hozircha hech kim test topshirmadi.")
        return

    text = "🏆 **G'oliblar va Ishtirokchilar ro'yxati (So'nggi 20 ta):**\n\n"
    for idx, r in enumerate(rows, start=1):
        status = f"🎖 Certificate №{r[3]}" if r[1] >= 10 else "❌ O'tmadi"
        text += f"{idx}. **{r[0]}** — {r[1]}/{r[2]} ball ({status})\n📅 {r[4]}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    user_full_names[user_id] = text
    user_scores[user_id] = 0
    user_current_q[user_id] = 0
    
    await update.message.reply_text(
        f"Rahmat, **{text}**!\nTestimiz 20 ta savoldan iborat. Boshlash uchun pastdagi tugmani bosing:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Testni boshlash", callback_data="start_quiz")]]),
        parse_mode="Markdown"
    )

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    q_index = user_current_q.get(user_id, 0)
    
    if q_index < len(QUESTIONS):
        q_data = QUESTIONS[q_index]
        keyboard = [[InlineKeyboardButton(opt, callback_data=f"ans_{i}")] for i, opt in enumerate(q_data["options"])]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"❓ **Savol {q_index + 1} / {len(QUESTIONS)}**\n\n{q_data['question']}"
        if update.callback_query:
            try:
                await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
            except Exception:
                pass
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        score = user_scores.get(user_id, 0)
        name = user_full_names.get(user_id, "Ishtirokchi")
        
        if update.callback_query:
            try:
                await update.callback_query.message.delete()
            except Exception:
                pass
                
        cert_num = str(random.randint(100000, 999999)) if score >= 10 else "—"
        
        save_result(user_id, name, score, len(QUESTIONS), cert_num)
        
        if score >= 10:
            pdf_buffer = generate_certificate_pdf(name, score, len(QUESTIONS), cert_num)
            
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=pdf_buffer,
                filename=f"Sertifikat_{name}.pdf",
                caption=f"🎉 Tabriklaymiz, {name}!\nSiz {len(QUESTIONS)} tadan {score} ta to'g'ri topib, sertifikatni qo'lga kiritdingiz!"
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Test yakunlandi. Natijangiz: {score} / {len(QUESTIONS)}.\n"
                     f"Afsuski, yetarli ball to'playolmadingiz. Qaytadan urinish uchun /start ni bosing."
            )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "start_quiz":
        user_current_q[user_id] = 0
        user_scores[user_id] = 0
        await send_question(update, context)
        return

    if query.data.startswith("ans_"):
        q_index = user_current_q.get(user_id, 0)
        if q_index < len(QUESTIONS):
            selected = int(query.data.split("_")[1])
            if selected == QUESTIONS[q_index]["correct"]:
                user_scores[user_id] = user_scores.get(user_id, 0) + 1
            
            user_current_q[user_id] = q_index + 1
            await send_question(update, context)

def main():
    init_db()
    threading.Thread(target=run_health_check_server, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 PDF Sertifikat boti ishga tushdi...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
