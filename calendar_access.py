"""
Доступ к Яндекс Календарю через CalDAV
"""
import os
import caldav
from dotenv import load_dotenv
from datetime import datetime, timedelta


def connect_to_calendar(username, token):
    """Подключается к календарю Яндекс через CalDAV"""
    # CalDAV URL для Яндекс Календаря
    caldav_url = f"https://caldav.yandex.ru"

    try:
        print(f"Подключение к Яндекс Календарю...")
        print(f"URL: {caldav_url}")
        print(f"Пользователь: {username}")

        # Создаём клиент CalDAV
        # Яндекс использует OAuth токен вместо пароля
        client = caldav.DAVClient(
            url=caldav_url,
            username=username,
            password=token
        )

        # Получаем principal (основной объект пользователя)
        print("Получение principal...")
        principal = client.principal()

        print("[OK] Подключение успешно!")
        return principal

    except Exception as e:
        print(f"[ERROR] Ошибка подключения: {e}")
        import traceback
        traceback.print_exc()
        return None


def list_calendars(principal):
    """Получает список календарей пользователя"""
    try:
        print("\nПолучение списка календарей...")
        calendars = principal.calendars()

        if not calendars:
            print("[INFO] Календари не найдены")
            return []

        print(f"\n[OK] Найдено календарей: {len(calendars)}\n")

        for i, calendar in enumerate(calendars, 1):
            print(f"{i}. {calendar.name}")
            print(f"   URL: {calendar.url}")
            print()

        return calendars

    except Exception as e:
        print(f"[ERROR] Ошибка получения календарей: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_recent_events(calendar, days=30):
    """Получает события за последние N дней"""
    try:
        print(f"\nПолучение событий за последние {days} дней...")

        # Временной диапазон
        start = datetime.now() - timedelta(days=days)
        end = datetime.now() + timedelta(days=days)

        # Получаем события
        events = calendar.date_search(start=start, end=end)

        if not events:
            print("[INFO] События не найдены")
            return []

        print(f"\n[OK] Найдено событий: {len(events)}\n")

        for i, event in enumerate(events[:10], 1):  # Показываем первые 10
            ical = event.icalendar_instance

            # Извлекаем информацию о событии
            for component in ical.walk():
                if component.name == "VEVENT":
                    summary = component.get('summary', 'Без названия')
                    dtstart = component.get('dtstart')
                    dtend = component.get('dtend')
                    location = component.get('location', '')

                    print(f"{i}. {summary}")
                    if dtstart:
                        print(f"   Начало: {dtstart.dt}")
                    if dtend:
                        print(f"   Конец: {dtend.dt}")
                    if location:
                        print(f"   Место: {location}")
                    print()

        return events

    except Exception as e:
        print(f"[ERROR] Ошибка получения событий: {e}")
        import traceback
        traceback.print_exc()
        return []


def main():
    load_dotenv()

    admin_token = os.getenv("YANDEX_ADMIN_TOKEN")

    # Для CalDAV нужен email пользователя
    # Попробуем разные варианты
    usernames = [
        "tn@imprice.ai",
        "neitan4",  # из информации о токене
        "1130000057842996",  # ID пользователя
    ]

    print("="*80)
    print("ДОСТУП К ЯНДЕКС КАЛЕНДАРЮ ЧЕРЕЗ CALDAV")
    print("="*80 + "\n")

    principal = None
    working_username = None

    # Пробуем разные варианты username
    for username in usernames:
        print(f"\nПопытка с username: {username}")
        print("-"*80)

        principal = connect_to_calendar(username, admin_token)

        if principal:
            working_username = username
            break

        print()

    if not principal:
        print("\n" + "="*80)
        print("[ERROR] НЕ УДАЛОСЬ ПОДКЛЮЧИТЬСЯ К КАЛЕНДАРЮ")
        print("="*80)
        print("\nВозможные причины:")
        print("  1. Административный токен не подходит для CalDAV")
        print("  2. Нужен персональный токен пользователя")
        print("  3. CalDAV требует другой формат авторизации")
        print("\nРекомендация:")
        print("  - Попросите пользователя создать OAuth приложение")
        print("  - Получите персональный токен с правами calendar:all")
        print("  - Документация: https://yandex.ru/dev/api360/doc/ru/access")
        return

    print("\n" + "="*80)
    print(f"[OK] УСПЕШНОЕ ПОДКЛЮЧЕНИЕ (username: {working_username})")
    print("="*80)

    # Получаем календари
    calendars = list_calendars(principal)

    if calendars:
        # Берём первый календарь и получаем события
        calendar = calendars[0]
        print(f"\nРабота с календарём: {calendar.name}")
        print("="*80)

        events = get_recent_events(calendar)

        if events:
            print("\n" + "="*80)
            print("[OK] ДОСТУП К КАЛЕНДАРЮ ПОЛУЧЕН!")
            print("="*80)
            print(f"\nИспользуемый токен работает для CalDAV")
            print(f"Username: {working_username}")
            print(f"\nСохраните для дальнейшего использования:")
            print(f"CALDAV_URL=https://caldav.yandex.ru")
            print(f"CALDAV_USERNAME={working_username}")
            print(f"CALDAV_TOKEN={admin_token[:20]}...")


if __name__ == "__main__":
    main()
