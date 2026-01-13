"""
Автоматическое скачивание файлов с Яндекс.Диска через браузер
Использует Selenium для эмуляции действий пользователя
"""
import time
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Настройки
PUBLIC_URL = "https://disk.yandex.ru/d/_JeaJNmm6UeQVA"
DOWNLOAD_DIR = Path("browser_downloads").absolute()


def setup_driver(download_dir):
    """Настройка Chrome драйвера"""
    chrome_options = Options()

    # Настройки для автоматического скачивания
    prefs = {
        "download.default_directory": str(download_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Опционально: headless режим (без GUI)
    # chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options)
    return driver


def download_folder(driver, folder_url, target_folder=""):
    """Скачивает все файлы из папки"""
    print(f"\nОткрываю папку: {folder_url}")
    driver.get(folder_url)

    # Ждём загрузки страницы
    time.sleep(3)

    try:
        # Ищем все элементы в списке файлов
        wait = WebDriverWait(driver, 10)

        # Находим все файлы и папки
        items = driver.find_elements(By.CSS_SELECTOR, "[data-id]")

        print(f"Найдено элементов: {len(items)}")

        folders = []
        files_count = 0

        for item in items:
            try:
                # Определяем тип элемента
                item_name = item.get_attribute("aria-label")
                if not item_name:
                    continue

                print(f"  Элемент: {item_name}")

                # Клик правой кнопкой для контекстного меню
                action = webdriver.ActionChains(driver)
                action.context_click(item).perform()
                time.sleep(0.5)

                # Ищем кнопку "Скачать"
                try:
                    download_btn = driver.find_element(By.XPATH, "//button[contains(., 'Скачать')]")
                    download_btn.click()
                    print(f"    → Скачивание начато")
                    files_count += 1
                    time.sleep(1)
                except:
                    # Возможно это папка
                    print(f"    → Пропущено (возможно, папка)")

                # Закрываем контекстное меню (клик в пустое место)
                driver.find_element(By.TAG_NAME, "body").click()
                time.sleep(0.3)

            except Exception as e:
                print(f"    Ошибка: {e}")
                continue

        print(f"\nИнициировано скачивание {files_count} файлов")
        return files_count

    except Exception as e:
        print(f"Ошибка при обработке папки: {e}")
        return 0


def main():
    # Создаём папку для загрузок
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    print("=" * 80)
    print("АВТОМАТИЧЕСКОЕ СКАЧИВАНИЕ ЧЕРЕЗ БРАУЗЕР")
    print("=" * 80)
    print(f"URL: {PUBLIC_URL}")
    print(f"Папка загрузки: {DOWNLOAD_DIR}")
    print()
    print("ВАЖНО: Убедитесь, что установлен Chrome и chromedriver")
    print("Установка: pip install selenium")
    print("ChromeDriver: https://chromedriver.chromium.org/")
    print()

    input("Нажмите Enter для начала...")

    try:
        # Запускаем браузер
        print("\nЗапуск браузера...")
        driver = setup_driver(DOWNLOAD_DIR)

        # Скачиваем файлы
        total_files = download_folder(driver, PUBLIC_URL)

        print("\n" + "=" * 80)
        print("ЗАВЕРШЕНО")
        print("=" * 80)
        print(f"Инициировано скачивание: {total_files} файлов")
        print(f"Файлы будут сохранены в: {DOWNLOAD_DIR}")
        print("\nОжидайте завершения загрузок в браузере...")

        # Оставляем браузер открытым на 60 секунд для завершения загрузок
        print("\nБраузер закроется через 60 секунд...")
        time.sleep(60)

    except Exception as e:
        print(f"\nОШИБКА: {e}")
        print("\nВозможные причины:")
        print("1. Chrome или ChromeDriver не установлены")
        print("2. Версии Chrome и ChromeDriver не совпадают")
        print("3. Изменилась структура страницы Яндекс.Диска")

    finally:
        try:
            driver.quit()
        except:
            pass


if __name__ == "__main__":
    main()
