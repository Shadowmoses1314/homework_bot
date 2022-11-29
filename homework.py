
import logging
import sys
import time

import requests
import telegram
from http import HTTPStatus

from dotenv import load_dotenv
from exceptions import HTTPRequestError, CheckResponseError, ParseStatusError


load_dotenv()


PRACTICUM_TOKEN = 'y0_AgAAAAAx7TXCAAYckQAAAADVLFONqWQ9HDHzQ7O74cyXrZTcYtbFjdg'
TELEGRAM_TOKEN = '5923306530:AAE3M6k_-EKXtMKfJAQnhvl2bu2YHtqHLiY'
TELEGRAM_CHAT_ID = '569115418'

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """проверяет доступность переменных окружения необходимых для работы."""
    list_token = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ]
    return all(list_token)


def send_message(bot, message):
    """отправляет сообщение в Telegram."""
    try:
        logging.debug(f'Бот отправил сообщение {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(error)


def get_api_answer(timestamp):
    """создает и отправляет запрос к эндпоинту."""
    try:
        homework_statuses = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp},
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            raise CheckResponseError
    except requests.RequestException:
        logging.error('Request exception error')
    homeworks_json = homework_statuses.json()
    if not isinstance(homeworks_json, dict):
        raise HTTPRequestError
    return homeworks_json


def check_response(response):
    """Проверка полученного ответа от эндпоинта."""
    if not response:
        message = 'содержит пустой словарь.'
        logging.error(message)
        raise TypeError(message)

    if not isinstance(response, dict):
        message = 'имеет некорректный тип.'
        logging.error(message)
        raise TypeError(message)

    if 'homeworks' not in response:
        message = 'отсутствие ожидаемых ключей в ответе.'
        logging.error(message)
        raise TypeError(message)

    if not isinstance(response.get('homeworks'), list):
        message = 'формат ответа не соответствует.'
        logging.error(message)
        raise TypeError(message)

    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    if not homework.get('homework_name'):
        logging.warning('Отсутствует имя домашней работы.')
    else:
        homework_name = homework.get('homework_name')

    homework_status = homework.get('status')
    if 'status' not in homework:
        message = 'Отсутстует ключ homework_status.'
        logging.error(message)
        raise ParseStatusError(message)

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Недокументированный статус домашней работы'
        logging.error(message)
        raise KeyError(message)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    last_send = {
        'error': None,
    }
    if not check_tokens():
        logging.critical(
            'Отсутствует обязательная переменная окружения.\n'
            'Программа принудительно остановлена.'
        )
        exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logging.debug('Ответ API пуст: нет домашних работ.')
                break
            for homework in homeworks:
                message = parse_status(homework)
                if last_send.get(homework['homework_name']) != message:
                    send_message(bot, message)
                    last_send[homework['homework_name']] = message
                timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if last_send['error'] != message:
                send_message(bot, message)
                last_send['error'] = message
        else:
            last_send['error'] = None
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        stream=sys.stdout

    )
    main()
