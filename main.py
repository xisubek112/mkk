import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import sqlite3

TOKEN = '7318741358:AAFj_DyN2xPwCF3UWGq0J_VZKb8dq8jkohs'
ADMIN_ID = 7126212094

bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect('bb.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS schools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region TEXT,
    school TEXT,
    registered INTEGER DEFAULT 0,
    user_id INTEGER DEFAULT NULL,
    ball INTEGER DEFAULT 0
)''')
conn.commit()

regions = ["Toshkent shaxar", "Toshkent viloyati", "Namangan", "Andijon", "Farg'ona", "Samarqand", "Buxoro", "Xorazm", "Qashqadaryo", "Surxondaryo",
           "Navoiy", "Jizzax", "Sirdaryo"]

user_states = {}

@bot.message_handler(commands=['start'])
def start(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('🎯 Turnirga qatnashish')
    markup.add('ball🔄uc', "ball🔄sovg'a")
    bot.send_message(message.chat.id, "Salom! Asosiy menyu:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '🎯 Turnirga qatnashish')
def join_tournament(message):
    markup = InlineKeyboardMarkup()
    for reg in regions:
        markup.add(InlineKeyboardButton(reg, callback_data=f'reg_{reg}'))
    bot.send_message(message.chat.id, "Viloyatni tanlang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reg_'))
def select_region(call):
    region = call.data.split('_')[1]
    cursor.execute('SELECT school, registered FROM schools WHERE region=?', (region,))
    schools = cursor.fetchall()

    markup = InlineKeyboardMarkup()
    for school, registered in schools:
        text = f"{school} ({'✅ band' if registered else '🟢 bo‘sh'})"
        markup.add(InlineKeyboardButton(text, callback_data=f'sch_{region}_{school}'))

    bot.edit_message_text(f'{region}dagi maktabni tanlang:', call.message.chat.id, call.message.message_id,
                          reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('sch_'))
def select_school(call):
    user_id = call.from_user.id
    cursor.execute('SELECT * FROM schools WHERE user_id=?', (user_id,))
    if cursor.fetchone():
        bot.answer_callback_query(call.id, "Siz allaqachon ro'yxatdan o'tgansiz!", show_alert=True)
        return

    _, region, school = call.data.split('_', 2)
    msg = bot.send_message(call.message.chat.id, f"{school} oldida tushgan rasmingizni yuboring:")
    bot.register_next_step_handler(msg, lambda m: receive_photo(m, region, school))

def receive_photo(message, region, school):
    if message.photo:
        photo = message.photo[-1].file_id
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Tasdiqlash ✅', callback_data=f'approve_{message.chat.id}_{region}_{school}'))
        bot.send_photo(ADMIN_ID, photo, caption=f"🆕 @{message.from_user.username}\n🗺 {region}\n🏫 {school}", reply_markup=markup)
        bot.send_message(message.chat.id, "Ro'yxatdan o'tishingiz qabul qilindi. Admin tasdiqlashini kuting.")
    else:
        bot.send_message(message.chat.id, "Iltimos, rasm yuboring.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def approve_registration(call):
    _, user_id, region, school = call.data.split('_', 3)
    cursor.execute('UPDATE schools SET registered=1, user_id=? WHERE region=? AND school=?', (user_id, region, school))
    conn.commit()
    bot.send_message(user_id, "✅ Ro'yxatdan o'tdingiz!")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id == ADMIN_ID:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Maktab ➕', 'Xabar yuborish 📢', 'Ball ➕')
        markup.add("Maktab 🧾")
        bot.send_message(message.chat.id, 'Admin panel:', reply_markup=markup)

# Xabar yuborish funksiyasi
@bot.message_handler(func=lambda message: message.text == 'Xabar yuborish 📢' and message.chat.id == ADMIN_ID)
def send_message_region(message):
    markup = InlineKeyboardMarkup()
    for reg in regions:
        markup.add(InlineKeyboardButton(reg, callback_data=f'msgreg_{reg}'))
    bot.send_message(message.chat.id, "Viloyatni tanlang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('msgreg_'))
def send_message_school(call):
    region = call.data.split('_')[1]
    cursor.execute('SELECT school FROM schools WHERE region=?', (region,))
    schools = cursor.fetchall()
    markup = InlineKeyboardMarkup()
    for school in schools:
        markup.add(InlineKeyboardButton(school[0], callback_data=f'msgsch_{region}_{school[0]}'))
    bot.edit_message_text("Maktabni tanlang:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('msgsch_'))
def request_admin_message(call):
    _, region, school = call.data.split('_', 2)
    msg = bot.send_message(call.message.chat.id, "Yubormoqchi bo'lgan habaringizni yozing:")
    bot.register_next_step_handler(msg, lambda m: send_to_user(m, region, school))

def send_to_user(message, region, school):
    cursor.execute('SELECT user_id FROM schools WHERE region=? AND school=?', (region, school))
    result = cursor.fetchone()
    if result and result[0]:
        bot.send_message(result[0], f"📢 Admin xabari:\n\n{message.text}")
        bot.send_message(message.chat.id, "✅ Xabar yuborildi!")
    else:
        bot.send_message(message.chat.id, "❌ Bu maktabga hech kim ro'yxatdan o'tmagan.")

# UC sovg'a funksiyasi uchun ball🔄uc tugmasi
@bot.message_handler(func=lambda m: m.text == 'ball🔄uc')
def check_ball(message):
    user_id = message.chat.id
    cursor.execute('SELECT ball FROM schools WHERE user_id=?', (user_id,))
    row = cursor.fetchone()
    ball = row[0] if row else 0
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('60 UC (100 ball)', callback_data='uc_60'))
    markup.add(InlineKeyboardButton('120 UC (200 ball)', callback_data='uc_120'))
    markup.add(InlineKeyboardButton('180 UC (300 ball)', callback_data='uc_180'))
    markup.add(InlineKeyboardButton('325 UC (500 ball)', callback_data='uc_325'))
    bot.send_message(user_id, f"Sizning balingiz: {ball}\nSovg'ani tanlang:", reply_markup=markup)

uc_options = {
    'uc_60': 100,
    'uc_120': 200,
    'uc_180': 300,
    'uc_325': 500
}

@bot.callback_query_handler(func=lambda call: call.data.startswith('uc_'))
def ask_pubg_id(call):
    user_id = call.from_user.id
    code = call.data
    cost = uc_options[code]
    cursor.execute('SELECT ball FROM schools WHERE user_id=?', (user_id,))
    row = cursor.fetchone()
    current_ball = row[0] if row else 0

    if current_ball >= cost:
        user_states[user_id] = {'uc_code': code, 'cost': cost}
        msg = bot.send_message(user_id, "UC olish uchun PUBG ID raqamingizni kiriting:")
        bot.answer_callback_query(call.id)
        bot.register_next_step_handler(msg, confirm_uc_request)
    else:
        bot.answer_callback_query(call.id, "❌ Ball yetarli emas!", show_alert=True)


def confirm_uc_request(message):
    user_id = message.chat.id
    pubg_id = message.text
    if user_id in user_states:
        uc_code = user_states[user_id]['uc_code']
        cost = user_states[user_id]['cost']
        cursor.execute('UPDATE schools SET ball = ball - ? WHERE user_id=?', (cost, user_id))
        conn.commit()

        bot.send_message(user_id, "✅ So'rovingiz qabul qilindi. Tez orada UC yetkaziladi.")
        bot.send_message(
            ADMIN_ID,
            f"🎁 UC buyurtma:\n👤: <a href='tg://user?id={user_id}'>Foydalanuvchi</a>\n🎮PUBG ID: {pubg_id}\n🎮 Paket: {uc_code.replace('uc_', '')} UC",
            parse_mode='HTML'
        )

        del user_states[user_id]
    else:
        bot.send_message(user_id, "⛔ Xatolik yuz berdi. Qaytadan urinib ko'ring.")

# ... (avvalgi kod saqlanadi)

# Ball ➕ funksiyasi (admin uchun)
@bot.message_handler(func=lambda message: message.text == 'Ball ➕' and message.chat.id == ADMIN_ID)
def add_ball_start(message):
    markup = InlineKeyboardMarkup()
    for reg in regions:
        markup.add(InlineKeyboardButton(reg, callback_data=f'ballreg_{reg}'))
    bot.send_message(message.chat.id, "Ball qo'shish uchun viloyatni tanlang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('ballreg_'))
def add_ball_select_school(call):
    region = call.data.split('_')[1]
    cursor.execute('SELECT school FROM schools WHERE region=?', (region,))
    schools = cursor.fetchall()
    markup = InlineKeyboardMarkup()
    for school in schools:
        markup.add(InlineKeyboardButton(school[0], callback_data=f'ballsch_{region}_{school[0]}'))
    bot.edit_message_text("Maktabni tanlang:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('ballsch_'))
def add_ball_input(call):
    _, region, school = call.data.split('_', 2)
    user_states[call.from_user.id] = {'region': region, 'school': school}
    msg = bot.send_message(call.message.chat.id, f"Qancha ball qo'shmoqchisiz {school} maktabiga?")
    bot.register_next_step_handler(msg, process_ball_addition)

def process_ball_addition(message):
    admin_id = message.chat.id
    if admin_id not in user_states:
        bot.send_message(admin_id, "⛔ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        return
    try:
        amount = int(message.text)
        region = user_states[admin_id]['region']
        school = user_states[admin_id]['school']
        cursor.execute('UPDATE schools SET ball = ball + ? WHERE region=? AND school=?', (amount, region, school))
        conn.commit()
        bot.send_message(admin_id, f"✅ {school} maktabiga {amount} ball qo‘shildi.")
        del user_states[admin_id]
    except ValueError:
        bot.send_message(admin_id, "⛔ Iltimos, faqat raqam kiriting.")

# Maktab ➕ funksiyasi (admin uchun)
@bot.message_handler(func=lambda message: message.text == 'Maktab ➕' and message.chat.id == ADMIN_ID)
def add_school_start(message):
    markup = InlineKeyboardMarkup()
    for reg in regions:
        markup.add(InlineKeyboardButton(reg, callback_data=f'addreg_{reg}'))
    bot.send_message(message.chat.id, "Qaysi viloyatga maktab qo'shmoqchisiz?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('addreg_'))
def add_school_region(call):
    region = call.data.split('_')[1]
    user_states[call.from_user.id] = {'region': region}
    msg = bot.send_message(call.message.chat.id, f"{region} uchun yangi maktab nomini kiriting:")
    bot.register_next_step_handler(msg, save_school_name)

def save_school_name(message):
    admin_id = message.chat.id
    if admin_id not in user_states or 'region' not in user_states[admin_id]:
        bot.send_message(admin_id, "⛔ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        return
    region = user_states[admin_id]['region']
    school_name = message.text
    cursor.execute('INSERT INTO schools (region, school) VALUES (?, ?)', (region, school_name))
    conn.commit()
    bot.send_message(admin_id, f"✅ {region} viloyatiga '{school_name}' maktabi qo‘shildi.")
    del user_states[admin_id]

# Ball ➕ funksiyasi (admin uchun)
@bot.message_handler(func=lambda message: message.text == 'Ball ➕' and message.chat.id == ADMIN_ID)
def add_ball_start(message):
    markup = InlineKeyboardMarkup()
    for reg in regions:
        markup.add(InlineKeyboardButton(reg, callback_data=f'ballreg_{reg}'))
    bot.send_message(message.chat.id, "Ball qo'shish uchun viloyatni tanlang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('ballreg_'))
def add_ball_select_school(call):
    region = call.data.split('_')[1]
    cursor.execute('SELECT school FROM schools WHERE region=?', (region,))
    schools = cursor.fetchall()
    markup = InlineKeyboardMarkup()
    for school in schools:
        markup.add(InlineKeyboardButton(school[0], callback_data=f'ballsch_{region}_{school[0]}'))
    bot.edit_message_text("Maktabni tanlang:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('ballsch_'))
def add_ball_input(call):
    _, region, school = call.data.split('_', 2)
    user_states[call.from_user.id] = {'region': region, 'school': school}
    msg = bot.send_message(call.message.chat.id, f"Qancha ball qo'shmoqchisiz {school} maktabiga?")
    bot.register_next_step_handler(msg, process_ball_addition)

def process_ball_addition(message):
    admin_id = message.chat.id
    if admin_id not in user_states:
        bot.send_message(admin_id, "⛔ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        return
    try:
        amount = int(message.text)
        region = user_states[admin_id]['region']
        school = user_states[admin_id]['school']
        cursor.execute('UPDATE schools SET ball = ball + ? WHERE region=? AND school=?', (amount, region, school))
        conn.commit()
        bot.send_message(admin_id, f"✅ {school} maktabiga {amount} ball qo‘shildi.")
        del user_states[admin_id]
    except ValueError:
        bot.send_message(admin_id, "⛔ Iltimos, faqat raqam kiriting.")

# Sovg'a funksiyasi
@bot.message_handler(func=lambda m: m.text == "ball🔄sovg'a")
def check_gift(message):
    user_id = message.chat.id
    cursor.execute('SELECT ball FROM schools WHERE user_id=?', (user_id,))
    row = cursor.fetchone()
    ball = row[0] if row else 0
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Kuller (1000 ball)', callback_data='gift_kuller'))
    markup.add(InlineKeyboardButton('Redmi note 13 (2000 ball)', callback_data='gift_redmi'))
    bot.send_message(user_id, f"Sizning balingiz: {ball}\nSovg'ani tanlang:", reply_markup=markup)

gift_options = {
    'gift_kuller': ('Kuller', 1000),
    'gift_redmi': ('Redmi note 13', 2000),
}

@bot.callback_query_handler(func=lambda call: call.data.startswith('gift_'))
def gift_request(call):
    user_id = call.from_user.id
    gift_key = call.data
    gift_name, cost = gift_options[gift_key]
    cursor.execute('SELECT ball FROM schools WHERE user_id=?', (user_id,))
    row = cursor.fetchone()
    current_ball = row[0] if row else 0

    if current_ball >= cost:
        cursor.execute('UPDATE schools SET ball = ball - ? WHERE user_id=?', (cost, user_id))
        conn.commit()
        bot.send_message(user_id, f"✅ Siz '{gift_name}' sovg'asini tanladingiz. Adminlar tez orada siz bilan bog'lanadi.")
        bot.send_message(
            ADMIN_ID,
            f"🎁 Sovg'a buyurtma:\n👤 <a href='tg://user?id={user_id}'>Foydalanuvchi</a>\n🎁 Sovg'a: {gift_name}",
            parse_mode='HTML'
        )
    else:
        bot.answer_callback_query(call.id, "❌ Ball yetarli emas!", show_alert=True)


# Admin paneldan ro'yxatdan o'tgan foydalanuvchini ko'rish
@bot.message_handler(func=lambda message: message.text == 'Maktab 🧾' and message.chat.id == ADMIN_ID)
def view_registered_users_start(message):
    markup = InlineKeyboardMarkup()
    for reg in regions:
        markup.add(InlineKeyboardButton(reg, callback_data=f'viewreg_{reg}'))
    bot.send_message(message.chat.id, "Qaysi viloyatdagi maktablarni ko'rmoqchisiz?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('viewreg_'))
def view_region_schools(call):
    region = call.data.split('_')[1]
    cursor.execute('SELECT school FROM schools WHERE region=?', (region,))
    schools = cursor.fetchall()
    markup = InlineKeyboardMarkup()
    for school in schools:
        markup.add(InlineKeyboardButton(school[0], callback_data=f'viewschool_{region}_{school[0]}'))
    bot.edit_message_text(f"{region} viloyatidagi maktablar:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('viewschool_'))
def show_registered_user(call):
    _, region, school = call.data.split('_', 2)
    cursor.execute('SELECT user_id FROM schools WHERE region=? AND school=? AND registered=1', (region, school))
    row = cursor.fetchone()
    if row and row[0]:
        user_id = row[0]
        bot.send_message(call.message.chat.id, f"📋 {school} maktabidan ro'yxatdan o'tgan foydalanuvchi:\n👉 <a href='tg://user?id={user_id}'>Foydalanuvchi profili</a>", parse_mode='HTML')
    else:
        bot.send_message(call.message.chat.id, f"❌ {school} maktabidan hech kim ro'yxatdan o'tmagan.")


bot.infinity_polling()
