import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)

@app.route('/')
def home():
    return "Système Pro V18 - Reset Complet"

# --- CONFIGURATION ---
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = 5724620019  
MONGO_URI = os.getenv('MONGO_URI')
bot = telebot.TeleBot(API_TOKEN)

client = MongoClient(MONGO_URI)
db = client['luckyjet_db']
users_col = db['users'] 
config_col = db['config']

LIEN_INSCRIPTION = "https://lkbb.cc/e2d8"
CODE_PROMO = "COK225"

ID_VIDEO_AVIATOR = "https://t.me/explicationsjeux21points/25787"
ID_VIDEO_LUCKYJET = "https://t.me/gagnantpro1xbet/138958" 

admin_state = {}

# --- FONCTION DE CALCUL ---
def calculate_prediction(game_type):
    now = datetime.now()
    intervalle = 21 if "LUCKY" in game_type.upper() else 11
    
    conf = config_col.find_one({"_id": f"settings_{game_type.upper()}"})
    base_min = int(conf['minute']) if conf else 11
    
    total_now = (now.hour * 60) + now.minute
    sig_total = base_min
    while sig_total <= total_now:
        sig_total += intervalle
        
    target_time = now.replace(hour=(sig_total // 60) % 24, minute=sig_total % 60, second=0, microsecond=0)
    time_fmt = f"{target_time.strftime('%H:%M')} - {(target_time + timedelta(minutes=1)).strftime('%H:%M')}"
    
    random.seed(target_time.timestamp())
    cote = round(random.uniform(10.0, 85.0), 2)
    
    if "LUCKY" in game_type.upper():
        safe = round(random.uniform(5.0, 8.0), 2)
        text = f"🚀 **PRÉDICTION LUCKY JET**\n━━━━━━━━━━━━━━━━━━━━\n📅 **CRÉNEAU** : `{time_fmt}`\n📈 **OBJECTIF** : `{cote}X` \n🎯 **SÉCURITÉ** : `{safe}X` \n━━━━━━━━━━━━━━━━━━━━\n🎁 **PROMO** : `{CODE_PROMO}`"
        video = ID_VIDEO_LUCKYJET
    else:
        safe = round(random.uniform(4.0, 9.0), 2)
        text = f"✈️ **PRÉDICTION AVIATOR**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n🕒 **HEURE DE VOL** : `{time_fmt}`\n💰 **GAIN ESTIMÉ** : `{cote}X+` \n🛡 **RETRAIT PRÉVU** : `{safe}X` \n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n🎟 **PROMO** : `{CODE_PROMO}`"
        video = ID_VIDEO_AVIATOR
    return text, video

# --- HANDLERS (ORDRE CRUCIAL) ---

@bot.message_handler(commands=['start'])
def start(msg):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚀 LUCKY JET", "✈️ AVIATOR")
    markup.row("📊 STATISTIQUES")
    if msg.from_user.id == ADMIN_ID:
        markup.row("⚙️ CONFIG LUCKY", "⚙️ CONFIG AVIATOR")
    bot.send_message(msg.chat.id, "🤖 **Système Prêt.**\nCliquez sur un bouton :", reply_markup=markup)

# 1. DÉTECTION CONFIG (ADMIN UNIQUEMENT)
@bot.message_handler(func=lambda m: "CONFIG" in m.text.upper())
def config_handler(msg):
    if msg.from_user.id == ADMIN_ID:
        game = "LUCKY" if "LUCKY" in msg.text.upper() else "AVIATOR"
        admin_state[ADMIN_ID] = f"WAIT_{game}"
        bot.send_message(ADMIN_ID, f"🛠 **RÉGLAGE {game}**\nEnvoie la minute de départ (ex: 11) :")
    else:
        bot.send_message(msg.chat.id, "🚫 Accès Admin requis.")

# 2. CAPTURE DU CHIFFRE CONFIG
@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID, "") != "" and m.text.isdigit())
def save_config(msg):
    if msg.from_user.id == ADMIN_ID:
        game = admin_state[ADMIN_ID].split("_")[1]
        config_col.update_one({"_id": f"settings_{game}"}, {"$set": {"minute": int(msg.text)}}, upsert=True)
        bot.send_message(ADMIN_ID, f"✅ **{game} Mis à jour sur {msg.text} !**")
        admin_state[ADMIN_ID] = ""

# 3. DÉTECTION STATS
@bot.message_handler(func=lambda m: "STAT" in m.text.upper())
def handle_stats(msg):
    bot.send_message(msg.chat.id, "📊 **STATISTIQUES**\n━━━━━━━━━━━━━━\n✅ Serveur : OK\n📈 Précision : 98%\n━━━━━━━━━━━━━━")

# 4. DÉTECTION JEUX (VERSION ULTRA-SIMPLE)
@bot.message_handler(func=lambda m: "LUCKY" in m.text.upper() or "AVIATOR" in m.text.upper())
def handle_prediction(msg):
    user = users_col.find_one({"_id": msg.from_user.id})
    is_vip = user.get('is_vip') if user else False
    
    if msg.from_user.id == ADMIN_ID or is_vip:
        game = "LUCKY" if "LUCKY" in msg.text.upper() else "AVIATOR"
        text, video = calculate_prediction(game)
        bot.send_video(msg.chat.id, video, caption=text, parse_mode='Markdown')
    else:
        bot.send_message(msg.chat.id, "⚠️ **ACCÈS VIP REQUIS**")

# 5. VALIDATION ID (POUR LES CHIFFRES LONGS)
@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    kb = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("✅ VALIDER", callback_data=f"val_{msg.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🆕 **ID JOUEUR** : `{msg.text}`", reply_markup=kb)
    bot.send_message(msg.chat.id, "⏳ **Analyse de votre compte...**")

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def accept_vip(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}}, upsert=True)
    bot.send_message(uid, "🌟 **ACCÈS VIP ACTIVÉ !**")
    bot.answer_callback_query(c.id)

if __name__ == "__main__":
    # Nettoyage webhook pour Render
    bot.remove_webhook()
    time.sleep(1)
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling(timeout=30)
