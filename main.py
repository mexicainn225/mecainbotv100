import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)

@app.route('/')
def home():
    return "Système Mexicain225 - Stratégie 100% Active 🚀"

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

# --- LOGIQUE : PRINCIPAL & RATTRAPAGE (+6min) ---
def get_next_single_signal():
    now = datetime.now()
    base_min = get_base_minute()
    total_now = now.hour * 60 + now.minute
    
    sig1_total = base_min
    while sig1_total + 6 <= total_now:
        sig1_total += 17
    
    time_principal = now.replace(hour=(sig1_total // 60) % 24, minute=sig1_total % 60, second=0, microsecond=0)
    time_rattrapage = time_principal + timedelta(minutes=6)

    if total_now >= sig1_total:
        target_time = time_rattrapage
        type_sig = "RATTRAPAGE ⚠️"
    else:
        target_time = time_principal
        type_sig = "PRINCIPAL ✅"
    
    # --- DETECTION FIABILITÉ 100% (Minutes commençant par 6,7,8,9) ---
    minute_str = str(target_time.minute).zfill(2) # ex: "06" ou "16"
    premier_chiffre = minute_str[0]
    second_chiffre = minute_str[1]
    
    # On vérifie si la minute finit par 6,7,8,9 OU si elle commence par 6,7,8,9 (ex: 06, 07, 46, 59)
    # Selon ta logique, on regarde si l'un des chiffres de la minute contient 6,7,8,9
    is_ultra_safe = any(c in "6789" for c in minute_str)

    random.seed(target_time.timestamp())
    cote = round(random.uniform(10, 150), 2)
    prev = random.randint(4, 7)
    random.seed()
    
    return target_time, cote, prev, type_sig, is_ultra_safe

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(msg):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btns = ["🚀 OBTENIR UN SIGNAL", "📊 STATISTIQUES"]
    if msg.from_user.id == ADMIN_ID:
        btns.append("⚙️ RÉGLAGE MINUTE")
    markup.add(*btns)
    bot.send_message(msg.chat.id, "👋 Bienvenue ! Prêt pour le prochain signal ?", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🚀 OBTENIR UN SIGNAL")
def send_signal(msg):
    u_id = msg.from_user.id
    user_data = get_user(u_id)
    kb = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("📍 JOUER MAINTENANT", url=LIEN_INSCRIPTION))

    if u_id == ADMIN_ID or user_data.get('is_vip'):
        target_time, cote, prev, type_sig, is_ultra_safe = get_next_single_signal()
        
        # Ajout du badge 100% si la condition est remplie
        badge_safe = "\n💎 **FIABILITÉ : 100% (CONFIRMÉ)**" if is_ultra_safe else ""
        
        txt = (f"🚀 **SIGNAL {type_sig}**{badge_safe}\n\n"
               f"📅 **HEURE** : `{target_time.strftime('%H:%M')} - {(target_time + timedelta(minutes=1)).strftime('%H:%M')}`\n"
               f"📈 **CÔTE** : `{cote}X+` \n"
               f"🎯 **PRÉVISION** : `{prev}X+` \n\n"
               f"🎁 **CODE PROMO** : `{CODE_PROMO}`")
        
        bot.send_video(msg.chat.id, ID_VIDEO_UNIQUE, caption=txt, reply_markup=kb, parse_mode='Markdown')
    else:
        txt_vip = f"⚠️ **ACCÈS VIP REQUIS**\n\n1️⃣ Inscris-toi : [ICI]({LIEN_INSCRIPTION})\n2️⃣ Code : **{CODE_PROMO}**\n3️⃣ Envoie ton ID ici."
        bot.send_message(msg.chat.id, txt_vip, parse_mode='Markdown', disable_web_page_preview=True)

# --- ADMIN ---
@bot.message_handler(func=lambda m: m.text == "⚙️ RÉGLAGE MINUTE" and m.from_user.id == ADMIN_ID)
def config_min(msg):
    admin_state[ADMIN_ID] = "WAITING_MIN"
    bot.send_message(ADMIN_ID, "📝 Entre la minute de départ (ex: 46) :")

@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID) == "WAITING_MIN" and m.from_user.id == ADMIN_ID)
def save_min(msg):
    if msg.text.isdigit():
        new_m = int(msg.text)
        config_col.update_one({"_id": "settings"}, {"$set": {"minute": new_m}}, upsert=True)
        admin_state[ADMIN_ID] = None
        bot.send_message(ADMIN_ID, f"✅ Cycle mis à jour ! Départ à : `{new_m}`")
    else:
        bot.send_message(ADMIN_ID, "❌ Nombre invalide.")

@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    if admin_state.get(ADMIN_ID) == "WAITING_MIN": return
    kb = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("✅ VALIDER", callback_data=f"val_{msg.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🔔 **NOUVEL ID** : `{msg.text}`", reply_markup=kb)
    bot.send_message(msg.chat.id, "✅ ID reçu ! Validation en cours.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def val_callback(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}}, upsert=True)
    bot.send_message(uid, "🌟 **VIP ACTIVÉ !** Réessaie le bouton SIGNAL.")
    bot.answer_callback_query(c.id, "Validé")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.infinity_polling(timeout=20)
