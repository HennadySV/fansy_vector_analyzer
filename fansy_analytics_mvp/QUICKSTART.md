# ⚡ Quick Start Guide

## Запуск за 3 шага

### Windows

```cmd
1. Распаковать архив
2. Двойной клик на start_windows.bat
3. Открыть http://localhost:5000
```

### Linux/Mac

```bash
1. pip install -r requirements.txt
2. cd backend && python web_server.py
3. Открыть http://localhost:5000
```

---

## Первое использование

### 1. Откройте Dashboard
```
http://localhost:5000
```

### 2. Нажмите "🧪 Тест (симуляция)"
Это запустит тестовые вызовы функций для демонстрации

### 3. Посмотрите результаты
- Статистика обновится real-time
- Появятся вызовы в истории
- Граф покажет зависимости

---

## Что дальше?

### Подключить к реальной базе Firebird

**Файл:** `backend/firebird_tracer.py`

```python
tracer = FirebirdTracer(
    host='localhost',                      # ваш хост
    database='C:\\Fansy\\BAL_META.FDB',   # путь к базе
    user='SYSDBA',                         # ваш user
    password='masterkey'                   # ваш пароль
)
```

### Интегрировать с вашими функциями

**Файл:** `backend/function_logger.py`

```python
# Добавьте в ваш код FANSY
from function_logger import get_logger

logger = get_logger()
call_id = logger.start_call('_F_SPECTRE', 'Get_NDFL_Nach', params)
# ... ваша логика ...
logger.end_call(call_id, result=result)
```

---

## Типичные проблемы

### ❌ "Module not found: flask"
```bash
pip install -r requirements.txt
```

### ❌ "Connection refused to Firebird"
- Проверьте, что Firebird запущен
- Проверьте путь к базе (должен быть полный путь)

### ❌ "Address already in use"
Порт 5000 занят. Измените в `web_server.py`:
```python
app.run(port=5001)  # другой порт
```

---

## Полезные ссылки

- **Full README:** [README.md](README.md)
- **API Docs:** http://localhost:5000/api/
- **Dashboard:** http://localhost:5000

---

## Feedback

Нашли баг или есть идея? Создайте Issue или напишите команде!

**Версия:** 1.0 MVP  
**Статус:** ✅ Ready
