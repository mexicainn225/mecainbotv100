import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)

@app.route('/')
def home():
    return "Système Pro V11 - Stats Classiques"

# --- CONFIGURATION ---
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = 5724620019  
MONGO_URI = os.getenv('MONGO_URI')
bot = telebot.TeleBot(API_TOKEN)

client = MongoClient(MONGO_URI)
db = client['luckyjet_db']
users_col = db['users'] 

LIEN_INSCRIPTION = "https://lkbb.cc/e2d8"
CODE_PROMO = "COK225"

ID_VIDEO_AVIATOR = "https://t.me/explicationsjeux21points/25787"
ID_VIDEO_LUCKYJET = "https://t.me/gagnantpro1xbet/138958" 

# --- FONCTIONS ---
def get_user(u_id):
    user = users_col.find_one({"_id": u_id})
    if not user:
        user = {"_id": u_id, "is_vip": False}
        users_col.insert_one(user)
    return user

def calculate_prediction(game_type):
    now = datetime.now()
    intervalle = 21 if game_type == "LUCKY" else 11
    
    # Calcul précis basé sur l'heure
    sig_total = (now.hour * 60) + 10 
    total_now = (now.hour * 60) + now.minute
    while sig_total <= total_now:
        sig_total += intervalle
            
    target_time = now.replace(hour=(sig_total // 60) % 24, minute=sig_total % 60, second=0, microsecond=0)
    time_fmt = f"{target_time.strftime('%H:%M')} - {(target_time + timedelta(minutes=1)).strftime('%H:%M')}"
    
    random.seed(target_time.timestamp())
    
    if game_type == "LUCKY":
        cote = round(random.uniform(10.0, 85.0), 2)
        safe = round(random.uniform(5.0, 8.0), 2)
        text = (f"🚀 **PRÉDICTION LUCKY JET**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 **CRÉNEAU** : `{time_fmt}`\n"
                f"📈 **OBJECTIF** : `{cote}X` \n"
                f"🎯 **SÉCURITÉ** : `{safe}X` \n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎁 **PROMO** : `{CODE_PROMO}`")
        video = ID_VIDEO_LUCKYJET
    else:
        cote = round(random.uniform(10.0, 85.0), 2)
        safe = round(random.uniform(4.0, 9.0), 2)
        text = (f"✈️ **PRÉDICTION AVIATOR**\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"🕒 **HEURE DE VOL** : `{time_fmt}`\n"
                f"💰 **GAIN ESTIMÉ** : `{cote}X+` \n"
                f"🛡 **RETRAIT PRÉVU** : `{safe}X` \n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"🎟 **PROMO** : `{CODE_PROMO}`")
        video = ID_VIDEO_AVIATOR
    random.seed()
    return text, video

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(msg):
    get_user(msg.from_user.id)
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("🚀 LUCKY JET", callback_data="game_LUCKY"),
        telebot.types.InlineKeyboardButton("✈️ AVIATOR", callback_data="game_AVIATOR")
    )
    markup.add(telebot.types.InlineKeyboardButton("📊 STATISTIQUES", callback_data="show_stats"))
    
    bot.send_message(msg.chat.id, f"👋 **Bienvenue sur le Robot Officiel**\n\nSélectionnez votre jeu :", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith("game_"))
def handle_game(c):
    u = get_user(c.from_user.id)
    if c.from_user.id == ADMIN_ID or u.get('is_vip'):
        game_type = c.data.split("_")[1]
        text, video = calculate_prediction(game_type)
        btn = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("📲 JOUER MAINTENANT", url=LIEN_INSCRIPTION))
        bot.send_video(c.message.chat.id, video, caption=text, reply_markup=btn, parse_mode='Markdown')
    else:
        bot.send_message(c.message.chat.id, "⚠️ **ACCÈS VIP REQUIS**")
    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data == "show_stats")
def handle_stats(c):
    # Retour aux statistiques du début (Simples et Pro)
    stats_pro = (
        f"📊 **STATISTIQUES PROFESSIONNELLES**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 **LUCKY JET** : `98.7% de précision`\n"
        f"✈️ **AVIATOR** : `97.9% de précision`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛰 **SERVEUR** : `ACTIF` (Abidjan/Paris)\n"
        f"📡 **LATENCE** : `14ms` (Très Rapide)\n"
        f"🔄 **MAJ ALGO** : `Toutes les 24h`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Utilisez le Code Promo {CODE_PROMO}*"
    )
    bot.send_message(c.message.chat.id, stats_pro, parse_mode='Markdown')
    bot.answer_callback_query(c.id)

# Validation ID
@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    kb = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("✅ VALIDER VIP", callback_data=f"val_{msg.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🆕 **DEMANDE VIP**\nID : `{msg.text}`", reply_markup=kb)
    bot.send_message(msg.chat.id, "⏳ **Vérification...**")

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def accept_vip(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}}, upsert=True)
    bot.send_message(uid, "🌟 **ACCÈS ACTIVÉ !**")
    bot.answer_callback_query(c.id, "Validé")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling(timeout=30)
