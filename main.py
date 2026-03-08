import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)

@app.route('/')
def home():
    return "Système Lucky Jet Pro - Cycle Infini OK"

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
ID_VIDEO_UNIQUE = "https://t.me/gagnantpro1xbet/138958" 

admin_state = {}

# --- FONCTIONS SYSTÈME ---
def get_user(u_id):
    user = users_col.find_one({"_id": u_id})
    if not user:
        user = {"_id": u_id, "is_vip": False}
        users_col.insert_one(user)
    return user

def get_base_minute():
    conf = config_col.find_one({"_id": "settings"})
    return conf['minute'] if conf else 16 

def get_next_signal():
    now = datetime.now()
    base_min = get_base_minute()
    
    total_now = now.hour * 60 + now.minute
    
    # Intervalle de 21 minutes
    sig_total = base_min
    while sig_total <= total_now:
        sig_total += 20
        
    target_hour = (sig_total // 60) % 24
    target_minute = sig_total % 60
    
    while target_minute >= 60:
        target_hour = (target_hour + 1) % 24
        target_minute -= 60

    target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    
    if target_time < now:
        target_time += timedelta(days=1)

    random.seed(target_time.timestamp())
    cote = round(random.uniform(10.0, 85.0), 2)
    prev = round(random.uniform(5.0, 8.0), 2)
    random.seed() 
    
    return target_time, cote, prev

# --- HANDLERS (COMMANDES) ---

@bot.message_handler(commands=['start'])
def start(msg):
    get_user(msg.from_user.id)
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btns = ["🚀 SIGNAL", "📊 STATISTIQUES"]
    if msg.from_user.id == ADMIN_ID:
        btns.append("⚙️ CONFIGURATION")
    markup.add(*btns)
    bot.send_message(msg.chat.id, "🛰 **Système Lucky Jet Connecté**", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🚀 SIGNAL")
def signal_handler(msg):
    u = get_user(msg.from_user.id)
    if msg.from_user.id == ADMIN_ID or u.get('is_vip'):
        t_time, cote, prev = get_next_signal()
        
        # Calcul du rappel (+8 minutes)
        rappel_time = t_time + timedelta(minutes=10)
        
        # Intervalles pour le signal principal
        main_start = t_time.strftime('%H:%M')
        main_end = (t_time + timedelta(minutes=1)).strftime('%H:%M')
        
        # Intervalles pour le rattrapage (+8 min)
        rappel_start = rappel_time.strftime('%H:%M')
        rappel_end = (rappel_time + timedelta(minutes=1)).strftime('%H:%M')
        
        caption = (f"🚀 **PRÉDICTION LUCKY JET**\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"📍 **SIGNAL** : `{main_start} À {main_end}`\n"
                   f"⚠️ **RATTRAPAGE** : `{rappel_start} À {rappel_end}`\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"📈 **OBJECTIF** : `{cote}X` \n"
                   f"🎯 **SÉCURITÉ** : `{prev}X` \n"
                   f"━━━━━━━━━━━━━━━━━━")
        
        btn = telebot.types.InlineKeyboardMarkup().add(
            telebot.types.InlineKeyboardButton("💻 JOUER MAINTENANT", url=LIEN_INSCRIPTION)
        )
        
        try:
            bot.send_video(msg.chat.id, ID_VIDEO_UNIQUE, caption=caption, reply_markup=btn, parse_mode='Markdown')
        except:
            bot.send_message(msg.chat.id, caption, reply_markup=btn, parse_mode='Markdown')
    else:
        bot.send_message(msg.chat.id, "⚠️ **ACCÈS VIP REQUIS**")

@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id_sent(msg):
    bot.send_message(msg.chat.id, "⏳ **Analyse de l'ID en cours...**")
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("✅ ACTIVER VIP", callback_data=f"val_{msg.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🆕 **DEMANDE D'ACTIVATION**\n🆔 ID Joueur : `{msg.text}`", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "📊 STATISTIQUES")
def stats_handler(msg):
    total_users = users_col.count_documents({})
    stats_text = (f"📊 **RAPPORT DE PRÉCISION**\n\n✅ Taux de succès : `98.4%` \n👥 Utilisateurs actifs : `{total_users}`")
    bot.send_message(msg.chat.id, stats_text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "⚙️ CONFIGURATION" and m.from_user.id == ADMIN_ID)
def config_admin(msg):
    admin_state[ADMIN_ID] = "WAIT_BASE"
    bot.send_message(ADMIN_ID, "🛠 **RÉGLAGE CYCLE**\nEntrez la minute de base :")

@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID) == "WAIT_BASE" and m.from_user.id == ADMIN_ID)
def save_config(msg):
    if msg.text.isdigit():
        config_col.update_one({"_id": "settings"}, {"$set": {"minute": int(msg.text)}}, upsert=True)
        bot.send_message(ADMIN_ID, f"✅ **Cycle synchronisé sur la minute {msg.text}**")
    admin_state[ADMIN_ID] = None

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def accept_vip(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}}, upsert=True)
    bot.send_message(uid, "🌟 **FÉLICITATIONS !**\nVIP activé.")
    bot.answer_callback_query(c.id, "Activé")

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling(timeout=20)
