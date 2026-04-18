# -*- coding: utf-8 -*-
"""
Обработчик webhook для тестирования workflow
Лабораторная работа №4
Дисциплина: Искусственный интеллект
Специальность: Математическое обеспечение и администрирование информационных систем
Тема диплома: Интеллектуальный модуль для виртуальной АТС
Автор: Громов
Группа: МОА-221
Дата: 2026
"""
import os
import json
import requests
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class ATSIntelligentRouter:
    """
    Клиент для интеллектуальной маршрутизации вызовов виртуальной АТС.
    
    Атрибуты:
        base_url: URL n8n сервера
        webhook_path: Путь webhook для маршрутизации
        secret: Секретный ключ для аутентификации
    """
    
    def __init__(
        self,
        base_url: str = None,
        webhook_path: str = "ats-intelligent-routing",
        secret: Optional[str] = None
    ):
        self.base_url = (base_url or os.getenv("N8N_URL", "http://localhost:5678")).rstrip('/')
        self.webhook_path = webhook_path
        self.secret = secret or os.getenv("WEBHOOK_SECRET")
        self.webhook_url = f"{self.base_url}/webhook/{webhook_path}"
        
        # Загрузка credentials для Yandex Cloud
        self.yandex_iam_token = os.getenv("YANDEX_IAM_TOKEN")
        self.yandex_folder_id = os.getenv("YANDEX_FOLDER_ID")
        
        logger.info(f"ATS Intelligent Router инициализирован: {self.webhook_url}")
        logger.info(f"Yandex Cloud Folder ID: {self.yandex_folder_id[:10] if self.yandex_folder_id else 'Not set'}...")
    
    def route_call(
        self,
        caller_input: str,
        caller_phone: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Маршрутизация вызова через интеллектуальный модуль АТС.
        
        Args:
            caller_input: Текст запроса абонента
            caller_phone: Номер телефона звонящего
            session_id: Идентификатор сессии (опционально)
        
        Returns:
            Dict: Результат маршрутизации с назначенным оператором
        """
        import uuid
        
        payload = {
            "caller_input": caller_input,
            "caller_phone": caller_phone,
            "session_id": session_id or str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "yandex_folder_id": self.yandex_folder_id,
            "yandex_iam_token": self.yandex_iam_token
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.secret:
            headers["X-Webhook-Secret"] = self.secret
        
        logger.info(f"Маршрутизация вызова: {caller_input[:50]}... (тел: {caller_phone})")
        
        try:
            response = requests.post(
                self.webhook_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"Вызов маршрутизирован: категория={result.get('routing_decision', {}).get('category')}, "
                       f"приоритет={result.get('routing_decision', {}).get('priority')}")
            
            return {
                "success": True,
                "response": result,
                "status_code": response.status_code,
                "routing_info": result.get("routing_decision", {}),
                "assigned_operator": result.get("assigned_operator"),
                "processing_time_ms": result.get("processing_time_ms")
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка маршрутизации: {e}")
            return {
                "success": False,
                "error": str(e),
                "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            }
    
    def batch_route_calls(
        self,
        calls: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Пакетная маршрутизация нескольких вызовов.
        
        Args:
            calls: Список словарей с ключами 'caller_input' и 'caller_phone'
        
        Returns:
            List: Результаты маршрутизации для каждого вызова
        """
        results = []
        for call in calls:
            result = self.route_call(
                caller_input=call.get('caller_input', ''),
                caller_phone=call.get('caller_phone', ''),
                session_id=call.get('session_id')
            )
            results.append(result)
        
        return results
    
    def get_operator_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики по операторам и обработанным вызовам.
        
        Returns:
            Dict: Статистика загрузки операторов
        """
        stats_url = f"{self.base_url}/webhook/ats-stats"
        
        try:
            response = requests.get(
                stats_url,
                timeout=10
            )
            response.raise_for_status()
            
            return {
                "success": True,
                "statistics": response.json()
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_workflow_status(self) -> Dict[str, Any]:
        """Проверка доступности n8n и workflow."""
        try:
            # Проверка health n8n
            health_response = requests.get(
                f"{self.base_url}/healthz",
                timeout=5
            )
            
            # Проверка доступности webhook
            webhook_check = requests.post(
                self.webhook_url,
                json={"test": "ping"},
                timeout=5,
                headers={"Content-Type": "application/json"}
            )
            
            return {
                "available": health_response.status_code == 200,
                "webhook_accessible": webhook_check.status_code in [200, 400],  # 400 означает что webhook существует
                "status_code": health_response.status_code,
                "n8n_version": health_response.headers.get('n8n-version', 'unknown')
            }
        except Exception as e:
            logger.error(f"Ошибка проверки статуса: {e}")
            return {
                "available": False,
                "webhook_accessible": False,
                "error": str(e)
            }


# Адаптер для обратной совместимости с базовым workflow
class WorkflowClient(ATSIntelligentRouter):
    """
    Клиент для взаимодействия с n8n workflow (адаптер для совместимости).
    Сохраняет интерфейс базового клиента для использования с basic_workflow.json
    """
    
    def __init__(self, base_url: str = "http://localhost:5678", webhook_path: str = "application", secret: Optional[str] = None):
        super().__init__(base_url, webhook_path, secret)
    
    def send_application(
        self,
        message: str,
        contact: str,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Отправка заявки в workflow (для базового workflow).
        
        Args:
            message: Текст заявки
            contact: Контактная информация
            priority: Приоритет (low, normal, high)
        
        Returns:
            Dict: Ответ от workflow
        """
        # Адаптация под интерфейс маршрутизации вызовов
        return self.route_call(
            caller_input=message,
            caller_phone=contact,
            session_id=f"app_{datetime.now().timestamp()}"
        )


# Точка входа для тестирования
if __name__ == "__main__":
    print("=" * 80)
    print("ЛАБОРАТОРНАЯ РАБОТА №4")
    print("Дисциплина: Искусственный интеллект")
    print("Специальность: Математическое обеспечение и администрирование ИС")
    print("Тема: Интеллектуальный модуль для виртуальной АТС")
    print("Автор: Громов")
    print("=" * 80)
    
    # Инициализация клиента
    router = ATSIntelligentRouter()
    
    # Проверка доступности
    print("\n1. Проверка доступности n8n и workflow...")
    status = router.check_workflow_status()
    
    if status.get("available"):
        print(f"   ✅ n8n доступен (версия: {status.get('n8n_version', 'unknown')})")
        print(f"   ✅ Webhook доступен: {status.get('webhook_accessible')}")
    else:
        print(f"   ❌ n8n недоступен: {status.get('error')}")
        print("\n   Убедитесь, что Docker контейнер запущен:")
        print("   cd week4/docker && docker-compose up -d")
        exit(1)
    
    # Тестовая маршрутизация вызовов
    print("\n2. Тестирование интеллектуальной маршрутизации вызовов...")
    print("-" * 80)
    
    test_calls = [
        {
            "caller_input": "У меня не работает интернет, постоянно обрывается соединение",
            "caller_phone": "+7 (999) 123-45-67",
            "description": "Техническая проблема"
        },
        {
            "caller_input": "Хочу подключить корпоративный тариф с расширенной аналитикой",
            "caller_phone": "+7 (999) 234-56-78",
            "description": "Продажи"
        },
        {
            "caller_input": "Неправильно списали деньги за прошлый месяц, требую возврат",
            "caller_phone": "+7 (999) 345-67-89",
            "description": "Рекламация"
        },
        {
            "caller_input": "Подскажите режим работы офиса продаж в выходные",
            "caller_phone": "+7 (999) 456-78-90",
            "description": "Общий вопрос"
        }
    ]
    
    for i, call in enumerate(test_calls, 1):
        print(f"\nТест {i}: {call['description']}")
        print(f"   Запрос: {call['caller_input']}")
        print(f"   Телефон: {call['caller_phone']}")
        
        result = router.route_call(
            caller_input=call['caller_input'],
            caller_phone=call['caller_phone']
        )
        
        if result["success"]:
            print(f"   ✅ Успешно маршрутизирован")
            routing_info = result.get("routing_info", {})
            print(f"   📊 Категория: {routing_info.get('category', 'unknown')}")
            print(f"   ⚡ Приоритет: {routing_info.get('priority', 0)}/5")
            print(f"   👤 Оператор: {result.get('assigned_operator', 'pending')}")
            print(f"   ⏱️ Время обработки: {result.get('processing_time_ms', 0)} мс")
        else:
            print(f"   ❌ Ошибка: {result.get('error')}")
    
    # Пакетная маршрутизация
    print("\n3. Пакетная обработка вызовов...")
    print("-" * 80)
    
    batch_calls = [
        {"caller_input": "Проблема с авторизацией в личном кабинете", "caller_phone": "+7 (999) 111-22-33"},
        {"caller_input": "Как подключить виртуальную АТС?", "caller_phone": "+7 (999) 222-33-44"},
        {"caller_input": "Жалоба на качество связи", "caller_phone": "+7 (999) 333-44-55"}
    ]
    
    batch_results = router.batch_route_calls(batch_calls)
    successful = sum(1 for r in batch_results if r["success"])
    
    print(f"Пакетная обработка завершена: {successful}/{len(batch_calls)} успешно")
    
    # Статистика
    print("\n4. Статистика операторов...")
    print("-" * 80)
    
    stats = router.get_operator_statistics()
    if stats.get("success"):
        print(f"✅ Статистика получена")
        print(f"   Данные: {stats.get('statistics', {})}")
    else:
        print(f"⚠️ Статистика временно недоступна (требуется дополнительный workflow)")
    
    print("\n" + "=" * 80)
    print("Тестирование завершено успешно!")
    print("=" * 80)