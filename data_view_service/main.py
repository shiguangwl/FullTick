import traceback
from flask import Flask, jsonify, Response, request, send_file
from flask_cors import CORS
import json
import threading
import queue
from datetime import datetime
from collections.abc import Generator
from typing import cast

from data_handler import DataHandler

app = Flask(
    __name__,
    static_folder='public',
    static_url_path='/',
)


_ = CORS(app)

# HTTP API 认证密钥
API_SECRET_KEY = "123456"

# SSE客户端管理
sse_clients: list[queue.Queue[any]] = []
sse_clients_lock = threading.Lock()

def notify_sse_clients(data) -> None:
    """通知所有SSE客户端有新数据"""
    with sse_clients_lock:
        for i, client_queue in enumerate(sse_clients):
            try:
                client_queue.put(data, block=False)
            except queue.Full:
                print(f"SSE客户端 {i+1} 队列已满，跳过")
                pass

# 数据记录
data_handler = DataHandler(notify_sse_clients)
data_lock = threading.Lock()


@app.route('/')
def index():
    """首页"""
    return send_file('public/index.html')

@app.route('/api', methods=['GET'])
def api_endpoint():
    try:
        sse_count = len(sse_clients)
        data_count = len(data_handler.data_record)
        
        response_data = {
            "success": True,
            "message": "服务器正常运行",
            "timestamp": datetime.now().isoformat(),
            "sse_clients_count": sse_count,
            "data_count": data_count,
            "server_info": {
                "version": "1.0.0",
                "endpoints": {
                    "sse": "/events",
                    "all_data": "/allDataList",
                }
            }
        }
        return jsonify(response_data)

    except Exception as e:
        print(f"健康检查时出错: {e}")
        error_response = jsonify({
            "success": False,
            "error": str(e),
            "message": "健康检查失败",
            "timestamp": datetime.now().isoformat()
        })
        return error_response, 500

@app.route('/allDataList', methods=['GET'])
def get_all_data():
    """获取全量数据"""
    try:
        with data_lock:
            response_data = data_handler.get_all_data_dict()
            return jsonify(response_data)

    except Exception as e:
        print(f"获取全量数据时出错: {e}")
        error_response = jsonify({
            "success": False,
            "error": str(e),
            "message": "获取数据时发生错误",
            "timestamp": datetime.now().isoformat()
        })
        return error_response, 500


@app.route('/events')
def sse_stream():
    """SSE事件流端点"""
    def event_stream() -> Generator[str, None, None]:
        client_queue: queue.Queue[any] = queue.Queue(maxsize=100)
        client_id = f"sse_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        with sse_clients_lock:
            sse_clients.append(client_queue)
            print(f"SSE客户端 {client_id} 已连接，当前客户端数: {len(sse_clients)}")

        try:
            yield f"data: {json.dumps({'type': 'connected', 'client_id': client_id, 'timestamp': datetime.now().isoformat()})}\n\n"
            
            with data_lock:
                if data_handler.data_record:
                    initial_data = {'type': 'initial', 'data': data_handler.get_all_data_dict(), 'count': len(data_handler.data_record)}
                    yield f"data: {json.dumps(initial_data)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'initial', 'data': [], 'count': 0})}\n\n"

            while True:
                try:
                    data = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(data)}\n\n"
                except queue.Empty:
                    heartbeat_data = {'type': 'heartbeat', 'timestamp': datetime.now().isoformat(), 'client_id': client_id}
                    yield f"data: {json.dumps(heartbeat_data)}\n\n"
        except GeneratorExit:
            print(f"SSE客户端 {client_id} 断开连接")
        except Exception as e:
            print(f"SSE客户端 {client_id} 发生错误: {e}")
        finally:
            with sse_clients_lock:
                if client_queue in sse_clients:
                    sse_clients.remove(client_queue)
    
    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/data', methods=['POST'])
def submit_data():
    """HTTP接口接收数据"""
    try:
        client_secret = request.headers.get('Secret-Key')
        if client_secret != API_SECRET_KEY:
            print(f"HTTP数据提交被拒绝: 无效的secret_key: {client_secret}")
            return jsonify({
                'success': False,
                'message': '无效的密钥',
                'timestamp': datetime.now().isoformat()
            }), 401

        if not request.is_json:
            return jsonify({
                'success': False,
                'message': '请求必须是JSON格式',
                'timestamp': datetime.now().isoformat()
            }), 400

        data = request.get_json()
        if data is None:
            return jsonify({
                'success': False,
                'message': '无效的JSON数据',
                'timestamp': datetime.now().isoformat()
            }), 400

        with data_lock:
            data_handler.accept(data)

        return jsonify({
            'success': True,
            'message': '数据已接收',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        print(f"处理HTTP数据时出错\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'数据处理失败: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500


if __name__ == "__main__":
    print("启动服务器...")
    print(f"HTTP API密钥: {API_SECRET_KEY}")
    print("API端点:")
    print("  POST /data - 提交数据 (需要secret_key头)")
    print("  GET /allDataList - 获取全量数据")
    print("  GET /events - SSE事件流")
    print("HTTP服务端点: http://localhost:5000")

    app.run(debug=True, host='0.0.0.0', port=5000)
