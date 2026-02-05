#!/usr/bin/env python3
"""
Fansy Analytics Web Server
Flask приложение с REST API и Server-Sent Events
"""

from flask import Flask, jsonify, request, render_template_string, Response
from flask_cors import CORS
import json
import time
import threading
from datetime import datetime
from collections import deque

# Импортируем наши модули
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from function_logger import FunctionCallLogger, get_logger
from graph_builder import DependencyGraphBuilder

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для разработки

# Глобальные объекты
function_logger = get_logger()
graph_builder = DependencyGraphBuilder()
event_stream = deque(maxlen=100)  # События для SSE


# ============================================================================
# Server-Sent Events (Real-time updates)
# ============================================================================

def add_event(event_type: str, data: dict):
    """Добавить событие в стрим"""
    event = {
        'type': event_type,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }
    event_stream.append(event)


@app.route('/api/events')
def events():
    """SSE endpoint для real-time обновлений"""
    def generate():
        last_index = 0
        while True:
            # Отправляем новые события
            if len(event_stream) > last_index:
                for i in range(last_index, len(event_stream)):
                    event = event_stream[i]
                    yield f"data: {json.dumps(event)}\n\n"
                last_index = len(event_stream)
            
            # Heartbeat каждые 30 секунд
            yield f": heartbeat\n\n"
            time.sleep(1)
    
    return Response(generate(), mimetype='text/event-stream')


# ============================================================================
# REST API - Function Calls
# ============================================================================

@app.route('/api/function-calls/history')
def get_call_history():
    """История вызовов функций"""
    limit = request.args.get('limit', 100, type=int)
    module = request.args.get('module', None)
    function = request.args.get('function', None)
    
    history = function_logger.get_history(limit, module, function)
    return jsonify({
        'success': True,
        'data': history,
        'count': len(history)
    })


@app.route('/api/function-calls/active')
def get_active_calls():
    """Активные вызовы"""
    active = function_logger.get_active_calls()
    return jsonify({
        'success': True,
        'data': active,
        'count': len(active)
    })


@app.route('/api/function-calls/stats')
def get_call_stats():
    """Статистика вызовов"""
    stats = function_logger.get_stats()
    return jsonify({
        'success': True,
        'data': stats
    })


@app.route('/api/function-calls/slow')
def get_slow_calls():
    """Медленные вызовы"""
    threshold = request.args.get('threshold', 1.0, type=float)
    limit = request.args.get('limit', 10, type=int)
    
    slow = function_logger.get_slow_calls(threshold, limit)
    return jsonify({
        'success': True,
        'data': slow,
        'count': len(slow)
    })


@app.route('/api/function-calls/tree')
def get_call_tree():
    """Дерево вызовов"""
    root_id = request.args.get('root_id', None, type=int)
    
    tree = function_logger.get_call_tree(root_id)
    return jsonify({
        'success': True,
        'data': tree
    })


# ============================================================================
# REST API - Dependency Graph
# ============================================================================

@app.route('/api/graph/stats')
def get_graph_stats():
    """Статистика графа"""
    stats = graph_builder.get_stats()
    return jsonify({
        'success': True,
        'data': stats
    })


@app.route('/api/graph/function/<func_name>')
def get_function_info(func_name):
    """Информация о функции"""
    info = graph_builder.get_function_info(func_name)
    if info:
        return jsonify({
            'success': True,
            'data': info
        })
    else:
        return jsonify({
            'success': False,
            'error': f"Функция '{func_name}' не найдена"
        }), 404


@app.route('/api/graph/subgraph/<func_name>')
def get_subgraph(func_name):
    """Подграф вокруг функции"""
    depth = request.args.get('depth', 2, type=int)
    direction = request.args.get('direction', 'both')
    
    subgraph = graph_builder.get_subgraph(func_name, depth, direction)
    
    # Конвертируем в JSON
    nodes = []
    for node, data in subgraph.nodes(data=True):
        nodes.append({
            'id': node,
            'module': data.get('module', ''),
            'params': data.get('params', 0),
            'lines': data.get('lines', 0)
        })
    
    edges = []
    for u, v, data in subgraph.edges(data=True):
        edges.append({
            'from': u,
            'to': v,
            'weight': data.get('weight', 1)
        })
    
    return jsonify({
        'success': True,
        'data': {
            'nodes': nodes,
            'edges': edges
        }
    })


@app.route('/api/graph/path')
def get_call_path():
    """Путь между функциями"""
    from_func = request.args.get('from')
    to_func = request.args.get('to')
    
    if not from_func or not to_func:
        return jsonify({
            'success': False,
            'error': 'Параметры from и to обязательны'
        }), 400
    
    path = graph_builder.get_call_path(from_func, to_func)
    return jsonify({
        'success': True,
        'data': path,
        'length': len(path)
    })


@app.route('/api/graph/circular')
def get_circular_deps():
    """Циклические зависимости"""
    cycles = graph_builder.find_circular_dependencies()
    return jsonify({
        'success': True,
        'data': cycles,
        'count': len(cycles)
    })


# ============================================================================
# REST API - Simulation (для тестирования)
# ============================================================================

@app.route('/api/simulate/call', methods=['POST'])
def simulate_call():
    """Симулировать вызов функции (для тестирования)"""
    data = request.json
    
    module = data.get('module', '_F_TEST')
    function = data.get('function', 'test_func')
    params = data.get('params', {})
    duration = data.get('duration', 0.1)
    error = data.get('error', None)
    
    # Начинаем вызов
    call_id = function_logger.start_call(module, function, params)
    
    # Отправляем событие
    add_event('function_call_start', {
        'call_id': call_id,
        'module': module,
        'function': function,
        'params': params
    })
    
    # Симулируем работу
    time.sleep(duration)
    
    # Завершаем
    result = f"Result from {module}.{function}" if not error else None
    function_logger.end_call(call_id, result=result, error=error)
    
    # Отправляем событие
    add_event('function_call_end', {
        'call_id': call_id,
        'module': module,
        'function': function,
        'duration': duration,
        'error': error
    })
    
    return jsonify({
        'success': True,
        'call_id': call_id
    })


# ============================================================================
# Frontend HTML (Single Page)
# ============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Fansy Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header h1 { font-size: 24px; margin-bottom: 5px; }
        .header p { opacity: 0.9; font-size: 14px; }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .panel {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .panel h2 {
            font-size: 18px;
            margin-bottom: 15px;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .stat-card {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .stat-value { font-size: 32px; font-weight: bold; }
        .stat-label { font-size: 14px; opacity: 0.9; }
        .call-item {
            padding: 10px;
            border-left: 3px solid #667eea;
            background: #f9f9f9;
            margin-bottom: 10px;
            border-radius: 4px;
            font-size: 12px;
        }
        .call-item.error { border-left-color: #ff4757; }
        .call-item .call-header {
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        .call-item .call-details {
            color: #666;
            font-size: 11px;
        }
        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 5px;
        }
        .status-running { background: #ffa502; animation: pulse 1s infinite; }
        .status-success { background: #2ed573; }
        .status-error { background: #ff4757; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        #graph { height: 600px; border: 1px solid #ddd; border-radius: 8px; }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin: 5px;
        }
        button:hover { background: #5568d3; }
        .controls { margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Fansy Analytics Dashboard</h1>
        <p>Real-time мониторинг и анализ legacy-системы | <span id="connection-status">🔴 Подключение...</span></p>
    </div>
    
    <div class="container">
        <!-- Статистика -->
        <div class="grid">
            <div class="panel">
                <h2>📊 Статистика вызовов</h2>
                <div class="stat-card">
                    <div>
                        <div class="stat-label">Всего вызовов</div>
                        <div class="stat-value" id="total-calls">0</div>
                    </div>
                    <div style="font-size: 48px;">📞</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                    <div>
                        <div class="stat-label">Среднее время</div>
                        <div class="stat-value" id="avg-time">0ms</div>
                    </div>
                    <div style="font-size: 48px;">⏱️</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                    <div>
                        <div class="stat-label">Активных</div>
                        <div class="stat-value" id="active-calls">0</div>
                    </div>
                    <div style="font-size: 48px;">🔄</div>
                </div>
            </div>
            
            <div class="panel">
                <h2>📈 По модулям</h2>
                <canvas id="modules-chart"></canvas>
            </div>
            
            <div class="panel">
                <h2>🔥 Top функций</h2>
                <canvas id="functions-chart"></canvas>
            </div>
        </div>
        
        <!-- Активные вызовы -->
        <div class="panel">
            <h2>🔄 Активные вызовы (real-time)</h2>
            <div id="active-calls-list" style="max-height: 200px; overflow-y: auto;">
                <p style="color: #999; text-align: center; padding: 20px;">Нет активных вызовов</p>
            </div>
        </div>
        
        <!-- История -->
        <div class="panel">
            <h2>📜 История вызовов (последние 20)</h2>
            <div id="call-history" style="max-height: 400px; overflow-y: auto;"></div>
        </div>
        
        <!-- Граф зависимостей -->
        <div class="panel">
            <h2>🕸️ Граф зависимостей</h2>
            <div class="controls">
                <button onclick="loadGraph('OP_P_NDFL_PRC_BODY')">OP_P_NDFL_PRC_BODY</button>
                <button onclick="loadGraph('Get_NDFL_Nach')">Get_NDFL_Nach</button>
                <button onclick="testSimulation()">🧪 Тест (симуляция)</button>
            </div>
            <div id="graph"></div>
        </div>
    </div>
    
    <script>
        let modulesChart, functionsChart;
        let eventSource;
        
        // Подключение к SSE
        function connectSSE() {
            eventSource = new EventSource('/api/events');
            
            eventSource.onopen = () => {
                document.getElementById('connection-status').innerHTML = '🟢 Подключено';
            };
            
            eventSource.onerror = () => {
                document.getElementById('connection-status').innerHTML = '🔴 Ошибка';
            };
            
            eventSource.onmessage = (event) => {
                if (event.data.trim() === '') return;
                
                try {
                    const data = JSON.parse(event.data);
                    handleEvent(data);
                } catch (e) {
                    console.error('Error parsing event:', e);
                }
            };
        }
        
        function handleEvent(event) {
            console.log('Event:', event);
            
            if (event.type === 'function_call_start') {
                // Обновляем активные вызовы
                updateActiveCalls();
            } else if (event.type === 'function_call_end') {
                // Обновляем историю и статистику
                updateActiveCalls();
                updateCallHistory();
                updateStats();
            }
        }
        
        // Обновление статистики
        async function updateStats() {
            try {
                const response = await fetch('/api/function-calls/stats');
                const data = await response.json();
                
                if (data.success) {
                    const stats = data.data;
                    document.getElementById('total-calls').textContent = stats.total_calls;
                    document.getElementById('avg-time').textContent = 
                        (stats.avg_time * 1000).toFixed(0) + 'ms';
                    document.getElementById('active-calls').textContent = stats.active_calls;
                    
                    // Обновляем графики
                    updateCharts(stats);
                }
            } catch (e) {
                console.error('Error updating stats:', e);
            }
        }
        
        // Обновление графиков
        function updateCharts(stats) {
            // Модули
            const moduleLabels = Object.keys(stats.by_module);
            const moduleData = Object.values(stats.by_module);
            
            if (modulesChart) {
                modulesChart.data.labels = moduleLabels;
                modulesChart.data.datasets[0].data = moduleData;
                modulesChart.update();
            }
            
            // Функции
            const funcLabels = Object.keys(stats.by_function).slice(0, 10);
            const funcData = Object.values(stats.by_function).slice(0, 10);
            
            if (functionsChart) {
                functionsChart.data.labels = funcLabels;
                functionsChart.data.datasets[0].data = funcData;
                functionsChart.update();
            }
        }
        
        // Обновление активных вызовов
        async function updateActiveCalls() {
            try {
                const response = await fetch('/api/function-calls/active');
                const data = await response.json();
                
                const container = document.getElementById('active-calls-list');
                
                if (data.data.length === 0) {
                    container.innerHTML = '<p style="color: #999; text-align: center; padding: 20px;">Нет активных вызовов</p>';
                    return;
                }
                
                container.innerHTML = data.data.map(call => `
                    <div class="call-item">
                        <div class="call-header">
                            <span class="status-indicator status-running"></span>
                            ${call.module}->${call.function}()
                        </div>
                        <div class="call-details">
                            Глубина: ${call.depth} | Начало: ${new Date(call.start_time).toLocaleTimeString()}
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Error updating active calls:', e);
            }
        }
        
        // Обновление истории
        async function updateCallHistory() {
            try {
                const response = await fetch('/api/function-calls/history?limit=20');
                const data = await response.json();
                
                const container = document.getElementById('call-history');
                container.innerHTML = data.data.reverse().map(call => {
                    const statusClass = call.status === 'ERROR' ? 'error' : '';
                    const statusIcon = call.status === 'SUCCESS' ? '✅' : '❌';
                    
                    return `
                        <div class="call-item ${statusClass}">
                            <div class="call-header">
                                <span class="status-indicator status-${call.status.toLowerCase()}"></span>
                                ${statusIcon} ${call.module}->${call.function}()
                            </div>
                            <div class="call-details">
                                Время: ${(call.duration * 1000).toFixed(2)}ms | 
                                ${new Date(call.start_time).toLocaleTimeString()}
                                ${call.error ? `<br>❌ ${call.error}` : ''}
                            </div>
                        </div>
                    `;
                }).join('');
            } catch (e) {
                console.error('Error updating history:', e);
            }
        }
        
        // Загрузка графа
        async function loadGraph(funcName) {
            try {
                const response = await fetch(`/api/graph/subgraph/${funcName}?depth=2`);
                const data = await response.json();
                
                if (!data.success) {
                    alert('Функция не найдена в графе');
                    return;
                }
                
                const nodes = new vis.DataSet(data.data.nodes.map(n => ({
                    id: n.id,
                    label: n.id,
                    title: `${n.module}.${n.id}\\nПараметров: ${n.params}`,
                    color: getNodeColor(n.module),
                    size: 20 + n.lines / 20
                })));
                
                const edges = new vis.DataSet(data.data.edges.map(e => ({
                    from: e.from,
                    to: e.to,
                    value: e.weight,
                    title: `Вызовов: ${e.weight}`
                })));
                
                const container = document.getElementById('graph');
                const graphData = { nodes, edges };
                
                const options = {
                    nodes: { shape: 'dot', font: { size: 12 } },
                    edges: { arrows: 'to', smooth: { type: 'cubicBezier' } },
                    physics: { 
                        barnesHut: { gravitationalConstant: -3000, springLength: 150 }
                    }
                };
                
                new vis.Network(container, graphData, options);
            } catch (e) {
                console.error('Error loading graph:', e);
            }
        }
        
        function getNodeColor(module) {
            const colors = {
                '_F_SPECTRE': '#FF6B6B',
                '_F_BUX': '#4ECDC4',
                '_F_DOC': '#45B7D1'
            };
            return colors[module] || '#95E1D3';
        }
        
        // Тестовая симуляция
        async function testSimulation() {
            const calls = [
                { module: '_F_SPECTRE', function: 'Get_NDFL_Nach', duration: 0.2 },
                { module: '_F_BUX', function: 'Get_Rate', duration: 0.1 },
                { module: '_F_DOC', function: 'GetDoc', duration: 0.15 }
            ];
            
            for (const call of calls) {
                await fetch('/api/simulate/call', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(call)
                });
                await new Promise(resolve => setTimeout(resolve, 100));
            }
        }
        
        // Инициализация
        window.onload = () => {
            // Графики
            modulesChart = new Chart(document.getElementById('modules-chart'), {
                type: 'doughnut',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
                    }]
                },
                options: { responsive: true, maintainAspectRatio: true }
            });
            
            functionsChart = new Chart(document.getElementById('functions-chart'), {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Вызовов',
                        data: [],
                        backgroundColor: '#667eea'
                    }]
                },
                options: { 
                    responsive: true, 
                    maintainAspectRatio: true,
                    scales: { y: { beginAtZero: true } }
                }
            });
            
            // Подключаемся к SSE
            connectSSE();
            
            // Начальные обновления
            updateStats();
            updateCallHistory();
            updateActiveCalls();
            
            // Периодические обновления
            setInterval(updateStats, 5000);
            setInterval(updateCallHistory, 3000);
            setInterval(updateActiveCalls, 1000);
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Главная страница"""
    return render_template_string(DASHBOARD_HTML)


# ============================================================================
# Загрузка тестовых данных
# ============================================================================

def load_test_data():
    """Загрузить тестовые данные для демонстрации"""
    print("📊 Загрузка тестовых данных...")
    
    # Добавляем функции в граф
    functions = [
        ('OP_P_NDFL_PRC_BODY', '_F_SPECTRE', [('doc_id', 'int'), ('dir_id', 'int')], 'Расчет НДФЛ', 2236),
        ('Get_NDFL_Nach', '_F_SPECTRE', [('b_date', 'DATE'), ('e_date', 'DATE')], 'Начисленный НДФЛ', 150),
        ('Get_Rate', '_F_BUX', [('date', 'DATE'), ('currency', 'STRING')], 'Курс валюты', 50),
        ('GetDoc', '_F_DOC', [('doc_id', 'INT')], 'Получить документ', 80),
        ('Get_CrossRate', '_F_BUX', [('from', 'STRING'), ('to', 'STRING')], 'Кросс-курс', 40),
    ]
    
    for name, module, params, desc, lines in functions:
        graph_builder.add_function(name, module, params, desc, lines)
    
    # Добавляем вызовы
    calls = [
        ('OP_P_NDFL_PRC_BODY', 'Get_NDFL_Nach', 2192),
        ('OP_P_NDFL_PRC_BODY', 'Get_NDFL_Nach', 2193),
        ('OP_P_NDFL_PRC_BODY', 'GetDoc', 30),
        ('OP_P_NDFL_PRC_BODY', 'Get_Rate', 45),
        ('GetDoc', 'Get_CrossRate', 20),
        ('Get_NDFL_Nach', 'Get_Rate', 50),
    ]
    
    for caller, callee, line in calls:
        graph_builder.add_call(caller, callee, line)
    
    print("✅ Тестовые данные загружены")


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    print("="*70)
    print("🚀 Fansy Analytics Web Server")
    print("="*70)
    
    load_test_data()
    
    print("\n📡 Запуск сервера...")
    print("🌐 Dashboard: http://localhost:5000")
    print("📊 API: http://localhost:5000/api/")
    print("\nНажмите Ctrl+C для остановки\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)