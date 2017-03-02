#! /usr/bin/python 

import sys
import time
import os
import logging
import subprocess
from functools import wraps
from telegram.ext import Updater, CommandHandler,Job
import sqlite3


LIST_OF_ADMINS = [123456678]

def restricted(func):
	@wraps(func)
	def wrapped(bot, update, *args, **kwargs):
		try:
			user_id = update.message.from_user.id
		except (NameError, AttributeError):
			try:
				user_id = update.inline_query.from_user.id
			except (NameError, AttributeError):
				try:
					user_id = update.chosen_inline_result.from_user.id
				except (NameError, AttributeError):
					try: 
						user_id = update.callback_query.from_user.id
					except (NameError, AttributeError):
						print("No User ID available in update.")
						return
		if user_id not in LIST_OF_ADMINS:
			print("Unathorized access denied for {}.".format(update.message.chat_id))
			return
		return func(bot, update, *args, **kwargs)
	return wrapped

@restricted
def restart(bot, update):
	bot.sendMessage(update.message.chat_id, "Bot is restarting...")
	time.sleep(0.2)
	os.execl(sys.executable, sys.executable, *sys.argv)

def start(bot, update):
    update.message.reply_text('Hello there! If you need /help, just ask for it!')

def help(bot, update):
    update.message.reply_text('List of implemented commands: ')
    update.message.reply_text('/hello - Say hi ;)')
    update.message.reply_text('/set_interval seconds - Get sensor status in the given interval')
    update.message.reply_text('/unset_interval - Stop interval')
    update.message.reply_text('/status - Get current system status')
    update.message.reply_text('/restart - Restart bot[requires admin status]')
    update.message.reply_text('/photo - Get latest photo of the bot')
    update.message.reply_text('/help - List implemented commands')

def hello(bot, update):
    update.message.reply_text(
        'Hello {}'.format(update.message.from_user.first_name))

def current_sensor_data():
	conn = sqlite3.connect('/home/pi/devel/littlepibot/littlepibot.db')
	with conn:
		conn.row_factory = sqlite3.Row
		curs = conn.cursor()
		curs.execute("SELECT * FROM sensor_data WHERE tdate=date('now') ORDER BY time(ttime) DESC LIMIT 1;")
		data = curs.fetchone()
		temperature = float(data["temperature"])
		humidity = float(data["humidity"])
		readout = data["ttime"]
	conn.close()
	return{'temperature':temperature, 'humidity':humidity, 'readout':readout}

def status(bot, update):
	data = current_sensor_data()
	uptime = subprocess.check_output(['/usr/bin/uptime'])
	msg_text = "System uptime: {0}\nLast sensor readout: {1}\nTemperature: {2:.2f} *C\nHumidity: {3:.2f} %".format(uptime,data['readout'],data['temperature'], data['humidity'])
	update.message.reply_text(msg_text)

def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))

def send_data(bot, job):
	data = current_sensor_data()
	msg_text = "Last sensor readout: {0}\nTemperature: {1:.2f} *C\nHumidity: {2:.2f} %".format(data['readout'],data['temperature'], data['humidity'])
	bot.sendMessage(job.context, text=msg_text)


def set_interval(bot, update, args, job_queue, chat_data):
	chat_id = update.message.chat_id
	try:
		interval = int(args[0])
		if interval < 0:
			update.message.reply_text('Sorry, unable to go back to the future!')
			return
		job = Job(send_data, interval, repeat=True, context=chat_id)
		chat_data['job'] = job
		job_queue.put(job)
		update.message.reply_text('Interval has been set!')
		intervals = True
	except (IndexError, ValueError):
		update.message.reply_text('Usage: /set_interval seconds')

def unset_interval(bot, update, chat_data):
	global intervals
	if 'job' not in chat_data:
		update.message.reply_text('No interval set!')
		return
	job = chat_data['job']
	job.schedule_removal()
	del chat_data['job']
	update.message.reply_text('Interval unset!')
	intervals = False

def photo(bot,update,chat_data):
	update.message.reply_text('What are you looking at?')
	bot.sendPhoto(chat_id = update.message.chat_id,photo=open('botcam.jpg','rb'))
#
def main():
	# global stuff
	# Token from @botfather for the telegram bot API
	updater = Updater('TOKEN:HERE')
	# start logging
	logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
	logger = logging.getLogger(__name__)

	# Dispatcher for the telegram bot stuff
	dp = updater.dispatcher
	dp.add_handler(CommandHandler('restart', restart))
	dp.add_handler(CommandHandler('start', start))
	dp.add_handler(CommandHandler('hello', hello))
	dp.add_handler(CommandHandler('help', help))
	dp.add_handler(CommandHandler('status', status))

	dp.add_handler(CommandHandler('set_interval', set_interval,
												pass_args=True,
												pass_job_queue=True,
												pass_chat_data=True))
	dp.add_handler(CommandHandler('unset_interval', unset_interval,
												pass_chat_data=True))
	dp.add_handler(CommandHandler('photo', photo,
												pass_chat_data=True))
	dp.add_error_handler(error)

	# start telegram bot ;)
	updater.start_polling()
	updater.idle()

if __name__ == '__main__':
	main()
