# Документация: Получение доступа к диску пользователя Яндекс 360

## Описание проблемы

При работе с Яндекс 360 для бизнеса возникает задача получения доступа к личному диску пользователя организации. Административный токен дает доступ только к общему диску организации, но не к личным дискам пользователей.

**Решение:** Использование метода **Token Exchange** для получения временного токена пользователя.

---

## Предварительные требования

### 1. Сервисное приложение в Яндекс 360

Вам нужно создать сервисное приложение с правами на доступ к диску:

1. Перейдите в админ-панель Яндекс 360
2. Откройте раздел **"Безопасность" → "Сервисные приложения"**
3. Найдите или создайте приложение с правами:
   - `cloud_api:disk.read` - чтение диска
   - `cloud_api:disk.write` - запись на диск (опционально)

### 2. Получение учетных данных приложения

Для сервисного приложения вам понадобятся:
- **Client ID** - идентификатор приложения
- **Client Secret** - секретный ключ приложения

**Как получить:**
1. В списке сервисных приложений API Яндекс 360: `GET https://api360.yandex.net/security/v1/org/{org_id}/service_applications`
2. Используйте административный токен для авторизации
3. В ответе найдите приложение с нужными правами и сохраните его `id`

**Пример ответа:**
```json
{
  "applications": [
    {
      "id": "bdb90dee90fe49329c24535283606260",
      "scopes": [
        "cloud_api:disk.read",
        "cloud_api:disk.info"
      ]
    }
  ]
}
```

### 3. ID пользователя

Получите ID пользователя, к диску которого нужен доступ:

```bash
GET https://api360.yandex.net/directory/v1/org/{org_id}/users?email=user@domain.com
Authorization: OAuth {admin_token}
```

**Ответ:**
```json
{
  "users": [
    {
      "id": "1130000057842996",
      "email": "tn@imprice.ai",
      "name": {
        "first": "Nikita",
        "last": "Tsukanov"
      }
    }
  ]
}
```

---

## Метод 1: Token Exchange (Рекомендуется)

### Описание

Token Exchange (RFC 8693) позволяет обменять учетные данные сервисного приложения на временный токен пользователя.

### Запрос

**Endpoint:** `https://oauth.yandex.ru/token`

**Method:** `POST`

**Content-Type:** `application/x-www-form-urlencoded`

### Параметры

| Параметр | Обязательный | Описание |
|----------|-------------|----------|
| `grant_type` | Да | `urn:ietf:params:oauth:grant-type:token-exchange` |
| `client_id` | Да | Client ID сервисного приложения |
| `client_secret` | Да | Client Secret сервисного приложения |
| `subject_token` | Да | ID или email пользователя |
| `subject_token_type` | Да | `urn:yandex:params:oauth:token-type:uid` или `urn:yandex:params:oauth:token-type:email` |

### Пример 1: По User ID

```bash
curl --location --request POST 'https://oauth.yandex.ru/token' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=urn:ietf:params:oauth:grant-type:token-exchange' \
  --data-urlencode 'client_id=bdb90dee90fe49329c24535283606260' \
  --data-urlencode 'client_secret=8ca3671933544d7d990045e7d512aa0d' \
  --data-urlencode 'subject_token=1130000057842996' \
  --data-urlencode 'subject_token_type=urn:yandex:params:oauth:token-type:uid'
```

### Пример 2: По Email

```bash
curl --location --request POST 'https://oauth.yandex.ru/token' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=urn:ietf:params:oauth:grant-type:token-exchange' \
  --data-urlencode 'client_id=bdb90dee90fe49329c24535283606260' \
  --data-urlencode 'client_secret=8ca3671933544d7d990045e7d512aa0d' \
  --data-urlencode 'subject_token=tn@imprice.ai' \
  --data-urlencode 'subject_token_type=urn:yandex:params:oauth:token-type:email'
```

### Успешный ответ

**HTTP Status:** `200 OK`

```json
{
  "access_token": "2.1130000057842996.997486.1768381487.1768377887976.1.0.11609667.BSFzzc69Js6_ATwI...",
  "expires_in": 3600,
  "issued_token_type": "urn:ietf:params:oauth:token-type:access_token",
  "token_type": "bearer"
}
```

**Важно:**
- `access_token` - токен для доступа к диску пользователя
- `expires_in` - срок действия в секундах (обычно 3600 = 1 час)
- Токен нужно обновлять каждый час

---

## Использование токена

### 1. Получение списка папок

```bash
GET https://cloud-api.yandex.net/v1/disk/resources?path=/
Authorization: OAuth {access_token}
```

**Пример ответа:**
```json
{
  "_embedded": {
    "items": [
      {
        "name": "Клиенты",
        "type": "dir",
        "path": "disk:/Клиенты"
      },
      {
        "name": "Дизайны",
        "type": "dir",
        "path": "disk:/Дизайны"
      }
    ]
  }
}
```

### 2. Доступ к конкретной папке

```bash
GET https://cloud-api.yandex.net/v1/disk/resources?path=/Клиенты&limit=100
Authorization: OAuth {access_token}
```

### 3. Скачивание файла

**Шаг 1:** Получить ссылку на скачивание

```bash
GET https://cloud-api.yandex.net/v1/disk/resources/download?path=/Клиенты/Папка/Файл.docx
Authorization: OAuth {access_token}
```

**Ответ:**
```json
{
  "href": "https://downloader.disk.yandex.ru/...",
  "method": "GET",
  "templated": false
}
```

**Шаг 2:** Скачать файл по ссылке

```bash
GET {href из предыдущего ответа}
```

---

## Код на Python

### Установка зависимостей

```bash
pip install requests python-dotenv
```

### Полный пример

```python
import os
import requests
from pathlib import Path
from dotenv import load_dotenv


def get_user_token(client_id, client_secret, user_id):
    """Получает токен пользователя через Token Exchange"""
    url = "https://oauth.yandex.ru/token"

    data = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
        'client_id': client_id,
        'client_secret': client_secret,
        'subject_token': str(user_id),
        'subject_token_type': 'urn:yandex:params:oauth:token-type:uid'
    }

    response = requests.post(url, data=data)

    if response.status_code == 200:
        result = response.json()
        return result.get('access_token')
    else:
        raise Exception(f"Ошибка получения токена: {response.status_code} - {response.text}")


def list_folders(token, path="/"):
    """Получает список папок на диске"""
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {"Authorization": f"OAuth {token}"}
    params = {"path": path, "limit": 1000}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        items = data.get("_embedded", {}).get("items", [])
        folders = [item for item in items if item.get("type") == "dir"]
        return folders
    else:
        raise Exception(f"Ошибка: {response.status_code} - {response.text}")


def download_file(token, file_path, local_path):
    """Скачивает файл с диска"""
    # Шаг 1: Получаем ссылку на скачивание
    url = "https://cloud-api.yandex.net/v1/disk/resources/download"
    headers = {"Authorization": f"OAuth {token}"}
    params = {"path": file_path}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise Exception(f"Ошибка получения ссылки: {response.status_code}")

    download_url = response.json().get("href")

    # Шаг 2: Скачиваем файл
    file_response = requests.get(download_url, stream=True)

    if file_response.status_code != 200:
        raise Exception(f"Ошибка скачивания: {file_response.status_code}")

    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    with open(local_path, 'wb') as f:
        for chunk in file_response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return local_path


def main():
    # Конфигурация
    CLIENT_ID = "bdb90dee90fe49329c24535283606260"
    CLIENT_SECRET = "8ca3671933544d7d990045e7d512aa0d"
    USER_ID = "1130000057842996"

    # Получаем токен пользователя
    print("Получение токена пользователя...")
    token = get_user_token(CLIENT_ID, CLIENT_SECRET, USER_ID)
    print(f"Токен получен: {token[:20]}...")

    # Получаем список папок
    print("\nПолучение списка папок...")
    folders = list_folders(token, "/")

    print(f"Найдено папок: {len(folders)}\n")
    for folder in folders:
        print(f"  - {folder.get('name')}")

    # Скачиваем файл
    print("\nСкачивание файла...")
    file_path = "/Клиенты/Юн.Индастриал/UInd. Предварительное предложение.docx"
    local_path = "downloads/test.docx"

    result = download_file(token, file_path, local_path)
    print(f"Файл скачан: {result.absolute()}")


if __name__ == "__main__":
    main()
```

---

## Настройка через .env

### Файл .env

```bash
# Административный токен (для Directory API)
YANDEX_ADMIN_TOKEN=y0_xxx...

# ID организации
YANDEX_ORG_ID=7140966

# Сервисное приложение
ClientID=bdb90dee90fe49329c24535283606260
Client_secret=8ca3671933544d7d990045e7d512aa0d

# Пользователь
USER_ID=1130000057842996
USER_EMAIL=tn@imprice.ai
```

### Использование в коде

```python
from dotenv import load_dotenv
import os

load_dotenv()

CLIENT_ID = os.getenv("ClientID")
CLIENT_SECRET = os.getenv("Client_secret")
USER_ID = os.getenv("USER_ID")
```

---

## Автоматическое обновление токена

Токен действителен 1 час. Для долгих операций нужно автоматически обновлять токен:

```python
import time
from datetime import datetime, timedelta


class TokenManager:
    def __init__(self, client_id, client_secret, user_id):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_id = user_id
        self.token = None
        self.expires_at = None

    def get_token(self):
        """Возвращает действующий токен, обновляет при необходимости"""
        if self.token is None or datetime.now() >= self.expires_at:
            self._refresh_token()
        return self.token

    def _refresh_token(self):
        """Обновляет токен"""
        url = "https://oauth.yandex.ru/token"
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'subject_token': str(self.user_id),
            'subject_token_type': 'urn:yandex:params:oauth:token-type:uid'
        }

        response = requests.post(url, data=data)

        if response.status_code == 200:
            result = response.json()
            self.token = result.get('access_token')
            expires_in = result.get('expires_in', 3600)
            # Обновляем за 5 минут до истечения
            self.expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
            print(f"Токен обновлен. Действителен до {self.expires_at}")
        else:
            raise Exception(f"Не удалось обновить токен: {response.status_code}")


# Использование
token_manager = TokenManager(CLIENT_ID, CLIENT_SECRET, USER_ID)

# Используем в запросах
headers = {"Authorization": f"OAuth {token_manager.get_token()}"}
```

---

## Обработка ошибок

### Типичные ошибки

| Код | Описание | Решение |
|-----|----------|---------|
| 400 | Неверные параметры | Проверьте формат grant_type и subject_token_type |
| 401 | Неверные учетные данные | Проверьте CLIENT_ID и CLIENT_SECRET |
| 403 | Доступ запрещен | Убедитесь, что приложение активировано для пользователя |
| 404 | Пользователь не найден | Проверьте USER_ID или email |

### Пример обработки ошибок

```python
def get_user_token_safe(client_id, client_secret, user_id):
    """Получает токен с обработкой ошибок"""
    try:
        url = "https://oauth.yandex.ru/token"
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
            'client_id': client_id,
            'client_secret': client_secret,
            'subject_token': str(user_id),
            'subject_token_type': 'urn:yandex:params:oauth:token-type:uid'
        }

        response = requests.post(url, data=data)

        if response.status_code == 200:
            return response.json().get('access_token')
        elif response.status_code == 400:
            print("Ошибка: Неверные параметры запроса")
        elif response.status_code == 401:
            print("Ошибка: Неверные CLIENT_ID или CLIENT_SECRET")
        elif response.status_code == 403:
            print("Ошибка: Приложение не активировано для пользователя")
        elif response.status_code == 404:
            print("Ошибка: Пользователь не найден")
        else:
            print(f"Ошибка: {response.status_code} - {response.text}")

        return None

    except requests.exceptions.RequestException as e:
        print(f"Ошибка сети: {e}")
        return None
```

---

## Ограничения и рекомендации

### Ограничения

1. **Срок действия токена:** 1 час (3600 секунд)
2. **Права доступа:** Только те, что предоставлены сервисному приложению
3. **Rate limits:** Соблюдайте лимиты API Яндекс (обычно 100 запросов/секунду)

### Рекомендации

1. **Кэшируйте токен:** Не запрашивайте новый токен для каждого запроса
2. **Обновляйте заранее:** Обновляйте токен за 5 минут до истечения
3. **Храните секреты безопасно:** Используйте .env файлы, не коммитьте в git
4. **Обрабатывайте ошибки:** Предусмотрите повторные попытки при сбоях
5. **Логируйте операции:** Ведите лог обращений к API для отладки

---

## Безопасность

### Хранение учетных данных

```python
# ❌ ПЛОХО - хардкод в коде
CLIENT_SECRET = "8ca3671933544d7d990045e7d512aa0d"

# ✅ ХОРОШО - через переменные окружения
CLIENT_SECRET = os.getenv("Client_secret")
```

### .gitignore

```
.env
*.env
*.env.*
```

### Ротация секретов

Регулярно меняйте CLIENT_SECRET сервисного приложения:
1. В админ-панели Яндекс 360
2. Раздел "Сервисные приложения"
3. Сгенерируйте новый секрет
4. Обновите в .env файле

---

## Дополнительные ресурсы

- [Документация Яндекс 360 API](https://yandex.ru/dev/api360/doc/ru/)
- [Сервисные приложения](https://yandex.ru/support/yandex-360/business/admin/ru/security-service-applications)
- [Яндекс.Диск API](https://yandex.ru/dev/disk-api/doc/ru/)
- [RFC 8693 - OAuth 2.0 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693)

---

## FAQ

### Q: Можно ли использовать для календаря?

**A:** Нет. Календарь работает только через CalDAV с персональным OAuth токеном пользователя. Token Exchange не дает доступ к календарю.

### Q: Сколько пользователей можно обслужить одновременно?

**A:** Количество не ограничено. Вы можете получать токены для разных пользователей параллельно.

### Q: Нужно ли согласие пользователя?

**A:** Нет, если используется сервисное приложение организации. Администратор может получить токен для любого пользователя организации.

### Q: Можно ли использовать для скачивания публичных папок?

**A:** Да, но только если вы получили токен владельца публичной папки. Административный токен не подходит.

---

## Примеры использования

### Пример 1: Бэкап всех файлов пользователя

```python
def backup_user_disk(token, backup_dir):
    """Создает резервную копию всего диска пользователя"""
    Path(backup_dir).mkdir(parents=True, exist_ok=True)

    def backup_folder(folder_path, local_dir):
        items = list_folder_contents(token, folder_path)

        for item in items:
            if item['type'] == 'dir':
                # Рекурсивно обрабатываем подпапки
                subfolder_path = item['path']
                subfolder_local = local_dir / item['name']
                subfolder_local.mkdir(exist_ok=True)
                backup_folder(subfolder_path, subfolder_local)
            else:
                # Скачиваем файл
                file_path = item['path']
                local_file = local_dir / item['name']
                download_file(token, file_path, str(local_file))
                print(f"Скачан: {item['name']}")

    backup_folder("/", Path(backup_dir))
```

### Пример 2: Поиск файлов по расширению

```python
def find_files_by_extension(token, extension, root_path="/"):
    """Ищет все файлы с указанным расширением"""
    results = []

    def search_folder(folder_path):
        items = list_folder_contents(token, folder_path)

        for item in items:
            if item['type'] == 'dir':
                search_folder(item['path'])
            elif item['name'].endswith(extension):
                results.append({
                    'name': item['name'],
                    'path': item['path'],
                    'size': item.get('size', 0)
                })

    search_folder(root_path)
    return results

# Использование
docx_files = find_files_by_extension(token, '.docx', '/Клиенты')
print(f"Найдено .docx файлов: {len(docx_files)}")
```

---

**Версия документа:** 1.0
**Дата:** 14 января 2026
**Автор:** Claude Code
