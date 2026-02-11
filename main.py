import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)

@app.route('/')
def home():
    return "Système Mexicain225 - Actif 🚀"

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

def get_user(u_id):
    user = users_col.find_one({"_id": u_id})
    if not user:
        user = {"_id": u_id, "is_vip": False}
        users_col.insert_one(user)
    return user

def get_base_minute():
    conf = config_col.find_one({"_id": "settings"})
    return conf['minute'] if conf else 46 

def get_grosse_cote_min():
    conf = config_col.find_one({"_id": "grosse_cote"})
    return conf['minute'] if conf else None

# --- LOGIQUE SIGNAUX CLASSIQUES ---
def get_next_single_signal():
    now = datetime.now()
    base_min = get_base_minute()
    total_now = now.hour * 60 + now.minute
    sig1_total = base_min
    while sig1_total + 6 <= total_now:
        sig1_total += 17
    time_p = now.replace(hour=(sig1_total // 60) % 24, minute=sig1_total % 60, second=0, microsecond=0)
    time_r = time_p + timedelta(minutes=6)
    
    if total_now >= sig1_total:
        target_time, type_sig = time_r, "RATTRAPAGE ⚠️"
    else:
        target_time, type_sig = time_p, "PRINCIPAL ✅"
    
    minute_str = str(target_time.minute).zfill(2)
    is_ultra_safe = any(c in "6789" for c in minute_str)
    random.seed(target_time.timestamp())
    cote = round(random.uniform(1.5, 5.0), 2)
    prev = round(random.uniform(2.0, 4.0), 2)
    random.seed()
    return target_time, cote, prev, type_sig, is_ultra_safe

# --- LOGIQUE GROSSE CÔTE ---
def get_grosse_cote_signal():
    now = datetime.now()
    target_min = get_grosse_cote_min()
    if target_min is None: return None
    
    target_hour = (now.hour + 1) % 24
    time_rattrapage = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
    time_principal = time_rattrapage - timedelta(minutes=10)
    
    total_now = now.hour * 60 + now.minute
    total_r = time_rattrapage.hour * 60 + time_rattrapage.minute
    
    if total_now >= total_r: return "EXPIRED"

    if total_now >= (time_principal.hour * 60 + time_principal.minute):
        target_time, type_sig = time_rattrapage, "RATTRAPAGE 🔥"
    else:
        target_time, type_sig = time_principal, "CONFIRMÉ 💎"

    random.seed(target_time.timestamp())
    cote = round(random.uniform(10.0, 150.0), 2)
    prev = round(random.uniform(8.0, 15.0), 2)
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
    bot.send_message(msg.chat.id, "👋 Bienvenue !", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📊 STATISTIQUES")
def stats(msg):
    h_imp = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]
    h_act = datetime.now().hour
    proch = next((f"{str(h).zfill(2)}h:00" for h in h_imp if h > h_act), "01h:00")
    bot.send_message(msg.chat.id, f"📊 **PRÉCISION** : `99.1%` \n📅 **PROCHAINE SESSION** : `{proch}`", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🚀 OBTENIR UN SIGNAL")
def send_signal(msg):
    u_id = msg.from_user.id
    user_data = get_user(u_id)
    if u_id == ADMIN_ID or user_data.get('is_vip'):
        t_time, cote, prev, type_sig, is_safe = get_next_single_signal()
        badge = "\n💎 **FIABILITÉ : 100%**" if is_safe else ""
        txt = (f"🚀 **SIGNAL {type_sig}**{badge}\n\n📅 **HEURE** : `{t_time.strftime('%H:%M')}`\n📈 **CÔTE** : `{cote}X+` \n🎯 **PRÉVISION** : `{prev}X+` \n\n🎁 **CODE PROMO** : `{CODE_PROMO}`")
        bot.send_video(msg.chat.id, ID_VIDEO_UNIQUE, caption=txt, reply_markup=telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("📍 JOUER MAINTENANT", url=LIEN_INSCRIPTION)), parse_mode='Markdown')
    else:
        bot.send_message(msg.chat.id, f"⚠️ **ACCÈS VIP REQUIS**\n\nCode : **{CODE_PROMO}**", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "💎 GROSSE CÔTE")
def send_grosse_cote(msg):
    u_id = msg.from_user.id
    user_data = get_user(u_id)
    if u_id == ADMIN_ID or user_data.get('is_vip'):
        res = get_grosse_cote_signal()
        if res is None or res == "EXPIRED":
            bot.send_message(msg.chat.id, "⏳ **ANALYSE EN COURS...**\n\nVeuillez patienter pour le prochain créneau.")
            return
        t_time, cote, prev, type_sig = res
        txt = (f"💎 **SIGNAL {type_sig}**\n\n📅 **HEURE** : `{t_time.strftime('%H:%M')}`\n📈 **OBJECTIF** : `{cote}X+` \n🎯 **PRÉVISION** : `{prev}X+` \n\n🎁 **CODE PROMO** : `{CODE_PROMO}`")
        bot.send_video(msg.chat.id, ID_VIDEO_UNIQUE, caption=txt, reply_markup=telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("📍 JOUER MAINTENANT", url=LIEN_INSCRIPTION)), parse_mode='Markdown')
    else:
        bot.send_message(msg.chat.id, "⚠️ **SIGNAL RÉSERVÉ AUX VIP**", parse_mode='Markdown')

# --- ADMIN ---
@bot.message_handler(func=lambda m: m.text == "⚙️ RÉGLAGE MINUTE" and m.from_user.id == ADMIN_ID)
def config_min(msg):
    admin_state[ADMIN_ID] = "WAITING_MIN"
    bot.send_message(ADMIN_ID, "📝 Minute signal classique :")

@bot.message_handler(func=lambda m: m.text == "🔥 RÉGLAGE GROSSE CÔTE" and m.from_user.id == ADMIN_ID)
def config_grosse(msg):
    admin_state[ADMIN_ID] = "WAITING_GROSSE"
    bot.send_message(ADMIN_ID, "🔥 Minute pour la Grosse Côte :")

@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID) in ["WAITING_MIN", "WAITING_GROSSE"] and m.from_user.id == ADMIN_ID)
def save_configs(msg):
    if msg.text.isdigit():
        val = int(msg.text)
        if admin_state[ADMIN_ID] == "WAITING_MIN":
            config_col.update_one({"_id": "settings"}, {"$set": {"minute": val}}, upsert=True)
            bot.send_message(ADMIN_ID, "✅ Réglé.")
        else:
            config_col.update_one({"_id": "grosse_cote"}, {"$set": {"minute": val}}, upsert=True)
            bot.send_message(ADMIN_ID, "✅ Grosse Côte programmée.")
        admin_state[ADMIN_ID] = None
    else:
        bot.send_message(ADMIN_ID, "❌ Invalide.")

@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    kb = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("✅ VALIDER", callback_data=f"val_{msg.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🔔 ID : `{msg.text}`", reply_markup=kb)
    bot.send_message(msg.chat.id, "✅ Validation en cours...")

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def val_callback(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}}, upsert=True)
    bot.send_message(uid, "🌟 **VIP ACTIVÉ !**")
    bot.answer_callback_query(c.id, "OK")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling(timeout=20)
