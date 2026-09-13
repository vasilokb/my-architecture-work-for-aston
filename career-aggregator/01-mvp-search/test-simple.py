#!/usr/bin/env python3
"""
Простой тест для проверки работы Career Aggregator 2
"""

import sys
import os
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

def check_dependencies():
    """Проверяем установленные зависимости"""
    print("Проверяем зависимости...")
    
    dependencies = {
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'pydantic': 'pydantic',
        'pydantic-settings': 'pydantic_settings',
        'loguru': 'loguru',
        'httpx': 'httpx',
        'python-dotenv': 'dotenv',
    }
    
    all_ok = True
    for name, module in dependencies.items():
        try:
            __import__(module)
            print(f"  OK: {name}")
        except ImportError:
            print(f"  MISSING: {name}")
            all_ok = False
    
    return all_ok

def test_imports():
    """Тестируем возможность импорта основных модулей"""
    print("\nТестируем импорт модулей...")
    
    try:
        from app.core.config import Settings
        print("  OK: app.core.config")
        
        # Проверяем создание настроек
        try:
            settings = Settings()
            print(f"  OK: Настройки созданы ({settings.app_name})")
        except Exception as e:
            print(f"  ERROR: Ошибка создания настроек: {e}")
            
        return True
        
    except ImportError as e:
        print(f"  ERROR: Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"  ERROR: Неожиданная ошибка: {e}")
        return False

def test_api():
    """Тестируем структуру API"""
    print("\nТестируем структуру API...")
    
    try:
        from app.api.main import app
        
        # Проверяем наличие роутеров
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        
        print(f"  Найдено {len(routes)} маршрутов")
        
        # Проверяем основные эндпоинты
        required_routes = ['/api/health', '/api/search', '/api/search/basic']
        found = []
        missing = []
        
        for route in required_routes:
            if route in routes:
                found.append(route)
            else:
                missing.append(route)
        
        if found:
            print(f"  OK: Найдены: {', '.join(found)}")
        
        if missing:
            print(f"  WARNING: Отсутствуют: {', '.join(missing)}")
            return False
        
        return True
            
    except Exception as e:
        print(f"  ERROR: Ошибка тестирования API: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("=" * 60)
    print("ТЕСТ: Career Aggregator 2")
    print("=" * 60)
    
    # Проверяем зависимости
    deps_ok = check_dependencies()
    
    if not deps_ok:
        print("\nУстановите недостающие зависимости:")
        print("pip install fastapi uvicorn pydantic pydantic-settings loguru httpx python-dotenv")
        return
    
    # Тестируем импорты
    imports_ok = test_imports()
    
    if imports_ok:
        # Тестируем структуру API
        api_ok = test_api()
        
        if api_ok:
            print("\n" + "=" * 60)
            print("РЕЗУЛЬТАТ: Все тесты пройдены успешно!")
            print("\nДля запуска API выполните:")
            print("uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000")
            print("\nДля запуска веб-интерфейса (в другом окне):")
            print("streamlit run app/ui/main.py --server.port 8501")
        else:
            print("\n" + "=" * 60)
            print("РЕЗУЛЬТАТ: Есть проблемы с API структурой")
    else:
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТ: Есть проблемы с импортом модулей")

if __name__ == "__main__":
    main()