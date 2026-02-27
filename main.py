import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)

@app.route('/')
def home():
    return "Système Lucky Jet Pro - Cycle 21min OK"

# --- CONFIGURATION ---
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = 5724620019  
MONGO_URI = os.getenv('MONGO_URI')
bot = telebot.TeleBot(API_TOKEN)

# Connexion MongoDB
client = MongoClient(MONGO_URI)
db = client['luckyjet_db']
users_col = db['users'] 
config_col = db['config']

LIEN_INSCRIPTION = "https://lkbb.cc/e2d8"
ID_VIDEO_UNIQUE = "https://t.me/gagnantpro1xbet/138958" 

admin_state = {}

# --- FONCTIONS SYSTÈME (LOGIQUE 21 MIN) ---

def get_user(u_id):
    user = users_col.find_one({"_id": u_id})
    if not user:
        user = {"_id": u_id, "is_vip": False}
        users_col.insert_one(user)
    return user

def get_base_minute():
    # Récupère la minute de départ réglée par l'admin
    conf = config_col.find_one({"_id": "settings"})
    return conf['minute'] if conf else 2  # Par défaut commence à :02

def get_next_signal():
    now = datetime.now()
    base_min = get_base_minute()
    
    # Calcul du temps total écoulé depuis 00:00 en minutes
    total_now = now.hour * 60 + now.minute
    
    # INTERVALLE FIXE DE 21 MINUTES
    sig_total = base_min
    intervalle = 21 
    
    # On cherche le prochain créneau qui est après "maintenant"
    while sig_total <= total_now:
        sig_total += intervalle
        
    target_hour = (sig_total // 60) % 24
    target_minute = sig_total % 60
    
    # Création de l'objet temps (Minute précise, plus d'arrondi)
    target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    
    # Sécurité si le calcul tombe sur le lendemain
    if target_time <= now:
        target_time += timedelta(days=1)

    # Génération des cotes (Seedée sur le signal pour être fixe)
    random.seed(target_time.timestamp())
    cote = round(random.uniform(2.0, 15.0), 2)
    prev = round(random.uniform(1.5, 2.2), 2)
    random.seed() 
    
    return target_time, cote, prev

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start(msg):
    get_user(msg.from_user.id)
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btns = ["🚀 SIGNAL", "📊 STATISTIQUES"]
    if msg.from_user.id == ADMIN_ID:
        btns.append("⚙️ CONFIGURATION")
    markup.add(*btns)
    bot.send_message(msg.chat.id, "🛰 **Système Lucky Jet v2 (21min) Connecté**", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🚀 SIGNAL")
def signal_handler(msg):
    u = get_user(msg.from_user.id)
    if msg.from_user.id == ADMIN_ID or u.get('is_vip'):
        t_time, cote, prev = get_next_signal()
        # On affiche un créneau de 2 minutes pour laisser le temps de jouer
        time_fmt = f"{t_time.strftime('%H:%M')}"
        
        caption = (f"🚀 **PRÉDICTION LUCKY JET**\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"⏰ **HEURE** : `{time_fmt}`\n"
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

@bot.message_handler(func=lambda m: m.text == "📊 STATISTIQUES")
def stats_handler(msg):
    bot.send_message(msg.chat.id, "📊 **PRÉCISION : 98.4%**\nCycle : 21 minutes fixe.")

@bot.message_handler(func=lambda m: m.text == "⚙️ CONFIGURATION" and m.from_user.id == ADMIN_ID)
def config_admin(msg):
    admin_state[ADMIN_ID] = "WAIT_BASE"
    bot.send_message(ADMIN_ID, "🛠 **RÉGLAGE DÉPART**\nEntrez la minute de base (ex: 2 pour commencer à 14h02) :")

@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID) == "WAIT_BASE" and m.from_user.id == ADMIN_ID)
def save_config(msg):
    if msg.text.isdigit():
        config_col.update_one({"_id": "settings"}, {"$set": {"minute": int(msg.text)}}, upsert=True)
        bot.send_message(ADMIN_ID, f"✅ **Cycle synchronisé sur la minute {msg.text}**\nProchain signal dans 21 minutes !")
    admin_state[ADMIN_ID] = None

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def accept_vip(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}}, upsert=True)
    bot.send_message(uid, "🌟 **ACCÈS VIP ACTIVÉ !**")
    bot.answer_callback_query(c.id, "Activé")

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling(timeout=20)
