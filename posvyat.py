import telebot
import sqlite3
import threading
from threading import Timer
from telebot.types import *

conn = sqlite3.connect("posvyat.db", check_same_thread=False)
curs = conn.cursor()
curs.execute("CREATE TABLE IF NOT EXISTS coordinates (longitude INTEGER, latitude INTEGER, code TEXT UNIQUE, id INTEGER UNIQUE)")
curs.execute("CREATE TABLE IF NOT EXISTS current_stantion (id INTEGER, code TEXT, message_id_location INTEGER, message_id_text INTEGER)")

conn.commit()

bot = telebot.TeleBot('')
lock = threading.Lock()

@bot.message_handler(commands=['start_game'])
def start_game(message):
    bot.delete_message(message.chat.id,message.id)
    if not curs.execute(f'select * from current_stantion where id={message.chat.id}').fetchone():
        text_m_id = bot.send_message(message.chat.id, 'Привет! Вот главное сообщение, которое поможет не заблудиться между станциями:').id
        loc_m_id = bot.send_location(message.chat.id,0,0,4*3600).id
        print(text_m_id, loc_m_id)
        with lock:
            curs.execute(f'insert into current_stantion values({message.chat.id},"",{loc_m_id}, {text_m_id})')
            conn.commit()
@bot.message_handler(commands=['start'])
def start_game(message):
    #bot.delete_message(message.chat.id,message.id)
    pass

@bot.message_handler(commands=['this_is_the_command_to_clear_db'])
def start_game(message):
    with lock:
        curs.execute(f'drop table if exists current_stantion')
        curs.execute(f'drop table if exists coordinates')
        curs.execute("CREATE TABLE IF NOT EXISTS coordinates (longitude INTEGER, latitude INTEGER, code TEXT UNIQUE, id INTEGER UNIQUE)")
        curs.execute("CREATE TABLE IF NOT EXISTS current_stantion (id INTEGER, code TEXT, message_id_location INTEGER, message_id_text INTEGER)")
        conn.commit()
    pass


@bot.message_handler(func=lambda m: m.text.lower()=='dove')
def create_new_station(message):
    bot.send_message(message.chat.id, 'Введи кодовую фразу (если перепутаешь, не волнуйся - просто заполни все заново)')
    bot.register_next_step_handler_by_chat_id(message.chat.id, code_step)

@bot.message_handler(content_types=['text'])
def text_handler(message):
    bot.delete_message(message.chat.id,message.id)
    if curs.execute(f'select * from current_stantion where id={message.chat.id}').fetchone():
        with lock:
            curs.execute(f'update current_stantion set code="{message.text.lower()}" where id={message.chat.id}')
            conn.commit()

def code_step(message):
    if message.text:
        bot.send_message(message.chat.id, 'Теперь поделись своим местоположением. На 8 часов, чтоб хватило!\nЕсли не помнишь, как это сделать, вот порядок кнопок: скрепочка -> зеленая кнопочка -> еще раз зеленая кнопочка.')
        bot.register_next_step_handler_by_chat_id(message.chat.id, lambda m: location_step(m,message.text))
    else:
        bot.send_message(message.chat.id, 'Мне нужен текст')
        bot.register_next_step_handler_by_chat_id(message.chat.id, code_step)

     
def location_step(message, code):
    if message.location:
        with lock:
            curs.execute(f'delete from coordinates where id={message.chat.id}')
            curs.execute(f'insert into coordinates values({message.location.longitude},{message.location.latitude},"{code.lower()}", {message.chat.id})')
            conn.commit()
        bot.send_message(message.chat.id, 'Молодец, все готово!')
        
    else:
        bot.send_message(message.chat.id, 'Местоположением, бро')
        bot.register_next_step_handler_by_chat_id(message.chat.id, lambda m: location_step(m,code))

@bot.edited_message_handler(content_types=['location'])
def location_edited(message):
    with lock:
        curs.execute(f'update coordinates set longitude={message.location.longitude},latitude={message.location.latitude} where id={message.chat.id}')
        conn.commit()

def update_crew_messages():
    all = curs.execute('select * from current_stantion').fetchall()
    #print(all)
    for crew in all:
        latlng = curs.execute(f'select latitude, longitude from coordinates where code = "{crew[1]}"').fetchone()
        #print('yee')
        
        if latlng:
            #print('ed',latlng[0], latlng[1], crew[0], crew[2])
            try:
                bot.edit_message_live_location(latlng[0], latlng[1], crew[0], crew[2])
                bot.edit_message_text(crew[1].capitalize()+':', crew[0],crew[3])
            except:
                pass
    t = Timer(5, update_crew_messages)
    t.start()
update_crew_messages()
bot.polling(none_stop=True)
print('hey')
