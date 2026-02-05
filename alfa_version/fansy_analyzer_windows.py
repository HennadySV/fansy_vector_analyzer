#!/usr/bin/env python3
"""
Fansy-SCRIPT Code Analyzer (Windows version)
Использование: python fansy_analyzer_windows.py путь\к\файлу.txt
"""

import re
import sys
import os
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


def main():
    print("=" * 70)
    print("Fansy-SCRIPT Code Analyzer (Windows)")
    print("=" * 70)
    print()
    
    # Проверяем аргументы
    if len(sys.argv) < 2:
        print("❌ Не указан файл для анализа!")
        print()
        print("Использование:")
        print("  python fansy_analyzer_windows.py <путь_к_файлу>")
        print()
        print("Примеры:")
        print("  python fansy_analyzer_windows.py OP_P_NDFL_PRC_BODY.txt")
        print("  python fansy_analyzer_windows.py C:\\Fansy\\OP_P_NDFL_PRC_BODY.txt")
        print()
        
        # Показываем .txt файлы в текущей директории
        txt_files = [f for f in os.listdir('.') if f.endswith('.txt')]
        if txt_files:
            print("Найденные .txt файлы в текущей директории:")
            for f in txt_files[:10]:  # Показываем максимум 10
                print(f"  - {f}")
            if len(txt_files) > 10:
                print(f"  ... и ещё {len(txt_files) - 10} файлов")
        return
    
    filepath = sys.argv[1]
    
    # Проверяем существование файла
    if not os.path.exists(filepath):
        print(f"❌ Файл не найден: {filepath}")
        print()
        print("Текущая директория:", os.getcwd())
        print()
        print("Файлы .txt в директории:")
        for f in os.listdir('.'):
            if f.endswith('.txt'):
                print(f"  - {f}")
        return
    
    print(f"📄 Анализ файла: {os.path.basename(filepath)}")
    print(f"   Полный путь: {os.path.abspath(filepath)}")
    print()
    
    try:
        # Парсим файл
        parser = FansyScriptParser()
        result = parser.analyze_file(filepath)
        
        print(f"   ✅ Файл успешно прочитан")
        print(f"   📊 Строк кода: {result['total_lines']}")
        print(f"   📦 Используемых модулей: {len(result['modules'])}")
        print(f"   🔧 Вызовов функций: {len(result['calls'])}")
        print()
        
        if result['header']:
            print(f"📋 Заголовок функции:")
            print(f"   Имя: {result['header'].name}")
            print(f"   Параметров: {result['header'].param_count()}")
            if result['header'].params:
                print(f"   Параметры:")
                for param_name, param_type in result['header'].params:
                    print(f"      - {param_name}: {param_type}")
            print(f"   Описание: {result['header'].description}")
            print()
        else:
            print("⚠️  Заголовок функции не найден (возможно, это не функция или формат отличается)")
            print()
        
        if result['modules']:
            print(f"📦 Используемые модули:")
            for module in result['modules']:
                print(f"   - {module}")
            print()
        else:
            print("⚠️  Модули не найдены (строка 'uses' отсутствует)")
            print()
        
        # Статистика вызовов
        if result['calls']:
            print(f"🔧 Статистика вызовов функций:")
            
            # Группируем по модулям
            by_module = defaultdict(list)
            for call in result['calls']:
                by_module[call.module].append(call)
            
            for module, calls in sorted(by_module.items()):
                print(f"\n   Модуль {module}: {len(calls)} вызовов")
                
                # Группируем по именам функций
                by_name = defaultdict(int)
                for call in calls:
                    by_name[call.name] += 1
                
                for func_name, count in sorted(by_name.items(), key=lambda x: -x[1])[:5]:
                    print(f"      - {func_name}: {count}x")
                
                if len(by_name) > 5:
                    print(f"      ... и ещё {len(by_name) - 5} функций")
            print()
        
        # Находим конкретные вызовы (если ищем что-то)
        interesting_functions = ['Get_NDFL_Nach', 'Get_NDFL', 'NDFL']
        found_interesting = []
        
        for target in interesting_functions:
            matching = [c for c in result['calls'] if target.lower() in c.name.lower()]
            if matching:
                found_interesting.extend(matching)
        
        if found_interesting:
            print(f"🔍 Найдены интересные вызовы (NDFL-related):")
            for call in found_interesting[:10]:  # Показываем максимум 10
                print(f"\n   📍 Строка {call.line_number}: {call.module}->{call.name}")
                print(f"      Аргументов: {call.args_count}")
                print(f"      Код: {call.line_text[:70]}{'...' if len(call.line_text) > 70 else ''}")
                if call.args and len(call.args) <= 10:
                    print(f"      Параметры:")
                    for i, arg in enumerate(call.args, 1):
                        print(f"         {i}. {arg[:50]}{'...' if len(arg) > 50 else ''}")
        
        print()
        print("=" * 70)
        print("✅ Анализ завершён успешно")
        print()
        
    except Exception as e:
        print(f"❌ Ошибка при анализе файла:")
        print(f"   {type(e).__name__}: {e}")
        print()
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()