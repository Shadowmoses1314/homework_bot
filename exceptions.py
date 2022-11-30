class HTTPRequestError(Exception):
    """Вывод Эндпоинт не доступен."""
    def __init__(self, response):
        message = (
            f'Эндпоинт {response.url} недоступен. '
            f'Код ответа API: {response.status_code}'
        )
        super().__init__(message)


class ParseStatusError(Exception):
    """Вывод API"""
    def __init__(self, text):
        """Вывод"""
        message = (
            f'Парсинг ответа API: {text}'
        )
        super().__init__(message)


class CheckResponseError(Exception):
    """Проверка API"""
    def __init__(self, response):
        """Вывод"""
        message = (
            f'Эндпоинт {response.url} недоступен.'
            f'Проверка ответа API: {response.status_code}'
            f'Проблемы с хедером {response.headers} '

        )
        super().__init__(message)
