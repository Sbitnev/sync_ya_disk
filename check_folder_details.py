"""
Получение подробной информации о публичной папке
"""
import os
import requests
import json
from dotenv import load_dotenv


def get_full_public_info(token, public_url):
    """Получает полную информацию о публичной папке"""
    url = "https://cloud-api.yandex.net/v1/disk/public/resources"
    headers = {
        "Authorization": f"OAuth {token}"
    }
    params = {
        "public_key": public_url
    }

    try:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            print("="*80)
            print("ПОЛНАЯ ИНФОРМАЦИЯ О ПУБЛИЧНОЙ ПАПКЕ:")
            print("="*80)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        else:
            print(f"Ошибка: {response.status_code}")
            print(response.text)
            return None

    except Exception as e:
        print(f"Ошибка: {e}")
        return None


def main():
    load_dotenv()
    token = os.getenv("Token")

    if not token:
        print("Токен не найден")
        return

    public_url = "https://disk.yandex.ru/d/_JeaJNmm6UeQVA"
    get_full_public_info(token, public_url)


if __name__ == "__main__":
    main()
