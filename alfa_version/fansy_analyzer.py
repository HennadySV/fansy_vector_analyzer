#!/usr/bin/env python3
"""
Fansy-SCRIPT Code Analyzer
Инструмент для анализа кода, поиска ошибок и проверки совместимости функций
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class FunctionSignature:
    """Сигнатура функции FANSY-SCRIPT"""
    name: str
    module: str
    params: List[Tuple[str, str]]  # [(param_name, param_type), ...]
    description: str
    line_number: int = 0
    
    def param_count(self) -> int:
        return len(self.params)
    
    def __str__(self):
        params_str = ', '.join([f'{name}:{type_}' for name, type_ in self.params])
        return f"{self.module}->{self.name}({params_str})"


@dataclass
class FunctionCall:
    """Вызов функции в коде"""
    name: str
    module: str
    args_count: int
    line_number: int
    line_text: str
    args: List[str]  # Текстовое представление аргументов
    
    def __str__(self):
        return f"Line {self.line_number}: {self.module}->{self.name}(...{self.args_count} args)"


@dataclass
class ErrorLogEntry:
    """Запись из лога ошибок"""
    error_type: str
    function_name: str
    line_number: int
    message: str
    doc_id: Optional[int] = None
    dir_id: Optional[int] = None


class FansyScriptParser:
    """Парсер кода FANSY-SCRIPT"""
    
    # Регулярные выражения для парсинга
    FUNC_HEADER_RE = re.compile(r'//\s*(\w+)\((.*?)\)\s*//==\s*(.*?)$', re.MULTILINE)
    USES_RE = re.compile(r'uses\s+([\w,\s_]+);', re.IGNORECASE)
    FUNC_CALL_RE = re.compile(r'(\w+)->(\w+)\s*\((.*?)\)', re.DOTALL)
    VAR_DECL_RE = re.compile(r'var\s+([\w\s,.:=()\'"\-+\[\]]+);', re.IGNORECASE)
    
    def __init__(self):
        self.functions: Dict[str, FunctionSignature] = {}
        self.calls: List[FunctionCall] = []
        self.modules_used: List[str] = []
        
    def parse_function_header(self, code: str) -> Optional[FunctionSignature]:
        """Парсит заголовок функции"""
        match = self.FUNC_HEADER_RE.search(code)
        if not match:
            return None
            
        func_name = match.group(1)
        params_str = match.group(2)
        description = match.group(3)
        
        # Парсим параметры
        params = []
        if params_str.strip():
            for param in params_str.split(','):
                param = param.strip()
                if ':' in param:
                    # %param:type формат
                    param_parts = param.split(':')
                    param_name = param_parts[0].strip().lstrip('%')
                    param_type = param_parts[1].strip()
                    params.append((param_name, param_type))
                else:
                    # Только имя, тип неизвестен
                    params.append((param.lstrip('%'), 'unknown'))
        
        return FunctionSignature(
            name=func_name,
            module='',  # Будет определён из контекста
            params=params,
            description=description
        )
    
    def parse_uses(self, code: str) -> List[str]:
        """Извлекает список используемых модулей"""
        match = self.USES_RE.search(code)
        if not match:
            return []
        
        modules_str = match.group(1)
        return [m.strip() for m in modules_str.split(',')]
    
    def parse_function_calls(self, code: str) -> List[FunctionCall]:
        """Находит все вызовы функций в коде"""
        calls = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Пропускаем комментарии
            if line.strip().startswith('//'):
                continue
            
            # Ищем вызовы функций MODULE->Function(...)
            for match in self.FUNC_CALL_RE.finditer(line):
                module = match.group(1)
                func_name = match.group(2)
                args_str = match.group(3)
                
                # Подсчитываем аргументы (упрощённо)
                args = self._parse_arguments(args_str)
                
                calls.append(FunctionCall(
                    name=func_name,
                    module=module,
                    args_count=len(args),
                    line_number=i,
                    line_text=line.strip(),
                    args=args
                ))
        
        return calls
    
    def _parse_arguments(self, args_str: str) -> List[str]:
        """Разбирает строку аргументов на отдельные аргументы"""
        if not args_str.strip():
            return []
        
        # Упрощённый парсинг - просто по запятым на верхнем уровне
        # TODO: Учитывать вложенные вызовы и строки
        args = []
        level = 0
        current_arg = []
        
        for char in args_str:
            if char == '(':
                level += 1
                current_arg.append(char)
            elif char == ')':
                level -= 1
                current_arg.append(char)
            elif char == ',' and level == 0:
                args.append(''.join(current_arg).strip())
                current_arg = []
            else:
                current_arg.append(char)
        
        if current_arg:
            args.append(''.join(current_arg).strip())
        
        return args
    
    def analyze_file(self, filepath: str) -> Dict:
        """Анализирует файл с кодом FANSY-SCRIPT"""
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Извлекаем информацию
        header = self.parse_function_header(code)
        modules = self.parse_uses(code)
        calls = self.parse_function_calls(code)
        
        return {
            'header': header,
            'modules': modules,
            'calls': calls,
            'total_lines': len(code.split('\n')),
            'code': code
        }


class CompatibilityChecker:
    """Проверка совместимости вызовов функций"""
    
    def __init__(self):
        self.signatures: Dict[str, FunctionSignature] = {}
        self.issues: List[Dict] = []
    
    def register_signature(self, sig: FunctionSignature):
        """Регистрирует сигнатуру функции"""
        key = f"{sig.module}.{sig.name}"
        self.signatures[key] = sig
    
    def check_call(self, call: FunctionCall) -> Optional[Dict]:
        """Проверяет вызов функции на совместимость"""
        key = f"{call.module}.{call.name}"
        
        if key not in self.signatures:
            return {
                'type': 'UNKNOWN_FUNCTION',
                'severity': 'WARNING',
                'call': call,
                'message': f"Функция {key} не найдена в базе сигнатур"
            }
        
        sig = self.signatures[key]
        
        if call.args_count != sig.param_count():
            return {
                'type': 'PARAM_COUNT_MISMATCH',
                'severity': 'ERROR',
                'call': call,
                'signature': sig,
                'message': f"Ожидается {sig.param_count()} параметров, передано {call.args_count}"
            }
        
        return None
    
    def check_all_calls(self, calls: List[FunctionCall]) -> List[Dict]:
        """Проверяет все вызовы и возвращает список проблем"""
        issues = []
        
        for call in calls:
            issue = self.check_call(call)
            if issue:
                issues.append(issue)
        
        return issues


class ErrorLogParser:
    """Парсер логов ошибок"""
    
    ERROR_PATTERNS = [
        (r'Не все входные параметры означены.*функци[ияю]\s+(\w+).*строка\s+(\d+)', 'PARAM_NOT_DEFINED'),
        (r'Ошибка.*doc_id[=:\s]+(\d+)', 'DOC_ERROR'),
        (r'dir_id[=:\s]+(\d+)', 'DIR_ERROR'),
    ]
    
    def parse_log(self, log_text: str) -> List[ErrorLogEntry]:
        """Парсит лог и извлекает записи об ошибках"""
        entries = []
        
        lines = log_text.split('\n')
        for line in lines:
            for pattern, error_type in self.ERROR_PATTERNS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    entry = ErrorLogEntry(
                        error_type=error_type,
                        function_name=match.group(1) if match.lastindex >= 1 else '',
                        line_number=int(match.group(2)) if match.lastindex >= 2 else 0,
                        message=line
                    )
                    entries.append(entry)
                    break
        
        return entries


class DependencyAnalyzer:
    """Анализатор зависимостей между функциями и таблицами"""
    
    def __init__(self):
        self.function_calls: Dict[str, List[str]] = defaultdict(list)  # func -> [called_funcs]
        self.table_access: Dict[str, List[str]] = defaultdict(list)    # func -> [tables]
    
    def add_function_call(self, caller: str, callee: str):
        """Регистрирует вызов функции"""
        self.function_calls[caller].append(callee)
    
    def add_table_access(self, function: str, table: str):
        """Регистрирует обращение к таблице"""
        self.table_access[function].append(table)
    
    def get_call_chain(self, function: str, max_depth: int = 5) -> List[List[str]]:
        """Возвращает цепочку вызовов от функции"""
        chains = []
        
        def traverse(func: str, chain: List[str], depth: int):
            if depth > max_depth or func in chain:  # Защита от циклов
                return
            
            new_chain = chain + [func]
            
            if func not in self.function_calls or not self.function_calls[func]:
                chains.append(new_chain)
                return
            
            for called in self.function_calls[func]:
                traverse(called, new_chain, depth + 1)
        
        traverse(function, [], 0)
        return chains
    
    def generate_mermaid_graph(self, function: str, include_tables: bool = True) -> str:
        """Генерирует Mermaid-граф зависимостей"""
        lines = ["graph TD"]
        
        # Добавляем вызовы функций
        for caller, callees in self.function_calls.items():
            if caller == function or function in self.function_calls.get(caller, []):
                for callee in callees:
                    lines.append(f"    {caller}[{caller}] --> {callee}[{callee}]")
        
        # Добавляем таблицы
        if include_tables:
            for func, tables in self.table_access.items():
                if func == function or function in self.function_calls.get(func, []):
                    for table in tables:
                        lines.append(f"    {func}[{func}] -.-> {table}[({table})]")
        
        return '\n'.join(lines)


def main():
    """Демонстрация использования инструментов"""
    print("=" * 70)
    print("Fansy-SCRIPT Code Analyzer")
    print("=" * 70)
    print()
    
    # Парсим файл с проблемной функцией
    parser = FansyScriptParser()
    result = parser.analyze_file('/mnt/user-data/uploads/OP_P_NDFL_PRC_BODY.txt')
    
    print(f"📄 Файл проанализирован: OP_P_NDFL_PRC_BODY.txt")
    print(f"   Строк кода: {result['total_lines']}")
    print(f"   Используемых модулей: {len(result['modules'])}")
    print(f"   Вызовов функций: {len(result['calls'])}")
    print()
    
    if result['header']:
        print(f"📋 Заголовок функции:")
        print(f"   Имя: {result['header'].name}")
        print(f"   Параметры: {result['header'].param_count()}")
        for param_name, param_type in result['header'].params:
            print(f"      - {param_name}: {param_type}")
        print(f"   Описание: {result['header'].description}")
        print()
    
    print(f"📦 Используемые модули:")
    for module in result['modules']:
        print(f"   - {module}")
    print()
    
    # Находим проблемный вызов Get_NDFL_Nach
    print(f"🔍 Поиск вызовов Get_NDFL_Nach:")
    ndfl_calls = [c for c in result['calls'] if c.name == 'Get_NDFL_Nach']
    
    for call in ndfl_calls:
        print(f"\n   Строка {call.line_number}:")
        print(f"   Модуль: {call.module}")
        print(f"   Аргументов: {call.args_count}")
        print(f"   Код: {call.line_text[:80]}...")
        print(f"   Аргументы:")
        for i, arg in enumerate(call.args, 1):
            print(f"      {i}. {arg[:60]}{'...' if len(arg) > 60 else ''}")
    
    print()
    print("=" * 70)
    print("✅ Анализ завершён")
    print()
    print("💡 Рекомендации:")
    print("   1. Проверьте актуальную сигнатуру Get_NDFL_Nach в META.DICMETAF")
    print("   2. Сравните количество параметров (найдено: 8)")
    print("   3. Обратите внимание на строку 2184 - новый расчёт TAX_DED_EX")
    print("   4. Возможно, TAX_DED_EX должен быть 9-м параметром")
    print()


if __name__ == '__main__':
    main()
