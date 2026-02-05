#!/usr/bin/env python3
"""
Dependency Graph Builder
Строит граф зависимостей функций FANSY-SCRIPT
"""

import json
import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import networkx as nx
from datetime import datetime


class DependencyGraphBuilder:
    """Строитель графа зависимостей функций"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.functions = {}  # func_name -> func_info
        self.call_counts = defaultdict(int)  # (caller, callee) -> count
        
    def add_function(self, name: str, module: str, params: List[Tuple[str, str]] = None, 
                     description: str = '', code_lines: int = 0):
        """Добавить функцию в граф"""
        self.functions[name] = {
            'name': name,
            'module': module,
            'params': params or [],
            'description': description,
            'code_lines': code_lines
        }
        
        self.graph.add_node(name,
            module=module,
            params=len(params) if params else 0,
            lines=code_lines,
            description=description[:100]
        )
    
    def add_call(self, caller: str, callee: str, line_number: int = None):
        """Добавить вызов функции"""
        # Увеличиваем счётчик вызовов
        self.call_counts[(caller, callee)] += 1
        
        # Добавляем рёбро или обновляем вес
        if self.graph.has_edge(caller, callee):
            self.graph[caller][callee]['weight'] += 1
            self.graph[caller][callee]['lines'].append(line_number)
        else:
            self.graph.add_edge(caller, callee,
                weight=1,
                lines=[line_number] if line_number else []
            )
    
    def get_function_info(self, name: str) -> Dict:
        """Получить информацию о функции"""
        if name not in self.functions:
            return None
        
        info = self.functions[name].copy()
        
        # Добавляем статистику из графа
        if name in self.graph:
            info['calls_to'] = list(self.graph.successors(name))
            info['called_by'] = list(self.graph.predecessors(name))
            info['out_degree'] = self.graph.out_degree(name)
            info['in_degree'] = self.graph.in_degree(name)
        
        return info
    
    def get_subgraph(self, func_name: str, depth: int = 2, direction: str = 'both') -> nx.DiGraph:
        """
        Получить подграф вокруг функции
        
        direction: 'both', 'forward' (кого вызывает), 'backward' (кто вызывает)
        """
        if func_name not in self.graph:
            return nx.DiGraph()
        
        nodes = {func_name}
        
        # Forward - кого вызывает эта функция
        if direction in ('both', 'forward'):
            for _ in range(depth):
                new_nodes = set()
                for node in nodes:
                    new_nodes.update(self.graph.successors(node))
                nodes.update(new_nodes)
        
        # Backward - кто вызывает эту функцию
        if direction in ('both', 'backward'):
            for _ in range(depth):
                new_nodes = set()
                for node in nodes:
                    new_nodes.update(self.graph.predecessors(node))
                nodes.update(new_nodes)
        
        return self.graph.subgraph(nodes).copy()
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """Найти циклические зависимости"""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except:
            return []
    
    def get_call_path(self, from_func: str, to_func: str) -> List[str]:
        """Найти путь вызовов между функциями"""
        try:
            if from_func in self.graph and to_func in self.graph:
                return nx.shortest_path(self.graph, from_func, to_func)
            return []
        except nx.NetworkXNoPath:
            return []
    
    def get_most_called_functions(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Самые часто вызываемые функции"""
        in_degrees = dict(self.graph.in_degree())
        sorted_funcs = sorted(in_degrees.items(), key=lambda x: -x[1])
        return sorted_funcs[:limit]
    
    def get_most_calling_functions(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Функции, которые вызывают больше всего других"""
        out_degrees = dict(self.graph.out_degree())
        sorted_funcs = sorted(out_degrees.items(), key=lambda x: -x[1])
        return sorted_funcs[:limit]
    
    def get_central_functions(self, limit: int = 10) -> List[Tuple[str, float]]:
        """Центральные функции (по betweenness centrality)"""
        if len(self.graph) == 0:
            return []
        
        centrality = nx.betweenness_centrality(self.graph)
        sorted_funcs = sorted(centrality.items(), key=lambda x: -x[1])
        return sorted_funcs[:limit]
    
    def get_isolated_functions(self) -> List[str]:
        """Изолированные функции (не вызывают и не вызываются)"""
        isolated = [node for node in self.graph.nodes() 
                   if self.graph.in_degree(node) == 0 and self.graph.out_degree(node) == 0]
        return isolated
    
    def get_stats(self) -> Dict:
        """Статистика графа"""
        stats = {
            'total_functions': len(self.graph.nodes()),
            'total_calls': len(self.graph.edges()),
            'avg_calls_per_function': len(self.graph.edges()) / len(self.graph.nodes()) if len(self.graph.nodes()) > 0 else 0,
            'most_called': self.get_most_called_functions(5),
            'most_calling': self.get_most_calling_functions(5),
            'circular_dependencies': len(self.find_circular_dependencies()),
            'isolated_functions': len(self.get_isolated_functions())
        }
        
        # Группируем по модулям
        by_module = defaultdict(int)
        for node, data in self.graph.nodes(data=True):
            by_module[data.get('module', 'unknown')] += 1
        stats['by_module'] = dict(by_module)
        
        return stats
    
    def export_to_json(self, filename: str):
        """Экспорт в JSON"""
        # Конвертируем граф в JSON-совместимый формат
        nodes = []
        for node, data in self.graph.nodes(data=True):
            node_info = {
                'id': node,
                'module': data.get('module', ''),
                'params': data.get('params', 0),
                'lines': data.get('lines', 0),
                'in_degree': self.graph.in_degree(node),
                'out_degree': self.graph.out_degree(node)
            }
            nodes.append(node_info)
        
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edge_info = {
                'from': u,
                'to': v,
                'weight': data.get('weight', 1),
                'lines': data.get('lines', [])
            }
            edges.append(edge_info)
        
        graph_data = {
            'stats': self.get_stats(),
            'nodes': nodes,
            'edges': edges,
            'exported_at': datetime.now().isoformat()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Граф экспортирован в {filename}")
    
    def export_to_html(self, filename: str, focus_func: str = None):
        """
        Экспорт в интерактивный HTML (vis.js)
        """
        # Подграф если задана функция
        if focus_func and focus_func in self.graph:
            subgraph = self.get_subgraph(focus_func, depth=2)
        else:
            subgraph = self.graph
        
        # Готовим данные для vis.js
        nodes_data = []
        for node, data in subgraph.nodes(data=True):
            color = self._get_node_color(data.get('module', ''))
            
            nodes_data.append({
                'id': node,
                'label': node,
                'title': f"{node}\nМодуль: {data.get('module', 'unknown')}\nПараметров: {data.get('params', 0)}",
                'color': color,
                'size': 20 + data.get('lines', 0) / 10
            })
        
        edges_data = []
        for u, v, data in subgraph.edges(data=True):
            edges_data.append({
                'from': u,
                'to': v,
                'value': data.get('weight', 1),
                'title': f"Вызовов: {data.get('weight', 1)}"
            })
        
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Fansy Dependency Graph{' - ' + focus_func if focus_func else ''}</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
        }}
        #mynetwork {{
            width: 100%;
            height: 800px;
            border: 1px solid lightgray;
        }}
        .info {{
            margin-bottom: 20px;
            padding: 10px;
            background: #f0f0f0;
            border-radius: 5px;
        }}
        h1 {{
            margin: 0 0 10px 0;
        }}
    </style>
</head>
<body>
    <div class="info">
        <h1>Граф зависимостей функций Fansy</h1>
        {f'<p><strong>Фокус на функции:</strong> {focus_func}</p>' if focus_func else ''}
        <p><strong>Функций:</strong> {len(nodes_data)} | <strong>Связей:</strong> {len(edges_data)}</p>
    </div>
    
    <div id="mynetwork"></div>
    
    <script type="text/javascript">
        var nodes = new vis.DataSet({json.dumps(nodes_data)});
        var edges = new vis.DataSet({json.dumps(edges_data)});
        
        var container = document.getElementById('mynetwork');
        var data = {{
            nodes: nodes,
            edges: edges
        }};
        var options = {{
            nodes: {{
                shape: 'dot',
                font: {{
                    size: 14
                }}
            }},
            edges: {{
                arrows: 'to',
                smooth: {{
                    type: 'cubicBezier'
                }}
            }},
            physics: {{
                stabilization: {{
                    iterations: 200
                }},
                barnesHut: {{
                    gravitationalConstant: -8000,
                    springConstant: 0.04,
                    springLength: 150
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 100
            }}
        }};
        
        var network = new vis.Network(container, data, options);
        
        // Клик по узлу - показываем детали
        network.on("click", function (params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                alert('Функция: ' + nodeId + '\\n\\nДля подробностей смотрите консоль');
                console.log('Node clicked:', nodeId, nodes.get(nodeId));
            }}
        }});
    </script>
</body>
</html>
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_template)
        
        print(f"✅ Интерактивный HTML создан: {filename}")
    
    def _get_node_color(self, module: str) -> str:
        """Цвет узла по модулю"""
        colors = {
            '_F_SPECTRE': '#FF6B6B',
            '_F_BUX': '#4ECDC4',
            '_F_DOC': '#45B7D1',
            '_F_PIF': '#FFA07A',
            '_F_ECO': '#98D8C8',
            '_METAL_F': '#C7CEEA',
            '_F_REPORT': '#FFDAB9'
        }
        return colors.get(module, '#95E1D3')


def example_usage():
    """Пример использования"""
    print("="*70)
    print("Пример построения графа зависимостей")
    print("="*70 + "\n")
    
    builder = DependencyGraphBuilder()
    
    # Добавляем функции
    builder.add_function('OP_P_NDFL_PRC_BODY', '_F_SPECTRE', 
        [('doc_id', 'int'), ('dir_id', 'int')],
        'Расчет НДФЛ', 2236)
    
    builder.add_function('Get_NDFL_Nach', '_F_SPECTRE',
        [('b_date', 'DATE'), ('e_date', 'DATE'), ('investor', 'INT')],
        'Получить начисленный НДФЛ', 150)
    
    builder.add_function('Get_Rate', '_F_BUX',
        [('date', 'DATE'), ('currency', 'STRING')],
        'Получить курс валюты', 50)
    
    builder.add_function('GetDoc', '_F_DOC',
        [('doc_id', 'INT')],
        'Получить документ', 80)
    
    builder.add_function('Get_CrossRate', '_F_BUX',
        [('from_val', 'STRING'), ('to_val', 'STRING')],
        'Кросс-курс', 40)
    
    # Добавляем вызовы
    builder.add_call('OP_P_NDFL_PRC_BODY', 'Get_NDFL_Nach', 2192)
    builder.add_call('OP_P_NDFL_PRC_BODY', 'Get_NDFL_Nach', 2193)
    builder.add_call('OP_P_NDFL_PRC_BODY', 'GetDoc', 30)
    builder.add_call('OP_P_NDFL_PRC_BODY', 'Get_Rate', 45)
    builder.add_call('GetDoc', 'Get_CrossRate', 20)
    builder.add_call('Get_NDFL_Nach', 'Get_Rate', 50)
    
    # Статистика
    print("📊 СТАТИСТИКА ГРАФА")
    print("="*70)
    stats = builder.get_stats()
    print(f"Всего функций: {stats['total_functions']}")
    print(f"Всего вызовов: {stats['total_calls']}")
    print(f"Среднее вызовов на функцию: {stats['avg_calls_per_function']:.2f}")
    print(f"Циклических зависимостей: {stats['circular_dependencies']}")
    print(f"\nПо модулям:")
    for module, count in stats['by_module'].items():
        print(f"  {module}: {count}")
    
    print(f"\nСамые вызываемые функции:")
    for func, count in stats['most_called']:
        print(f"  {func}: {count} вызовов")
    
    # Информация о функции
    print(f"\n📋 ИНФОРМАЦИЯ О ФУНКЦИИ")
    print("="*70)
    info = builder.get_function_info('OP_P_NDFL_PRC_BODY')
    print(f"Имя: {info['name']}")
    print(f"Модуль: {info['module']}")
    print(f"Параметров: {len(info['params'])}")
    print(f"Строк кода: {info['code_lines']}")
    print(f"Вызывает: {', '.join(info['calls_to'])}")
    print(f"Вызывается из: {', '.join(info['called_by'])}")
    
    # Путь между функциями
    print(f"\n🔍 ПУТЬ МЕЖДУ ФУНКЦИЯМИ")
    print("="*70)
    path = builder.get_call_path('OP_P_NDFL_PRC_BODY', 'Get_CrossRate')
    if path:
        print(f"Путь от OP_P_NDFL_PRC_BODY до Get_CrossRate:")
        print(" → ".join(path))
    
    # Экспорт
    builder.export_to_json('data/dependency_graph.json')
    builder.export_to_html('frontend/dependency_graph.html', focus_func='OP_P_NDFL_PRC_BODY')
    
    print(f"\n✅ Готово!")


if __name__ == '__main__':
    example_usage()