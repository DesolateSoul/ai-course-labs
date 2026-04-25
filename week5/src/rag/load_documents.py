# -*- coding: utf-8 -*-
"""
Скрипт для загрузки документов в векторную базу
"""
import os
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent.parent.parent))

from document_loader import DocumentLoader
from chunking import ChunkingStrategy
from vector_store import VectorStoreManager
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_documents_to_db():
    """Загрузка документов в векторную базу"""
    
    print("=" * 80)
    print("ЗАГРУЗКА ДОКУМЕНТОВ В ВЕКТОРНУЮ БАЗУ")
    print("=" * 80)
    
    # 1. Загрузка документов из директории
    print("\n1. Загрузка документов из data/documents/...")
    loader = DocumentLoader(source_directory="./data/documents")
    
    # Проверяем, есть ли файлы
    stats = loader.get_statistics()
    print(f"   Найдено файлов: {stats['files']}")
    print(f"   Общий размер: {stats['total_size_mb']} MB")
    
    if sum(stats['files'].values()) == 0:
        print("\n❌ ОШИБКА: Нет файлов в директории ./data/documents/")
        print("   Поместите файл с ФЗ-152 в папку data/documents/")
        return False
    
    # Загружаем документы
    documents = loader.load_directory()
    print(f"   Загружено документов: {len(documents)}")
    
    if not documents:
        print("❌ ОШИБКА: Не удалось загрузить документы")
        return False
    
    # 2. Разбиение на чанки
    print("\n2. Разбиение документов на чанки...")
    chunks = ChunkingStrategy.split_documents(
        documents,
        strategy="recursive",
        chunk_size=512,
        chunk_overlap=50
    )
    
    stats_chunks = ChunkingStrategy.get_statistics(chunks)
    print(f"   Создано чанков: {stats_chunks['count']}")
    print(f"   Средний размер: {stats_chunks['avg_size']} символов")
    
    # 3. Создание векторного хранилища и добавление чанков
    print("\n3. Создание векторной базы данных...")
    
    # Удаляем старую коллекцию, если есть
    store = VectorStoreManager(
        persist_directory="./data/chroma_db",
        collection_name="security_documents"
    )
    
    # Очищаем существующую коллекцию
    store.clear()
    print("   Старая коллекция очищена")
    
    # Добавляем новые документы
    print(f"\n4. Добавление {len(chunks)} чанков в векторную базу...")
    result = store.add_documents(chunks, batch_size=50)
    
    print(f"\n✅ УСПЕШНО ЗАГРУЖЕНО:")
    print(f"   • Добавлено документов: {result['documents_added']}")
    print(f"   • Всего в базе: {result['total_documents']}")
    print(f"   • Коллекция: {result['collection_name']}")
    
    # Проверяем, что документы загружены
    test_search = store.search("персональные данные", k=3)
    if test_search:
        print(f"\n✅ Тестовый поиск работает! Найдено {len(test_search)} результатов")
    else:
        print(f"\n⚠️ Тестовый поиск не вернул результатов")
    
    return True


if __name__ == "__main__":
    success = load_documents_to_db()
    
    if success:
        print("\n" + "=" * 80)
        print("ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО")
        print("=" * 80)
        print("\nТеперь можно запускать security_rag_pipeline.py")
    else:
        print("\n" + "=" * 80)
        print("ЗАГРУЗКА НЕ УДАЛАСЬ")
        print("=" * 80)
        print("\nУбедитесь, что:")
        print("1. В папке data/documents/ есть файлы (PDF, TXT или MD)")
        print("2. Файл с ФЗ-152 скопирован в эту папку")
        print("3. Установлены все зависимости (pip install -r requirements.txt)")