import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# Render uchun Health Check veb-serveri
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot ishlayapti!")

def run_health_check_server():
    server_address = ('', 10000)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    httpd.serve_forever()

# Bot sozlamalari (O'z tokeningizni yozing)
TOKEN = "8812256632:AAGPMq6Fb8yixbV-ThbVW13GwiqbtXN8Xyg"

# 20 talik test savollari
QUESTIONS = [
    {
        "question": "O'zbekiston poytaxti qaysi?",
        "options": ["Samarqand", "Toshkent", "Buxoro"],
        "correct": 1
    },
    {
        "question": "Dunyodagi eng katta okean qaysi?",
        "options": ["Atlantika okeani", "Tinch okeani", "Hind okeani"],
        "correct": 1
    },
    {
        "question": "Yer yuzidagi eng uzun daryo qaysi?",
        "options": ["Nil", "Amazonka", "Misisipi"],
        "correct": 0
    },
    {
        "question": "Quyosh sistemasidagi eng katta sayyora qaysi?",
        "options": ["Zuxro", "Mars", "Yupiter"],
        "correct": 2
    },
    {
        "question": "Fransiya poytaxti qaysi shahar?",
        "options": ["Parij", "Berlin", "Rim"],
        "correct": 0
    },
    {
        "question": "Inson tanasidagi eng katta organ qaysi?",
        "options": ["Yurak", "Teri", "Jigar"],
        "correct": 1
    },
    {
        "question": "Dunyodagi eng baland cho'qqi qaysi?",
        "options": ["Kengur", "Chogori", "Jomolungma (Everest)"],
        "correct": 2
    },
    {
        "question": "Suvning kimyoviy formulasi qanday?",
        "options": ["H2O", "CO2", "NaCl"],
        "correct": 0
    },
    {
        "question": "Alisher Navoiy qaysi yilda tavallud topgan?",
        "options": ["1441-yil", "1500-yil", "1336-yil"],
        "correct": 0
    },
    {
        "question": "Yaponiya poytaxti qaysi shahar?",
        "options": ["Pekin", "Tokio", "Seul"],
        "correct": 1
    },
    {
        "question": "O'zbekiston Respublikasining davlat bayrog'i qachon qabul qilingan?",
        "options": ["1991-yil 1-sentyabr", "1992-yil 18-noyabr", "1993-yil 8-dekabr"],
        "correct": 1
    },
    {
        "question": "Dunyodagi eng kichik davlat qaysi?",
        "options": ["Monako", "Vatikan", "San-Marino"],
        "correct": 1
    },
    {
        "question": "Qaysi qit'a 'Qora qit'a' deb ataladi?",
        "options": ["Osiyo", "Afrika", "Janubiy Amerika"],
        "correct": 1
    },
    {
        "question": "Amir Temur qachon tavallud topgan?",
        "options": ["1336-yil", "1405-yil", "1226-yil"],
        "correct": 0
    },
    {
        "question": "Dunyodagi eng chuqur ko'l qaysi?",
        "options": ["Baykal", "Kaspiy", "Victoriya"],
        "correct": 0
    },
    {
        "question": "Matematikada pi (π) sonining taxminiy qiymati nechaga teng?",
        "options": ["3.14", "2.71", "1.41"],
        "correct": 0
    },
    {
        "question": "Italiya poytaxti qaysi shahar?",
        "options": ["Madrid", "Rim", "Afina"],
        "correct": 1
    },
    {
        "question": "Yorug'lik tezligi sekundiga taxminan necha kilometr?",
        "options": ["300 000 km/s", "150 000 km/s", "3 000 km/s"],
        "correct": 0
    },
    {
        "question": "Qaysi element Mendeleev jadvalida 'O' belgisi bilan belgilangan?",
        "options": ["Oltin", "Kislorod", "Vodorod"],
        "correct": 1
    },
    {
        "question": "Birlashgan Millatlar Tashkiloti (BMT) qachon tashkil etilgan?",
        "options": ["1945-yil", "1939-yil", "1950-yil"],
        "correct": 0
    }
]

user_scores = {}
user_current_q = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_scores[user_id] = 0
    user_current_q[user_id] = 0
    await update.message.reply_text("Assalomu alaykum! 20 talik test botiga xush kelibsiz. Testni boshlash uchun /quiz buyrug'ini bosing.")

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_scores[user_id] = 0
    user_current_q[user_id] = 0
    await send_question(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    q_index = user_current_q[user_id]
    
    if q_index < len(QUESTIONS):
        q_data = QUESTIONS[q_index]
        keyboard = [[InlineKeyboardButton(opt, callback_data=f"{i}")] for i, opt in enumerate(q_data["options"])]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"❓ Savol {q_index + 1}/{len(QUESTIONS)}:\n{q_data['question']}"
        if update.callback_query:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        score = user_scores[user_id]
        # Agar 20 tadan 10 tadan ko'p topsa sertifikat olish huquqini beramiz
        if score >= 10:
            keyboard = [[InlineKeyboardButton("📜 Sertifikatni olish", callback_data="get_cert")]]
            await update.callback_query.message.edit_text(
                f"🎉 Tabriklaymiz! Siz testdan muvaffaqiyatli o'tdingiz!\nNatijangiz: {score} / {len(QUESTIONS)}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            if update.callback_query:
                await update.callback_query.message.edit_text(
                    f"❌ Test yakunlandi. Natijangiz: {score} / {len(QUESTIONS)}.\nAfsuski, yetarli ball to'playolmadingiz. Qaytadan urinish uchun /quiz ni bosing."
                )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "get_cert":
        await query.message.reply_text("✨ Tabriklaymiz! Sizning maxsus sertifikatingiz muvaffaqiyatli taqdim etildi!")
        return

    q_index = user_current_q.get(user_id, 0)
    if q_index < len(QUESTIONS):
        selected = int(query.data)
        if selected == QUESTIONS[q_index]["correct"]:
            user_scores[user_id] += 1
        
        user_current_q[user_id] += 1
        await send_question(update, context)

def main():
    threading.Thread(target=run_health_check_server, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 20 talik Test boti ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
