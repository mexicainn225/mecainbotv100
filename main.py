import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient

# --- INITIALISATION FLASK (Pour Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Système Mexicain225 Actif 🚀"

@app.route('/health')
def health():
    return "OK", 200

# --- CONFIGURATION ---
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = 5724620019  
MONGO_URI = os.getenv('MONGO_URI')

bot = telebot.TeleBot(API_TOKEN)

# Connexion MongoDB
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['luckyjet_db']
    users_col = db['users'] 
    config_col = db['config']
except Exception as e:
    print(f"Erreur MongoDB: {e}")

LIEN_INSCRIPTION = "https://lkbb.cc/e2d8"
CODE_PROMO = "COK225"
ID_VIDEO_UNIQUE = "https://t.me/gagnantpro1xbet/138958" 

admin_state = {}

# --- FONCTIONS BASE DE DONNÉES ---
def get_user(u_id):
    try:
        user = users_col.find_one({"_id": u_id})
        if not user:
            user = {"_id": u_id, "is_vip": False}
            users_col.insert_one(user)
        return user
    except:
        return {"_id": u_id, "is_vip": False}

def set_vip(u_id):
    users_col.update_one({"_id": u_id}, {"$set": {"is_vip": True}}, upsert=True)

def get_base_minute():
    try:
        conf = config_col.find_one({"_id": "settings"})
        return conf['minute'] if conf else 23
    except:
        return 23

# --- LOGIQUE SIGNAL (7 MIN / CÔTE 10-150 / PREV 4-7) ---
def get_universal_signal():
    now = datetime.now()
    base_minute = get_base_minute()
    total_minutes_now = now.hour * 60 + now.minute
    
    next_sig_total = base_minute
    while next_sig_total <= total_minutes_now:
        next_sig_total += 14  # Intervalle de 7 minutes réglé ici
        
    target_hour = (next_sig_total // 60) % 24
    target_minute = next_sig_total % 60
    
    start_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    random.seed(start_time.timestamp()) 
    
    # Côte entre 10 et 150 | Prévision entre 4 et 7
    cote = round(random.uniform(10, 150), 2)
    prev = random.randint(4, 7)
    
    random.seed() 
    return start_time, cote, prev

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(msg):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btns = ["🚀 OBTENIR UN SIGNAL", "📊 STATISTIQUES"]
    if msg.from_user.id == ADMIN_ID:
        btns.append("⚙️ CHANGER LA MINUTE")
    markup.add(*btns)
    bot.send_message(msg.chat.id, "👋 Bienvenue sur l'espace privé Mexicain225 !", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🚀 OBTENIR UN SIGNAL")
def check_signal(msg):
    u_id = msg.from_user.id
    user_data = get_user(u_id)
    kb = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("📍 CLIQUE ICI POUR JOUER", url=LIEN_INSCRIPTION))

    # Vérification VIP (Les anciens dans MongoDB sont reconnus ici)
    if u_id == ADMIN_ID or user_data.get('is_vip'):
        start_time, cote, prev = get_universal_signal()
        # Plage de 1 minute réglée ici (start_time + 1)
        txt = (f"🚀 **SIGNAL CONFIRMÉ**\n\n⚡️ **HEURE** : `{start_time.strftime('%H:%M')} - {(start_time + timedelta(minutes=1)).strftime('%H:%M')}`\n"
               f"⚡️ **CÔTE** : `{cote}X+` \n⚡️ **PRÉVISION** : `{prev}X+` \n\n🎁 **CODE** : `{CODE_PROMO}`")
        bot.send_video(msg.chat.id, ID_VIDEO_UNIQUE, caption=txt, reply_markup=kb, parse_mode='Markdown')
    else:
        txt = f"⚠️ **VIP REQUIS**\n\n1️⃣ Inscris-toi : [CLIQUE ICI]({LIEN_INSCRIPTION})\n2️⃣ Code : **{CODE_PROMO}**\n3️⃣ Envoie ton ID ici pour validation."
        bot.send_video(msg.chat.id, ID_VIDEO_UNIQUE, caption=txt, reply_markup=kb, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    if admin_state.get(ADMIN_ID) == "WAITING_MINUTE": return
    # Bouton de validation pour l'Admin
    kb = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("✅ VALIDER VIP", callback_data=f"val_{msg.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🔔 **NOUVEL ID** : `{msg.text}`", reply_markup=kb)
    bot.send_message(msg.chat.id, "✅ ID reçu ! Validation en cours par l'administrateur.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def val_callback(c):
    uid = int(c.data.split("_")[1])
    set_vip(uid)
    bot.send_message(uid, "🌟 **VIP ACTIVÉ !** Vous pouvez maintenant obtenir les signaux.")
    bot.answer_callback_query(c.id, "Utilisateur validé !")

@bot.message_handler(func=lambda m: m.text == "⚙️ CHANGER LA MINUTE" and m.from_user.id == ADMIN_ID)
def ask_new_minute(msg):
    admin_state[ADMIN_ID] = "WAITING_MINUTE"
    bot.send_message(ADMIN_ID, "📝 Entre la nouvelle minute de base (0-59) :")

@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID) == "WAITING_MINUTE" and m.from_user.id == ADMIN_ID)
def save_new_minute(msg):
    if msg.text.isdigit():
        new_min = int(msg.text)
        config_col.update_one({"_id": "settings"}, {"$set": {"minute": new_min}}, upsert=True)
        admin_state[ADMIN_ID] = None
        bot.send_message(ADMIN_ID, f"✅ Minute de base réglée sur : `{new_min}`.")
    else:
        bot.send_message(ADMIN_ID, "❌ Veuillez entrer un chiffre uniquement.")

# --- LANCEMENT ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.infinity_polling(timeout=20)
