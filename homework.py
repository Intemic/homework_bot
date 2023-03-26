import logging
from http import HTTPStatus
import os
import requests
import time

from dotenv import load_dotenv
import telegram 
from telegram.error import TelegramError

from exceptions import ErrorEnv, ErrorConnection, ErrorResponseData, ErrorSend, ErrorStatus

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

home_work_state = {}

def check_tokens():
    """Проверим определены ли все необходимые переменные."""
    if PRACTICUM_TOKEN is None:
        raise ErrorEnv('Не определена переменная: "PRACTICUM_TOKEN"')
    
    if TELEGRAM_TOKEN is None:
        raise ErrorEnv('Не определена переменная: "TELEGRAM_TOKEN"')

    if TELEGRAM_CHAT_ID is None:
        raise ErrorEnv('Не определена переменная: "TELEGRAM_CHAT_ID"')


def send_message(bot: telegram.Bot, message: str):
    """Отправка сообщения."""
    try: 
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Отправлено сообщение : {message}')
    except TelegramError as error:
        logger.error(error)
        raise ErrorSend('Не удалось отправить сообщение')


def get_api_answer(timestamp: int) -> dict:
    """Получаем данные от сервера."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
           raise Exception('Ошибка подключения') 
        return response.json()
    except Exception as error:
         logger.error(error)
         raise ErrorConnection('Ошибка подключения')


def check_response(response: dict):
    """Проверяем соответствие ответа сервера типу данных."""
    if not type(response) is dict:
        raise ErrorResponseData()
    
    home_works = response.get('homeworks')
    if home_works is None or not type(home_works) is list:
        raise ErrorResponseData()

    if response.get('current_date') is None:
        raise ErrorResponseData()
    
    if len(home_works) > 0:
        if home_works[0].get('status') is None:
            raise ErrorResponseData()
        if home_works[0].get('homework_name') is None:
            raise ErrorResponseData()


def parse_status(homework) -> str:
    """Считываем статус работы."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise ErrorResponseData()

    try: 
        verdict = HOMEWORK_VERDICTS[homework.get('status')]
    except KeyError:
        raise ErrorStatus('Не корректный статус работы')

    # проверим что статус изменился
    if not homework_name in home_work_state:
        home_work_state[homework_name] = verdict
    elif home_work_state[homework_name] != verdict:    
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    try:
       check_tokens() 
    except ErrorEnv as error:
       logger.critical(error) 
       return None

    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    while True:
        timestamp = int(time.time())
        try:
            answer = get_api_answer(timestamp)
            check_response(answer)
            text_status = parse_status(answer[0].get('homeworks'))
            if text_status:
                send_message(text_status)


        except Exception as error:
            message = f'Сбой в работе программы: {error}'

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()