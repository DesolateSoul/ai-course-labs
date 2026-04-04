# -*- coding: utf-8 -*-
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
import random
from datetime import datetime

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 1: Определите схему входных параметров (под АТС)
# ═════════════════════════════════════════════════════════════════════════════
class CustomToolInput(BaseModel):
    """
    Схема входных параметров для интеллектуальной маршрутизации вызовов АТС.
    """
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

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 2: Реализуйте класс инструмента для АТС
# ═════════════════════════════════════════════════════════════════════════════
class CustomTool(BaseTool):
    """
    Интеллектуальный инструмент маршрутизации вызовов для виртуальной АТС.

    Назначение:
    Анализирует входящий вызов (номер вызывающего, номер вызываемого, приоритет)
    и принимает решение о маршрутизации: куда направить вызов, какой голосовой
    сценарий активировать, есть ли доступные операторы.

    Интеграция с дипломом:
    Инструмент имитирует работу модуля интеллектуальной маршрутизации,
    который является ключевым компонентом виртуальной АТС. Может быть расширен
    для использования с реальными SIP-серверами и ML-моделями приоритизации.
    """

    # Обязательные атрибуты
    name = "vats_routing_engine"
    description = """
    Инструмент интеллектуальной маршрутизации для виртуальной АТС.
    Используйте для принятия решений о направлении звонка.

    Параметры:
    - caller_number: номер вызывающего (например: '74951234567')
    - called_number: номер получателя или короткий номер ('102', '112')
    - priority: целое число от 1 до 5 (чем выше, тем важнее вызов)

    Возвращает JSON с решением: маршрут, назначенный оператор, задержку.
    """
    args_schema: Type[BaseModel] = CustomToolInput

    def _run(self, caller_number: str, called_number: str, priority: int = 3) -> str:
        """
        Основная логика интеллектуальной маршрутизации вызова.

        Args:
            caller_number: Номер вызывающего абонента
            called_number: Номер вызываемого абонента
            priority: Приоритет вызова (1-5)

        Returns:
            str: Результат маршрутизации в читаемом формате
        """
        logger.info(f"📞 Входящий вызов: {caller_number} -> {called_number} (приоритет {priority})")

        # Шаг 1: Проверка корректности номеров
        if not self._validate_phone(caller_number) or not self._validate_phone(called_number):
            return "❌ Ошибка: некорректный формат номера. Используйте только цифры."

        # Шаг 2: Определяем тип номера назначения
        dest_type = self._get_destination_type(called_number)

        # Шаг 3: Вычисляем приоритет с учётом времени суток
        effective_priority = self._adjust_priority_by_time(priority)

        # Шаг 4: Выбираем маршрут и оператора
        route = self._select_route(dest_type, effective_priority)
        operator = self._assign_operator(effective_priority)

        # Шаг 5: Формируем результат
        result = {
            "status": "success",
            "caller": caller_number,
            "called": called_number,
            "destination_type": dest_type,
            "effective_priority": effective_priority,
            "route": route,
            "assigned_operator": operator,
            "estimated_wait_time_sec": self._estimate_wait_time(effective_priority),
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"✅ Маршрутизация завершена: {route}")
        return str(result)

    # ═════════════════════════════════════════════════════════════════════════
    # Вспомогательные методы (интеллектуальная логика АТС)
    # ═════════════════════════════════════════════════════════════════════════

    def _validate_phone(self, number: str) -> bool:
        """Проверка номера: только цифры, длина от 3 до 15 символов."""
        return number.isdigit() and 3 <= len(number) <= 15

    def _get_destination_type(self, number: str) -> str:
        """Определяет тип назначения: короткий номер, городской, мобильный."""
        if len(number) <= 5:
            return "short_code"   # Короткий номер (101, 102, 112)
        elif number.startswith("7495"):
            return "moscow_city"  # Московский городской
        elif number.startswith("79") or number.startswith("89"):
            return "mobile"       # Мобильный
        else:
            return "external"     # Другой регион/город

    def _adjust_priority_by_time(self, priority: int) -> int:
        """Корректировка приоритета в зависимости от времени суток."""
        hour = datetime.now().hour
        # В часы пик (9-11, 18-20) повышаем приоритет
        if (9 <= hour <= 11) or (18 <= hour <= 20):
            adjusted = min(priority + 1, 5)
            logger.info(f"⏰ Часы пик, приоритет повышен: {priority} -> {adjusted}")
            return adjusted
        # Ночью (23-6) понижаем приоритет неэкстренных вызовов
        if 23 <= hour or hour <= 6:
            adjusted = max(priority - 1, 1)
            logger.info(f"🌙 Ночное время, приоритет понижен: {priority} -> {adjusted}")
            return adjusted
        return priority

    def _select_route(self, dest_type: str, priority: int) -> str:
        """Выбор маршрута на основе типа назначения и приоритета."""
        routes = {
            "short_code": "🔴 Прямое подключение к экстренной службе",
            "moscow_city": "🏢 Маршрут через городскую АТС",
            "mobile": "📱 Маршрут через мобильного оператора",
            "external": "🌐 Маршрут через межгород"
        }
        base_route = routes.get(dest_type, "🔄 Стандартный маршрут")

        if priority >= 4:
            return f"{base_route} (приоритетная линия)"
        return base_route

    def _assign_operator(self, priority: int) -> str:
        """Назначение оператора в зависимости от приоритета."""
        if priority >= 4:
            return "Старший оператор (свободная линия)"
        elif priority == 3:
            return "Обычный оператор (может быть очередь)"
        else:
            return "Автоинформатор (IVR)"

    def _estimate_wait_time(self, priority: int) -> int:
        """Оценка времени ожидания в секундах (чем выше приоритет, тем меньше ждать)."""
        wait_map = {5: 0, 4: 2, 3: 5, 2: 10, 1: 15}
        return wait_map.get(priority, 10)

    async def _arun(self, caller_number: str, called_number: str, priority: int = 3) -> str:
        """Асинхронная версия (для высоконагруженных АТС)."""
        # Для демонстрации просто вызываем синхронную версию
        return self._run(caller_number, called_number, priority)

    def to_langchain_tool(self) -> BaseTool:
        """Конвертация в формат LangChain."""
        return self

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 3: Пример использования (для тестирования)
# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    tool = CustomTool()

    print("=" * 60)
    print("Тестирование интеллектуального модуля виртуальной АТС")
    print("=" * 60)

    # Тест 1: Вызов на короткий номер (экстренная служба)
    result1 = tool.run(caller_number="74951234567", called_number="112", priority=5)
    print("\n📞 Тест 1 (экстренный вызов):")
    print(result1)

    # Тест 2: Обычный городской вызов
    result2 = tool.run(caller_number="74959998877", called_number="74952223344", priority=2)
    print("\n📞 Тест 2 (городской вызов):")
    print(result2)

    # Тест 3: Некорректный номер
    result3 = tool.run(caller_number="abc", called_number="123", priority=3)
    print("\n📞 Тест 3 (ошибочный номер):")
    print(result3)