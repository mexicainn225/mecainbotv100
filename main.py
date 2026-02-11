import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)

@app.route('/')
def home():
    return "Système Mexicain225 - Multi-Signaux Actif 🚀"

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
ID_VIDEO_UNIQUE = "https://t.me/gagnantpro1xbet/138958" 

admin_state = {}

# --- FONCTIONS UTILES ---
def get_user(u_id):
    user = users_col.find_one({"_id": u_id})
    if not user:
        user = {"_id": u_id, "is_vip": False}
        users_col.insert_one(user)
    return user

def get_base_minute():
    conf = config_col.find_one({"_id": "settings"})
    return conf['minute'] if conf else 46 

def get_grosse_cote_list():
    conf = config_col.find_one({"_id": "grosse_cote"})
    return conf['minutes'] if conf and 'minutes' in conf else []

def send_subscription_block(chat_id):
    txt_vip = (f"⚠️ **ACCÈS PRIVÉ REQUIS**\n\n"
               f"Pour activer le robot et accéder aux signaux, suivez ces étapes :\n\n"
               f"1️⃣ Inscris-toi ici : [LIEN D'INSCRIPTION]({LIEN_INSCRIPTION})\n"
               f"2️⃣ Utilise le code promo : **{CODE_PROMO}**\n"
               f"3️⃣ Envoie ton **ID JOUEUR** ici pour validation.\n\n"
               f"🚀 *Accès à vie après activation.*")
    bot.send_message(chat_id, txt_vip, parse_mode='Markdown', disable_web_page_preview=True)

# --- LOGIQUE SIGNAL NORMAL ---
def get_next_single_signal():
    now = datetime.now()
    base_min = get_base_minute()
    total_now = now.hour * 60 + now.minute
    sig1_total = base_min
    while sig1_total + 10 <= total_now:
        sig1_total += 17
    
    t_p = now.replace(hour=(sig1_total // 60) % 24, minute=sig1_total % 60, second=0, microsecond=0)
    t_r = t_p + timedelta(minutes=10)
    target_time, type_sig = (t_r, "RATTRAPAGE ⚠️") if total_now >= sig1_total else (t_p, "PRINCIPAL ✅")
    
    random.seed(target_time.timestamp())
    cote = round(random.uniform(5.0, 115.0), 2)
    prev = round(random.uniform(5.0, 12.0), 2)
    random.seed()
    return target_time, cote, prev, type_sig

# --- LOGIQUE MULTI GROSSE CÔTE ---
def get_grosse_cote_signal():
    now = datetime.now()
    minutes_list = get_grosse_cote_list()
    if not minutes_list: return None
    
    total_now = now.hour * 60 + now.minute
    target_min = None
    
    # Chercher la première minute de la liste qui n'est pas encore passée
    for m in sorted(minutes_list):
        t_rattrapage_total = now.hour * 60 + m
        if total_now < t_rattrapage_total:
            target_min = m
            break
            
    if target_min is None: return "EXPIRED"
    
    t_rattrapage = now.replace(minute=target_min, second=0, microsecond=0)
    t_principal = t_rattrapage - timedelta(minutes=10)
    
    if total_now >= (t_principal.hour * 60 + t_principal.minute):
        target_time, type_sig = t_rattrapage, "RATTRAPAGE 🔥"
    else:
        target_time, type_sig = t_principal, "CONFIRMÉ 💎"

    random.seed(target_time.timestamp())
    cote = round(random.uniform(10.0, 200.0), 2)
    prev = round(random.uniform(10.0, 25.0), 2)
    random.seed()
    return target_time, cote, prev, type_sig

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(msg):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btns = ["🚀 OBTENIR UN SIGNAL", "💎 GROSSE CÔTE", "📊 STATISTIQUES"]
    if msg.from_user.id == ADMIN_ID:
        btns.append("⚙️ RÉGLAGE MINUTE")
        btns.append("🔥 RÉGLAGE GROSSE CÔTE")
    markup.add(*btns)
    bot.send_message(msg.chat.id, "👋 Session prête. Choisissez une option.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🚀 OBTENIR UN SIGNAL")
def normal_sig(msg):
    u = get_user(msg.from_user.id)
    if msg.from_user.id == ADMIN_ID or u.get('is_vip'):
        t_time, cote, prev, type_sig = get_next_single_signal()
        time_fmt = f"{t_time.strftime('%H:%M')} à {(t_time + timedelta(minutes=1)).strftime('%H:%M')}"
        txt = (f"🚀 **SIGNAL {type_sig}**\n\n📅 **HEURE** : `{time_fmt}`\n📈 **CÔTE** : `{cote}X+` \n🎯 **PRÉVISION** : `{prev}X+` \n\n🎁 **CODE PROMO** : `{CODE_PROMO}`")
        bot.send_video(msg.chat.id, ID_VIDEO_UNIQUE, caption=txt, reply_markup=telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("📍 JOUER MAINTENANT", url=LIEN_INSCRIPTION)), parse_mode='Markdown')
    else:
        send_subscription_block(msg.chat.id)

@bot.message_handler(func=lambda m: m.text == "💎 GROSSE CÔTE")
def big_sig(msg):
    u = get_user(msg.from_user.id)
    if msg.from_user.id == ADMIN_ID or u.get('is_vip'):
        res = get_grosse_cote_signal()
        if res is None or res == "EXPIRED":
            bot.send_message(msg.chat.id, "⏳ **ANALYSE EN COURS...**\n\nVeuillez patienter pour le prochain créneau.")
            return
        t_time, cote, prev, type_sig = res
        time_fmt = f"{t_time.strftime('%H:%M')} à {(t_time + timedelta(minutes=1)).strftime('%H:%M')}"
        txt = (f"💎 **SIGNAL {type_sig}**\n\n📅 **HEURE** : `{time_fmt}`\n📈 **OBJECTIF** : `{cote}X+` \n🎯 **PRÉVISION** : `{prev}X+` \n\n🎁 **CODE PROMO** : `{CODE_PROMO}`")
        bot.send_video(msg.chat.id, ID_VIDEO_UNIQUE, caption=txt, reply_markup=telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("📍 JOUER MAINTENANT", url=LIEN_INSCRIPTION)), parse_mode='Markdown')
    else:
        send_subscription_block(msg.chat.id)

# --- ADMIN COMMANDS ---
@bot.message_handler(func=lambda m: m.text == "⚙️ RÉGLAGE MINUTE" and m.from_user.id == ADMIN_ID)
def config_min(msg):
    admin_state[ADMIN_ID] = "WAIT_MIN"
    bot.send_message(ADMIN_ID, "📝 Minute signal classique :")

@bot.message_handler(func=lambda m: m.text == "🔥 RÉGLAGE GROSSE CÔTE" and m.from_user.id == ADMIN_ID)
def config_grosse(msg):
    admin_state[ADMIN_ID] = "WAIT_GROSSE"
    bot.send_message(ADMIN_ID, "🔥 Entre les minutes séparées par des virgules (ex: 10, 25, 45) :")

@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID) in ["WAIT_MIN", "WAIT_GROSSE"] and m.from_user.id == ADMIN_ID)
def save_configs(msg):
    text = msg.text
    if admin_state[ADMIN_ID] == "WAIT_MIN" and text.isdigit():
        config_col.update_one({"_id": "settings"}, {"$set": {"minute": int(text)}}, upsert=True)
        bot.send_message(ADMIN_ID, "✅ Signal Classique réglé.")
    elif admin_state[ADMIN_ID] == "WAIT_GROSSE":
        try:
            # Transformation de "10, 20, 30" en [10, 20, 30]
            mins = [int(x.strip()) for x in text.split(',')]
            config_col.update_one({"_id": "grosse_cote"}, {"$set": {"minutes": mins}}, upsert=True)
            bot.send_message(ADMIN_ID, f"✅ {len(mins)} signaux Grosses Côtes enregistrés.")
        except:
            bot.send_message(ADMIN_ID, "❌ Erreur. Utilisez le format: 10, 20, 30")
    admin_state[ADMIN_ID] = None

@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    kb = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("✅ VALIDER", callback_data=f"val_{msg.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🔔 ID REÇU : `{msg.text}`", reply_markup=kb)
    bot.send_message(msg.chat.id, "✅ ID reçu ! Validation en cours.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def val_callback(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}}, upsert=True)
    bot.send_message(uid, "🌟 **FÉLICITATIONS ! Ton accès VIP est activé.**")
    bot.answer_callback_query(c.id, "Activé")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling(timeout=20)
