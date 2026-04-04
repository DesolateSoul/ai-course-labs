# Отчёт по лабораторной работе №2
## Дисциплина: Искусственный интеллект

---
## Общая информация

| Параметр | Значение |
|----------|----------|
| **Студент** | Громов Степан Егорович |
| **Группа** | МОА-221 |
| **Специальность** | Математическое обеспечение и администрирование информационных систем |
| **Тема диплома** | Интеллектуальный модуль для виртуальной автоматической телефонной станции |

---
## 1. Цель работы

Целью лабораторной работы является создание интеллектуального AI-агента с использованием библиотеки LangChain, реализующего паттерн ReAct (Reasoning + Acting). Агент должен поддерживать:
- множество инструментов (поиск, вычисления, специализированные функции)
- краткосрочную и долгосрочную память (семантическая память на ChromaDB)
- механизмы безопасности (guardrails) для фильтрации вредоносных запросов

Работа является подготовительным этапом для создания интеллектуального модуля виртуальной АТС в рамках дипломного проектирования.

---
## 2. Выполненные задачи

- [x] Реализовано ядро агента на LangChain
- [x] Создано минимум 2 инструмента
- [x] Реализован кастомный инструмент для специальности
- [x] Подключена семантическая память (ChromaDB)
- [x] Реализованы guardrails
- [x] Написаны тесты

---
## 3. Ход работы

### 3.1. Архитектура агента

Архитектура агента построена по модульному принципу и включает следующие компоненты:
┌─────────────────────────────────────────────────────────────────┐
│ AI Агент │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│ │ LLM │ │ Memory │ │ Guardrails │ │
│ │ (YandexGPT) │ │ ├─ Working │ │ └─ Input Validation │ │
│ └─────────────┘ │ └─ Semantic │ │ │ │
│ │ (ChromaDB) │ └─────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ Инструменты │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│ │ SearchTool │ │ Calculate │ │ CustomTool │ │
│ │ (поиск) │ │ (кальк.) │ │ (маршрутизация АТС) │ │
│ └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

**Пояснение компонентов:**

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| **LLM** | YandexGPT (LangChain) | Генерация ответов, принятие решений о вызове инструментов |
| **Working Memory** | ConversationBufferMemory | Хранение истории текущего диалога |
| **Semantic Memory** | ChromaDB + sentence-transformers | Долговременное хранение знаний, семантический поиск |
| **Guardrails** | Кастомный валидатор | Фильтрация вредоносных запросов, PII, SQL-инъекций |
| **Tools** | LangChain BaseTool | Расширение возможностей агента |

### 3.2. Реализованные инструменты

| Инструмент | Назначение | Параметры |
|-----------|-----------|-----------|
| **search_web** | Поиск информации в интернете | `query` (str) — поисковый запрос<br>`num_results` (int, 1-10) — кол-во результатов |
| **calculate** | Безопасные математические вычисления | `expression` (str) — выражение<br>`precision` (int, 0-10) — точность |
| **vats_routing_engine** | Маршрутизация вызовов АТС | `caller_number` (str) — номер вызывающего<br>`called_number` (str) — номер получателя<br>`priority` (int, 1-5) — приоритет вызова |

### 3.3. Кастомный инструмент

**Описание инструмента:**

Кастомный инструмент `CustomTool` реализует интеллектуальную маршрутизацию вызовов для виртуальной АТС. Он анализирует входящий вызов (номер вызывающего, номер вызываемого, приоритет) и принимает решение о направлении звонка с учётом:
- типа номера назначения (короткий номер, городской, мобильный)
- времени суток (часы пик повышают приоритет)
- доступности операторов

**Листинг кода (`src/tools/custom_tool.py`):**
"""
Специализированный инструмент для дипломной работы
Лабораторная работа №2
Автор: Громов Степан Егорович
Специальность: Математическое обеспечение и администрирование информационных систем
Тема диплома: Интеллектуальный модуль для виртуальной автоматической телефонной станции
"""
from langchain.tools import BaseTool
from typing import Type, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CustomToolInput(BaseModel):
    """Схема входных параметров для интеллектуальной маршрутизации вызовов АТС."""
    caller_number: str = Field(
        description="Номер вызывающего абонента (в формате: 74951234567)"
    )
    called_number: str = Field(
        description="Номер вызываемого абонента или короткий номер (например: 101)"
    )
    priority: int = Field(
        description="Приоритет вызова (1 - низкий, 5 - высокий)",
        default=3,
        ge=1,
        le=5
    )

class CustomTool(BaseTool):
    """
    Интеллектуальный инструмент маршрутизации вызовов для виртуальной АТС.
    """
    name = "vats_routing_engine"
    description = """
    Инструмент интеллектуальной маршрутизации для виртуальной АТС.
    Используйте для принятия решений о направлении звонка.
    """
    args_schema: Type[BaseModel] = CustomToolInput

    def _run(self, caller_number: str, called_number: str, priority: int = 3) -> str:
        """Основная логика интеллектуальной маршрутизации вызова."""
        logger.info(f"📞 Входящий вызов: {caller_number} -> {called_number} (приоритет {priority})")
        
        # Валидация номеров
        if not self._validate_phone(caller_number) or not self._validate_phone(called_number):
            return "❌ Ошибка: некорректный формат номера."
        
        # Определение типа назначения
        dest_type = self._get_destination_type(called_number)
        
        # Корректировка приоритета по времени
        effective_priority = self._adjust_priority_by_time(priority)
        
        # Выбор маршрута и оператора
        route = self._select_route(dest_type, effective_priority)
        operator = self._assign_operator(effective_priority)
        
        result = {
            "status": "success",
            "caller": caller_number,
            "called": called_number,
            "destination_type": dest_type,
            "effective_priority": effective_priority,
            "route": route,
            "assigned_operator": operator,
            "estimated_wait_time_sec": self._estimate_wait_time(effective_priority)
        }
        return str(result)

    def _validate_phone(self, number: str) -> bool:
        return number.isdigit() and 3 <= len(number) <= 15

    def _get_destination_type(self, number: str) -> str:
        if len(number) <= 5:
            return "short_code"
        elif number.startswith("7495"):
            return "moscow_city"
        elif number.startswith("79") or number.startswith("89"):
            return "mobile"
        return "external"

    def _adjust_priority_by_time(self, priority: int) -> int:
        hour = datetime.now().hour
        if (9 <= hour <= 11) or (18 <= hour <= 20):
            return min(priority + 1, 5)
        if 23 <= hour or hour <= 6:
            return max(priority - 1, 1)
        return priority

    def _select_route(self, dest_type: str, priority: int) -> str:
        routes = {
            "short_code": "🔴 Прямое подключение к экстренной службе",
            "moscow_city": "🏢 Маршрут через городскую АТС",
            "mobile": "📱 Маршрут через мобильного оператора",
            "external": "🌐 Маршрут через межгород"
        }
        base = routes.get(dest_type, "🔄 Стандартный маршрут")
        return f"{base} (приоритетная линия)" if priority >= 4 else base

    def _assign_operator(self, priority: int) -> str:
        if priority >= 4:
            return "Старший оператор"
        elif priority == 3:
            return "Обычный оператор"
        return "Автоинформатор (IVR)"

    def _estimate_wait_time(self, priority: int) -> int:
        return {5: 0, 4: 2, 3: 5, 2: 10, 1: 15}.get(priority, 10)

    async def _arun(self, caller_number: str, called_number: str, priority: int = 3) -> str:
        return self._run(caller_number, called_number, priority)

    def to_langchain_tool(self) -> BaseTool:
        return self

\# Тестирование инструмента
tool = CustomTool()

# Экстренный вызов на 112
result = tool.run(caller_number="74951234567", called_number="112", priority=5)
print(result)
# Вывод: {'status': 'success', 'route': '🔴 Прямое подключение к экстренной службе (приоритетная линия)', ...}

\### 3.4. Тестирование

\<img width="758" height="295" alt="image" src="https://github.com/user-attachments/assets/03fc18a1-08d3-4141-8804-bb45e5a7011b" />


\<img width="1800" height="531" alt="image" src="https://github.com/user-attachments/assets/1706dbe5-49d2-4003-8e4f-841cd4752aa9" />


\### 3.5. Интеграция с дипломом

\Материалы лабораторной работы будут использованы в дипломном проекте следующим образом:

Архитектура агента → основа для интеллектуального модуля АТС

Паттерн ReAct → для принятия решений о маршрутизации вызовов

Семантическая память → для хранения истории обращений клиентов

Кастомный инструмент → прототип модуля маршрутизации

Guardrails → для фильтрации спама и вредоносных запросов

Планируемое развитие:

Интеграция с реальной SIP-инфраструктурой

Обучение модели на данных о звонках

Добавление распознавания речи (ASR) и синтеза речи (TTS)

\---

\## 4. Результаты

| Критерий | Статус |

|----------|--------|

| Агент работает | ✅ |

| Инструменты созданы | ✅ |

| Память подключена | ✅ |

| Guardrails реализованы | ✅ |

| Код в GitHub | ✅ |

\---

\## 5. Выводы

\Что изучено в ходе работы:

Архитектура AI-агентов на базе LangChain

Паттерн ReAct (Reasoning + Acting) для принятия решений

Работа с векторными базами данных (ChromaDB, embeddings)

Создание кастомных инструментов для расширения функциональности

Механизмы безопасности для LLM-приложений (guardrails)

Трудности:

Настройка мультиязычных embeddings для русского языка

Безопасное выполнение математических выражений без eval()

Планы по развитию:
Интеграция с реальными API (Yandex Search, SIP-сервер)

Добавление большего количества инструментов для АТС

Разработка веб-интерфейса для взаимодействия с агентом
\---

\## 6. Список источников

. . .

