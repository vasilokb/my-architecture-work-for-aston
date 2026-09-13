"""
Сервис для работы с эмбеддингами текста.

Этот модуль предоставляет функциональность для преобразования текста
в векторные представления (эмбеддинги) с использованием моделей
Sentence-Transformers и расчета семантического сходства.
"""

import asyncio
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.core.logging import log_function_call
from app.models.hh import Vacancy, VacancyWithEmbedding


class EmbeddingServiceError(Exception):
    """Базовое исключение для ошибок сервиса эмбеддингов."""
    pass


class EmbeddingModelNotLoadedError(EmbeddingServiceError):
    """Исключение при попытке использовать не загруженную модель."""
    pass


class EmbeddingService:
    """
    Сервис для работы с эмбеддингами текста.
    
    Обеспечивает:
    - Загрузку и кэширование моделей Sentence-Transformers
    - Преобразование текста в векторные представления
    - Расчет семантического сходства между текстами
    - Ранжирование вакансий по релевантности запросу
    """
    
    def __init__(self):
        """Инициализирует сервис эмбеддингов."""
        self.model: Optional[SentenceTransformer] = None
        self.model_name = settings.embedding_model
        self.device = settings.embedding_device
        self.dimension = settings.embedding_dimension
        self.normalize = settings.embedding_normalize
        self.cache_dir = settings.embedding_cache_dir
        
        logger.info(
            f"Инициализация сервиса эмбеддингов. "
            f"Модель: {self.model_name}, Устройство: {self.device}"
        )
    
    async def initialize(self):
        """
        Асинхронно инициализирует сервис (загружает модель).
        
        Этот метод должен быть вызван перед использованием сервиса.
        """
        if self.model is not None:
            logger.debug("Модель эмбеддингов уже загружена")
            return
        
        logger.info(f"Загрузка модели эмбеддингов: {self.model_name}")
        
        try:
            # Загружаем модель в отдельном потоке, чтобы не блокировать event loop
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                self._load_model
            )
            
            logger.info(
                f"Модель эмбеддингов загружена успешно. "
                f"Размерность: {self.model.get_sentence_embedding_dimension()}"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели эмбеддингов: {e}")
            raise EmbeddingServiceError(f"Не удалось загрузить модель: {e}")
    
    def _load_model(self) -> SentenceTransformer:
        """
        Синхронно загружает модель Sentence-Transformers.
        
        Returns:
            Загруженная модель SentenceTransformer
        """
        return SentenceTransformer(
            self.model_name,
            device=self.device,
            cache_folder=self.cache_dir,
        )
    
    @log_function_call
    async def encode_text(self, text: str) -> List[float]:
        """
        Преобразует текст в векторное представление.
        
        Args:
            text: Текст для кодирования
        
        Returns:
            Векторное представление текста (эмбеддинг)
        
        Raises:
            EmbeddingModelNotLoadedError: Если модель не загружена
        """
        if self.model is None:
            raise EmbeddingModelNotLoadedError("Модель эмбеддингов не загружена")
        
        if not text or not text.strip():
            logger.warning("Пустой текст передан для кодирования")
            return [0.0] * self.dimension
        
        try:
            # Кодируем текст в отдельном потоке
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.model.encode(
                    text,
                    normalize_embeddings=self.normalize,
                    show_progress_bar=False,
                )
            )
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Ошибка при кодировании текста: {e}")
            raise EmbeddingServiceError(f"Ошибка кодирования текста: {e}")
    
    @log_function_call
    async def encode_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Преобразует список текстов в векторные представления.
        
        Args:
            texts: Список текстов для кодирования
        
        Returns:
            Список векторных представлений
        
        Raises:
            EmbeddingModelNotLoadedError: Если модель не загружена
        """
        if self.model is None:
            raise EmbeddingModelNotLoadedError("Модель эмбеддингов не загружена")
        
        if not texts:
            return []
        
        # Фильтруем пустые тексты
        valid_texts = [text for text in texts if text and text.strip()]
        if not valid_texts:
            return []
        
        try:
            # Кодируем тексты батчами в отдельном потоке
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.encode(
                    valid_texts,
                    normalize_embeddings=self.normalize,
                    show_progress_bar=False,
                    batch_size=32,
                )
            )
            
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"Ошибка при кодировании текстов: {e}")
            raise EmbeddingServiceError(f"Ошибка кодирования текстов: {e}")
    
    @log_function_call
    async def calculate_similarity(
        self,
        query_embedding: List[float],
        document_embeddings: List[List[float]],
    ) -> List[float]:
        """
        Вычисляет косинусное сходство между запросом и документами.
        
        Args:
            query_embedding: Эмбеддинг запроса
            document_embeddings: Список эмбеддингов документов
        
        Returns:
            Список scores сходства для каждого документа
        """
        if not document_embeddings:
            return []
        
        try:
            # Преобразуем в numpy массивы для вычислений
            query_array = np.array(query_embedding).reshape(1, -1)
            docs_array = np.array(document_embeddings)
            
            # Вычисляем косинусное сходство
            similarities = cosine_similarity(query_array, docs_array)
            
            # Преобразуем в список и нормализуем (если нужно)
            scores = similarities[0].tolist()
            
            return scores
            
        except Exception as e:
            logger.error(f"Ошибка при вычислении сходства: {e}")
            raise EmbeddingServiceError(f"Ошибка вычисления сходства: {e}")
    
    @log_function_call
    async def rank_vacancies_by_relevance(
        self,
        query: str,
        vacancies: List[Vacancy],
        threshold: Optional[float] = None,
    ) -> List[VacancyWithEmbedding]:
        """
        Ранжирует вакансии по релевантности запросу.
        
        Args:
            query: Поисковый запрос
            vacancies: Список вакансий для ранжирования
            threshold: Порог релевантности (вакансии с score ниже отфильтровываются)
        
        Returns:
            Отсортированный список вакансий с scores релевантности
        """
        if not vacancies:
            return []
        
        if threshold is None:
            threshold = settings.relevance_threshold
        
        logger.info(
            f"Ранжирование {len(vacancies)} вакансий по запросу: '{query[:50]}...'"
        )
        
        try:
            # Шаг 1: Подготавливаем тексты для кодирования
            vacancy_texts = []
            for vacancy in vacancies:
                # Создаем текстовое представление вакансии
                text_parts = []
                
                if vacancy.name:
                    text_parts.append(vacancy.name)
                
                if vacancy.description:
                    # Берем только начало описания для экономии токенов
                    text_parts.append(vacancy.short_description)
                
                if vacancy.key_skills:
                    text_parts.append(" ".join(vacancy.key_skills[:5]))
                
                vacancy_text = " ".join(text_parts)
                vacancy_texts.append(vacancy_text)
            
            # Шаг 2: Кодируем запрос и вакансии
            query_embedding = await self.encode_text(query)
            vacancy_embeddings = await self.encode_texts(vacancy_texts)
            
            if not vacancy_embeddings:
                logger.warning("Не удалось получить эмбеддинги для вакансий")
                return []
            
            # Шаг 3: Вычисляем сходство
            similarity_scores = await self.calculate_similarity(
                query_embedding,
                vacancy_embeddings,
            )
            
            # Шаг 4: Создаем список вакансий с scores
            ranked_vacancies = []
            for i, (vacancy, score) in enumerate(zip(vacancies, similarity_scores)):
                if score >= threshold:
                    ranked_vacancy = VacancyWithEmbedding(
                        **vacancy.dict(),
                        embedding=vacancy_embeddings[i],
                        relevance_score=score,
                    )
                    ranked_vacancies.append(ranked_vacancy)
            
            # Шаг 5: Сортируем по убыванию релевантности
            ranked_vacancies.sort(key=lambda x: x.relevance_score or 0.0, reverse=True)
            
            logger.info(
                f"Ранжирование завершено. "
                f"Всего вакансий: {len(vacancies)}, "
                f"После фильтрации: {len(ranked_vacancies)}, "
                f"Лучший score: {ranked_vacancies[0].relevance_score if ranked_vacancies else 0:.3f}"
            )
            
            return ranked_vacancies
            
        except Exception as e:
            logger.error(f"Ошибка при ранжировании вакансий: {e}")
            raise EmbeddingServiceError(f"Ошибка ранжирования вакансий: {e}")
    
    @log_function_call
    async def find_similar_vacancies(
        self,
        reference_vacancy: Vacancy,
        vacancies: List[Vacancy],
        top_k: int = 10,
    ) -> List[Tuple[Vacancy, float]]:
        """
        Находит вакансии, похожие на reference вакансию.
        
        Args:
            reference_vacancy: Референсная вакансия
            vacancies: Список вакансий для поиска похожих
            top_k: Количество наиболее похожих вакансий для возврата
        
        Returns:
            Список пар (вакансия, score сходства)
        """
        if not vacancies:
            return []
        
        try:
            # Создаем текстовое представление reference вакансии
            ref_text_parts = []
            if reference_vacancy.name:
                ref_text_parts.append(reference_vacancy.name)
            if reference_vacancy.description:
                ref_text_parts.append(reference_vacancy.short_description)
            if reference_vacancy.key_skills:
                ref_text_parts.append(" ".join(reference_vacancy.key_skills))
            
            ref_text = " ".join(ref_text_parts)
            
            # Ранжируем вакансии по сходству с reference
            ranked = await self.rank_vacancies_by_relevance(
                query=ref_text,
                vacancies=vacancies,
                threshold=0.0,  # Без порога
            )
            
            # Возвращаем top_k результатов
            result = [
                (Vacancy(**v.dict(exclude={"embedding", "relevance_score"})), v.relevance_score or 0.0)
                for v in ranked[:top_k]
            ]
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при поиске похожих вакансий: {e}")
            raise EmbeddingServiceError(f"Ошибка поиска похожих вакансий: {e}")
    
    async def close(self):
        """Освобождает ресурсы сервиса."""
        # SentenceTransformer не требует явного закрытия,
        # но мы можем очистить кэш если нужно
        self.model = None
        logger.debug("Сервис эмбеддингов закрыт")


# Фабрика для создания сервиса
async def get_embedding_service() -> EmbeddingService:
    """
    Возвращает экземпляр сервиса эмбеддингов.
    
    Используется для dependency injection.
    """
    service = EmbeddingService()
    await service.initialize()
    return service