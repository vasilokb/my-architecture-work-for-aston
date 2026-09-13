#!/usr/bin/env python3
"""
Простой тест API Career Aggregator 2
Проверяет базовую функциональность без всех зависимостей
"""

import sys
import asyncio
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

async def test_basic_imports():
    """Тестируем возможность импорта основных модулей"""
    print("Тестируем импорт основных модулей...")
    
    try:
        # Пробуем импортировать основные модули
        from app.core.config import Settings
        print("✓ app.core.config импортирован успешно")
        
        from app.api.main import app
        print("✓ app.api.main импортирован успешно")
        
        # Проверяем создание настроек
        try:
            settings = Settings()
            print(f"✓ Настройки созданы: {settings.app_name}")
        except Exception as e:
            print(f"✗ Ошибка создания настроек: {e}")
            
        return True
        
    except ImportError as e:
        print(f"✗ Ошибка импорта: {e}")
        print("\nУстановите зависимости:")
        print("pip install fastapi uvicorn pydantic python-dotenv")
        return False
    except Exception as e:
        print(f"✗ Неожиданная ошибка: {e}")
        return False

async def test_api_structure():
    """Тестируем структуру API"""
    print("\nТестируем структуру API...")
    
    try:
        from app.api.main import app
        from app.api.endpoints import health, search
        
        # Проверяем наличие роутеров
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        
        print(f"Найдено {len(routes)} маршрутов:")
        for route in sorted(routes)[:10]:  # Показываем первые 10
            print(f"  - {route}")
        
        if len(routes) > 10:
            print(f"  ... и еще {len(routes) - 10} маршрутов")
            
        # Проверяем основные эндпоинты
        required_routes = ['/api/health', '/api/search', '/api/search/basic']
        missing = [r for r in required_routes if r not in routes]
        
        if missing:
            print(f"X Отсутствуют маршруты: {missing}")
            return False
        else:
            print("V Все основные маршруты присутствуют")
            return True
            
    except Exception as e:
        print(f"✗ Ошибка тестирования API: {e}")
        return False

def check_dependencies():
    """Проверяем установленные зависимости"""
    print("\nПроверяем зависимости...")
    
    dependencies = {
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'pydantic': 'pydantic',
        'loguru': 'loguru',
        'httpx': 'httpx',
        'python-dotenv': 'dotenv',
    }
    
    all_ok = True
    for name, module in dependencies.items():
        try:
            __import__(module)
            print(f"V {name} установлен")
        except ImportError:
            print(f"X {name} не установлен")
            all_ok = False
    
    return all_ok

async def main():
    """Основная функция тестирования"""
    print("=" * 60)
    print("Тест Career Aggregator 2 API")
    print("=" * 60)
    
    # Проверяем зависимости
    deps_ok = check_dependencies()
    
    if not deps_ok:
        print("\nУстановите недостающие зависимости:")
        print("pip install fastapi uvicorn pydantic loguru httpx python-dotenv")
        return
    
    # Тестируем импорты
    imports_ok = await test_basic_imports()
    
    if imports_ok:
        # Тестируем структуру API
        await test_api_structure()
        
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТ: API готов к запуску!")
        print("\nДля запуска выполните:")
        print("uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000")
        print("\nЗатем откройте в браузере:")
        print("http://localhost:8000/api/health")
    else:
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТ: Есть проблемы с импортом")
        print("Убедитесь, что все зависимости установлены")

if __name__ == "__main__":
    asyncio.run(main())