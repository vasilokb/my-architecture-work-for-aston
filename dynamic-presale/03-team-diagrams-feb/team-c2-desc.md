**Пользовательский путь и работа приложения по шагам:**

## **1. Пользовательский путь (User Journey)**

### **Шаг 1: Создание пресейла**
```
Пользователь → Открывает http://localhost:3000
→ Нажимает "Создать пресейл"
→ Вводит название: "Проект X - Мобильное приложение"
→ Нажимает "Сохранить"
```

### **Шаг 2: Загрузка требований**
```
→ Переходит в созданный пресейл
→ Видит 2 варианта:
  1. Ввести текст в редакторе
  2. Загрузить файл
→ Выбирает "Загрузить файл"
→ Перетаскивает файл "Требования_проекта.docx" (50 страниц)
→ Система показывает прогресс загрузки
→ Файл загружен, появляется в списке
```

### **Шаг 3: Выбор команды**
```
→ Нажимает "Выбрать специалистов"
→ Отмечает галочками:
  - Системный аналитик (SA/BA)
  - Backend разработчик
  - Frontend разработчик
  - QA инженер
  - DevOps инженер
→ Сохраняет выбор
```

### **Шаг 4: Запуск AI-анализа**
```
→ Нажимает "Начать AI-анализ"
→ Видит окно с параметрами:
  - Модель анализа: "Стандартная декомпозиция"
  - Уровень детализации: "Средний"
  - Включать риски: Да
→ Нажимает "Запустить"
→ Видит статус: "Обработка файла..."
```

### **Шаг 5: Просмотр результатов**
```
Через 20 секунд:
→ Статус меняется на "Анализ завершён"
→ Автоматически открывается вкладка "Результаты"
→ Видит:
  - 5 эпиков
  - 23 задачи
  - Таблицу с оценками по ролям
  - Итоговую оценку: 340 человеко-часов
```

### **Шаг 6: Редактирование и экспорт**
```
→ Редактирует некоторые оценки
→ Нажимает "Пересчитать"
→ Нажимает "Экспорт в Excel"
→ Скачивает файл "Проект_X_оценка.xlsx"
→ Закрывает приложение
```

---

## **2. Техническая реализация (как работает система)**

### **Шаг 1: Создание пресейла (Frontend → Backend)**

```javascript
// Frontend (React) отправляет запрос:
POST http://localhost:8080/api/v1/presales
{
  "name": "Проект X - Мобильное приложение",
  "created_by": "user123"
}

// API Gateway (8080) получает запрос:
1. Проверяет JWT токен через Keycloak
2. Маршрутизирует на User Service
3. User Service создает запись в PostgreSQL
4. Возвращает ID пресейла: "presale_001"
```

### **Шаг 2: Загрузка файла (сложный процесс)**

```python
# 2.1 Frontend загружает файл:
const formData = new FormData();
formData.append('file', file);
formData.append('presale_id', 'presale_001');

POST http://localhost:8080/api/v1/files/upload

# 2.2 API Gateway → File Service (8084):
File Service:
1. Валидирует файл (размер, тип, безопасность)
2. Сохраняет в MinIO (Object Storage)
3. Создает запись в PostgreSQL (метаданные)
4. Запускает асинхронное извлечение текста

# 2.3 Извлечение текста из разных форматов:

# Для DOCX:
File Service → DOCX Parser:
- Извлекает текст с сохранением структуры
- Заголовки → H1, H2, H3
- Списки → маркированные/нумерованные
- Таблицы → преобразует в текст

# Для PDF:
File Service → PDF Processor:
- Проверяет: текстовый PDF или скан?
- Текстовый PDF: извлекает текст
- Скан PDF → OCR Engine:
  * Применяет Tesseract OCR
  * Поддерживает RU/EN
  * Добавляет предупреждение в метаданные

# 2.4 Нормализация текста:
Text Normalizer:
- Удаляет дублирующиеся абзацы
- Объединяет разорванные предложения
- Удаляет служебные метаданные
- Сохраняет в MinIO как чистый текст
```

### **Шаг 3: Запуск AI-анализа (оркестрация)**

```python
# 3.1 Frontend → Processing Service (8082):
POST http://localhost:8080/api/v1/analysis/start
{
  "presale_id": "presale_001",
  "file_ids": ["file_001"],
  "roles": ["SA", "Backend", "Frontend", "QA", "DevOps"],
  "parameters": {
    "model": "standard",
    "detail_level": "medium",
    "include_risks": true
  }
}

# 3.2 Processing Service создает документ:
1. Регистрирует документ в PostgreSQL (статус: "queued")
2. Создает контекст анализа (файлы + роли + параметры)
3. Отправляет задачу в Queue Service (8083)

# 3.3 Queue Service (8083) управляет очередью:
Job Queue:
- Принимает задачу
- Проверяет лимиты конcurrency (макс 5 параллельных)
- Назначает worker
- Отслеживает прогресс
```

### **Шаг 4: AI-обработка (самое интересное)**

```python
# 4.1 Queue Service → AI Service (8085):
POST http://localhost:8085/api/v1/ai/process
{
  "document_id": "doc_001",
  "text_content": "извлеченный_текст...",
  "roles": ["SA", "Backend", ...],
  "parameters": {...}
}

# 4.2 AI Service подготавливает промпт:
Prompt Builder:
1. Берет шаблон из PostgreSQL
2. Вставляет контекст:
   - Текст требований
   - Список ролей
   - Параметры анализа
3. Форматирует для LLM

# 4.3 Вызов внешней LLM:
AI Service → External LLM API:
POST https://api.external-llm.com/v1/chat/completions
{
  "model": "gpt-4",
  "messages": [...],
  "response_format": {"type": "json_object"},
  "temperature": 0.2
}

# 4.4 LLM возвращает структурированный JSON:
{
  "epics": [
    {
      "title": "Разработка архитектуры",
      "tasks": [
        {
          "title": "Проектирование API",
          "role": "Backend",
          "pert_estimate": {
            "optimistic": 8,
            "most_likely": 16,
            "pessimistic": 24
          }
        },
        // ... другие задачи
      ]
    }
  ],
  "risks": ["Недостаточная детализация требований"],
  "assumptions": ["Команда имеет опыт с технологией X"]
}
```

### **Шаг 5: Валидация и расчеты**

```python
# 5.1 AI Service → Analysis Service (8086):
POST http://localhost:8086/api/v1/analysis/validate
{
  "llm_response": {...},
  "document_id": "doc_001"
}

# 5.2 Analysis Service выполняет:
Schema Validator:
- Проверяет структуру JSON
- Валидирует обязательные поля
- Проверяет типы данных

Quality Gate:
- Проверяет качество ответа
- Ищет placeholder тексты
- Оценивает полноту

PERT Calculator:
- Для каждой задачи рассчитывает:
  expected = (optimistic + 4*most_likely + pessimistic) / 6
- Округляет до 0.5 часа
- Суммирует по эпикам и ролям

# 5.3 Analysis Service → Result Service (8087):
POST http://localhost:8087/api/v1/results/store
{
  "document_id": "doc_001",
  "analysis_result": {...},
  "totals": {
    "expected_hours": 340,
    "by_role": {...}
  }
}
```

### **Шаг 6: Отображение результатов пользователю**

```javascript
// 6.1 Frontend опрашивает статус:
// Пока идет обработка - polling каждые 2 секунды
GET http://localhost:8080/api/v1/documents/doc_001/status

// Response:
{
  "status": "processing",
  "progress": 65,
  "message": "Выполняется AI-анализ..."
}

// 6.2 Когда статус = "completed":
GET http://localhost:8080/api/v1/documents/doc_001/results

// 6.3 Frontend отображает:
- Таблицу эпиков/задач
- Фильтры по ролям
- Графики распределения
- Кнопки редактирования
```

### **Шаг 7: Редактирование и экспорт**

```python
# 7.1 Пользователь редактирует оценку:
PATCH http://localhost:8080/api/v1/results/task_001
{
  "pert_estimate": {
    "optimistic": 10,  // было 8
    "most_likely": 18, // было 16
    "pessimistic": 26  // было 24
  }
}

# 7.2 Result Service:
1. Сохраняет новую версию (versioning)
2. Пересчитывает expected: (10 + 4*18 + 26) / 6 = 18
3. Обновляет итоговые суммы

# 7.3 Экспорт в Excel:
GET http://localhost:8080/api/v1/exports/doc_001/excel

# Result Service:
1. Генерирует Excel файл:
   - Лист "Задачи": эпик, задача, роль, O/M/P/E
   - Лист "Сводка": итоги по ролям
   - Лист "Риски": выявленные риски
2. Сохраняет в MinIO
3. Возвращает ссылку для скачивания
```

---

## **3. Критические процессы и обработка ошибок**

### **Обработка больших файлов:**
```python
# File Service:
if file_size > 50MB:
    return error("Файл слишком большой")
    
if file_count > 5:
    return error("Слишком много файлов")

# Streaming processing для больших файлов:
with open(file_path, 'rb') as f:
    for chunk in read_in_chunks(f, chunk_size=1024*1024):  # 1MB chunks
        process_chunk(chunk)
```

### **Обработка ошибок LLM:**
```python
# AI Service:
try:
    response = call_llm_api(prompt)
except TimeoutError:
    # Ретри 3 раза с экспоненциальной задержкой
    retry_with_backoff(max_retries=3)
    
except InvalidResponseError:
    # Пробуем другую модель
    switch_model(fallback_model)
    
finally:
    # Логируем все ошибки
    log_error_to_postgres(error_details)
```

### **Восстановление после сбоев:**
```python
# Queue Service отслеживает "зависшие" задачи:
def monitor_stuck_jobs():
    jobs = get_jobs_older_than(30 * 60)  # 30 минут
    for job in jobs:
        if job.status == "processing":
            # Перезапускаем с того же места
            restart_job(job.id)
            log_incident("job_restarted", job.id)
```

---

## **4. Соответствие требованиям ТЗ**

### **Функциональные требования:**
- **FR-05**: Drag & drop загрузка ✅ (File Service)
- **FR-08**: Кнопка "Начать AI-анализ" ✅ (Processing Service)
- **FR-09**: Статус обработки ✅ (Queue Service + polling)
- **FR-17**: Расчет бюджета ✅ (Analysis Service PERT)
- **FR-19**: Редактирование задач ✅ (Result Service versioning)

### **Нефункциональные требования:**
- **NFR-01**: ≤30 секунд обработки ✅ (оптимизированный пайплайн)
- **NFR-12**: Парсинг текста ✅ (File Service parsers)
- **NFR-14**: OCR для сканов ✅ (OCR Engine)
- **NFR-18**: PERT расчеты ✅ (Analysis Service)
- **NFR-19**: Экспорт XLSX/PDF ✅ (Result Service exports)

---

## **5. Преимущества этой архитектуры**

### **Для пользователя:**
1. **Быстро** - анализ за 20-30 секунд
2. **Удобно** - drag & drop, интуитивный интерфейс
3. **Гибко** - редактирование результатов
4. **Практично** - готовые отчеты для заказчика

### **Для разработки:**
1. **Масштабируемо** - можно добавлять новые LLM провайдеры
2. **Надежно** - обработка ошибок, ретраи, мониторинг
3. **Поддерживаемо** - четкое разделение ответственности
4. **Тестируемо** - каждый сервис независим

**Итог:** Система работает как конвейер, где каждый сервис выполняет свою узкую задачу, что обеспечивает высокую производительность, надежность и возможность масштабирования.