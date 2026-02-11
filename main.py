import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)

@app.route('/')
def home():
    return "Serveur Mexicain225 - Actif 🚀"

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

# --- FONCTIONS SYSTÈME ---
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

def notify_all_vips(message_text):
    vips = users_col.find({"is_vip": True})
    for v in vips:
        try:
            bot.send_message(v['_id'], message_text, parse_mode='Markdown')
        except:
            pass

# --- LOGIQUE SIGNAL CLASSIQUE (Automatique) ---
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

# --- LOGIQUE GROSSE CÔTE (Manuelle avec basculement d'heure) ---
def get_grosse_cote_signal():
    now = datetime.now()
    minutes_list = get_grosse_cote_list()
    if not minutes_list: return None
    
    total_now = now.hour * 60 + now.minute
    target_min = None
    target_hour = now.hour
    sorted_mins = sorted(minutes_list)
    
    # 1. On cherche dans l'heure actuelle
    for m in sorted_mins:
        if total_now < (now.hour * 60 + m):
            target_min = m
            target_hour = now.hour
            break
            
    # 2. Si minutes passées, on bascule sur l'heure suivante (ex: 23h40 -> 00h10)
    if target_min is None:
        target_min = sorted_mins[0]
        target_hour = (now.hour + 1) % 24
    
    target_time = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
    
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
    bot.send_message(msg.chat.id, "Session active.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💎 GROSSE CÔTE")
def big_sig(msg):
    u = get_user(msg.from_user.id)
    if msg.from_user.id == ADMIN_ID or u.get('is_vip'):
        res = get_grosse_cote_signal()
        if not res:
            bot.send_message(msg.chat.id, "⏳ **INDISPONIBLE**\n\nAttendez la prochaine notification.")
            return
        t_time, cote, prev, label = res
        time_fmt = f"{t_time.strftime('%H:%M')} - {(t_time + timedelta(minutes=1)).strftime('%H:%M')}"
        txt = (f"💎 **{label}**\n\n📅 **HEURE** : `{time_fmt}`\n📈 **OBJECTIF** : `{cote}X+` \n🎯 **VALEUR** : `{prev}X+` \n\n🎁 **CODE PROMO** : `{CODE_PROMO}`")
        bot.send_video(msg.chat.id, ID_VIDEO_UNIQUE, caption=txt, reply_markup=telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("ACCÈS JEU", url=LIEN_INSCRIPTION)), parse_mode='Markdown')
    else:
        bot.send_message(msg.chat.id, f"⚠️ **ACCÈS PRIVÉ**\n\nInscrivez-vous avec le code promo **{CODE_PROMO}** sur [ce lien]({LIEN_INSCRIPTION}) puis envoyez votre ID ici.", parse_mode='Markdown', disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == "🚀 SIGNAL")
def normal_sig(msg):
    u = get_user(msg.from_user.id)
    if msg.from_user.id == ADMIN_ID or u.get('is_vip'):
        t_time, cote, prev, label = get_next_single_signal()
        time_fmt = f"{t_time.strftime('%H:%M')} - {(t_time + timedelta(minutes=1)).strftime('%H:%M')}"
        txt = (f"🚀 **{label}**\n\n📅 **HEURE** : `{time_fmt}`\n📈 **CÔTE** : `{cote}X+` \n🎯 **VALEUR** : `{prev}X+`")
        bot.send_video(msg.chat.id, ID_VIDEO_UNIQUE, caption=txt, reply_markup=telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("ACCÈS JEU", url=LIEN_INSCRIPTION)), parse_mode='Markdown')
    else:
        bot.send_message(msg.chat.id, f"⚠️ **ACCÈS PRIVÉ**\n\nCode promo : **{CODE_PROMO}**\nLien : [Cliquez ici]({LIEN_INSCRIPTION})", parse_mode='Markdown', disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == "📊 STATS")
def stats(msg):
    h_impaires = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]
    h_actuelle = datetime.now().hour
    prochaine = next((f"{str(h).zfill(2)}:00" for h in h_impaires if h > h_actuelle), "01:00")
    txt = (f"📊 **ÉTAT**\n\nPrécision : `99.1%` \nProchaine Session : `{prochaine}`")
    bot.send_message(msg.chat.id, txt, parse_mode='Markdown')

# --- ADMIN ACTIONS ---
@bot.message_handler(func=lambda m: m.text == "⚙️ SET 02" and m.from_user.id == ADMIN_ID)
def config_grosse(msg):
    admin_state[ADMIN_ID] = "WAIT_GROSSE"
    bot.send_message(ADMIN_ID, "Entrez les minutes (ex: 10, 23, 30) :")

@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID) == "WAIT_GROSSE" and m.from_user.id == ADMIN_ID)
def save_grosse(msg):
    try:
        mins = [int(x.strip()) for x in msg.text.split(',')]
        config_col.update_one({"_id": "grosse_cote"}, {"$set": {"minutes": mins}}, upsert=True)
        bot.send_message(ADMIN_ID, "✅ Programmation enregistrée.")
        
        # NOTIFICATION VIP
        txt_notif = "🔔 **INFORMATION**\n\nNouveaux signaux disponibles dans la section **💎 GROSSE CÔTE**."
        threading.Thread(target=notify_all_vips, args=(txt_notif,)).start()
    except:
        bot.send_message(ADMIN_ID, "Erreur format.")
    admin_state[ADMIN_ID] = None

@bot.message_handler(func=lambda m: m.text == "⚙️ SET 01" and m.from_user.id == ADMIN_ID)
def config_min(msg):
    admin_state[ADMIN_ID] = "WAIT_MIN"
    bot.send_message(ADMIN_ID, "Minute de base :")

@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID) == "WAIT_MIN" and m.from_user.id == ADMIN_ID)
def save_min(msg):
    if msg.text.isdigit():
        config_col.update_one({"_id": "settings"}, {"$set": {"minute": int(msg.text)}}, upsert=True)
        bot.send_message(ADMIN_ID, "OK.")
    admin_state[ADMIN_ID] = None

@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    kb = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("VALIDER", callback_data=f"val_{msg.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🔔 ID REÇU : `{msg.text}`", reply_markup=kb)
    bot.send_message(msg.chat.id, "ID reçu. Vérification en cours.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def val_callback(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}}, upsert=True)
    bot.send_message(uid, "🌟 **ACCÈS ACTIVÉ.**")
    bot.answer_callback_query(c.id, "Validé")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling(timeout=20)
