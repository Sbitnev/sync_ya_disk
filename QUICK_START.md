# Быстрый старт: Доступ к диску пользователя Яндекс 360

## Шаг 1: Подготовка (5 минут)

### 1.1 Получите CLIENT_ID и CLIENT_SECRET

```python
import requests
import os

ADMIN_TOKEN = "y0_xxx..."  # Ваш административный токен
ORG_ID = "7140966"  # ID вашей организации

# Получаем список приложений
url = f"https://api360.yandex.net/security/v1/org/{ORG_ID}/service_applications"
headers = {"Authorization": f"OAuth {ADMIN_TOKEN}"}

response = requests.get(url, headers=headers)
apps = response.json()["applications"]

# Ищем приложение с правами на диск
for app in apps:
    if "cloud_api:disk.read" in app["scopes"]:
        print(f"CLIENT_ID: {app['id']}")
        # CLIENT_SECRET нужно получить в админ-панели Яндекс 360
```

### 1.2 Получите USER_ID

```python
# Получаем ID пользователя по email
email = "tn@imprice.ai"
url = f"https://api360.yandex.net/directory/v1/org/{ORG_ID}/users?email={email}"

response = requests.get(url, headers=headers)
user = response.json()["users"][0]

print(f"USER_ID: {user['id']}")
```

---

## Шаг 2: Получение токена (1 минута)

```python
import requests

def get_user_token(client_id, client_secret, user_id):
    url = "https://oauth.yandex.ru/token"

    data = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
        'client_id': client_id,
        'client_secret': client_secret,
        'subject_token': str(user_id),
        'subject_token_type': 'urn:yandex:params:oauth:token-type:uid'
    }

    response = requests.post(url, data=data)
    return response.json()['access_token']

# Используем
CLIENT_ID = "bdb90dee90fe49329c24535283606260"
CLIENT_SECRET = "8ca3671933544d7d990045e7d512aa0d"
USER_ID = "1130000057842996"

token = get_user_token(CLIENT_ID, CLIENT_SECRET, USER_ID)
print(f"Токен получен: {token[:20]}...")
```

---

## Шаг 3: Использование токена

### 3.1 Список папок

```python
url = "https://cloud-api.yandex.net/v1/disk/resources"
headers = {"Authorization": f"OAuth {token}"}
params = {"path": "/", "limit": 100}

response = requests.get(url, headers=headers, params=params)
items = response.json()["_embedded"]["items"]

for item in items:
    if item["type"] == "dir":
        print(f"📁 {item['name']}")
```

### 3.2 Скачивание файла

```python
from pathlib import Path

def download_file(token, file_path, local_path):
    # Шаг 1: Получаем ссылку
    url = "https://cloud-api.yandex.net/v1/disk/resources/download"
    headers = {"Authorization": f"OAuth {token}"}
    params = {"path": file_path}

    response = requests.get(url, headers=headers, params=params)
    download_url = response.json()["href"]

    # Шаг 2: Скачиваем
    file_data = requests.get(download_url)

    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    with open(local_path, 'wb') as f:
        f.write(file_data.content)

    print(f"Файл скачан: {local_path}")

# Используем
download_file(
    token,
    "/Клиенты/Папка/Файл.docx",
    "downloads/Файл.docx"
)
```

---

## Готовый скрипт (копируй и используй)

```python
import requests
from pathlib import Path

# === КОНФИГУРАЦИЯ ===
CLIENT_ID = "bdb90dee90fe49329c24535283606260"
CLIENT_SECRET = "8ca3671933544d7d990045e7d512aa0d"
USER_ID = "1130000057842996"

# === ФУНКЦИИ ===

def get_token():
    """Получает токен пользователя"""
    url = "https://oauth.yandex.ru/token"
    data = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'subject_token': str(USER_ID),
        'subject_token_type': 'urn:yandex:params:oauth:token-type:uid'
    }
    response = requests.post(url, data=data)
    return response.json()['access_token']

def list_folders(token, path="/"):
    """Получает список папок"""
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {"Authorization": f"OAuth {token}"}
    params = {"path": path, "limit": 100}

    response = requests.get(url, headers=headers, params=params)
    items = response.json()["_embedded"]["items"]

    return [item for item in items if item["type"] == "dir"]

def download_file(token, file_path, local_path):
    """Скачивает файл"""
    # Получаем ссылку
    url = "https://cloud-api.yandex.net/v1/disk/resources/download"
    headers = {"Authorization": f"OAuth {token}"}
    params = {"path": file_path}

    response = requests.get(url, headers=headers, params=params)
    download_url = response.json()["href"]

    # Скачиваем
    file_data = requests.get(download_url, stream=True)

    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    with open(local_path, 'wb') as f:
        for chunk in file_data.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

# === ИСПОЛЬЗОВАНИЕ ===

# 1. Получаем токен
print("Получение токена...")
token = get_token()
print("✓ Токен получен\n")

# 2. Выводим список папок
print("Папки на диске:")
folders = list_folders(token)
for i, folder in enumerate(folders, 1):
    print(f"{i}. {folder['name']}")

# 3. Скачиваем файл
print("\nСкачивание файла...")
download_file(
    token,
    "/Клиенты/Юн.Индастриал/UInd. Предварительное предложение.docx",
    "downloads/test.docx"
)
print("✓ Файл скачан")
```

---

## Важно помнить

1. **Токен действителен 1 час** - обновляйте его для долгих операций
2. **Храните секреты в .env** - не коммитьте в git
3. **Обрабатывайте ошибки** - проверяйте статус коды ответов

---

## Следующие шаги

Для более продвинутого использования смотрите:
- `DOCUMENTATION_TOKEN_EXCHANGE.md` - полная документация
- `get_token_exchange.py` - готовый скрипт с обработкой ошибок
- `download_file_with_user_token.py` - пример скачивания с прогресс-баром

---

**Готово!** Теперь вы можете работать с диском любого пользователя организации.
