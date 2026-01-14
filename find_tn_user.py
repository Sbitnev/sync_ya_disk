"""
Поиск пользователя tn@imprice.ai и проверка доступа к его диску
"""
import os
import requests
from dotenv import load_dotenv


def find_user_by_email(admin_token, org_id, email):
    """Ищет пользователя по точному email"""
    url = f"https://api360.yandex.net/directory/v1/org/{org_id}/users"
    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }

    try:
        # Получаем всех пользователей
        all_users = []
        page = 1
        per_page = 100

        while True:
            params = {"page": page, "perPage": per_page}
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                users = data.get("users", [])

                if not users:
                    break

                all_users.extend(users)
                page += 1

                # Ограничиваем 500 пользователями
                if len(all_users) >= 500:
                    break
            else:
                print(f"Ошибка: {response.status_code}")
                break

        print(f"Всего пользователей: {len(all_users)}")

        # Ищем нужного пользователя
        for user in all_users:
            user_email = user.get("email", "")
            if email.lower() in user_email.lower():
                print(f"\n[НАЙДЕНО] Пользователь:")
                print(f"  Email: {user_email}")
                print(f"  ID: {user.get('id')}")
                print(f"  Имя: {user.get('name', {}).get('first', '')} {user.get('name', {}).get('last', '')}")
                print(f"  Департамент: {user.get('departmentId', 'Нет')}")

                # Проверяем, есть ли информация о владельце публичной папки
                if user_email == "tn@imprice.ai":
                    return user

        return None

    except Exception as e:
        print(f"Ошибка: {e}")
        return None


def check_if_folder_is_shared(admin_token, folder_path="/Клиенты"):
    """Проверяет, расшарена ли папка на диске организации"""
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {
        "Authorization": f"OAuth {admin_token}"
    }
    params = {
        "path": folder_path,
        "fields": "name,path,type,public_key,public_url,owner,share"
    }

    try:
        print(f"\nПроверка папки: {folder_path}")
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Папка найдена!")
            print(f"  Имя: {data.get('name')}")
            print(f"  Тип: {data.get('type')}")
            print(f"  Владелец: {data.get('owner', {})}")
            print(f"  Публичная: {data.get('public_url', 'Нет')}")
            print(f"  Расшарена: {data.get('share', {})}")
            return True
        elif response.status_code == 404:
            print(f"[INFO] Папка не найдена: {folder_path}")
            return False
        else:
            print(f"Статус: {response.status_code}")
            print(f"Ответ: {response.text}")
            return False

    except Exception as e:
        print(f"Ошибка: {e}")
        return False


def main():
    load_dotenv()

    admin_token = os.getenv("YANDEX_ADMIN_TOKEN")
    org_id = os.getenv("YANDEX_ORG_ID")

    print("="*80)
    print("ПОИСК ПОЛЬЗОВАТЕЛЯ TN@IMPRICE.AI")
    print("="*80)

    # Ищем пользователя
    user = find_user_by_email(admin_token, org_id, "tn@imprice.ai")

    if not user:
        print("\n[ERROR] Пользователь tn@imprice.ai не найден")
        print("\nВозможные причины:")
        print("  1. Это внешний пользователь (не из организации)")
        print("  2. Это алиас или группа")
        print("  3. Email написан по-другому")
        return

    user_id = user.get("id")

    # Проверяем, есть ли папка "Клиенты" на диске организации
    print("\n" + "="*80)
    print("ПРОВЕРКА НАЛИЧИЯ ПАПКИ НА ДИСКЕ ОРГАНИЗАЦИИ")
    print("="*80)

    possible_paths = [
        "/Клиенты",
        "/Проекты",
        f"/Домашняя/{user.get('email')}/Клиенты",
        f"/Общая папка/Клиенты",
    ]

    for path in possible_paths:
        found = check_if_folder_is_shared(admin_token, path)
        if found:
            print(f"\n[OK] Папка найдена на диске организации: {path}")
            return

    print("\n" + "="*80)
    print("ИТОГ:")
    print("="*80)
    print("Папка 'Клиенты' находится на ЛИЧНОМ диске пользователя tn@imprice.ai")
    print("и не расшарена на диск организации.")
    print("\nРешения:")
    print("  1. Попросите tn@imprice.ai расшарить папку на организацию")
    print("  2. Используйте публичную ссылку (но владелец запретил скачивание)")
    print("  3. Попросите tn@imprice.ai дать прямые права на папку другим пользователям")


if __name__ == "__main__":
    main()
