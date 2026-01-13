@echo off
echo ========================================
echo Установка зависимостей для решений
echo ========================================
echo.

echo [1/3] Установка базовых зависимостей...
pip install -r requirements.txt

echo.
echo [2/3] Установка Selenium (для браузерной автоматизации)...
pip install selenium

echo.
echo [3/3] Установка yadisk (для OAuth)...
pip install yadisk

echo.
echo ========================================
echo Установка завершена!
echo ========================================
echo.
echo Доступные решения:
echo   1. rclone - см. setup_rclone.md
echo   2. Selenium - python browser_downloader.py
echo   3. OAuth - python oauth_downloader.py
echo.
echo Подробности в SOLUTIONS.md
echo.
pause
