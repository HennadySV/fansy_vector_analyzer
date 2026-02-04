# Визуализация архитектуры и потоков данных Fansy

## 1. Общая трёхслойная архитектура

```mermaid
graph TB
    subgraph GUI["GUI Layer - Приложения"]
        SPECTRE[SPECTRE<br/>Торговые операции]
        TRUST[TRUST<br/>Доверительное управление]
        DEPO[DEPO<br/>Депозитарий]
        ADMIN[ADMIN<br/>Администрирование]
        BALTUN[BALTUN<br/>Бухгалтерия]
    end
    
    subgraph META["META Layer - Метаданные и Бизнес-логика"]
        direction LR
        DICMETAF[(DICMETAF<br/>Функции FANSY-SCRIPT)]
        DICFORMS[(DICFORMS<br/>Формы)]
        DICSELEC[(DICSELEC<br/>Выборки SQL)]
        DICFIELD[(DICFIELD<br/>Поля)]
        DICAPPL[(DICAPPL<br/>Приложения)]
    end
    
    subgraph DATA["DATA Layer - Данные"]
        direction LR
        OD_DOCS[(OD_DOCS<br/>Документы)]
        OD_DOLS[(OD_DOLS<br/>Позиции)]
        OD_TURNS[(OD_TURNS<br/>Обороты)]
        OD_WIRING[(OD_WIRING<br/>Проводки)]
        OD_RESTS[(OD_RESTS<br/>Остатки)]
    end
    
    SPECTRE --> DICMETAF
    TRUST --> DICMETAF
    DEPO --> DICMETAF
    ADMIN --> DICMETAF
    BALTUN --> DICMETAF
    
    DICMETAF --> OD_DOCS
    DICSELEC --> OD_TURNS
    DICFORMS --> OD_DOLS
    
    style GUI fill:#e1f5ff
    style META fill:#fff4e1
    style DATA fill:#e8f5e9
```

## 2. Поток выполнения документа с ошибкой

```mermaid
sequenceDiagram
    participant User as Пользователь
    participant GUI as SPECTRE (GUI)
    participant Meta as META (Functions)
    participant Data as DATA (Tables)
    
    User->>GUI: Создаёт документ<br/>расчёта НДФЛ
    GUI->>Data: INSERT OD_DOCS<br/>doc_id=4734767
    GUI->>Data: INSERT OD_STEPS<br/>dir_id=4734776
    
    Note over GUI,Meta: Запуск директивы "Расчет финансовых результатов"
    
    GUI->>Meta: Exec OP_P_NDFL_PRC_BODY<br/>(doc_id=4734767, dir_id=4734776)
    
    Meta->>Data: SELECT данные<br/>из OD_DOCS, U_OP_P_NDFL
    Data-->>Meta: Возврат данных документа
    
    Meta->>Meta: Расчёт промежуточных<br/>значений (FR1, FR2, NB, etc)
    
    Note over Meta: Строка 2192: Вызов Get_NDFL_Nach
    
    Meta->>Meta: _F_SPECTRE->Get_NDFL_Nach(<br/>old_b_date, e_date, INVESTOR,<br/>CONTRACT, NAL_PER, KBK1, FALSE, IS_ALF)
    
    rect rgb(255, 200, 200)
        Note right of Meta: ❌ ОШИБКА:<br/>"Не все входные<br/>параметры означены"
    end
    
    Meta-->>GUI: ERROR
    GUI-->>User: Показ ошибки
```

## 3. Зависимости функции OP_P_NDFL_PRC_BODY

```mermaid
graph LR
    subgraph "Модуль _F_BUX (Бухгалтерия)"
        Get_CrossRate[Get_CrossRate]
        Get_Plan_By_SysName[Get_Plan_By_SysName]
        Get_RUR_ID[Get_RUR_ID]
        Get_Rests_Inc[Get_Rests_Inc]
    end
    
    subgraph "Модуль _F_DOC (Документооборот)"
        Get_APP_OPTION[Get_APP_OPTION]
    end
    
    subgraph "Модуль _F_SPECTRE (Специфичные функции)"
        Get_NAL_PER[Get_NAL_PER]
        Get_NDFL_Nach[Get_NDFL_Nach<br/>⚠️ ПРОБЛЕМА ЗДЕСЬ]
        Get_DEAL_IDS[Get_DEAL_IDS]
        Get_DEAL_FR[Get_DEAL_FR]
    end
    
    subgraph "Модуль _F_PIF (ПИФы)"
        FR4_DO_PARTY[FR4_DO_PARTY]
    end
    
    OP_P_NDFL_PRC_BODY[OP_P_NDFL_PRC_BODY<br/>Основная функция]
    
    OP_P_NDFL_PRC_BODY --> Get_CrossRate
    OP_P_NDFL_PRC_BODY --> Get_Plan_By_SysName
    OP_P_NDFL_PRC_BODY --> Get_RUR_ID
    OP_P_NDFL_PRC_BODY --> Get_Rests_Inc
    OP_P_NDFL_PRC_BODY --> Get_APP_OPTION
    OP_P_NDFL_PRC_BODY --> Get_NAL_PER
    OP_P_NDFL_PRC_BODY --> Get_NDFL_Nach
    OP_P_NDFL_PRC_BODY --> Get_DEAL_IDS
    OP_P_NDFL_PRC_BODY --> Get_DEAL_FR
    OP_P_NDFL_PRC_BODY --> FR4_DO_PARTY
    
    style Get_NDFL_Nach fill:#ff9999,stroke:#ff0000,stroke-width:3px
```

## 4. Таблицы данных, задействованные в расчёте

```mermaid
graph TD
    OP_P_NDFL_PRC_BODY[OP_P_NDFL_PRC_BODY]
    
    subgraph "Основные таблицы"
        OD_DOCS[(OD_DOCS<br/>Заголовки документов)]
        U_OP_P_NDFL[(U_OP_P_NDFL<br/>Специфичные поля НДФЛ)]
        OD_FACES[(OD_FACES<br/>Контрагенты)]
    end
    
    subgraph "Проводки и обороты"
        OD_STEPS[(OD_STEPS<br/>Шаги выполнения)]
        OD_WIRING[(OD_WIRING<br/>Проводки)]
        OD_TURNS[(OD_TURNS<br/>Обороты)]
        OD_RESTS[(OD_RESTS<br/>Остатки)]
    end
    
    subgraph "Справочники"
        OD_BALANCES[(OD_BALANCES<br/>Счета)]
        OD_ACC_PLANS[(OD_ACC_PLANS<br/>Планы счетов)]
        OD_DOC_CATS[(OD_DOC_CATS<br/>Категории документов)]
    end
    
    subgraph "НДФЛ специфика"
        OD_NDFL[(OD_NDFL<br/>Начисления НДФЛ)]
        D_B_CONTRACTS[(D_B_CONTRACTS<br/>Договоры)]
    end
    
    OP_P_NDFL_PRC_BODY -->|SELECT| OD_DOCS
    OP_P_NDFL_PRC_BODY -->|SELECT| U_OP_P_NDFL
    OP_P_NDFL_PRC_BODY -->|SELECT| OD_FACES
    OP_P_NDFL_PRC_BODY -->|SELECT| OD_TURNS
    OP_P_NDFL_PRC_BODY -->|SELECT| OD_RESTS
    OP_P_NDFL_PRC_BODY -->|SELECT| OD_NDFL
    
    OP_P_NDFL_PRC_BODY -->|INSERT/UPDATE| OD_STEPS
    OP_P_NDFL_PRC_BODY -->|INSERT| OD_WIRING
    
    OD_WIRING --> OD_TURNS
    OD_TURNS --> OD_RESTS
    OD_RESTS --> OD_BALANCES
    OD_BALANCES --> OD_ACC_PLANS
```

## 5. Детальный поток данных для Get_NDFL_Nach

```mermaid
graph TB
    Start([Вызов Get_NDFL_Nach])
    
    Params[/"Параметры:<br/>1. old_b_date (DATE)<br/>2. e_date (DATE)<br/>3. INVESTOR (INT)<br/>4. CONTRACT (INT/STRING)<br/>5. NAL_PER (INT)<br/>6. KBK (STRING)<br/>7. FLAG (BOOLEAN)<br/>8. IS_ALF (BOOLEAN)<br/>❓ 9. TAX_DED_EX? (FLOAT)"/]
    
    Query1[(SELECT от OD_NDFL<br/>Начисления налога)]
    Query2[(SELECT от OD_TURNS<br/>Выплаты налога)]
    
    Calc[Расчёт:<br/>Начислено - Выплачено]
    
    Result[/Возврат:<br/>FROM_PAY или FROM_ADD/]
    
    Start --> Params
    Params --> Query1
    Params --> Query2
    Query1 --> Calc
    Query2 --> Calc
    Calc --> Result
    
    style Start fill:#e3f2fd
    style Params fill:#fff9c4
    style Result fill:#c8e6c9
    style Calc fill:#f8bbd0
```

## 6. Временная линия изменений (гипотеза)

```mermaid
gantt
    title Предполагаемая история изменения Get_NDFL_Nach
    dateFormat YYYY-MM-DD
    section Функция Get_NDFL_Nach
    Старая версия (8 параметров)      :done, v1, 2020-01-01, 2025-09-30
    Изменение функции (9 параметров?) :crit, v2, 2025-10-01, 2025-10-31
    Текущая версия                     :active, v3, 2025-11-01, 2026-01-19
    
    section Вызовы функции
    OP_P_NDFL_PRC_BODY (не обновлён)  :crit, call1, 2020-01-01, 2026-01-19
    Другие функции (обновлены?)       :done, call2, 2020-01-01, 2026-01-19
    
    section Заявки
    Заявка 51157 (вычеты по ИИС)     :milestone, 2025-01-11, 0d
```

## 7. План устранения проблемы

```mermaid
graph TD
    A[Начало] --> B{Получить определение<br/>Get_NDFL_Nach из META}
    
    B -->|SQL запрос| C[Анализ сигнатуры<br/>и параметров]
    
    C --> D{Сколько параметров<br/>ожидается?}
    
    D -->|8 параметров| E[Проблема в другом<br/>Проверить типы]
    D -->|9 параметров| F[Добавить TAX_DED_EX<br/>как 9-й параметр]
    D -->|Другое| G[Детальный анализ<br/>изменений]
    
    E --> H[Исправить<br/>OP_P_NDFL_PRC_BODY]
    F --> H
    G --> H
    
    H --> I[Обновить FUNC_BODY<br/>в DICMETAF]
    
    I --> J[Тестирование<br/>на тестовых данных]
    
    J --> K{Тесты прошли?}
    
    K -->|Да| L[Развёртывание<br/>в продакшн]
    K -->|Нет| M[Дополнительная<br/>отладка]
    
    M --> H
    
    L --> N[Документирование<br/>изменений]
    
    N --> O[Конец]
    
    style D fill:#fff9c4
    style F fill:#c8e6c9
    style K fill:#ffccbc
    style L fill:#b2dfdb
```

## 8. Архитектура решения для предотвращения проблем

```mermaid
graph TB
    subgraph "Новый инструментарий"
        Parser[FANSY-SCRIPT Parser<br/>Парсинг кода]
        Analyzer[Static Analyzer<br/>Проверка типов]
        DepGraph[Dependency Graph<br/>Граф зависимостей]
        VerControl[Version Control<br/>История изменений]
    end
    
    subgraph "META база"
        DICMETAF[(DICMETAF<br/>Функции)]
        DICMETAF_HISTORY[(DICMETAF_HISTORY<br/>История версий)]
    end
    
    subgraph "Процесс разработки"
        Dev[Разработчик]
        Review[Code Review]
        Test[Автотесты]
        Deploy[Деплой]
    end
    
    Dev -->|Изменяет функцию| DICMETAF
    DICMETAF -->|Триггер| Parser
    Parser --> Analyzer
    Analyzer --> DepGraph
    
    Analyzer -->|Находит проблемы| Review
    DepGraph -->|Показывает затронутые функции| Review
    
    Review -->|Одобрено| Test
    Test -->|Успешно| Deploy
    
    DICMETAF -->|Backup| DICMETAF_HISTORY
    VerControl -->|Управляет| DICMETAF_HISTORY
    
    Deploy -->|Обновляет| DICMETAF
    
    style Analyzer fill:#ffccbc
    style Review fill:#fff9c4
    style Test fill:#c8e6c9
```
