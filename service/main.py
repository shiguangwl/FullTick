from __future__ import annotations

import logging
import os
import threading
from datetime import UTC, datetime

from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS

from config import config, setup_logging
from data_handler import DataHandler
from data_persistence import DataPersistence

# 设置日志
setup_logging(config)
logger = logging.getLogger(__name__)


def get_current_timestamp() -> str:
    """获取当前UTC时间戳."""
    return datetime.now(tz=UTC).isoformat()


app = Flask(
    __name__,
    static_folder="public",
    static_url_path="/",
)

CORS(app)

# 移除SSE相关代码, 改为增量数据接口

# 初始化服务
data_persistence = DataPersistence(config.data_file_path)
data_handler = DataHandler()
data_lock = threading.Lock()

# 只在reloader的子进程中执行初始化, 避免重复执行
# WERKZEUG_RUN_MAIN环境变量只在reloader的子进程中存在
if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    # 启动时加载数据
    loaded_data = data_persistence.load_data()
    if loaded_data:
        data_handler.load_from_dict_list(loaded_data)

    # 启动自动保存
    data_persistence.start_auto_save(
        get_data_callback=lambda: data_handler.get_all_data(),
        interval=config.auto_save_interval,
    )
    logger.info("数据服务初始化完成")


@app.route("/")
def index() -> Response:
    """首页."""
    return send_file("public/index.html")


@app.route("/api", methods=["GET"])
def api_endpoint() -> Response | tuple[Response, int]:
    """API健康检查端点."""
    try:
        data_count = len(data_handler.data_record)

        response_data = {
            "success": True,
            "message": "服务器正常运行",
            "timestamp": get_current_timestamp(),
            "data_count": data_count,
            "server_info": {
                "version": "1.0.0",
                "endpoints": {
                    "all_data": "/allDataList",
                },
            },
        }
        return jsonify(response_data)

    except (ValueError, KeyError, TypeError) as e:
        logger.exception("健康检查时出错")
        error_response = jsonify(
            {
                "success": False,
                "error": str(e),
                "message": "健康检查失败",
                "timestamp": get_current_timestamp(),
            },
        )
        return error_response, 500


@app.route("/allDataList", methods=["GET"])
def get_all_data() -> Response | tuple[Response, int]:
    """获取数据, 支持可选的时间参数进行增量查询."""
    try:
        # 获取可选的since参数
        since_time = request.args.get("since")

        with data_lock:
            # 增量查询或全量查询
            response_data = data_handler.get_data_since(since_time) if since_time else data_handler.get_all_data()
            return jsonify(response_data)

    except (ValueError, KeyError, TypeError) as e:
        logger.exception("获取数据时出错")
        error_response = jsonify(
            {
                "success": False,
                "error": str(e),
                "message": "获取数据时发生错误",
                "timestamp": get_current_timestamp(),
            },
        )
        return error_response, 500


# SSE端点已移除, 改为增量数据接口


@app.route("/data", methods=["POST"])
def submit_data() -> tuple[Response, int] | Response:
    """HTTP接口接收数据."""
    try:
        client_secret = request.headers.get("Secret-Key")
        if client_secret != config.api_secret_key:
            logger.warning("HTTP数据提交被拒绝: 无效的secret_key: %s", client_secret)
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "无效的密钥",
                        "timestamp": get_current_timestamp(),
                    },
                ),
                401,
            )

        if not request.is_json:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "请求必须是JSON格式",
                        "timestamp": get_current_timestamp(),
                    },
                ),
                400,
            )

        data = request.get_json()
        if data is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "无效的JSON数据",
                        "timestamp": get_current_timestamp(),
                    },
                ),
                400,
            )

        if isinstance(data, dict):
            data_list = [data]
        elif isinstance(data, list):
            data_list = data
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "数据格式错误,必须是对象或数组",
                        "timestamp": get_current_timestamp(),
                    },
                ),
                400,
            )

        with data_lock:
            data_handler.accept(data_list)
            # 数据处理后立即保存
            data_persistence.save_data(data_handler.get_all_data())

        return jsonify(
            {
                "success": True,
                "message": "数据已接收",
                "timestamp": get_current_timestamp(),
            },
        )

    except (ValueError, KeyError, TypeError) as e:
        logger.exception("处理HTTP数据时出错")
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"数据处理失败: {e!s}",
                    "timestamp": get_current_timestamp(),
                },
            ),
            500,
        )


if __name__ == "__main__":
    logger.info("启动服务器...")
    logger.info("HTTP API密钥: %s", config.api_secret_key)
    logger.info("API端点:")
    logger.info("  POST /data - 提交数据 (需要secret_key头)")
    logger.info("  GET /allDataList - 获取数据 (支持since参数进行增量查询)")
    logger.info("HTTP服务端点: http://%s:%d", config.host, config.port)

    try:
        app.run(debug=config.debug, host=config.host, port=config.port)
    except KeyboardInterrupt:
        logger.info("收到中断信号, 正在关闭服务器...")
        data_persistence.stop_auto_save_thread()
        logger.info("服务器已关闭")
