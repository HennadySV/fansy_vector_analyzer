#!/usr/bin/env python3
"""
Firebird SQL Tracer
Перехватывает и логирует SQL-запросы к базе данных Firebird
"""

import fdb
import time
import json
import threading
from datetime import datetime
from typing import List, Dict, Any
from collections import deque
import re


class FirebirdTracer:
    """Трейсер SQL-запросов к Firebird"""
    
    def __init__(self, host: str, database: str, user: str, password: str, max_history: int = 1000):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.max_history = max_history
        
        # История запросов (circular buffer)
        self.query_history = deque(maxlen=max_history)
        self.active_queries = {}  # query_id -> query_info
        self.query_counter = 0
        self.lock = threading.Lock()
        
        # Статистика
        self.stats = {
            'total_queries': 0,
            'total_time': 0.0,
            'errors': 0,
            'by_type': {'SELECT': 0, 'INSERT': 0, 'UPDATE': 0, 'DELETE': 0, 'OTHER': 0}
        }
        
        self.connection = None
        self.is_running = False
        
    def connect(self):
        """Подключение к базе данных"""
        try:
            self.connection = fdb.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                charset='UTF8'
            )
            print(f"✅ Подключено к Firebird: {self.host}:{self.database}")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к Firebird: {e}")
            return False
    
    def disconnect(self):
        """Отключение от базы данных"""
        if self.connection:
            self.connection.close()
            self.connection = None
            print("🔌 Отключено от Firebird")
    
    def _get_query_type(self, sql: str) -> str:
        """Определить тип SQL-запроса"""
        sql_upper = sql.strip().upper()
        if sql_upper.startswith('SELECT'):
            return 'SELECT'
        elif sql_upper.startswith('INSERT'):
            return 'INSERT'
        elif sql_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif sql_upper.startswith('DELETE'):
            return 'DELETE'
        else:
            return 'OTHER'
    
    def _extract_tables(self, sql: str) -> List[str]:
        """Извлечь имена таблиц из SQL"""
        # Упрощённый парсинг - ищем FROM и JOIN
        tables = []
        
        # FROM clause
        from_match = re.search(r'FROM\s+(\w+)', sql, re.IGNORECASE)
        if from_match:
            tables.append(from_match.group(1))
        
        # JOIN clauses
        join_matches = re.finditer(r'JOIN\s+(\w+)', sql, re.IGNORECASE)
        for match in join_matches:
            tables.append(match.group(1))
        
        # INSERT INTO / UPDATE
        insert_match = re.search(r'(?:INSERT\s+INTO|UPDATE)\s+(\w+)', sql, re.IGNORECASE)
        if insert_match:
            tables.append(insert_match.group(1))
        
        return list(set(tables))  # Уникальные
    
    def trace_query(self, sql: str, params: tuple = None) -> Dict[str, Any]:
        """
        Выполнить и протрейсить SQL-запрос
        
        Returns:
            dict с информацией о выполнении
        """
        if not self.connection:
            raise Exception("Нет подключения к БД. Вызовите connect() сначала.")
        
        query_id = self.query_counter
        self.query_counter += 1
        
        query_type = self._get_query_type(sql)
        tables = self._extract_tables(sql)
        
        query_info = {
            'id': query_id,
            'sql': sql,
            'params': params,
            'type': query_type,
            'tables': tables,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'duration': None,
            'rows_affected': 0,
            'error': None,
            'status': 'RUNNING'
        }
        
        # Добавляем в активные
        with self.lock:
            self.active_queries[query_id] = query_info
        
        start = time.time()
        cursor = None
        result = []
        
        try:
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            # Получаем результаты для SELECT
            if query_type == 'SELECT':
                result = cursor.fetchall()
                query_info['rows_affected'] = len(result)
            else:
                query_info['rows_affected'] = cursor.rowcount
                self.connection.commit()
            
            query_info['status'] = 'SUCCESS'
            
        except Exception as e:
            query_info['error'] = str(e)
            query_info['status'] = 'ERROR'
            with self.lock:
                self.stats['errors'] += 1
            
        finally:
            if cursor:
                cursor.close()
            
            end = time.time()
            duration = end - start
            
            query_info['end_time'] = datetime.now().isoformat()
            query_info['duration'] = duration
            
            # Обновляем статистику
            with self.lock:
                self.stats['total_queries'] += 1
                self.stats['total_time'] += duration
                self.stats['by_type'][query_type] += 1
                
                # Перемещаем из активных в историю
                del self.active_queries[query_id]
                self.query_history.append(query_info)
        
        return {
            'query_info': query_info,
            'result': result if query_type == 'SELECT' else None
        }
    
    def get_history(self, limit: int = 100, query_type: str = None) -> List[Dict]:
        """Получить историю запросов"""
        with self.lock:
            history = list(self.query_history)
        
        # Фильтруем по типу если нужно
        if query_type:
            history = [q for q in history if q['type'] == query_type]
        
        # Возвращаем последние N
        return history[-limit:]
    
    def get_active_queries(self) -> List[Dict]:
        """Получить активные (выполняющиеся) запросы"""
        with self.lock:
            return list(self.active_queries.values())
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        with self.lock:
            stats = self.stats.copy()
            stats['avg_time'] = stats['total_time'] / stats['total_queries'] if stats['total_queries'] > 0 else 0
            stats['active_queries'] = len(self.active_queries)
            return stats
    
    def get_slow_queries(self, threshold: float = 1.0, limit: int = 10) -> List[Dict]:
        """Получить медленные запросы (> threshold секунд)"""
        with self.lock:
            slow = [q for q in self.query_history if q['duration'] and q['duration'] > threshold]
            slow.sort(key=lambda x: x['duration'], reverse=True)
            return slow[:limit]
    
    def get_table_stats(self) -> Dict[str, Dict]:
        """Статистика по таблицам"""
        table_stats = {}
        
        with self.lock:
            for query in self.query_history:
                for table in query['tables']:
                    if table not in table_stats:
                        table_stats[table] = {
                            'reads': 0,
                            'writes': 0,
                            'total_time': 0.0,
                            'queries': 0
                        }
                    
                    stats = table_stats[table]
                    stats['queries'] += 1
                    stats['total_time'] += query['duration'] or 0
                    
                    if query['type'] == 'SELECT':
                        stats['reads'] += 1
                    elif query['type'] in ('INSERT', 'UPDATE', 'DELETE'):
                        stats['writes'] += 1
        
        # Вычисляем средние
        for table, stats in table_stats.items():
            stats['avg_time'] = stats['total_time'] / stats['queries'] if stats['queries'] > 0 else 0
        
        return table_stats
    
    def export_to_json(self, filename: str):
        """Экспорт истории в JSON"""
        with self.lock:
            data = {
                'stats': self.get_stats(),
                'history': list(self.query_history),
                'table_stats': self.get_table_stats(),
                'exported_at': datetime.now().isoformat()
            }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Экспортировано в {filename}")


class FirebirdTracerWrapper:
    """
    Обёртка для прозрачного трейсинга
    Используется как замена обычному fdb.Connection
    """
    
    def __init__(self, tracer: FirebirdTracer):
        self.tracer = tracer
        self._connection = tracer.connection
    
    def cursor(self):
        return TracedCursor(self.tracer, self._connection.cursor())
    
    def commit(self):
        return self._connection.commit()
    
    def rollback(self):
        return self._connection.rollback()
    
    def close(self):
        return self._connection.close()


class TracedCursor:
    """Курсор с трейсингом"""
    
    def __init__(self, tracer: FirebirdTracer, cursor):
        self.tracer = tracer
        self._cursor = cursor
    
    def execute(self, sql: str, params: tuple = None):
        # Вызываем трейсер
        result = self.tracer.trace_query(sql, params)
        # Возвращаем реальный курсор (уже выполнен)
        return self._cursor
    
    def fetchall(self):
        return self._cursor.fetchall()
    
    def fetchone(self):
        return self._cursor.fetchone()
    
    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size)
    
    def close(self):
        return self._cursor.close()
    
    @property
    def rowcount(self):
        return self._cursor.rowcount
    
    @property
    def description(self):
        return self._cursor.description


def example_usage():
    """Пример использования трейсера"""
    
    # Настройки подключения (ЗАМЕНИТЕ на ваши!)
    tracer = FirebirdTracer(
        host='localhost',
        database='/path/to/database.fdb',
        user='SYSDBA',
        password='masterkey'
    )
    
    # Подключаемся
    if not tracer.connect():
        return
    
    try:
        # Пример запросов
        print("\n" + "="*70)
        print("Тестовые запросы к META базе")
        print("="*70 + "\n")
        
        # 1. Получить список функций
        result = tracer.trace_query("""
            SELECT FUNC_NAME, APP_NUM 
            FROM DICMETAF 
            WHERE FUNC_NAME LIKE '%NDFL%'
            LIMIT 10
        """)
        
        print(f"✅ Запрос 1: Найдено {result['query_info']['rows_affected']} функций")
        print(f"   Время: {result['query_info']['duration']:.3f}s")
        
        # 2. Вставка тестовой записи (если есть тестовая таблица)
        # result = tracer.trace_query("""
        #     INSERT INTO TEST_TABLE (NAME, VALUE) VALUES (?, ?)
        # """, ('test', 123))
        
        # Показываем статистику
        print("\n" + "="*70)
        print("СТАТИСТИКА")
        print("="*70)
        
        stats = tracer.get_stats()
        print(f"Всего запросов: {stats['total_queries']}")
        print(f"Среднее время: {stats['avg_time']:.3f}s")
        print(f"Ошибок: {stats['errors']}")
        print(f"\nПо типам:")
        for qtype, count in stats['by_type'].items():
            if count > 0:
                print(f"  {qtype}: {count}")
        
        # Показываем историю
        print("\n" + "="*70)
        print("ИСТОРИЯ ЗАПРОСОВ")
        print("="*70)
        
        history = tracer.get_history(limit=5)
        for query in history:
            print(f"\n[{query['id']}] {query['type']} - {query['status']}")
            print(f"    SQL: {query['sql'][:80]}...")
            print(f"    Время: {query['duration']:.3f}s")
            print(f"    Таблицы: {', '.join(query['tables'])}")
        
        # Статистика по таблицам
        print("\n" + "="*70)
        print("СТАТИСТИКА ПО ТАБЛИЦАМ")
        print("="*70)
        
        table_stats = tracer.get_table_stats()
        for table, stats in sorted(table_stats.items(), key=lambda x: x[1]['queries'], reverse=True)[:10]:
            print(f"\n{table}:")
            print(f"  Запросов: {stats['queries']}")
            print(f"  Чтений: {stats['reads']}, Записей: {stats['writes']}")
            print(f"  Среднее время: {stats['avg_time']:.3f}s")
        
        # Экспорт
        tracer.export_to_json('logs/trace_export.json')
        
    finally:
        tracer.disconnect()


if __name__ == '__main__':
    example_usage()
