# -*- coding: utf-8 -*-
"""
Ядро AI-агента с поддержкой инструментов и памяти
Лабораторная работа №2
Дисциплина: Искусственный интеллект
Автор: Громов Степан Егорович
Группа: МОАИС-01-21
Специальность: Математическое обеспечение и администрирование информационных систем
Тема диплома: Интеллектуальный модуль для виртуальной автоматической телефонной станции
Дата: 2026
"""
import os
import sys
import json
import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import time

from langchain.agents import initialize_agent, AgentType, Tool
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, SystemMessage

# Локальные импорты
from tools.search_tool import SearchTool
from tools.calc_tool import CalculateTool
from tools.custom_tool import CustomTool  # Адаптированный инструмент для АТС
from memory.working_memory import WorkingMemory
from memory.semantic_memory import SemanticMemory
from guardrails.input_validator import InputGuardrails

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """
    Конфигурация AI-агента.

    Атрибуты:
        name: Имя агента
        version: Версия агента
        max_iterations: Максимальное количество итераций ReAct
        temperature: Параметр креативности LLM
        memory_enabled: Флаг включения памяти
        guardrails_enabled: Флаг включения защиты
        verbose: Режим подробного логирования
    """
    name: str = "VATSRoutingAssistant"
    version: str = "2.0"
    max_iterations: int = 10
    temperature: float = 0.7
    memory_enabled: bool = True
    guardrails_enabled: bool = True
    verbose: bool = True


@dataclass
class AgentResponse:
    """
    Структурированный ответ агента.

    Атрибуты:
        success: Флаг успешного выполнения
        answer: Текстовый ответ
        steps: Список выполненных шагов
        duration_ms: Время выполнения в миллисекундах
        tokens_used: Оценка использованных токенов
        error: Сообщение об ошибке (если есть)
    """
    success: bool
    answer: str
    steps: List[Dict]
    duration_ms: int
    tokens_used: int
    error: Optional[str] = None


class AIAgent:
    """
    Основной класс AI-агента для интеллектуальной маршрутизации АТС.

    Реализует архитектуру с поддержкой:
    • Множественных инструментов (поиск, калькулятор, маршрутизация АТС)
    • Краткосрочной и долгосрочной памяти
    • Механизмов безопасности (guardrails)
    • Паттерна ReAct для принятия решений

    Пример использования:
    >>> agent = AIAgent()
    >>> response = agent.run("Маршрутизируй вызов с 74951234567 на 112")
    >>> print(response.answer)
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Инициализация AI-агента.

        Args:
            config: Конфигурация агента (опционально, используется default)

        Raises:
            ValueError: Если не найдены необходимые переменные окружения
        """
        self.config = config or AgentConfig()
        logger.info(f"Инициализация агента: {self.config.name} v{self.config.version}")

        # Инициализация LLM
        self.llm = self._init_llm()
        logger.info("LLM инициализирован")

        # Инициализация инструментов
        self.tools = self._init_tools()
        logger.info(f"Доступно инструментов: {len(self.tools)}")

        # Инициализация памяти
        self.working_memory = None
        self.semantic_memory = None
        if self.config.memory_enabled:
            self.working_memory = WorkingMemory()
            self.semantic_memory = SemanticMemory()
            logger.info("Память активирована (рабочая + семантическая)")

        # Инициализация guardrails
        self.guardrails = None
        if self.config.guardrails_enabled:
            self.guardrails = InputGuardrails()
            logger.info("Guardrails активированы")

        # Инициализация LangChain-агента
        self.agent = self._init_agent()
        logger.info("Агент готов к работе")

        # Статистика
        self.request_count = 0
        self.total_tokens = 0

    def _init_llm(self):
        """
        Инициализация LLM-клиента (YandexGPT).

        Returns:
            YandexGPTLangChain: Настроенный клиент LLM

        Raises:
            ValueError: Если не найдены учётные данные
        """
        from langchain_community.llms import YandexGPT

        iam_token = os.getenv("YANDEX_IAM_TOKEN")
        folder_id = os.getenv("YANDEX_FOLDER_ID")

        if not iam_token or not folder_id:
            logger.warning(
                "Не найдены YANDEX_IAM_TOKEN или YANDEX_FOLDER_ID. "
                "Используется имитация LLM для тестирования."
            )
            # Имитация LLM для тестирования (если нет токена)
            from langchain.llms.fake import FakeListLLM
            responses = [
                "Я проанализировал запрос. Для маршрутизации вызова на АТС необходимо определить приоритет и тип номера.",
                "Результат маршрутизации: вызов направлен на экстренную службу с высоким приоритетом.",
                f"Поиск завершён. Информация найдена."
            ]
            return FakeListLLM(responses=responses)

        return YandexGPT(
            iam_token=iam_token,
            folder_id=folder_id,
            temperature=self.config.temperature,
            max_tokens=1000
        )

    def _init_tools(self) -> List[Tool]:
        """
        Инициализация инструментов агента.

        Returns:
            List[Tool]: Список доступных инструментов
        """
        tools = [
            SearchTool().to_langchain_tool(),
            CalculateTool().to_langchain_tool(),
            CustomTool().to_langchain_tool(),  # Инструмент маршрутизации АТС
        ]
        
        for tool in tools:
            logger.info(f"Зарегистрирован инструмент: {tool.name}")
        
        return tools

    def _init_agent(self):
        """
        Инициализация LangChain-агента.

        Returns:
            AgentExecutor: Настроенный агент LangChain
        """
        memory = None
        if self.working_memory:
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                max_token_limit=4000
            )

        return initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            memory=memory,
            verbose=self.config.verbose,
            max_iterations=self.config.max_iterations,
            handle_parsing_errors=True
        )

    def run(self, query: str, session_id: Optional[str] = None) -> AgentResponse:
        """
        Выполнение запроса к агенту.

        Args:
            query: Текстовый запрос пользователя
            session_id: Идентификатор сессии (опционально)

        Returns:
            AgentResponse: Структурированный ответ агента
        """
        start_time = time.time()
        session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"📨 Новый запрос: {query[:100]}...")

        # Проверка безопасности входа
        if self.guardrails:
            security_check = self.guardrails.validate_input(query)
            if not security_check.is_safe:
                logger.warning(f"⛔ Запрос отклонён guardrails: {security_check.reason}")
                return AgentResponse(
                    success=False,
                    answer="Запрос отклонён системой безопасности.",
                    steps=[],
                    duration_ms=0,
                    tokens_used=0,
                    error=security_check.reason
                )

        try:
            # Выполнение запроса через агента LangChain
            logger.info("🔄 Выполнение запроса через агента...")
            result = self.agent.run(query)

            # Сохранение в рабочую память (краткосрочную)
            if self.working_memory:
                self.working_memory.add_message("user", query)
                self.working_memory.add_message("assistant", result)
                logger.debug("Сохранено в рабочую память")

            # Сохранение в семантическую память (долгосрочную)
            if self.semantic_memory and session_id:
                self.semantic_memory.add_document(
                    content=f"Query: {query}\nAnswer: {result}",
                    metadata={
                        "session_id": session_id,
                        "type": "interaction",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                logger.debug("Сохранено в семантическую память")

            # Формирование ответа
            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)

            self.request_count += 1
            tokens_used = self._estimate_tokens(query, result)
            self.total_tokens += tokens_used

            response = AgentResponse(
                success=True,
                answer=result,
                steps=self._extract_steps(),
                duration_ms=duration_ms,
                tokens_used=tokens_used
            )

            logger.info(f"✅ Запрос выполнен за {duration_ms}мс, токенов: {tokens_used}")
            return response

        except Exception as e:
            logger.error(f"❌ Ошибка выполнения: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                answer="Произошла ошибка при обработке запроса.",
                steps=[],
                duration_ms=0,
                tokens_used=0,
                error=str(e)
            )

    def _extract_steps(self) -> List[Dict]:
        """
        Извлечение шагов выполнения из истории агента.

        Returns:
            List[Dict]: Список шагов ReAct
        """
        # В production: парсинг логов LangChain
        # Для текущей версии возвращаем пустой список
        return []

    def _estimate_tokens(self, input_text: str, output_text: str) -> int:
        """
        Оценка количества использованных токенов.

        Args:
            input_text: Входной текст
            output_text: Выходной текст

        Returns:
            int: Приблизительное количество токенов
        """
        # Приблизительно: 1 токен ≈ 4 символа для русского языка
        # Плюс служебные токены для инструментов
        input_tokens = len(input_text) // 4
        output_tokens = len(output_text) // 4
        tool_overhead = 50  # Примерная оценка на вызовы инструментов
        
        return input_tokens + output_tokens + tool_overhead

    def get_stats(self) -> Dict:
        """
        Получение статистики агента.

        Returns:
            Dict: Статистика использования
        """
        stats = {
            "name": self.config.name,
            "version": self.config.version,
            "tools_count": len(self.tools),
            "memory_enabled": self.config.memory_enabled,
            "guardrails_enabled": self.config.guardrails_enabled,
            "request_count": self.request_count,
            "total_tokens": self.total_tokens
        }
        
        # Добавляем статистику семантической памяти
        if self.semantic_memory:
            stats["semantic_memory"] = self.semantic_memory.get_stats()
        
        return stats

    def save_session(self, session_id: str) -> bool:
        """
        Сохранение текущей сессии в долговременную память.

        Args:
            session_id: Идентификатор сессии

        Returns:
            bool: Успешность сохранения
        """
        if self.working_memory and self.semantic_memory:
            messages = self.working_memory.get_messages()
            content = str(messages)
            self.semantic_memory.add_document(
                content=content,
                metadata={
                    "session_id": session_id,
                    "type": "full_session",
                    "timestamp": datetime.now().isoformat()
                }
            )
            logger.info(f"Сессия {session_id} сохранена")
            return True
        return False

    def clear_memory(self) -> None:
        """Очистка рабочей памяти агента."""
        if self.working_memory:
            self.working_memory.clear()
            logger.info("Рабочая память очищена")


# Точка входа для тестирования
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 80)
    print("ЛАБОРАТОРНАЯ РАБОТА №2")
    print("Интеллектуальный модуль для виртуальной АТС")
    print("Автор: Громов Степан Егорович")
    print("Специальность: Математическое обеспечение и администрирование ИС")
    print("=" * 80)

    # Создание агента
    agent = AIAgent()

    # Вывод статистики
    print("\n📊 Статистика агента:")
    stats = agent.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Тестовые запросы
    test_queries = [
        "Маршрутизируй вызов с номера 74951234567 на номер 112 с высоким приоритетом",
        "Сколько будет (15 + 25) * 4?",
        "Найди информацию о последних обновлениях YandexGPT",
        "Что такое виртуальная АТС и как она работает?"
    ]

    print("\n" + "=" * 80)
    print("ТЕСТИРОВАНИЕ АГЕНТА")
    print("=" * 80)

    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Тест {i}: {query}")
        print("-" * 50)
        
        response = agent.run(query)
        
        print(f"\n🤖 Ответ агента:")
        print(response.answer[:500])  # Ограничиваем вывод
        print(f"\n⏱️ Время: {response.duration_ms}мс | Токены: {response.tokens_used}")
        
        if response.error:
            print(f"❌ Ошибка: {response.error}")
        
        print("-" * 50)

    # Финальная статистика
    print("\n" + "=" * 80)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 80)
    final_stats = agent.get_stats()
    for key, value in final_stats.items():
        print(f"   {key}: {value}")
    print("=" * 80)
