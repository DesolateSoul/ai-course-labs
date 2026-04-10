# -*- coding: utf-8 -*-
"""
Интеллектуальный агент для виртуальной АТС
Лабораторная работа №3
Автор: Громов Степан Егорович
Специальность: Математическое обеспечение и администрирование информационных систем
Тема диплома: Интеллектуальный модуль для виртуальной автоматической телефонной станции
"""
from typing import Dict, Optional, List, Any
import time
import logging
from datetime import datetime
import random
from base_agent import BaseAgent, AgentConfig

logger = logging.getLogger(__name__)


class SmartASTAgent(BaseAgent):
    """
    Интеллектуальный агент для виртуальной автоматической телефонной станции (АТС).

    Назначение:
    Обеспечение интеллектуальной маршрутизации вызовов, анализа звонков,
    прогнозирования нагрузки и оптимизации распределения ресурсов
    на виртуальной АТС.

    Возможности:
    • Интеллектуальная маршрутизация вызовов на основе контекста
    • Анализ качества звонков (ASR, ACD, NER)
    • Прогнозирование нагрузки на АТС
    • Обнаружение аномалий и мошеннических звонков
    • Автоматическая классификация абонентов

    Интеграция с дипломом:
    Агент используется в практической части дипломной работы
    для разработки интеллектуального модуля виртуальной АТС,
    обеспечивающего автоматическую маршрутизацию и анализ вызовов
    в real-time режиме.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        default_config = AgentConfig(
            role="Интеллектуальный диспетчер АТС",
            goal="Оптимизировать маршрутизацию вызовов и управление ресурсами АТС",
            backstory="""Вы — опытный специалист по телекоммуникациям 
            и интеллектуальным системам с expertise в области виртуальных АТС, 
            VoIP-технологий и алгоритмов маршрутизации. Вы умеете анализировать 
            паттерны звонков, прогнозировать нагрузку и принимать оптимальные 
            решения в реальном времени."""
        )

        if config:
            default_config.role = config.role
            default_config.goal = config.goal
            default_config.backstory = config.backstory

        super().__init__(default_config)

        # Специфичные атрибуты для АТС
        self.call_history = []
        self.route_decisions = []
        self.quality_metrics = {}
        self.anomaly_detections = []
        self.operator_availability = {}
        self.current_calls = []

    def execute_task(self, task_description: str, context: Optional[Dict] = None) -> Dict:
        """
        Выполнение задачи интеллектуальной обработки вызовов.

        Args:
            task_description: Описание задачи (тип звонка, параметры)
            context: Контекст (информация о звонке, операторах)

        Returns:
            Dict: Результаты интеллектуальной обработки
        """
        start_time = time.time()
        self.state.current_task = task_description

        logger.info(f"Интеллектуальный агент АТС начинает задачу: {task_description[:100]}...")

        results = {
            "task": task_description,
            "status": "completed",
            "call_routing": self._intelligent_routing(task_description, context),
            "call_analysis": self._analyze_call(task_description, context),
            "load_prediction": self._predict_system_load(context),
            "anomaly_detection": self._detect_anomalies(context),
            "recommendations": self._generate_optimization_recommendations(task_description),
            "execution_time": 0
        }

        results["execution_time"] = time.time() - start_time

        self.state.completed_tasks.append(task_description)
        self.statistics["tasks_completed"] += 1
        self.statistics["total_execution_time"] += results["execution_time"]

        # Сохранение звонка в историю
        if context:
            self.call_history.append({
    "timestamp": datetime.now().isoformat(),
    "task": task_description,
    "routing_decision": results["call_routing"].get("selected_operator"),
    "quality_score": results["call_analysis"].get("quality_metrics", {}).get("mos", 0)  # ← число
})

        logger.info(f"Интеллектуальная обработка завершена за {results['execution_time']:.2f}с")

        return results

    def _intelligent_routing(self, task: str, context: Optional[Dict]) -> Dict:
        """
        Интеллектуальная маршрутизация вызова.

        Алгоритм:
        1. Анализ контекста звонка
        2. Определение приоритета
        3. Выбор оптимального оператора
        """
        if not context:
            context = {}

        caller_id = context.get("caller_id", "unknown")
        caller_type = context.get("caller_type", "regular")  # regular, vip, technical
        required_skill = context.get("required_skill", "general")
        call_priority = context.get("priority", 1)  # 1-5, где 5 - наивысший

        # Симуляция доступности операторов
        available_operators = self._get_available_operators()

        # Алгоритм выбора оператора
        selected_operator = None
        selection_score = 0

        for operator in available_operators:
            score = 0
            # Учёт квалификации
            if required_skill in operator.get("skills", []):
                score += 3
            # Учёт загрузки
            score += (5 - operator.get("current_load", 0))
            # Приоритет VIP
            if caller_type == "vip":
                score += operator.get("vip_experience", 0) * 2

            if score > selection_score:
                selection_score = score
                selected_operator = operator

        # Генерация маршрута
        routing_result = {
            "call_id": f"call_{int(time.time())}_{random.randint(1000, 9999)}",
            "caller_id": caller_id,
            "caller_type": caller_type,
            "priority": call_priority,
            "selected_operator": selected_operator["name"] if selected_operator else "queue",
            "operator_id": selected_operator["id"] if selected_operator else None,
            "estimated_wait_time": random.randint(5, 120) if not selected_operator else 0,
            "routing_strategy": "skill_based",
            "confidence_score": round(selection_score / 10, 2)
        }

        self.route_decisions.append(routing_result)
        return routing_result

    def _analyze_call(self, task: str, context: Optional[Dict]) -> Dict:
        """
        Анализ качества звонка и речевых метрик.

        Анализируемые метрики:
        - ASR (Answer Seizure Ratio) - доля отвеченных вызовов
        - ACD (Average Call Duration) - средняя длительность
        - NER (Network Efficiency Ratio) - эффективность сети
        """
        # Симуляция анализа звонка
        call_duration = random.randint(30, 600)  # секунды

        analysis = {
            "call_id": f"call_{int(time.time())}",
            "quality_metrics": {
                "asr": round(random.uniform(0.85, 0.98), 3),  # Answer Seizure Ratio
                "acd": call_duration,  # Average Call Duration
                "ner": round(random.uniform(0.92, 0.99), 3),  # Network Efficiency Ratio
                "mos": round(random.uniform(3.5, 4.5), 1),  # Mean Opinion Score
                "jitter_ms": random.randint(1, 50),
                "packet_loss_percent": round(random.uniform(0.1, 2.5), 1)
            },
            "call_classification": self._classify_call(task, context),
            "sentiment_analysis": {
                "sentiment": random.choice(["positive", "neutral", "negative"]),
                "confidence": round(random.uniform(0.7, 0.95), 2)
            },
            "speech_analysis": {
                "talk_time_percent": round(random.uniform(40, 80), 1),
                "silence_percent": round(random.uniform(5, 20), 1),
                "interruptions": random.randint(0, 5)
            },
            "overall_quality": random.choice(["excellent", "good", "fair", "poor"])
        }

        self.quality_metrics = analysis
        return analysis

    def _classify_call(self, task: str, context: Optional[Dict]) -> Dict:
        """
        Классификация типа звонка и абонента.

        Типы звонков:
        - support (техподдержка)
        - sales (продажи)
        - complaint (жалоба)
        - informational (информационный)
        - emergency (экстренный)
        """
        call_types = ["support", "sales", "complaint", "informational", "emergency"]
        selected_type = random.choice(call_types)

        classification = {
            "call_type": selected_type,
            "confidence": round(random.uniform(0.75, 0.98), 2),
            "priority": 3 if selected_type == "support" else 2,
            "recommended_department": self._get_department_for_call_type(selected_type),
            "keywords_detected": [
                random.choice(["помощь", "проблема", "настройка", "счёт", "техподдержка"])
            ]
        }
        return classification

    def _get_department_for_call_type(self, call_type: str) -> str:
        """Определение отдела для маршрутизации."""
        departments = {
            "support": "Техническая поддержка",
            "sales": "Отдел продаж",
            "complaint": "Отдел качества",
            "informational": "Информационная служба",
            "emergency": "Аварийная служба"
        }
        return departments.get(call_type, "Общий отдел")

    def _predict_system_load(self, context: Optional[Dict]) -> Dict:
        """
        Прогнозирование нагрузки на АТС.

        Использует исторические данные и текущие тренды
        для предсказания загрузки системы.
        """
        current_hour = datetime.now().hour

        # Базовые паттерны нагрузки
        if 9 <= current_hour <= 12 or 14 <= current_hour <= 18:
            base_load = random.uniform(0.7, 0.95)  # Часы пик
        elif 12 <= current_hour <= 14:
            base_load = random.uniform(0.4, 0.6)  # Обеденное время
        else:
            base_load = random.uniform(0.2, 0.4)  # Низкая нагрузка

        prediction = {
            "current_load": round(base_load, 2),
            "predicted_load_next_hour": round(base_load + random.uniform(-0.1, 0.1), 2),
            "peak_hours": ["09:00-12:00", "15:00-18:00"],
            "available_channels": random.randint(10, 100),
            "busy_channels": int(50 * base_load),
            "queue_length": random.randint(0, 15),
            "load_status": "high" if base_load > 0.7 else "medium" if base_load > 0.4 else "low"
        }

        return prediction

    def _detect_anomalies(self, context: Optional[Dict]) -> Dict:
        """
        Обнаружение аномалий и мошеннических звонков.

        Анализирует:
        - Необычно высокая частота звонков
        - Короткие звонки с одного номера
        - Подозрительные маршруты
        """
        # Симуляция обнаружения аномалий
        has_anomaly = random.random() < 0.1  # 10% вероятность аномалии

        if has_anomaly:
            anomaly = {
                "detected": True,
                "anomaly_type": random.choice(["call_storm", "short_calls", "suspicious_pattern"]),
                "severity": random.choice(["low", "medium", "high"]),
                "affected_caller": f"anonym_{random.randint(1000, 9999)}",
                "recommended_action": "block" if random.random() < 0.5 else "monitor"
            }
        else:
            anomaly = {
                "detected": False,
                "message": "No anomalies detected"
            }

        if has_anomaly:
            self.anomaly_detections.append(anomaly)

        return anomaly

    def _get_available_operators(self) -> List[Dict]:
        """Получение списка доступных операторов."""
        operators = [
            {
                "id": f"op_{i}",
                "name": f"Оператор {i}",
                "skills": random.sample(["general", "technical", "sales", "vip"],
                                        random.randint(1, 3)),
                "current_load": random.randint(0, 5),
                "vip_experience": random.randint(0, 3)
            }
            for i in range(1, 11)
        ]
        return operators

    def _generate_optimization_recommendations(self, task: str) -> List[str]:
        """
        Генерация рекомендаций по оптимизации работы АТС.
        """
        recommendations = [
            "В часы пик рекомендуется увеличить количество операторов технической поддержки",
            "Внедрить интеллектуальное голосовое меню (IVR) для разгрузки операторов",
            "Настроить автоматический callback для звонков в очередь",
            "Оптимизировать балансировку нагрузки между серверами АТС",
            "Внедрить систему мониторинга качества связи в реальном времени",
            "Настроить предиктивную маршрутизацию на основе истории абонента",
            "Использовать NLP для автоматической классификации обращений"
        ]
        return random.sample(recommendations, random.randint(3, 5))

    def get_current_queue_status(self) -> Dict:
        """Получение текущего статуса очереди звонков."""
        return {
            "calls_in_queue": random.randint(0, 20),
            "average_wait_time_sec": random.randint(10, 180),
            "operators_online": random.randint(3, 15),
            "operators_available": random.randint(0, 8),
            "longest_wait_sec": random.randint(30, 300)
        }

    def get_call_statistics(self) -> Dict:
        """Получение статистики по обработанным звонкам."""
        total_calls = len(self.call_history)
        if total_calls == 0:
            return {"total_calls": 0}

        successful_routes = sum(1 for c in self.call_history if c.get("routing_decision") != "queue")

        return {
            "total_calls": total_calls,
            "successfully_routed": successful_routes,
            "routing_success_rate": round(successful_routes / total_calls, 2) if total_calls > 0 else 0,
            "average_quality_score": round(sum(c.get("quality_score", 0) for c in self.call_history) / total_calls, 2),
            "anomalies_detected": len(self.anomaly_detections)
        }

    def get_capabilities(self) -> List[str]:
        """Возможности интеллектуального агента АТС."""
        return [
            "Интеллектуальная маршрутизация вызовов (skill-based routing)",
            "Анализ качества звонков (ASR, ACD, MOS, NER)",
            "Прогнозирование нагрузки на АТС",
            "Обнаружение аномалий и мошеннических звонков",
            "Автоматическая классификация абонентов",
            "Анализ тональности разговора",
            "Оптимизация распределения операторов",
            "Реал-тайм мониторинг очереди звонков"
        ]


if __name__ == "__main__":
    # Пример использования интеллектуального агента АТС
    agent = SmartASTAgent()

    # Тестовые сценарии
    test_scenarios = [
        {
            "description": "Входящий звонок от VIP-клиента",
            "context": {
                "caller_id": "vip_1001",
                "caller_type": "vip",
                "required_skill": "vip",
                "priority": 5
            }
        },
        {
            "description": "Звонок в техническую поддержку",
            "context": {
                "caller_id": "user_2567",
                "caller_type": "regular",
                "required_skill": "technical",
                "priority": 3
            }
        },
        {
            "description": "Жалоба на качество связи",
            "context": {
                "caller_id": "user_3891",
                "caller_type": "regular",
                "required_skill": "general",
                "priority": 4
            }
        }
    ]

    print("=" * 70)
    print("ИНТЕЛЛЕКТУАЛЬНЫЙ АГЕНТ ДЛЯ ВИРТУАЛЬНОЙ АТС")
    print("=" * 70)

    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'=' * 70}")
        print(f"СЦЕНАРИЙ {i}: {scenario['description']}")
        print(f"{'=' * 70}")

        result = agent.execute_task(scenario["description"], context=scenario["context"])

        print(f"\n📞 ИНФОРМАЦИЯ О ЗВОНКЕ:")
        print(f"   ID звонка: {result['call_routing']['call_id']}")
        print(f"   Тип абонента: {result['call_routing']['caller_type']}")
        print(f"   Приоритет: {result['call_routing']['priority']}")

        print(f"\n🔄 МАРШРУТИЗАЦИЯ:")
        print(f"   Выбранный оператор: {result['call_routing']['selected_operator']}")
        print(f"   Стратегия: {result['call_routing']['routing_strategy']}")
        print(f"   Время ожидания: {result['call_routing']['estimated_wait_time']} сек")
        print(f"   Уверенность: {result['call_routing']['confidence_score']}")

        print(f"\n📊 АНАЛИЗ ЗВОНКА:")
        print(f"   Тип звонка: {result['call_analysis']['call_classification']['call_type']}")
        print(f"   Качество (MOS): {result['call_analysis']['quality_metrics']['mos']}")
        print(f"   Тональность: {result['call_analysis']['sentiment_analysis']['sentiment']}")

        print(f"\n⚠️ АНОМАЛИИ:")
        anomaly = result['anomaly_detection']
        if anomaly.get('detected'):
            print(f"   Обнаружена аномалия: {anomaly['anomaly_type']}")
            print(f"   Серьёзность: {anomaly['severity']}")
        else:
            print(f"   Аномалий не обнаружено")

        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        for rec in result['recommendations'][:3]:
            print(f"   • {rec}")

        print(f"\n⏱️ Время обработки: {result['execution_time']:.3f} сек")

    # Вывод общей статистики
    print(f"\n{'=' * 70}")
    print("ИТОГОВАЯ СТАТИСТИКА РАБОТЫ АГЕНТА")
    print(f"{'=' * 70}")
    stats = agent.get_call_statistics()
    print(f"   Всего обработано звонков: {stats['total_calls']}")
    print(f"   Успешно маршрутизировано: {stats['successfully_routed']}")
    print(f"   Эффективность маршрутизации: {stats['routing_success_rate'] * 100:.1f}%")
    print(f"   Обнаружено аномалий: {stats['anomalies_detected']}")

    print(f"\n{'=' * 70}")
    print("ВОЗМОЖНОСТИ АГЕНТА:")
    print(f"{'=' * 70}")
    for cap in agent.get_capabilities():
        print(f"   ✓ {cap}")