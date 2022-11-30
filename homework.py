import logging
import sys
import time
import os

import requests
import telegram
from http import HTTPStatus

from dotenv import load_dotenv
from exceptions import HTTPRequestError, CheckResponseError, ParseStatusError


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)


def check_tokens():
    """Проверяем наличие токенов."""
    tokens = {
        'practicum_token': PRACTICUM_TOKEN,
        'telegram_token': TELEGRAM_TOKEN,
        'telegram_chat_id': TELEGRAM_CHAT_ID,
    }
    for key, value in tokens.items():
        if value is None:
            logger.critical(f'{key} отсутствует')
            return False
    logger.info('Токены найдены')
    return True


def send_message(bot, message):
    """отправляет сообщение в Telegram."""
    try:
        logger.debug(f'Бот отправил сообщение {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(error)


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
        logger.error('Request exception error')

    try:
        return homework_statuses.json()
    except ValueError:
        logger.error('Ошибка парсинга ответа из формата json')
        raise HTTPRequestError('Ошибка парсинга ответа из формата json')


def check_response(response):
    """Проверка полученного ответа от эндпоинта."""
    if not response:
        logger.error('содержит пустой словарь.')
        raise TypeError

    if 'homeworks' not in response:
        logger.error('отсутствие homeworks ключей в ответе.')
        raise TypeError

    if 'current_date' not in response:
        logger.error('отсутствие current_date ключей в ответе.')
        raise TypeError

    if not isinstance(response.get('homeworks'), list):
        logger.error('формат ответа не соответствует.')
        raise TypeError

    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if not homework.get('homework_name'):
        logger.warning('Отсутствует имя домашней работы.')
        raise NameError

    if 'status' not in homework:
        logger.error('Отсутстует ключ homework_status.')
        raise ParseStatusError

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status not in HOMEWORK_VERDICTS:
        logger.error('Недокументированный статус домашней работы')
        raise KeyError

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    last_send = {
        'error': None,
    }
    if not check_tokens():
        logger.critical(
            'Отсутствует обязательная переменная окружения.\n'
            'Программа принудительно остановлена.'
        )
        exit('Критическая ошибка(((')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if not len(homeworks):
                logger.debug('Ответ API пуст: нет домашних работ.')
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
        format='%(asctime)s [%(levelname)s] %(message)s [%(funcName)s]',
        stream=sys.stdout
    )

    main()
