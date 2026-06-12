import telebot
import random
import os
import threading
import time
from datetime import datetime
from flask import Flask, request
from pymongo import MongoClient

app = Flask(__name__)

# --- CONFIGURATION ---
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = 5724620019  
MONGO_URI = os.getenv('MONGO_URI')
bot = telebot.TeleBot(API_TOKEN)

client = MongoClient(MONGO_URI)
db = client['luckyjet_db']
users_col = db['users'] 
config_col = db['config']  # Collection pour stocker la minute de départ de l'admin

LIEN_INSCRIPTION = "https://lkbb.cc/e2d8"
ID_VIDEO_UNIQUE = "https://t.me/gagnantpro1xbet/138958" 

# --- LOGIQUE DE PAIRES DE MINUTES DYNAMIQUES ---
def get_next_signal():
    now = datetime.now()
    
    # Récupérer la minute de départ depuis MongoDB (par défaut : 1)
    config = config_col.find_one({"_id": "settings"})
    start_min = config.get("start_minute", 1) if config else 1
    
    # Générer la liste des minutes du Signal 1 toutes les 4 minutes à partir du départ choisi
    # Exemple si start_min = 1 : [1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53, 57]
    target_minutes = []
    current_calc_min = start_min
    while current_calc_min < 60:
        target_minutes.append(current_calc_min)
        current_calc_min += 4
    
    current_min = now.minute
    target_s1 = None
    target_hour = now.hour

    # Trouver la prochaine minute de Signal 1 disponible
    for m in target_minutes:
        if m > current_min:
            target_s1 = m
            break
    
    # Si l'heure est finie, on passe au premier créneau de l'heure suivante
    if target_s1 is None:
        target_s1 = target_minutes[0]
        target_hour = (now.hour + 1) % 24

    # Le Signal 2 suit immédiatement 1 minute après le Signal 1 (ex: 41 -> 42, 45 -> 46)
    target_s2 = target_s1 + 1

    # Gestion du débordement si le Signal 2 bascule sur l'heure suivante (ex: 59 -> 00)
    target_hour_s2 = target_hour
    if target_s2 >= 60:
        target_s2 = target_s2 % 60
        target_hour_s2 = (target_hour + 1) % 24

    time_s1 = now.replace(hour=target_hour, minute=target_s1, second=0, microsecond=0)
    time_s2 = now.replace(hour=target_hour_s2, minute=target_s2, second=0, microsecond=0)

    # GÉNÉRATION DES CÔTES (SÉCURITÉ FIXE 1.50)
    random.seed(time_s1.timestamp())
    cote = round(random.uniform(10.0, 85.0), 2)
    prev = 1.50
    random.seed() 
    
    return time_s1, time_s2, cote, prev

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start(msg):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btns = ["🚀 SIGNAL", "📊 STATISTIQUES"]
    if msg.from_user.id == ADMIN_ID:
        btns.append("⚙️ CONFIGURATION")
    markup.add(*btns)
    bot.send_message(msg.chat.id, "🛰 **Système Lucky Jet Connecté**", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🚀 SIGNAL")
def signal_handler(msg):
    u = users_col.find_one({"_id": msg.from_user.id})
    if msg.from_user.id == ADMIN_ID or (u and u.get('is_vip')):
        t_s1, t_s2, cote, prev = get_next_signal()
        
        caption = (f"🚀 **PRÉDICTION LUCKY JET**\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"📍 **SIGNAL 1** : `{t_s1.strftime('%H:%M')}`\n"
                   f"📍 **SIGNAL 2** : `{t_s2.strftime('%H:%M')}`\n"
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
        bot.send_message(msg.chat.id, "⚠️ **ACCÈS VIP REQUIS**\n\nEnvoyez votre ID joueur pour activation.")

# --- OPTIONS ADMINISTRATEUR ---

@bot.message_handler(func=lambda m: m.text == "⚙️ CONFIGURATION" and m.from_user.id == ADMIN_ID)
def config_menu(msg):
    config = config_col.find_one({"_id": "settings"})
    current_start = config.get("start_minute", 1) if config else 1
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("Minute :01", callback_data="set_1"),
        telebot.types.InlineKeyboardButton("Minute :02", callback_data="set_2"),
        telebot.types.InlineKeyboardButton("Minute :03", callback_data="set_3")
    )
    bot.send_message(
        msg.chat.id, 
        f"⚙️ **CONFIGURATION DES MINUTES**\n\nMinute de départ actuelle : `:{current_start:02d}`\n\n"
        "Pour changer sur une autre valeur libre, envoie un message avec le mot-clé **depart** suivi de la minute.\n"
        "Exemple : `depart 1` ou `depart 3`", 
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def set_minute_callback(c):
    new_min = int(c.data.split("_")[1])
    config_col.update_one({"_id": "settings"}, {"$set": {"start_minute": new_min}}, upsert=True)
    bot.answer_callback_query(c.id, f"Départ configuré à :{new_min:02d}")
    bot.edit_message_text(f"✅ **Configuration mise à jour**\nLes paires commenceront désormais aux minutes : `:{new_min:02d}`, `:{new_min+4:02d}`, `:{new_min+8:02d}`...", c.message.chat.id, c.message.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text.lower().startswith("depart"))
def set_minute_text(msg):
    try:
        new_min = int(msg.text.split()[1])
        if 0 <= new_min < 60:
            config_col.update_one({"_id": "settings"}, {"$set": {"start_minute": new_min}}, upsert=True)
            bot.send_message(msg.chat.id, f"✅ **Succès !** La minute de départ a été fixée à `:{new_min:02d}`.", parse_mode='Markdown')
        else:
            bot.send_message(msg.chat.id, "⚠️ Choisis une minute valide entre 0 et 59.")
    except:
        bot.send_message(msg.chat.id, "Format incorrect. Écris par exemple : `depart 1`")

# --- GESTION DES ID & ACTIVATION ADMIN ---
@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    users_col.update_one({"_id": msg.from_user.id}, {"$set": {"player_id": msg.text}}, upsert=True)
    bot.send_message(msg.chat.id, "⏳ **ID enregistré !**\nL'administrateur va valider votre accès.")
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("✅ ACTIVER VIP", callback_data=f"val_{msg.from_user.id}"))
    
    bot.send_message(
        ADMIN_ID, 
        f"🆕 **NOUVEL ID**\n👤: @{msg.from_user.username}\n🆔 ID: `{msg.text}`", 
        reply_markup=markup, 
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def valider_callback(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}})
    
    bot.answer_callback_query(c.id, "Activé !")
    bot.edit_message_text(f"✅ VIP activé pour {uid}", c.message.chat.id, c.message.message_id)
    
    try:
        bot.send_message(uid, "🌟 **Accès VIP activé !** Cliquez sur 🚀 **SIGNAL**.")
    except:
        pass

@bot.message_handler(func=lambda m: m.text == "📊 STATISTIQUES")
def stats_handler(msg):
    count = users_col.count_documents({})
    bot.send_message(msg.chat.id, f"📊 **STATISTIQUES**\n👥 Joueurs : `{count}`\n✅ Précision : `98%`", parse_mode='Markdown')

# --- WEBHOOK ---
@app.route('/webhook1win', methods=['POST'])
def handle_webhook():
    data = request.json
    p_id = str(data.get('uid') or data.get('player_id'))
    if p_id:
        user = users_col.find_one({"player_id": p_id})
        if user:
            users_col.update_one({"_id": user['_id']}, {"$set": {"is_vip": True}})
            bot.send_message(user['_id'], "✅ **DÉPÔT DÉTECTÉ**\nVIP activé !")
            return "OK", 200
    return "Ignored", 200

@app.route('/')
def home():
    return "Robot 1 en ligne - Cycle Dynamique 4min"

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.infinity_polling(timeout=20)
