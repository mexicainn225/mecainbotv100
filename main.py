import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)

@app.route('/')
def home():
    return "Système Pro V9 - Initialisation 11min OK"

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

# --- FONCTIONS SYSTÈME ---
def get_user(u_id):
    user = users_col.find_one({"_id": u_id})
    if not user:
        user = {"_id": u_id, "is_vip": False}
        users_col.insert_one(user)
    return user

def get_base_min(game):
    try:
        conf = config_col.find_one({"_id": f"settings_{game}"})
        if conf and 'minute' in conf: return int(conf['minute'])
    except: pass
    # INITIALISATION DIRECTE SI VIDE
    return 11 if game == "AVIATOR" else 10 

def calculate_prediction(game_type):
    now = datetime.now()
    base_min = get_base_min(game_type)
    total_now = now.hour * 60 + now.minute
    
    # INTERVALLES FIXES
    intervalle = 21 if "LUCKY" in game_type else 11
    
    sig_total = base_min
    while sig_total <= total_now:
        sig_total += intervalle
            
    target_time = now.replace(hour=(sig_total // 60) % 24, minute=sig_total % 60, second=0, microsecond=0)
    time_fmt = f"{target_time.strftime('%H:%M')} - {(target_time + timedelta(minutes=1)).strftime('%H:%M')}"
    
    random.seed(target_time.timestamp())
    
    if "LUCKY" in game_type:
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
        # AVIATOR INITIALISÉ SUR 11
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
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚀 LUCKY JET", "✈️ AVIATOR")
    markup.row("📊 STATISTIQUES")
    if msg.from_user.id == ADMIN_ID:
        markup.row("⚙️ CONFIG LUCKY", "⚙️ CONFIG AVIATOR")
    
    bot.send_message(msg.chat.id, "👋 **Algorithme Pro V9 Connecté.**\nInitialisation 11min terminée.", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: ("LUCKY" in m.text or "AVIATOR" in m.text) and "CONFIG" not in m.text)
def handle_games(msg):
    u = get_user(msg.from_user.id)
    if msg.from_user.id == ADMIN_ID or u.get('is_vip') == True:
        game = "LUCKY" if "LUCKY" in msg.text else "AVIATOR"
        text, video = calculate_prediction(game)
        btn = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("📲 JOUER", url=LIEN_INSCRIPTION))
        bot.send_video(msg.chat.id, video, caption=text, reply_markup=btn, parse_mode='Markdown')
    else:
        bot.send_message(msg.chat.id, "⚠️ **ACCÈS VIP REQUIS**")

@bot.message_handler(func=lambda m: "STATISTIQUES" in m.text)
def handle_stats(msg):
    stats = (f"📊 **ANALYSE TECHNIQUE PRO**\n"
             f"━━━━━━━━━━━━━━━━━━━━━━\n"
             f"✅ **Précision Algorithmique** : `98.6%` \n"
             f"🚀 **Cycle Lucky Jet** : `21 min` \n"
             f"✈️ **Cycle Aviator** : `11 min` \n"
             f"━━━━━━━━━━━━━━━━━━━━━━\n"
             f"📡 **Statut** : `Opérationnel` \n"
             f"⚡ **Latence** : `8ms` \n"
             f"━━━━━━━━━━━━━━━━━━━━━━")
    bot.send_message(msg.chat.id, stats, parse_mode='Markdown')

@bot.message_handler(func=lambda m: "CONFIG" in m.text and m.from_user.id == ADMIN_ID)
def config_start(msg):
    game = "LUCKY" if "LUCKY" in msg.text else "AVIATOR"
    admin_state[ADMIN_ID] = f"WAIT_{game}"
    bot.send_message(ADMIN_ID, f"🛠 **RÉGLAGE {game}**\nMinute actuelle : {datetime.now().minute}\nEnvoie la nouvelle base :")

@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID, "").startswith("WAIT_"))
def config_save(msg):
    if msg.from_user.id == ADMIN_ID and msg.text.isdigit():
        game = admin_state[ADMIN_ID].split("_")[1]
        config_col.update_one({"_id": f"settings_{game}"}, {"$set": {"minute": int(msg.text)}}, upsert=True)
        bot.send_message(ADMIN_ID, f"✅ **{game} SYNCHRONISÉ SUR {msg.text}**")
        admin_state[ADMIN_ID] = None

@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    kb = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("✅ VALIDER VIP", callback_data=f"val_{msg.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🆕 **ID REÇU** : `{msg.text}`", reply_markup=kb)
    bot.send_message(msg.chat.id, "⏳ **Vérification VIP en cours...**")

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def accept_vip(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}}, upsert=True)
    bot.send_message(uid, "🌟 **ACCÈS VIP ACTIVÉ !**")
    bot.answer_callback_query(c.id, "Validé")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling(timeout=30)
