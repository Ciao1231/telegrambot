#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time, sys, os, os.path, re, sqlite3, json
from  threading import Timer
om_th=None
## if sys.version_info.major == 2:
## 	print("REQUIRED PYTHON 3+")
## 	sys.exit(1)

if sys.argv[-1].lower() == "stop" and os.path.isfile("vkonline.pid"): (os.kill(int(open("vkonline.pid").read()), -9),
print("Process killed"), sys.exit(0))

open("vkonline.pid", "w").write(str(os.getpid()))

"""
Telegram Bot VK Online checker
(C) 2019 alekssamos
"""

"""
http://qaru.site/questions/1440331/use-pip-installuninstall-inside-a-python-script
"""
try:
	import telebot
except ImportError:
	os.system("pip install pytelegrambotapi")
	try: import telebot
	except ImportError:
		os.system("easy_install pip && pip install pytelegrambotapi")
	try:
		import telebot
	except ImportError:
		try:
			from pip import main as pipmain
		except ImportError:
			from pip._internal import main as pipmain
		pipmain(['install', 'pytelegrambotapi'])
		try:
			import telebot
		except ImportError:
			print("pip install pytelegrambotapi")
			sys.exit(2)
from telebot import util
import requests

with sqlite3.connect("vkonline.db") as conn:
	cursor = conn.cursor()
	cursor.execute("""CREATE TABLE IF NOT EXISTS targets
	(CHAT_ID INTEGER, title TEXT, vklink TEXT,
	laststatus TEXT DEFAULT Offline, lasttime INTEGER DEFAULT 0)
	""")
	cursor.execute("""CREATE TABLE IF NOT EXISTS timezones
	(CHAT_ID INTEGER, h INTEGER DEFAULT 0, m INTEGER DEFAULT 0)
	""")

try: inp = raw_input
except NameError: inp = input
try:
	bot_token = sys.argv[1]
except IndexError:
	try:
		bot_token = os.environ["voc_token"]
	except KeyError:
		try: bot_token = inp("Введите токен Telegram:\n").strip()
		except KeyboardInterrupt: sys.exit(0)
try:
	vk_token = sys.argv[2]
except IndexError:
	try:
		vk_token = os.environ["voc_vktoken"]
	except KeyError:
		try: vk_token = inp("Введите токен VK:\n").strip()
		except KeyboardInterrupt: sys.exit(0)
bot = telebot.TeleBot(bot_token)
try: gm = bot.get_me()
except telebot.apihelper.ApiException:
	print("Не правильный токен Telegram!")
	sys.exit(1)
try:
	json.loads(requests.get("https://api.vk.com/method/users.get?user_ids={0}&fields=online&v=5.80&access_token={1}".format("", vk_token)).content.decode("UTF8"))["response"]
except KeyError:
	print("Не правильный токен VK!")
	sys.exit(1)
print("""Бот {0} успешно  запущен!
@{1} https://t.me/{1}""".format(gm.first_name, gm.username))
keyboard1 = telebot.types.ReplyKeyboardMarkup(True, False)
keyboard1.row("Добавить", "Удалить", "Список целей", "Время")

def vk_user_is_online(vkid):
	vkid=vkid.split('/')[-1]
	try:
		resp = requests.get("https://api.vk.com/method/users.get?user_ids={0}&fields=online&v=5.80&access_token={1}".format(vkid, vk_token)).content.decode("UTF8")
		return json.loads(resp)["response"][0]["online"]
	except:
		return False

def online_monitor_start(seconds=30):
	try:
		targets = getTargets()
		if not targets: return False
		for target in targets:
			chat_id, title, vklink, old_pstatus, lasttime = target
			# headers = {"Cookie":"remixlang=0;", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:69.0) Gecko/20100101 Firefox/97A0"}
			# resp = requests.get(vklink, headers=headers).content.decode("CP1251")
			# rr = re.search(r"""<div class="profile_online_lv">(.*?)</div>""", resp)
			# if not rr: return False
			t = getTime(chat_id)
			h, m = (t.tm_hour, t.tm_min)
			# pstatus = rr.group(1)
			# pstatus = re.sub("<.*?>", "", pstatus).strip()
			is_online = vk_user_is_online(vklink)
			time.sleep(0.5)
			if is_online: pstatus = "Online"
			else: pstatus = "Offline"
			old_is_online = targetGetStatus(chat_id, title, vklink)[0] in "Online"
			targetSetStatus(chat_id, title, vklink, pstatus)
			if old_is_online:
				if not is_online:
					bot.send_message(chat_id, "#{0} оффлайн {1}:{2}".format(title, h, m))
			if not old_is_online:
				if is_online:
					bot.send_message(chat_id, "#{0} онлайн {1}:{2}".format(title, h, m))
	except: pass
	finally:
		om_th = Timer(seconds, online_monitor_start, [seconds])
		om_th.start()

def online_monitor_stop():
	om_th.cancel()

def targetSetStatus(chat_id, title, vklink, pstatus):
	if title == "" or vklink == "": return False
	with sqlite3.connect("vkonline.db") as conn:
		try:
			cursor = conn.cursor()
			target = (pstatus, time.time(), chat_id, title, vklink)
			cursor.execute("UPDATE targets SET laststatus=?, lasttime=? WHERE chat_id=? AND title=? AND vklink=?", target)
			conn.commit()
			return True
		except: return False

def targetGetStatus(chat_id, title, vklink):
	with sqlite3.connect("vkonline.db") as conn:
		try:
			cursor = conn.cursor()
			sql = "SELECT laststatus, lasttime FROM targets WHERE chat_id=? AND title=? AND vklink=?"
			cursor.execute(sql, [(chat_id), (title), (vklink)])
			return cursor.fetchone()
		except: return False

def addTarget(chat_id, title, vklink):
	if title == "" or vklink == "": return False
	if getTargetByTitle(chat_id, title) or getTargetByVklink(chat_id, vklink):
		return True
	with sqlite3.connect("vkonline.db") as conn:
		try:
			cursor = conn.cursor()
			if title == "":
				title = getTargetByVklink(chat_id, "")[1]
				target = (vklink, title, "")
				cursor.execute("UPDATE targets SET vklink=? WHERE chat_id=? AND vklink=?", target)
				conn.commit()
				return True
			target = [(chat_id, title, vklink, "", 0)]
			cursor.executemany("INSERT INTO targets VALUES (?,?,?,?,?)", target)
			conn.commit()
		except: return False
		return True

def getTargets(chat_id=None):
	with sqlite3.connect("vkonline.db") as conn:
		try:
			cursor = conn.cursor()
			if chat_id==None:
				sql = "SELECT * FROM targets"
				cursor.execute(sql)
			else:
				sql = "SELECT * FROM targets WHERE chat_id=?"
				cursor.execute(sql, [(chat_id)])
			return cursor.fetchall()
		except: return False

def getTargetByTitle(chat_id, title):
	with sqlite3.connect("vkonline.db") as conn:
		try:
			cursor = conn.cursor()
			sql = "SELECT * FROM targets WHERE chat_id=? AND title=?"
			cursor.execute(sql, [(chat_id), (title)])
			return cursor.fetchone()
		except: return False

def getTargetByVklink(chat_id, vklink):
	with sqlite3.connect("vkonline.db") as conn:
		try:
			cursor = conn.cursor()
			sql = "SELECT * FROM targets WHERE chat_id=? AND vklink=?"
			cursor.execute(sql, [(chat_id), (vklink)])
			return cursor.fetchone()
		except: return False

def deleteTargetByTitle(chat_id, title):
	with sqlite3.connect("vkonline.db") as conn:
		try:
			cursor = conn.cursor()
			sql = "DELETE FROM targets WHERE chat_id=? AND title=?"
			cursor.execute(sql, [(chat_id), (title)])
			conn.commit()
			return True
		except: return False

def deleteTargetByVklink(chat_id, vklink):
	with sqlite3.connect("vkonline.db") as conn:
		try:
			cursor = conn.cursor()
			sql = "DELETE FROM targets WHERE chat_id=? AND vklink=?"
			cursor.execute(sql, [(chat_id), (vklink)])
			conn.commit()
			return True
		except: return False


def getTime(chat_id):
	with sqlite3.connect("vkonline.db") as conn:
		try:
			cursor = conn.cursor()
			sql = "SELECT h, m FROM timezones WHERE chat_id=?"
			cursor.execute(sql, [(chat_id)])
			h, m = cursor.fetchone()
		except: return False
		h = h * 60 * 60
		m = m * 60
		return time.gmtime( time.time() + h + m )

def setTimeZone(chat_id, msg):
	msg = re.sub(r'[^0-9:+-]', '', msg)
	try: h, m = msg.split(':')
	except ValueError: return False
	with sqlite3.connect("vkonline.db") as conn:
		try:
			cursor = conn.cursor()
			if getTime(chat_id):
				tz = (int(h[0]+h[1:]), int(h[0]+m), chat_id)
				sql = "UPDATE timezones SET h=?, m=? WHERE chat_id=?"
				cursor.execute(sql, tz)
			else:
				tz = [(chat_id, int(h[0]+h[1:]), int(h[0]+m))]
				sql = "INSERT INTO timezones VALUES (?,?,?)"
				cursor.executemany(sql, tz)
			conn.commit()
		except: return False
	return True


def setTimeZoneCallback(message):
	chat_id = message.chat.id
	text = message.text
	if not setTimeZone(chat_id, text):
		markup = telebot.types.ForceReply(selective=True)
		msg = bot.send_message(chat_id,
		'Не получилось. Введите ещё раз. Формат:'+"\n"+
		'+-час:минута  +3:00 или -3:30',
		reply_markup=markup)
		bot.register_next_step_handler(msg, setTimeZoneCallback)
	else:
		bot.send_message(chat_id,
		'Установлено. /currenttime - проверить текущее время'+"\n"+
		'Теперь нажмите кнопку Добавить   /add', reply_markup=keyboard1)


@bot.message_handler(commands=['start'])
def start_message(message):
	markup = telebot.types.ForceReply(selective=True)
	msg = bot.send_message(message.chat.id,
	'Введи свой часовой пояс. '+"\n"+
	'Например: +3:00 или -3:30',
	reply_markup=markup)
	bot.register_next_step_handler(msg, setTimeZoneCallback)

@bot.message_handler(commands=['currenttime'])
def currenttime_message(message):
	chat_id = message.chat.id
	t = getTime(chat_id)
	if not t:
		bot.send_message(message.chat.id, "Не получилось. Возможно, часовой пояс не установлен.")
		return False
	h, m = (t.tm_hour, t.tm_min)
	if h <= 9: ct = "0" + str(h)
	else: ct = str(h)
	if m <= 9: ct = ct + ":0" + str(m)
	else: ct = ct + ":" + str(m)
	bot.send_message(message.chat.id, "#currenttime Время: "+ct, reply_markup=keyboard1)

@bot.message_handler(commands=['list'])
def listTargets_message(message):
	chat_id = message.chat.id
	targets = getTargets(chat_id)
	if not targets:
		bot.send_message(chat_id, "Здесь ничего нет. Сначала добавьте. /add", reply_markup=keyboard1)
		return False
	msg=""
	for target in targets:
		msg = msg +"{0} {1} {2}".format(target[1], target[2], target[3]) + "\n"
	splitted_text = util.split_string(msg, 4000)
	for text in splitted_text:
		bot.send_message(chat_id, text, reply_markup=keyboard1, disable_web_page_preview=True)

@bot.message_handler(commands=['del', 'delete'])
def delTarget_message(message):
	chat_id = message.chat.id
	markup = telebot.types.ForceReply(selective=True)
	msg = bot.send_message(chat_id, "введите название цели или ссылку для удаления", reply_markup=markup)
	bot.register_next_step_handler(msg, targetDelete)

def targetDelete(message):
	chat_id = message.chat.id
	text = message.text
	if not "vk.com" in text:
		text = re.sub(r'[^0-9a-zA-Zа-яёА-ЯЁ]', '_', text)
	else:
		text = text.strip().lower().replace("http:", "https:").replace("m.vk.", "vk.")
		if text.startswith("vk."): text = "https://"+text
	if not getTargetByTitle(chat_id, text) and not getTargetByVklink(chat_id, text):
		bot.send_message(chat_id, "Такая цель не существует.", reply_markup=keyboard1)
		return False
	if deleteTargetByTitle(chat_id, text) or deleteTargetByVklink(chat_id, text):
		bot.send_message(chat_id, "Цель удалена!", reply_markup=keyboard1)
	else:
		bot.send_message(chat_id, "Ошибка при удалении.", reply_markup=keyboard1)

@bot.message_handler(commands=['add'])
def add_message(message):
	chat_id = message.chat.id
	if not getTime(chat_id):
		bot.send_message(chat_id, "Сначала укажите часовой пояс. /start")
		return False
	markup = telebot.types.ForceReply(selective=True)
	msg = bot.send_message(chat_id, "введите название цели", reply_markup=markup)
	bot.register_next_step_handler(msg, targetSetTitle)

def targetSetTitle(message):
	chat_id = message.chat.id
	text = message.text
	text = re.sub(r'[^0-9a-zA-Zа-яёА-ЯЁ]', '_', text)
	markup = telebot.types.ForceReply(selective=True)
	if len(text)<2:
		msg = bot.send_message(chat_id, "Название слишком короткое", reply_markup=markup)
		bot.register_next_step_handler(msg, targetSetTitle)
		return False
	if getTargetByTitle(chat_id, text):
		msg = bot.send_message(chat_id, "Такое название уже есть", reply_markup=markup)
		bot.register_next_step_handler(msg, targetSetTitle)
		return False
	ud[chat_id] = text
	msg = bot.send_message(chat_id, "введите ссылку", reply_markup=markup)
	bot.register_next_step_handler(msg, targetSetVklink)

def targetSetVklink(message):
	chat_id = message.chat.id
	text = message.text.strip().lower().replace("http:", "https:").replace("m.vk.", "vk.")
	if text.startswith("vk."): text = "https://"+text
	markup = telebot.types.ForceReply(selective=True)
	if not "https://vk.com/" in text:
		msg = bot.send_message(chat_id, "Формат: vk.com/id1", reply_markup=markup, disable_web_page_preview=True)
		bot.register_next_step_handler(msg, targetSetVklink)
		return False
	if getTargetByVklink(chat_id, text):
		msg = bot.send_message(chat_id, "Такая ссылка уже есть", reply_markup=markup, disable_web_page_preview=True)
		bot.register_next_step_handler(msg, targetSetVklink)
		return False
	if addTarget(chat_id, ud[chat_id], text):
		bot.send_message(chat_id, "цель добавлена", reply_markup=keyboard1)
	else:
		bot.send_message(chat_id, "Произошла ошибка. Повторите запрос позднее.", reply_markup=keyboard1)
	del ud[chat_id]


@bot.message_handler(content_types=['text'])
def text_message(message):
	chat_id = message.chat.id
	text = message.text
	if "Добавить" in text:
		add_message(message)
	if "Удалить" in text:
		delTarget_message(message)
	if "Список целей" in text:
		listTargets_message(message)
	if "Время" in text:
		currenttime_message(message)

ud={}

online_monitor_start(10)
bot.enable_save_next_step_handlers(delay=2)
bot.load_next_step_handlers()
bot.infinity_polling()
