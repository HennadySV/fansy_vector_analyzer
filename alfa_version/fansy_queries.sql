-- ============================================================================
-- SQL-запросы для анализа метаданных системы Fansy
-- ============================================================================

-- 1. ПОИСК ОПРЕДЕЛЕНИЯ ФУНКЦИИ Get_NDFL_Nach
-- ============================================================================
-- Этот запрос найдёт текущую версию функции Get_NDFL_Nach в модуле _F_SPECTRE

SELECT 
    M.FUNC_NAME,
    M.APP_NUM,
    A.APPL_ID,
    M.FUNC_DESCR,
    M.FUNC_HEAD,      -- Заголовок с параметрами
    M.FUNC_BODY,      -- Тело функции
    M.SYS_DATE,       -- Дата последнего изменения
    M.SYS_USER        -- Кто изменял
FROM 
    META.DICMETAF M
    JOIN META.DICAPPL A ON A.NUM = M.APP_NUM
WHERE 
    M.FUNC_NAME = 'Get_NDFL_Nach'
    AND A.APPL_ID = '_F_SPECTRE'
ORDER BY 
    M.SYS_DATE DESC;


-- 2. ИСТОРИЯ ИЗМЕНЕНИЙ ФУНКЦИИ (если есть система версионирования)
-- ============================================================================
-- Если в системе ведётся история, можно увидеть все версии функции

SELECT 
    M.FUNC_NAME,
    M.FUNC_HEAD,
    M.SYS_DATE,
    M.SYS_USER,
    LENGTH(M.FUNC_BODY) AS BODY_SIZE
FROM 
    META.DICMETAF M
    JOIN META.DICAPPL A ON A.NUM = M.APP_NUM
WHERE 
    M.FUNC_NAME LIKE '%Get_NDFL_Nach%'
    AND A.APPL_ID = '_F_SPECTRE'
ORDER BY 
    M.SYS_DATE DESC;


-- 3. ПОИСК ВСЕХ ВЫЗОВОВ Get_NDFL_Nach В СИСТЕМЕ
-- ============================================================================
-- Находит все функции, которые вызывают Get_NDFL_Nach

SELECT 
    M.FUNC_NAME AS CALLER_FUNCTION,
    A.APPL_ID AS CALLER_MODULE,
    M.FUNC_DESCR,
    M.SYS_DATE,
    -- Подсчёт вхождений (примерно)
    (LENGTH(M.FUNC_BODY) - LENGTH(REPLACE(M.FUNC_BODY, 'Get_NDFL_Nach', ''))) / 14 AS CALLS_COUNT
FROM 
    META.DICMETAF M
    JOIN META.DICAPPL A ON A.NUM = M.APP_NUM
WHERE 
    M.FUNC_BODY CONTAINING 'Get_NDFL_Nach'
ORDER BY 
    CALLS_COUNT DESC, M.FUNC_NAME;


-- 4. ИНФОРМАЦИЯ О ДОКУМЕНТЕ С ОШИБКОЙ
-- ============================================================================
-- Получаем данные о документе doc_id=4734767

SELECT 
    D.ID,
    D.NUM AS DOC_NUMBER,
    D.D_DATE AS DOC_DATE,
    D.D_CAT,
    DC.CAT_NAME,
    DC.SYS_NAME,
    D.WHOS AS USER_ID,
    D.STATE
FROM 
    DATA.OD_DOCS D
    LEFT JOIN DATA.OD_DOC_CATS DC ON DC.ID = D.D_CAT
WHERE 
    D.ID = 4734767;


-- 5. ДИРЕКТИВА ДОКУМЕНТА (STEP)
-- ============================================================================
-- Получаем информацию о директиве dir_id=4734776

SELECT 
    S.ID AS STEP_ID,
    S.DOC AS DOC_ID,
    S.S_NUM AS STEP_NUMBER,
    S.FUNC_NAME,
    S.STATE,
    S.ERROR_CODE,
    S.ERROR_TEXT,
    S.EXEC_DATE,
    S.EXEC_TIME
FROM 
    DATA.OD_STEPS S
WHERE 
    S.ID = 4734776;


-- 6. ПРОВОДКИ ПО ДОКУМЕНТУ
-- ============================================================================
-- Смотрим какие проводки создал документ

SELECT 
    W.ID AS WIRING_ID,
    W.O_STEP AS STEP_ID,
    W.WIRDATE AS WIRING_DATE,
    W.NUM AS WIRING_NUMBER,
    T.TYPE_ AS TURN_TYPE,
    T.AMOUNT,
    B.SYS_NAME AS BALANCE_ACCOUNT,
    B.ACC_NAME AS ACCOUNT_NAME
FROM 
    DATA.OD_WIRING W
    JOIN DATA.OD_STEPS S ON S.ID = W.O_STEP
    LEFT JOIN DATA.OD_TURNS T ON T.WIRING = W.ID
    LEFT JOIN DATA.OD_RESTS R ON R.ID = T.REST
    LEFT JOIN DATA.OD_BALANCES B ON B.ID = R.BAL_ACC
WHERE 
    S.DOC = 4734767
ORDER BY 
    W.WIRDATE, W.ID, T.TYPE_;


-- 7. СПЕЦИФИЧНЫЕ ДАННЫЕ РАСЧЁТА НДФЛ
-- ============================================================================
-- Таблица U_OP_P_NDFL содержит специфичные поля для расчёта

SELECT 
    H.*
FROM 
    DATA.U_OP_P_NDFL H
WHERE 
    H.DOC = 4734767;


-- 8. НАЧИСЛЕНИЯ НДФЛ ПО ИНВЕСТОРУ
-- ============================================================================
-- Смотрим историю начислений НДФЛ для понимания контекста

SELECT 
    N.ID,
    N.FACE,
    N.R_DATE,
    N.R_TYPE,
    N.CODE,
    N.SUMMA,
    N.LINK_CODE
FROM 
    DATA.OD_NDFL N
WHERE 
    N.FACE = (SELECT INVESTOR FROM DATA.U_OP_P_NDFL WHERE DOC = 4734767)
    AND N.R_DATE >= '2025-01-01'
ORDER BY 
    N.R_DATE DESC;


-- 9. СПИСОК ВСЕХ ФУНКЦИЙ МОДУЛЯ _F_SPECTRE
-- ============================================================================
-- Для понимания контекста модуля

SELECT 
    M.FUNC_NAME,
    M.FUNC_DESCR,
    M.SYS_DATE,
    LENGTH(M.FUNC_BODY) AS CODE_SIZE,
    CASE 
        WHEN M.FUNC_BODY CONTAINING 'Get_NDFL' THEN 'X'
        ELSE ''
    END AS USES_NDFL
FROM 
    META.DICMETAF M
    JOIN META.DICAPPL A ON A.NUM = M.APP_NUM
WHERE 
    A.APPL_ID = '_F_SPECTRE'
ORDER BY 
    M.FUNC_NAME;


-- 10. ЗАВИСИМЫЕ ФУНКЦИИ (которые вызывают друг друга)
-- ============================================================================
-- Строим граф зависимостей функций в модуле _F_SPECTRE

WITH RECURSIVE FuncDeps AS (
    SELECT 
        M1.FUNC_NAME AS CALLER,
        M2.FUNC_NAME AS CALLEE,
        1 AS LEVEL
    FROM 
        META.DICMETAF M1
        JOIN META.DICAPPL A1 ON A1.NUM = M1.APP_NUM
        CROSS JOIN META.DICMETAF M2
        JOIN META.DICAPPL A2 ON A2.NUM = M2.APP_NUM
    WHERE 
        A1.APPL_ID = '_F_SPECTRE'
        AND M1.FUNC_BODY CONTAINING M2.FUNC_NAME
        AND M1.FUNC_NAME <> M2.FUNC_NAME
        AND M2.FUNC_NAME LIKE 'Get_%'
    
    UNION ALL
    
    SELECT 
        FD.CALLER,
        M.FUNC_NAME,
        FD.LEVEL + 1
    FROM 
        FuncDeps FD
        JOIN META.DICMETAF M ON M.FUNC_NAME <> FD.CALLER
        JOIN META.DICAPPL A ON A.NUM = M.APP_NUM
    WHERE 
        FD.LEVEL < 3
        AND A.APPL_ID = '_F_SPECTRE'
        AND FD.CALLEE = M.FUNC_NAME
)
SELECT DISTINCT 
    CALLER,
    CALLEE,
    LEVEL
FROM 
    FuncDeps
WHERE 
    CALLER = 'OP_P_NDFL_PRC_BODY' 
    OR CALLEE CONTAINING 'NDFL'
ORDER BY 
    LEVEL, CALLER, CALLEE;


-- 11. ПОИСК ИЗМЕНЕНИЙ В ОКТЯБРЕ 2025
-- ============================================================================
-- Находим все функции, изменённые в период предполагаемого изменения Get_NDFL_Nach

SELECT 
    M.FUNC_NAME,
    A.APPL_ID,
    M.FUNC_DESCR,
    M.SYS_DATE,
    M.SYS_USER
FROM 
    META.DICMETAF M
    JOIN META.DICAPPL A ON A.NUM = M.APP_NUM
WHERE 
    M.SYS_DATE >= '2025-10-01' 
    AND M.SYS_DATE < '2025-11-01'
    AND (
        M.FUNC_NAME CONTAINING 'NDFL'
        OR M.FUNC_BODY CONTAINING 'Get_NDFL_Nach'
        OR M.FUNC_BODY CONTAINING 'TAX_DED'
    )
ORDER BY 
    M.SYS_DATE DESC;


-- 12. ОПЦИИ ПРИЛОЖЕНИЯ
-- ============================================================================
-- Проверяем настройки, которые могут влиять на поведение

SELECT 
    APP_ID,
    OPTION_NAME,
    OPTION_VALUE,
    DESCR
FROM 
    META.DICOPT
WHERE 
    (OPTION_NAME LIKE '%NDFL%' OR OPTION_NAME LIKE '%TAX%')
    AND APP_ID IN (SELECT APPL_ID FROM META.DICAPPL WHERE APPL_ID = '_F_SPECTRE')
ORDER BY 
    OPTION_NAME;


-- ============================================================================
-- UTILITY: Экспорт тела функции в файл (для анализа)
-- ============================================================================
-- Этот запрос можно использовать для экспорта тела функции

SELECT 
    M.FUNC_HEAD || '
' || M.FUNC_BODY AS FULL_FUNCTION
FROM 
    META.DICMETAF M
    JOIN META.DICAPPL A ON A.NUM = M.APP_NUM
WHERE 
    M.FUNC_NAME = 'Get_NDFL_Nach'
    AND A.APPL_ID = '_F_SPECTRE';


-- ============================================================================
-- ДИАГНОСТИКА: Проверка целостности метаданных
-- ============================================================================

-- Проверка наличия всех необходимых таблиц
SELECT 
    'META' AS DATABASE,
    RDB$RELATION_NAME AS TABLE_NAME
FROM 
    RDB$RELATIONS
WHERE 
    RDB$RELATION_NAME IN ('DICMETAF', 'DICAPPL', 'DICFORMS', 'DICSELEC', 'DICFIELD')
    AND RDB$SYSTEM_FLAG = 0
ORDER BY 
    RDB$RELATION_NAME;

-- Статистика по функциям в системе
SELECT 
    A.APPL_ID,
    COUNT(*) AS FUNCTION_COUNT,
    SUM(LENGTH(M.FUNC_BODY)) AS TOTAL_CODE_SIZE,
    AVG(LENGTH(M.FUNC_BODY)) AS AVG_FUNCTION_SIZE
FROM 
    META.DICMETAF M
    JOIN META.DICAPPL A ON A.NUM = M.APP_NUM
GROUP BY 
    A.APPL_ID
ORDER BY 
    FUNCTION_COUNT DESC;
