# -*- coding: utf-8 -*-
"""
Специализированный RAG для информационной безопасности
Лабораторная работа №5
Автор: Громов
Специальность: Информационная безопасность
"""
from rag_pipeline import RAGPipeline
from typing import Dict, Any, List
from langchain.prompts import ChatPromptTemplate


class SecurityRAGPipeline(RAGPipeline):
    """
    RAG-система для вопросов по информационной безопасности.
    
    Особенности:
    • Приоритет нормативным документам (ГОСТ, ФСТЭК)
    • Точное цитирование требований
    • Классификация по уровням критичности
    """
    
    def __init__(self, vectorstore, llm=None, top_k: int = 5):
        super().__init__(vectorstore, llm, top_k)
        
        # Специфичный промпт для ИБ
        self.rag_prompt = ChatPromptTemplate.from_template("""
Ты — эксперт по информационной безопасности.
Используй ТОЛЬКО предоставленный контекст для ответа.
Цитируй конкретные пункты нормативных документов.

Если вопрос касается требований безопасности:
• Укажи нормативный документ (ГОСТ, ФСТЭК, PCI DSS, 152-ФЗ)
• Приведи конкретный пункт/требование
• Укажи уровень критичности

Контекст из документов:
{context}

Вопрос: {question}

Ответ:
""")
    
    def query(self, question: str, include_sources: bool = True) -> Dict[str, Any]:
        """Запрос с ИБ-специфичной обработкой."""
        result = super().query(question, include_sources)
        
        # Добавление ИБ-метаданных
        result["domain"] = "information_security"
        result["compliance_check"] = self._check_compliance_keywords(question)
        
        return result
    
    def _check_compliance_keywords(self, question: str) -> Dict[str, bool]:
        """Проверка на ключевые слова комплаенса."""
        keywords = {
            "gost": any(kw in question.lower() for kw in ["гост", "ГОСТ"]),
            "fstek": any(kw in question.lower() for kw in ["фстэк", "ФСТЭК"]),
            "pci_dss": any(kw in question.lower() for kw in ["pci dss", "pci_dss"]),
            "152fz": any(kw in question.lower() for kw in ["152-фз", "152-фз", "персональные данные"])
        }
        return keywords


# Использование
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    from vector_store import VectorStoreManager

    load_dotenv()

    print("=" * 80)
    print("СПЕЦИАЛИЗИРОВАННЫЙ RAG ДЛЯ ИНФОРМАЦИОННОЙ БЕЗОПАСНОСТИ")
    print("=" * 80)

    # Инициализация векторного хранилища
    vectorstore = VectorStoreManager(
        persist_directory="./data/chroma_db",
        collection_name="security_documents"
    )

    # Инициализация LLM (опционально)
    llm = None
    try:
        from langchain_community.llms import YandexGPT

        iam_token = os.getenv("YANDEX_IAM_TOKEN")
        folder_id = os.getenv("YANDEX_FOLDER_ID")

        if iam_token and folder_id:
            llm = YandexGPT(
                iam_token=iam_token,
                folder_id=folder_id,
                temperature=0.3,
                max_tokens=500
            )
            print("✅ YandexGPT подключён")
        else:
            print("⚠️ YandexGPT не подключён (работаем без LLM)")
    except ImportError:
        print("⚠️ LangChain YandexGPT не установлен (работаем без LLM)")

    # Создание ИБ-пайплайна
    security_rag = SecurityRAGPipeline(
        vectorstore=vectorstore,
        llm=llm,
        top_k=5
    )

    # Тестовые вопросы по ИБ и ФЗ-152
    test_questions = [
        "Что такое персональные данные по закону 152-ФЗ?",
        "Какие требования к обработке персональных данных?",
        "Что такое согласие на обработку персональных данных?",
        "Какие права у субъекта персональных данных?",
        "Что такое информационная безопасность?"
    ]

    print("\n" + "=" * 80)
    print("ТЕСТОВЫЕ ЗАПРОСЫ ПО ИНФОРМАЦИОННОЙ БЕЗОПАСНОСТИ")
    print("=" * 80)

    for i, question in enumerate(test_questions, 1):
        print(f"\n{'=' * 60}")
        print(f"ВОПРОС {i}: {question}")
        print(f"{'=' * 60}")

        result = security_rag.query(question)

        if result["success"]:
            print(f"\nОТВЕТ:")
            print(result["answer"])

            print(f"\nМетаданные:")
            print(f" • Домен: {result.get('domain', 'N/A')}")
            print(f" • Проверка комплаенса: {result.get('compliance_check', {})}")
            print(f" • Найдено источников: {result['sources_count']}")
            print(f" • Время выполнения: {result['execution_time']}с")

            if result["sources"]:
                print(f"\nИсточники:")
                for j, source in enumerate(result["sources"][:3], 1):
                    metadata = source.get('metadata', {})
                    print(f"  {j}. {metadata.get('source', 'Unknown')} "
                          f"(score: {source['similarity_score']:.3f})")
        else:
            print(f"\nОШИБКА: {result.get('answer', 'Неизвестная ошибка')}")

    print("\n" + "=" * 80)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 80)
