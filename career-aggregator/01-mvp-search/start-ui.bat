@echo off
echo ========================================
echo Запуск веб-интерфейса Career Aggregator 2
echo ========================================
echo.

echo 1. Активация виртуального окружения
call venv\Scripts\activate

echo.
echo 2. Установка Streamlit (если не установлен)
pip install streamlit pandas

echo.
echo 3. Запуск веб-интерфейса
echo Веб-интерфейс будет доступен по адресу: http://localhost:8501
echo.
echo Для остановки нажмите Ctrl+C
echo.

streamlit run app/ui/main.py --server.port 8501

pause