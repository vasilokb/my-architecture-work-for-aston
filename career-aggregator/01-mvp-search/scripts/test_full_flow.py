#!/usr/bin/env python3
"""
Скрипт для тестирования полного потока Career Aggregator 2.

Этот скрипт проверяет работу всех компонентов системы:
1. Проверка доступности API
2. Поиск вакансий через API
3. Проверка кэширования
4. Проверка фильтров
5. Проверка аналитики
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional


class CareerAggregatorTester:
    """Тестер полного потока Career Aggregator 2."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "CareerAggregatorTester/1.0"
        })
    
    def test_health(self) -> bool:
        """Тест health endpoint."""
        print("🔍 Тестирование health endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data.get('status')}")
                print(f"   Version: {data.get('version')}")
                print(f"   Timestamp: {data.get('timestamp')}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_detailed_health(self) -> bool:
        """Тест detailed health endpoint."""
        print("🔍 Тестирование detailed health endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/api/health/detailed", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Detailed health check passed")
                
                # Проверяем зависимости
                deps = data.get('dependencies', {})
                for dep_name, dep_info in deps.items():
                    status = dep_info.get('status', 'unknown')
                    icon = "✅" if status == "healthy" else "⚠️" if status == "disabled" else "❌"
                    print(f"   {icon} {dep_name}: {status}")
                
                # Проверяем кэш
                cache = data.get('cache', {})
                if cache:
                    hit_rate = cache.get('hit_rate', 0)
                    print(f"   📊 Cache hit rate: {hit_rate:.1%}")
                
                return True
            else:
                print(f"❌ Detailed health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Detailed health check error: {e}")
            return False
    
    def test_filters(self) -> bool:
        """Тест получения фильтров."""
        print("🔍 Тестирование filters endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/api/filters", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Filters endpoint passed")
                
                areas = data.get('areas', [])
                experience_levels = data.get('experience_levels', [])
                schedules = data.get('schedules', [])
                
                print(f"   📍 Areas: {len(areas)} регионов")
                print(f"   👤 Experience levels: {len(experience_levels)} уровней")
                print(f"   📅 Schedules: {len(schedules)} графиков")
                
                if areas and experience_levels and schedules:
                    return True
                else:
                    print("⚠️  Некоторые фильтры пусты")
                    return False
            else:
                print(f"❌ Filters endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Filters endpoint error: {e}")
            return False
    
    def test_search(self, query: str, use_semantic: bool = True) -> Optional[Dict[str, Any]]:
        """Тест поиска вакансий."""
        print(f"🔍 Тестирование поиска: '{query}' (semantic: {use_semantic})...")
        
        payload = {
            "query": query,
            "filters": {},
            "limit": 10,
            "use_semantic": use_semantic,
        }
        
        try:
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/api/search",
                json=payload,
                timeout=30
            )
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                vacancies = data.get('vacancies', [])
                total_results = data.get('total_results', 0)
                cache_hit = data.get('cache_hit', False)
                
                print(f"✅ Поиск выполнен за {elapsed_time:.2f} секунд")
                print(f"   📊 Найдено вакансий: {total_results}")
                print(f"   📄 Показано: {len(vacancies)}")
                print(f"   ⚡ Кэш: {'Попадание' if cache_hit else 'Промах'}")
                
                if vacancies:
                    # Показываем первую вакансию
                    first_vacancy = vacancies[0]
                    print(f"   🎯 Первая вакансия: {first_vacancy.get('name')}")
                    print(f"   💰 Зарплата: {first_vacancy.get('salary', {}).get('from', 'Не указана')}")
                    print(f"   🏙️  Город: {first_vacancy.get('area', 'Не указан')}")
                
                return data
            else:
                print(f"❌ Поиск failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Поиск error: {e}")
            return None
    
    def test_cache_behavior(self) -> bool:
        """Тест поведения кэша."""
        print("🔍 Тестирование поведения кэша...")
        
        # Первый запрос (должен быть промах кэша)
        print("   Первый запрос (ожидается промах кэша)...")
        result1 = self.test_search("python разработчик", use_semantic=True)
        if not result1:
            return False
        
        cache_hit1 = result1.get('cache_hit', False)
        
        # Ждем немного
        time.sleep(1)
        
        # Второй запрос (должно быть попадание в кэш)
        print("   Второй запрос (ожидается попадание в кэша)...")
        result2 = self.test_search("python разработчик", use_semantic=True)
        if not result2:
            return False
        
        cache_hit2 = result2.get('cache_hit', False)
        
        # Проверяем поведение кэша
        if not cache_hit1 and cache_hit2:
            print("✅ Поведение кэша корректное: первый запрос - промах, второй - попадание")
            return True
        else:
            print(f"⚠️  Неожиданное поведение кэша: первый={cache_hit1}, второй={cache_hit2}")
            return False
    
    def test_search_with_filters(self) -> bool:
        """Тест поиска с фильтрами."""
        print("🔍 Тестирование поиска с фильтрами...")
        
        payload = {
            "query": "python",
            "filters": {
                "experience": "senior",
                "schedule": "full_day",
            },
            "limit": 5,
            "use_semantic": True,
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/search",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Поиск с фильтрами выполнен")
                print(f"   📊 Найдено: {data.get('total_results', 0)} вакансий")
                return True
            else:
                print(f"❌ Поиск с фильтрами failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Поиск с фильтрами error: {e}")
            return False
    
    def test_cache_stats(self) -> bool:
        """Тест статистики кэша."""
        print("🔍 Тестирование статистики кэша...")
        
        try:
            response = self.session.get(f"{self.base_url}/api/cache/stats", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Статистика кэша получена")
                print(f"   🔑 Всего ключей: {data.get('total_keys', 0)}")
                print(f"   🎯 Hit rate: {data.get('hit_rate', 0):.1%}")
                print(f"   💾 Использовано памяти: {data.get('memory_used', 'N/A')}")
                return True
            else:
                print(f"❌ Статистика кэша failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Статистика кэша error: {e}")
            return False
    
    def run_full_test(self) -> bool:
        """Запуск полного теста."""
        print("=" * 60)
        print("🚀 Запуск полного теста Career Aggregator 2")
        print("=" * 60)
        
        tests = [
            ("Health check", self.test_health),
            ("Detailed health", self.test_detailed_health),
            ("Filters", self.test_filters),
            ("Search (semantic)", lambda: self.test_search("python разработчик москва", True)),
            ("Search (non-semantic)", lambda: self.test_search("java разработчик", False)),
            ("Cache behavior", self.test_cache_behavior),
            ("Search with filters", self.test_search_with_filters),
            ("Cache stats", self.test_cache_stats),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n{'='*40}")
            print(f"📋 Тест: {test_name}")
            print(f"{'='*40}")
            
            try:
                result = test_func()
                results.append((test_name, result))
                
                if result:
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"💥 {test_name}: ERROR - {e}")
                results.append((test_name, False))
        
        # Сводка результатов
        print(f"\n{'='*60}")
        print("📊 Сводка результатов тестирования")
        print(f"{'='*60}")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name}")
        
        print(f"\n🎯 Итог: {passed}/{total} тестов пройдено ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("✨ Все тесты пройдены успешно!")
            return True
        else:
            print(f"⚠️  {total - passed} тестов не пройдено")
            return False


def main():
    """Основная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Тестирование полного потока Career Aggregator 2")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL API")
    parser.add_argument("--quick", action="store_true", help="Быстрый тест (только health и поиск)")
    
    args = parser.parse_args()
    
    tester = CareerAggregatorTester(args.url)
    
    if args.quick:
        # Быстрый тест
        print("🚀 Запуск быстрого теста...")
        if not tester.test_health():
            print("❌ Health check failed, exiting...")
            sys.exit(1)
        
        if not tester.test_search("python разработчик"):
            print("❌ Search test failed, exiting...")
            sys.exit(1)
        
        print("✅ Быстрый тест пройден успешно!")
    else:
        # Полный тест
        success = tester.run_full_test()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()