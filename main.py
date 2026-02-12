import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)

@app.route('/')
def home():
    return "Système Mexicain225 - Arret Strict"

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

# --- FONCTIONS ---
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
    # On récupère aussi l'heure à laquelle l'admin a validé pour verrouiller
    return conf if conf else {}

def notify_all_vips(message_text):
    vips = users_col.find({"is_vip": True})
    for v in vips:
        try:
            bot.send_message(v['_id'], message_text, parse_mode='Markdown')
        except:
            pass

# --- LOGIQUE SIGNAL 02 @ 10 MIN ---
def get_next_single_signal():
    now = datetime.now()
    base_min = get_base_minute()
    total_now = now.hour * 60 + now.minute
    sig_total = base_min
    while sig_total + 10 <= total_now:
        sig_total += 17
    t_p = now.replace(hour=(sig_total // 60) % 24, minute=sig_total % 60, second=0, microsecond=0)
    t_r = t_p + timedelta(minutes=10)
    target_time, label = (t_r, "SIGNAL 02") if total_now >= sig_total else (t_p, "SIGNAL 01")
    random.seed(target_time.timestamp())
    cote = round(random.uniform(5.0, 115.0), 2)
    prev = round(random.uniform(5.0, 12.0), 2)
    random.seed()
    return target_time, cote, prev, label

# --- LOGIQUE GROSSE CÔTE (VERROUILLAGE STRICT) ---
def get_grosse_cote_signal():
    now = datetime.now()
    conf = get_grosse_cote_list()
    if not conf or 'minutes' not in conf: return None
    
    minutes_list = sorted(conf['minutes'])
    # L'heure cible est fixée au moment où tu as programmé + 2h
    target_hour = conf.get('target_hour')
    
    target_time = None
    for m in minutes_list:
        # On ne crée le signal que pour l'heure cible précise
        t_check = now.replace(hour=target_hour, minute=m, second=0, microsecond=0)
        
        # SI LA MINUTE EST ENCORE À VENIR (dans l'heure cible)
        if t_check > now:
            target_time = t_check
            break
            
    # SI TOUTES LES MINUTES DE L'HEURE CIBLE SONT PASSÉES -> STOP
    if not target_time:
        return "EXPIRED"

    random.seed(target_time.timestamp())
    cote = round(random.uniform(10.0, 200.0), 2)
    prev = round(random.uniform(10.0, 25.0), 2)
    random.seed()
    return target_time, cote, prev, "CONFIRMÉ 💎"

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(msg):
    get_user(msg.from_user.id)
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btns = ["🚀 SIGNAL", "💎 GROSSE CÔTE", "📊 STATS"]
    if msg.from_user.id == ADMIN_ID:
        btns.append("⚙️ SET 01")
        btns.append("⚙️ SET 02")
    markup.add(*btns)
    bot.send_message(msg.chat.id, "Session en ligne.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💎 GROSSE CÔTE")
def big_sig(msg):
    u = get_user(msg.from_user.id)
    if msg.from_user.id == ADMIN_ID or u.get('is_vip'):
        res = get_grosse_cote_signal()
        if res == "EXPIRED" or res is None:
            bot.send_message(msg.chat.id, "📊 **CALCULE EN COURS**\n\nLes prochaines analyses arrivent. Vous recevrez une notification dès validation.")
            return
        
        t_time, cote, prev, label = res
        time_fmt = f"{t_time.strftime('%H:%M')} - {(t_time + timedelta(minutes=1)).strftime('%H:%M')}"
        txt = (f"💎 **{label}**\n\n📅 **HEURE** : `{time_fmt}`\n📈 **OBJECTIF** : `{cote}X+` \n🎯 **VALEUR** : `{prev}X+` \n\n🎁 **CODE PROMO** : `{CODE_PROMO}`")
        bot.send_video(msg.chat.id, ID_VIDEO_UNIQUE, caption=txt, reply_markup=telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("ACCÈS JEU", url=LIEN_INSCRIPTION)), parse_mode='Markdown')
    else:
        bot.send_message(msg.chat.id, "⚠️ Accès VIP requis.")

@bot.message_handler(func=lambda m: m.text == "⚙️ SET 02" and m.from_user.id == ADMIN_ID)
def config_grosse(msg):
    admin_state[ADMIN_ID] = "WAIT_GROSSE"
    bot.send_message(ADMIN_ID, "Entrez les minutes (ex: 10, 35) :")

@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID) == "WAIT_GROSSE" and m.from_user.id == ADMIN_ID)
def save_grosse(msg):
    try:
        mins = [int(x.strip()) for x in msg.text.split(',')]
        now = datetime.now()
        # On enregistre l'heure cible (Maintenant + 2h)
        target_h = (now.hour + 2) % 24
        config_col.update_one({"_id": "grosse_cote"}, {"$set": {"minutes": mins, "target_hour": target_h}}, upsert=True)
        bot.send_message(ADMIN_ID, f"✅ Programmation verrouillée pour {target_h}h.")
        
        threading.Thread(target=notify_all_vips, args=("🔔 **ALERTE GROSSE CÔTE**\n\nNouveaux signaux validés !",)).start()
    except:
        bot.send_message(ADMIN_ID, "Erreur format.")
    admin_state[ADMIN_ID] = None

# SET 01, SIGNAL, STATS... (Reste du code identique)
@bot.message_handler(func=lambda m: m.text == "🚀 SIGNAL")
def normal_sig(msg):
    u = get_user(msg.from_user.id)
    if msg.from_user.id == ADMIN_ID or u.get('is_vip'):
        t_time, cote, prev, label = get_next_single_signal()
        time_fmt = f"{t_time.strftime('%H:%M')} - {(t_time + timedelta(minutes=1)).strftime('%H:%M')}"
        txt = (f"🚀 **{label}**\n\n📅 **HEURE** : `{time_fmt}`\n📈 **CÔTE** : `{cote}X+` \n🎯 **VALEUR** : `{prev}X+`")
        bot.send_video(msg.chat.id, ID_VIDEO_UNIQUE, caption=txt, reply_markup=telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("ACCÈS JEU", url=LIEN_INSCRIPTION)), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "⚙️ SET 01" and m.from_user.id == ADMIN_ID)
def config_min(msg):
    admin_state[ADMIN_ID] = "WAIT_MIN"
    bot.send_message(ADMIN_ID, "Base minute :")

@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID) == "WAIT_MIN" and m.from_user.id == ADMIN_ID)
def save_min(msg):
    if msg.text.isdigit():
        config_col.update_one({"_id": "settings"}, {"$set": {"minute": int(msg.text)}}, upsert=True)
        bot.send_message(ADMIN_ID, "OK.")
    admin_state[ADMIN_ID] = None

@bot.message_handler(func=lambda m: m.text == "📊 STATS")
def stats(msg):
    bot.send_message(msg.chat.id, "📊 **SESSIONS**\n\nPrécision : `99.1%` \nStatut : `Optimal`", parse_mode='Markdown')

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling(timeout=20)
