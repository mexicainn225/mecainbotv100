import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)

@app.route('/')
def home():
    return "Système Pro V13 - Tous VIP Activés"

# --- CONFIGURATION ---
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = 5724620019  
MONGO_URI = os.getenv('MONGO_URI')
bot = telebot.TeleBot(API_TOKEN)

# Connexion MongoDB (On utilise la même base pour garder les anciens VIP)
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
    # Cette fonction va chercher l'utilisateur dans ta base existante
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
    return 11 if game == "AVIATOR" else 10

def calculate_prediction(game_type):
    now = datetime.now()
    intervalle = 21 if "LUCKY" in game_type else 11
    base_min = get_base_min(game_type)
    
    total_now = (now.hour * 60) + now.minute
    sig_total = base_min
    
    while sig_total <= total_now:
        sig_total += intervalle
            
    target_time = now.replace(hour=(sig_total // 60) % 24, minute=sig_total % 60, second=0, microsecond=0)
    time_fmt = f"{target_time.strftime('%H:%M')} - {(target_time + timedelta(minutes=1)).strftime('%H:%M')}"
    
    random.seed(target_time.timestamp())
    
    if "LUCKY" in game_type:
        cote = round(random.uniform(10.0, 85.0), 2)
        safe = round(random.uniform(5.0, 8.0), 2)
        text = (f"🚀 **PRÉDICTION LUCKY JET**\n━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 **CRÉNEAU** : `{time_fmt}`\n📈 **OBJECTIF** : `{cote}X` \n"
                f"🎯 **SÉCURITÉ** : `{safe}X` \n━━━━━━━━━━━━━━━━━━━━\n"
                f"🎁 **PROMO** : `{CODE_PROMO}`")
        video = ID_VIDEO_LUCKYJET
    else:
        cote = round(random.uniform(10.0, 85.0), 2)
        safe = round(random.uniform(4.0, 9.0), 2)
        text = (f"✈️ **PRÉDICTION AVIATOR**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"🕒 **HEURE DE VOL** : `{time_fmt}`\n💰 **GAIN ESTIMÉ** : `{cote}X+` \n"
                f"🛡 **RETRAIT PRÉVU** : `{safe}X` \n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
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
    
    bot.send_message(msg.chat.id, "👋 **Robot Officiel Activé**", reply_markup=markup, parse_mode='Markdown')

# GESTION DES JEUX (Reconnaissance automatique des anciens VIP)
@bot.message_handler(func=lambda m: ("LUCKY" in m.text.upper() or "AVIATOR" in m.text.upper()) and "CONFIG" not in m.text.upper())
def handle_games(msg):
    u = get_user(msg.from_user.id)
    
    # Vérification : Est-ce que l'utilisateur est déjà VIP dans MongoDB ?
    if msg.from_user.id == ADMIN_ID or u.get('is_vip') == True:
        game = "LUCKY" if "LUCKY" in msg.text.upper() else "AVIATOR"
        text, video = calculate_prediction(game)
        btn = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("📲 JOUER", url=LIEN_INSCRIPTION))
        bot.send_video(msg.chat.id, video, caption=text, reply_markup=btn, parse_mode='Markdown')
    else:
        # Si pas encore VIP
        bot.send_message(msg.chat.id, "⚠️ **ACCÈS VIP REQUIS**\n\nInscrivez-vous avec le code promo et envoyez votre ID ici.")

@bot.message_handler(func=lambda m: "STATISTIQUES" in m.text.upper())
def handle_stats(msg):
    stats = (f"📊 **STATISTIQUES PROFESSIONNELLES**\n"
             f"━━━━━━━━━━━━━━━━━━━━━━\n"
             f"🚀 **LUCKY JET** : `98.7% de précision`\n"
             f"✈️ **AVIATOR** : `97.9% de précision`\n"
             f"━━━━━━━━━━━━━━━━━━━━━━\n"
             f"🛰 **SERVEUR** : `ACTIF` \n"
             f"📡 **LATENCE** : `14ms` \n"
             f"🔄 **MAJ ALGO** : `Toutes les 24h`\n"
             f"━━━━━━━━━━━━━━━━━━━━━━\n"
             f"✅ *Code Promo : {CODE_PROMO}*")
    bot.send_message(msg.chat.id, stats, parse_mode='Markdown')

# --- CONFIG ADMIN ---
@bot.message_handler(func=lambda m: "CONFIG" in m.text.upper() and m.from_user.id == ADMIN_ID)
def config_start(msg):
    game = "LUCKY" if "LUCKY" in m.text.upper() else "AVIATOR"
    admin_state[ADMIN_ID] = f"WAIT_{game}"
    bot.send_message(ADMIN_ID, f"🛠 **RÉGLAGE {game}**\nEnvoie la minute de départ :")

@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID, "") and admin_state[ADMIN_ID].startswith("WAIT_"))
def config_save(msg):
    if msg.from_user.id == ADMIN_ID and msg.text.isdigit():
        game = admin_state[ADMIN_ID].split("_")[1]
        config_col.update_one({"_id": f"settings_{game}"}, {"$set": {"minute": int(msg.text)}}, upsert=True)
        bot.send_message(ADMIN_ID, f"✅ **{game} Mis à jour !**")
        admin_state[ADMIN_ID] = None

# Validation VIP (pour les nouveaux)
@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    kb = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("✅ VALIDER", callback_data=f"val_{msg.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🆕 **ID REÇU** : `{msg.text}`", reply_markup=kb)
    bot.send_message(msg.chat.id, "⏳ **Vérification...**")

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def accept_vip(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}}, upsert=True)
    bot.send_message(uid, "🌟 **ACCÈS VIP ACTIVÉ !**")
    bot.answer_callback_query(c.id)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling(timeout=30)
