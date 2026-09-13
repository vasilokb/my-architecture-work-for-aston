"""
Streamlit веб-интерфейс для Career Aggregator 2.

Этот модуль предоставляет пользовательский интерфейс для
семантического поиска вакансий с интеграцией HH.ru.
"""

import streamlit as st
import pandas as pd
import requests
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# Конфигурация страницы
st.set_page_config(
    page_title="Career Aggregator 2",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Настройки API
API_BASE_URL = "http://localhost:8000"  # В продакшене заменить на реальный URL


def init_session_state():
    """Инициализирует состояние сессии."""
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    if "search_filters" not in st.session_state:
        st.session_state.search_filters = {}
    if "search_stats" not in st.session_state:
        st.session_state.search_stats = {}
    if "filters_data" not in st.session_state:
        st.session_state.filters_data = None
    if "api_health" not in st.session_state:
        st.session_state.api_health = None


def check_api_health() -> bool:
    """Проверяет доступность API."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            st.session_state.api_health = response.json()
            return True
        else:
            st.session_state.api_health = None
            return False
    except Exception:
        st.session_state.api_health = None
        return False


def load_filters():
    """Загружает фильтры из API."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/filters", timeout=10)
        if response.status_code == 200:
            st.session_state.filters_data = response.json()
            return True
        return False
    except Exception:
        return False


def search_vacancies(query: str, filters: Dict[str, Any], use_semantic: bool = True) -> Optional[Dict[str, Any]]:
    """
    Выполняет поиск вакансий через API.
    
    Args:
        query: Поисковый запрос
        filters: Фильтры поиска
        use_semantic: Использовать семантическое ранжирование
    
    Returns:
        Результаты поиска или None при ошибке
    """
    try:
        payload = {
            "query": query,
            "filters": filters,
            "limit": 50,
            "use_semantic": use_semantic,
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/search",
            json=payload,
            timeout=30,
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Ошибка API: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        st.error("Таймаут запроса к API. Попробуйте позже.")
        return None
    except Exception as e:
        st.error(f"Ошибка при выполнении поиска: {str(e)}")
        return None


def display_vacancy_card(vacancy: Dict[str, Any]):
    """Отображает карточку вакансии."""
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Заголовок вакансии
            st.markdown(f"### [{vacancy['name']}]({vacancy['alternate_url']})")
            
            # Компания
            if vacancy.get('employer'):
                st.markdown(f"**Компания:** {vacancy['employer']}")
            
            # Локация и график
            location_schedule = []
            if vacancy.get('area'):
                location_schedule.append(f"📍 {vacancy['area']}")
            if vacancy.get('schedule'):
                location_schedule.append(f"📅 {vacancy['schedule']}")
            if vacancy.get('experience'):
                location_schedule.append(f"👤 {vacancy['experience']}")
            
            if location_schedule:
                st.markdown(" • ".join(location_schedule))
            
            # Зарплата
            if vacancy.get('salary') and vacancy['salary'].get('from'):
                salary_from = vacancy['salary']['from']
                salary_to = vacancy['salary'].get('to', '')
                currency = vacancy['salary'].get('currency', 'RUR')
                
                salary_text = f"💰 **Зарплата:** {salary_from:,.0f}"
                if salary_to:
                    salary_text += f" - {salary_to:,.0f}"
                
                # Конвертируем валюту в символ
                currency_symbol = {
                    "RUR": "₽",
                    "USD": "$",
                    "EUR": "€",
                }.get(currency, currency)
                
                salary_text += f" {currency_symbol}"
                st.markdown(salary_text)
            
            # Ключевые навыки
            if vacancy.get('key_skills'):
                skills_text = ", ".join(vacancy['key_skills'][:5])
                st.markdown(f"**Навыки:** {skills_text}")
            
            # Описание (сокращенное)
            if vacancy.get('description'):
                description = vacancy['description'][:200] + "..." if len(vacancy['description']) > 200 else vacancy['description']
                with st.expander("Описание"):
                    st.markdown(description)
        
        with col2:
            # Релевантность (если есть)
            if vacancy.get('relevance_score'):
                score = vacancy['relevance_score']
                score_percent = int(score * 100)
                
                # Прогресс-бар релевантности
                st.progress(score)
                st.markdown(f"**Релевантность:** {score_percent}%")
            
            # Дата публикации
            if vacancy.get('published_at'):
                try:
                    pub_date = datetime.fromisoformat(vacancy['published_at'].replace('Z', '+00:00'))
                    days_ago = (datetime.now() - pub_date).days
                    
                    if days_ago == 0:
                        date_text = "Сегодня"
                    elif days_ago == 1:
                        date_text = "Вчера"
                    elif days_ago < 7:
                        date_text = f"{days_ago} дня назад"
                    else:
                        date_text = f"{days_ago} дней назад"
                    
                    st.markdown(f"📅 {date_text}")
                except:
                    pass
            
            # Кнопка "Подробнее"
            st.link_button("Открыть на HH.ru", vacancy['alternate_url'])
        
        st.divider()


def display_search_stats(stats: Dict[str, Any]):
    """Отображает статистику поиска."""
    if not stats:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Найдено вакансий",
            value=stats.get('total_results', 0),
        )
    
    with col2:
        st.metric(
            label="Показано",
            value=stats.get('returned_results', 0),
        )
    
    with col3:
        if stats.get('cache_hit'):
            st.metric(
                label="Кэш",
                value="Попадание",
                delta="⚡ Быстро",
            )
        else:
            st.metric(
                label="Кэш",
                value="Промах",
                delta="⏳ Медленно",
                delta_color="inverse",
            )
    
    with col4:
        processing_time = stats.get('processing_time', 0)
        if processing_time:
            st.metric(
                label="Время обработки",
                value=f"{processing_time:.0f} мс",
            )


def display_filters_sidebar():
    """Отображает боковую панель с фильтрами."""
    with st.sidebar:
        st.header("🔍 Фильтры поиска")
        
        # Текстовый поиск
        query = st.text_input(
            "Поисковый запрос",
            value=st.session_state.search_query,
            placeholder="Например: python разработчик, Москва, senior",
            help="Введите запрос на естественном языке. Можно указать профессию, город, опыт и т.д."
        )
        
        # Кнопка поиска
        col1, col2 = st.columns(2)
        with col1:
            search_button = st.button("🔍 Найти", type="primary", use_container_width=True)
        with col2:
            if st.session_state.search_results:
                clear_button = st.button("🗑️ Очистить", use_container_width=True)
                if clear_button:
                    st.session_state.search_results = None
                    st.session_state.search_query = ""
                    st.rerun()
        
        st.divider()
        
        # Расширенные фильтры
        with st.expander("📊 Расширенные фильтры", expanded=False):
            if st.session_state.filters_data:
                # Город
                areas = st.session_state.filters_data.get('areas', [])
                if areas:
                    area_options = _extract_area_options(areas)
                    selected_area = st.selectbox(
                        "Город",
                        options=[""] + [opt["name"] for opt in area_options],
                        index=0,
                    )
                    if selected_area:
                        area_id = next((opt["id"] for opt in area_options if opt["name"] == selected_area), None)
                        if area_id:
                            st.session_state.search_filters["area"] = area_id
                
                # Опыт
                experience_levels = st.session_state.filters_data.get('experience_levels', [])
                if experience_levels:
                    exp_options = [""] + [exp["name"] for exp in experience_levels]
                    selected_exp = st.selectbox("Опыт работы", options=exp_options, index=0)
                    if selected_exp:
                        exp_id = next((exp["id"] for exp in experience_levels if exp["name"] == selected_exp), None)
                        if exp_id:
                            st.session_state.search_filters["experience"] = exp_id
                
                # График работы
                schedules = st.session_state.filters_data.get('schedules', [])
                if schedules:
                    schedule_options = [""] + [sched["name"] for sched in schedules]
                    selected_schedule = st.selectbox("График работы", options=schedule_options, index=0)
                    if selected_schedule:
                        schedule_id = next((sched["id"] for sched in schedules if sched["name"] == selected_schedule), None)
                        if schedule_id:
                            st.session_state.search_filters["schedule"] = schedule_id
                
                # Зарплата
                salary_min = st.number_input("Зарплата от", min_value=0, value=0, step=10000)
                if salary_min > 0:
                    st.session_state.search_filters["salary"] = salary_min
                
                # Валюта
                currency = st.selectbox("Валюта", options=["RUR", "USD", "EUR"], index=0)
                if salary_min > 0:
                    st.session_state.search_filters["currency"] = currency
            
            # Семантический поиск
            use_semantic = st.checkbox("Использовать семантический поиск", value=True,
                                      help="Включить AI-ранжирование по релевантности")
            st.session_state.search_filters["use_semantic"] = use_semantic
        
        st.divider()
        
        # Информация о системе
        with st.expander("ℹ️ О системе", expanded=False):
            if st.session_state.api_health:
                st.markdown("**Статус API:** ✅ Работает")
                
                # Информация о кэше
                cache = st.session_state.api_health.get('cache', {})
                if cache:
                    hit_rate = cache.get('hit_rate', 0)
                    st.markdown(f"**Hit rate кэша:** {hit_rate:.1%}")
                
                # Зависимости
                deps = st.session_state.api_health.get('dependencies', {})
                for dep_name, dep_info in deps.items():
                    status = dep_info.get('status', 'unknown')
                    icon = "✅" if status == "healthy" else "⚠️" if status == "disabled" else "❌"
                    st.markdown(f"{icon} **{dep_name}:** {status}")
            else:
                st.markdown("**Статус API:** ❌ Недоступен")
            
            st.markdown("---")
            st.markdown("**Career Aggregator 2**")
            st.markdown("Система семантического поиска вакансий")
            st.markdown("Версия: 0.1.0")
            st.markdown("Источник данных: HH.ru API")
        
        return query, search_button


def _extract_area_options(areas: List[Dict[str, Any]], depth: int = 0) -> List[Dict[str, Any]]:
    """Рекурсивно извлекает опции регионов."""
    options = []
    
    for area in areas:
        prefix = "─" * depth + " " if depth > 0 else ""
        options.append({
            "id": area["id"],
            "name": f"{prefix}{area['name']}",
        })
        
        if "areas" in area and area["areas"]:
            options.extend(_extract_area_options(area["areas"], depth + 1))
    
    return options


def display_analytics(results: Dict[str, Any]):
    """Отображает аналитику результатов поиска."""
    if not results or not results.get('vacancies'):
        return
    
    vacancies = results['vacancies']
    
    st.header("📊 Аналитика результатов")
    
    # Создаем DataFrame для анализа
    df_data = []
    for vac in vacancies:
        df_data.append({
            "Название": vac['name'][:50] + "..." if len(vac['name']) > 50 else vac['name'],
            "Компания": vac.get('employer', 'Не указано'),
            "Город": vac.get('area', 'Не указано'),
            "Зарплата от": vac.get('salary', {}).get('from'),
            "Зарплата до": vac.get('salary', {}).get('to'),
            "Опыт": vac.get('experience', 'Не указано'),
            "Релевантность": vac.get('relevance_score', 0),
        })
    
    df = pd.DataFrame(df_data)
    
    # Вкладки с аналитикой
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Распределение", "💰 Зарплаты", "🏙️ Города", "📋 Данные"])
    
    with tab1:
        # Распределение по опыту
        if df['Опыт'].notna().any():
            exp_counts = df['Опыт'].value_counts()
            fig1 = px.pie(
                values=exp_counts.values,
                names=exp_counts.index,
                title="Распределение по опыту работы",
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        # Распределение по релевантности
        if df['Релевантность'].notna().any():
            fig2 = px.histogram(
                df,
                x='Релевантность',
                nbins=20,
                title="Распределение по релевантности",
                labels={'Релевантность': 'Релевантность (0-1)'},
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    with tab2:
        # Анализ зарплат
        salary_df = df[df['Зарплата от'].notna()].copy()
        
        if not salary_df.empty:
            # Средняя зарплата
            avg_salary = salary_df['Зарплата от'].mean()
            st.metric("Средняя зарплата (от)", f"{avg_salary:,.0f} ₽")
            
            # Диаграмма зарплат
            fig3 = px.box(
                salary_df,
                y='Зарплата от',
                title="Распределение зарплат",
                labels={'Зарплата от': 'Зарплата, ₽'},
            )
            st.plotly_chart(fig3, use_container_width=True)
            
            # Зарплата по опыту
            if salary_df['Опыт'].notna().any():
                salary_by_exp = salary_df.groupby('Опыт')['Зарплата от'].mean().sort_values(ascending=False)
                fig4 = px.bar(
                    x=salary_by_exp.index,
                    y=salary_by_exp.values,
                    title="Средняя зарплата по опыту",
                    labels={'x': 'Опыт', 'y': 'Средняя зарплата, ₽'},
                )
                st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Нет данных о зарплатах для анализа")
    
    with tab3:
        # Распределение по городам
        if df['Город'].notna().any():
            city_counts = df['Город'].value_counts().head(10)
            fig5 = px.bar(
                x=city_counts.index,
                y=city_counts.values,
                title="Топ-10 городов по количеству вакансий",
                labels={'x': 'Город', 'y': 'Количество вакансий'},
            )
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("Нет данных о городах для анализа")
    
    with tab4:
        # Таблица с данными
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Релевантность": st.column_config.ProgressColumn(
                    "Релевантность",
                    format="%.2f",
                    min_value=0,
                    max_value=1,
                ),
                "Зарплата от": st.column_config.NumberColumn(
                    "Зарплата от",
                    format="%d ₽",
                ),
                "Зарплата до": st.column_config.NumberColumn(
                    "Зарплата до",
                    format="%d ₽",
                ),
            }
        )
        
        # Кнопка экспорта
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Экспорт в CSV",
            data=csv,
            file_name=f"vacancies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )


def main():
    """Основная функция Streamlit приложения."""
    # Инициализация состояния
    init_session_state()
    
    # Заголовок приложения
    st.title("🔍 Career Aggregator 2")
    st.markdown("### Система семантического поиска вакансий с HH.ru")
    
    # Проверка доступности API
    if not check_api_health():
        st.error("⚠️ API сервер недоступен. Убедитесь, что сервер запущен на localhost:8000")
        st.info("Запустите сервер командой: `uvicorn app.api.main:app --reload`")
        
        if st.button("🔄 Проверить снова"):
            st.rerun()
        
        return
    
    # Загрузка фильтров (один раз при запуске)
    if st.session_state.filters_data is None:
        with st.spinner("Загрузка фильтров..."):
            if not load_filters():
                st.error("Не удалось загрузить фильтры. Попробуйте обновить страницу.")
                return
    
    # Отображение боковой панели с фильтрами
    query, search_button = display_filters_sidebar()
    
    # Основная область контента
    if search_button and query:
        st.session_state.search_query = query
        
        with st.spinner(f"Ищем вакансии по запросу: '{query}'..."):
            # Выполняем поиск
            use_semantic = st.session_state.search_filters.pop("use_semantic", True)
            results = search_vacancies(query, st.session_state.search_filters, use_semantic)
            
            if results:
                st.session_state.search_results = results
                st.session_state.search_stats = {
                    "total_results": results.get("total_results", 0),
                    "returned_results": results.get("returned_results", 0),
                    "cache_hit": results.get("cache_hit", False),
                    "processing_time": results.get("processing_time", 0),
                }
                st.rerun()
    
    # Отображение результатов поиска
    if st.session_state.search_results:
        results = st.session_state.search_results
        
        # Статистика поиска
        display_search_stats(st.session_state.search_stats)
        
        # Параметры поиска
        with st.expander("📋 Параметры поиска", expanded=False):
            if results.get("search_params"):
                params = results["search_params"]
                st.json(params)
        
        # Результаты поиска
        st.header(f"📄 Результаты поиска ({len(results['vacancies'])})")
        
        # Фильтрация результатов
        if results['vacancies']:
            # Слайдер для фильтрации по релевантности
            if any(v.get('relevance_score') for v in results['vacancies']):
                min_relevance = st.slider(
                    "Минимальная релевантность",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.3,
                    step=0.05,
                    help="Фильтровать вакансии по минимальной релевантности"
                )
                
                filtered_vacancies = [
                    v for v in results['vacancies']
                    if v.get('relevance_score', 1.0) >= min_relevance
                ]
            else:
                filtered_vacancies = results['vacancies']
            
            # Отображение вакансий
            if filtered_vacancies:
                for vacancy in filtered_vacancies:
                    display_vacancy_card(vacancy)
                
                # Аналитика
                display_analytics(results)
            else:
                st.warning("Нет вакансий, соответствующих выбранному фильтру релевантности")
        else:
            st.info("По вашему запросу ничего не найдено. Попробуйте изменить параметры поиска.")
    
    # Приветственный экран (когда нет результатов)
    elif not st.session_state.search_results:
        st.markdown("---")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            ### 🚀 Начните поиск вакансий
            
            **Как это работает:**
            1. Введите запрос на естественном языке (например: "python разработчик, Москва, senior")
            2. Используйте фильтры для уточнения поиска
            3. Нажмите кнопку "Найти"
            
            **Особенности системы:**
            - 🤖 **AI-парсинг запросов** - система понимает естественный язык
            - 🧠 **Семантический поиск** - ранжирование по релевантности с использованием эмбеддингов
            - ⚡ **Кэширование** - быстрые повторные запросы
            - 📊 **Аналитика** - визуализация результатов поиска
            
            **Примеры запросов:**
            - "системный аналитик, удаленная работа"
            - "frontend разработчик react, Санкт-Петербург"
            - "менеджер проекта, опыт 3-6 лет"
            - "data scientist, машинное обучение"
            """)
        
        with col2:
            st.markdown("""
            ### 📈 Статистика системы
            
            **Текущий статус:**
            """)
            
            if st.session_state.api_health:
                health = st.session_state.api_health
                
                # Статус API
                st.success(f"✅ API: {health.get('status', 'unknown')}")
                
                # Кэш
                cache = health.get('cache', {})
                if cache:
                    hit_rate = cache.get('hit_rate', 0)
                    st.metric("Hit rate кэша", f"{hit_rate:.1%}")
                
                # Зависимости
                deps = health.get('dependencies', {})
                healthy_deps = sum(1 for d in deps.values() if d.get('status') == 'healthy')
                total_deps = len(deps)
                st.metric("Сервисы", f"{healthy_deps}/{total_deps}")
            
            # Быстрые запросы
            st.markdown("### 🔍 Быстрый поиск")
            
            quick_queries = [
                "python разработчик",
                "системный аналитик",
                "тестировщик",
                "менеджер проекта",
            ]
            
            for q in quick_queries:
                if st.button(q, use_container_width=True):
                    st.session_state.search_query = q
                    st.rerun()
        
        # Информация о HH.ru
        st.markdown("---")
        st.markdown("""
        ### ℹ️ О данных
        
        **Источник данных:** [HH.ru API](https://api.hh.ru/)
        
        **Ограничения:**
        - Максимум 2000 вакансий за запрос
        - Только открытые вакансии
        - Данные обновляются в реальном времени
        
        **Примечание:** Система использует только публичные методы HH.ru API и не требует аутентификации для поиска вакансий.
        """)


if __name__ == "__main__":
    main()
