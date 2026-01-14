"""
Управление токеном пользователя с автоматическим обновлением
"""
import time
import requests
from datetime import datetime, timedelta
from loguru import logger


class TokenManager:
    """
    Менеджер токенов с автоматическим обновлением

    Получает токен пользователя через Token Exchange и автоматически
    обновляет его за 5 минут до истечения срока действия.
    """

    def __init__(self, client_id, client_secret, user_id, token_lifetime=3600, refresh_before=300):
        """
        Инициализация менеджера токенов

        :param client_id: ID сервисного приложения
        :param client_secret: Секрет сервисного приложения
        :param user_id: ID пользователя
        :param token_lifetime: Время жизни токена в секундах (по умолчанию 3600 = 1 час)
        :param refresh_before: Обновлять токен за N секунд до истечения (по умолчанию 300 = 5 минут)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_id = str(user_id)
        self.token_lifetime = token_lifetime
        self.refresh_before = refresh_before

        self._token = None
        self._token_expires_at = None

        # Получаем токен при инициализации
        self._refresh_token()

    @property
    def token(self):
        """
        Возвращает актуальный токен, автоматически обновляя его при необходимости
        """
        # Проверяем, не истек ли токен или не пора ли его обновить
        if self._should_refresh():
            logger.debug("Токен истекает или истек, обновляем...")
            self._refresh_token()

        return self._token

    def _should_refresh(self):
        """
        Проверяет, нужно ли обновить токен

        :return: True если токен нужно обновить
        """
        if not self._token or not self._token_expires_at:
            return True

        # Обновляем токен за refresh_before секунд до истечения
        now = datetime.now()
        time_until_expiry = (self._token_expires_at - now).total_seconds()

        return time_until_expiry <= self.refresh_before

    def _refresh_token(self):
        """
        Получает новый токен через Token Exchange
        """
        url = "https://oauth.yandex.ru/token"

        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'subject_token': self.user_id,
            'subject_token_type': 'urn:yandex:params:oauth:token-type:uid'
        }

        try:
            logger.debug("Запрос нового токена через Token Exchange...")
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            self._token = result.get('access_token')
            expires_in = result.get('expires_in', self.token_lifetime)

            # Устанавливаем время истечения токена
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)

            logger.success(f"Токен получен. Действителен до: {self._token_expires_at.strftime('%H:%M:%S')}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении токена: {e}")
            raise

    def get_token_info(self):
        """
        Возвращает информацию о текущем токене

        :return: Словарь с информацией о токене
        """
        if not self._token or not self._token_expires_at:
            return {
                'has_token': False,
                'expires_at': None,
                'time_until_expiry': None
            }

        now = datetime.now()
        time_until_expiry = (self._token_expires_at - now).total_seconds()

        return {
            'has_token': True,
            'expires_at': self._token_expires_at,
            'time_until_expiry': time_until_expiry,
            'needs_refresh': self._should_refresh()
        }

    def force_refresh(self):
        """
        Принудительно обновляет токен
        """
        logger.info("Принудительное обновление токена...")
        self._refresh_token()
