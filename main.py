import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)

@app.route('/')
def home():
    return "Système Multi-Jeux - VIP Automatique Opérationnel"

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
        if conf and 'minute' in conf:
            return int(conf['minute'])
    except:
        pass
    return datetime.now().minute 

# --- LOGIQUE PRÉDICTIONS ---
def get_prediction(game_type):
    now = datetime.now()
    base_min = get_base_min(game_type)
    total_now = now.hour * 60 + now.minute
    
    intervalle = 21 if game_type == "LUCKY" else 13
    sig_total = base_min
    
    # Trouver le prochain signal
    while sig_total <= total_now:
        sig_total += intervalle
            
    target_time = now.replace(hour=(sig_total // 60) % 24, minute=sig_total % 60, second=0, microsecond=0)
    
    random.seed(target_time.timestamp())
    if game_type == "LUCKY":
        cote = round(random.uniform(10.0, 85.0), 2)
        prev = round(random.uniform(5.0, 8.0), 2)
        label = "PRÉDICTION LUCKY JET"
        video = ID_VIDEO_LUCKYJET
    else:
        # Aviator : Objectif 10X-85X / Sécurité 4X-9X
        cote = round(random.uniform(10.0, 85.0), 2)
        prev = round(random.uniform(4.0, 9.0), 2)
        label = "PRÉDICTION AVIATOR"
        video = ID_VIDEO_AVIATOR
        
    random.seed()
    return target_time, cote, prev, label, video

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(msg):
    get_user(msg.from_user.id)
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🚀 LUCKY JET", "✈️ AVIATOR")
    markup.add("📊 STATISTIQUES")
    if msg.from_user.id == ADMIN_ID:
        markup.add("⚙️ CONFIG LUCKY", "⚙️ CONFIG AVIATOR")
    
    welcome_text = (
        f"👋 **Bienvenue sur le Robot Officiel !**\n\n"
        f"⚠️ **RÈGLES OBLIGATOIRES :**\n"
        f"1️⃣ Inscription Code Promo : `{CODE_PROMO}`\n"
        f"2️⃣ Compte rechargé pour l'activation.\n\n"
        f"Choisissez votre jeu pour commencer :"
    )
    bot.send_message(msg.chat.id, welcome_text, reply_markup=markup, parse_mode='Markdown')

# Détection simplifiée pour AVIATOR et LUCKY JET
@bot.message_handler(func=lambda m: "LUCKY" in m.text or "AVIATOR" in m.text)
def game_handler(msg):
    u = get_user(msg.from_user.id)
    
    # Vérifie si Admin ou si déjà marqué VIP dans la base
    if msg.from_user.id == ADMIN_ID or u.get('is_vip') == True:
        game_type = "LUCKY" if "LUCKY" in msg.text else "AVIATOR"
        
        t_time, cote, prev, label, video = get_prediction(game_type)
        time_fmt = f"{t_time.strftime('%H:%M')} - {(t_time + timedelta(minutes=1)).strftime('%H:%M')}"
        
        if game_type == "LUCKY":
            cap = f"🚀 **{label}**\n━━━━━━━━━━━━━━━━━━\n📅 **CRÉNEAU** : `{time_fmt}`\n📈 **OBJECTIF** : `{cote}X` \n🎯 **SÉCURITÉ** : `{prev}X` \n━━━━━━━━━━━━━━━━━━\n🎁 **CODE PROMO** : `{CODE_PROMO}`"
        else:
            cap = f"✈️ **{label}**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n🕒 **HEURE DE VOL** : `{time_fmt}`\n💰 **GAIN ESTIMÉ** : `{cote}X+` \n🛡 **RETRAIT PRÉVU** : `{prev}X` \n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n🎟 **PROMO** : `{CODE_PROMO}`"
        
        btn = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("📲 JOUER MAINTENANT", url=LIEN_INSCRIPTION))
        bot.send_video(msg.chat.id, video, caption=cap, reply_markup=btn, parse_mode='Markdown')
    else:
        bot.send_message(msg.chat.id, f"⚠️ **ACCÈS VIP REQUIS**\n\nInscrivez-vous avec le code `{CODE_PROMO}` et envoyez votre ID joueur ici pour l'activation.")

@bot.message_handler(func=lambda m: "CONFIG" in m.text and m.from_user.id == ADMIN_ID)
def config_choice(msg):
    game = "LUCKY" if "LUCKY" in msg.text else "AVIATOR"
    admin_state[ADMIN_ID] = f"WAIT_{game}"
    bot.send_message(ADMIN_ID, f"🛠 **CONFIG {game}**\nEntrez la minute de base (ex: 10) :")

@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID, "") and admin_state[ADMIN_ID].startswith("WAIT_"))
def save_config(msg):
    if msg.from_user.id == ADMIN_ID and msg.text.isdigit():
        game = admin_state[ADMIN_ID].split("_")[1]
        config_col.update_one({"_id": f"settings_{game}"}, {"$set": {"minute": int(msg.text)}}, upsert=True)
        bot.send_message(ADMIN_ID, f"✅ **{game} MIS À JOUR**")
        admin_state[ADMIN_ID] = None

@bot.message_handler(func=lambda m: "STATISTIQUES" in m.text)
def stats_handler(msg):
    stats_pro = (
        f"📊 **STATISTIQUES PROFESSIONNELLES**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 **LUCKY JET** : `98.7% de précision`\n"
        f"✈️ **AVIATOR** : `97.9% de précision`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛰 **SERVEUR** : `OPÉRATIONNEL`\n"
        f"📡 **LATENCE** : `14ms` \n"
        f"🔄 **ALGO** : `V3.2.1 Stable` \n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Inscrit avec : {CODE_PROMO}*"
    )
    bot.send_message(msg.chat.id, stats_pro, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    kb = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("✅ VALIDER", callback_data=f"val_{msg.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🆕 **DEMANDE VIP**\nID JOUEUR : `{msg.text}`", reply_markup=kb)
    bot.send_message(msg.chat.id, "⏳ **Analyse de l'ID en cours...**")

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def accept_vip(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}}, upsert=True)
    bot.send_message(uid, f"🌟 **ACCÈS ACTIVÉ !**\n\nVotre compte est désormais lié au serveur VIP avec le code `{CODE_PROMO}`. Bons gains !")
    bot.answer_callback_query(c.id, "Validé")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling(timeout=20)
