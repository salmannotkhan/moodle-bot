from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    Filters
)
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import logging
import json
import time
import re
import os

URL = 'https://mca.glsmoodle.in'
LOGIN_URL = f'{URL}/login/index.php'
sesskey_regex = r'(?<="sesskey":").+(?=","sessiontimeout")'
headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
}
creds = {
    'anchor': '',
    'username': '',
    'password': ''
}

UNAME, PWD = range(2)


def assignments(update, context):
    if 'logged_in' not in context.user_data.keys():
        message = 'Login first by using /login in bot PM'
    else:
        creds['username'] = context.user_data['username']
        creds['password'] = context.user_data['password']
        with requests.session() as s:
            login_page = s.get(LOGIN_URL)
            soup = BeautifulSoup(login_page.text, 'html.parser')
            headers['Cookie'] = f'MoodleSession={s.cookies.get("MoodleSession")}'
            token = soup.find('input', {'name': 'logintoken'}).attrs['value']
            creds['logintoken'] = token

            s.post(LOGIN_URL,
                allow_redirects=False,
                data=creds,
                headers=headers)
            headers['Cookie'] = f'MoodleSession={s.cookies.get("MoodleSession")}'

            data = s.get(URL)
            soup = BeautifulSoup(data.text, 'html.parser')
            sesskey = re.findall(sesskey_regex, str(soup))[0]

            action = 'core_calendar_get_action_events_by_timesort'
            params = {
                'sesskey': sesskey,
                'info': action
            }

            today = int(datetime.today().timestamp())

            headers['X-Requested-With'] = 'XMLHttpRequest'
            payload = [{
                'index': 0,
                'methodname': action,
                'args': {
                    'limitnum': 11,
                    'timesortfrom': today,
                    'limittononsuspendedevents': True
                }
            }]
            data = s.post(f'{URL}/lib/ajax/service.php',
                        params=params,
                        data=json.dumps(payload),
                        headers=headers)
            message = data.json()
    update.message.reply_text(message)


logging.basicConfig(format='%(asctime)s-%(name)s-%(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def start(update, context):
    update.message.reply_text('Moodle is shit')


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def login(update, context):
    update.message.reply_text('Enter your moodle username')
    return UNAME


def uname(update, context):
    context.user_data['username'] = update.message.text
    update.message.reply_text('Enter your moodle password')
    return PWD


def pwd(update, context):
    context.user_data['password'] = update.message.text
    creds['username'] = context.user_data['username']
    creds['password'] = context.user_data['password']
    with requests.session() as s:
        login_page = s.get(LOGIN_URL)
        soup = BeautifulSoup(login_page.text, 'html.parser')
        headers['Cookie'] = f'MoodleSession={s.cookies.get("MoodleSession")}'
        token = soup.find('input', {'name': 'logintoken'}).attrs['value']
        creds['logintoken'] = token

        s.post(LOGIN_URL,
               allow_redirects=False,
               data=creds,
               headers=headers)
        headers['Cookie'] = f'MoodleSession={s.cookies.get("MoodleSession")}'
        data = s.get(LOGIN_URL + '?testsession=461',
                     allow_redirects=False,
                     headers=headers)
        if data.status_code == 303:
            message = 'Login Successful! Now you can use /assignments command'
            context.user_data['logged_in'] = True
        else:
            message = 'Login Failed!!! Check username and password again!'
            context.user_data['logged_in'] = False
    update.message.reply_text(message)
    return ConversationHandler.END


def cancel(update, context):
    update.message.reply_text('Bye')


def main():
    updater = Updater(os.environ['API_KEY'])

    dp = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('login', login)],
        states={
            UNAME: [MessageHandler(Filters.text, uname)],
            PWD: [MessageHandler(Filters.text, pwd)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(CommandHandler("start", start))

    dp.add_handler(CommandHandler("assignments", assignments))
    dp.add_handler(conv_handler)
    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()

print(time.time()-start)
