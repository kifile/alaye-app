"""
FastAPI 服务器适配器
为 PyWebViewAPI 提供 HTTP 接口
"""

import json
import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# 导入 API 核心业务逻辑
from .api import api_core
from .auto_register import APIRegistry

logger = logging.getLogger(__name__)

# 全局变量存储 FastAPI 应用实例
fastapi_app: FastAPI = None


# WebSocket 连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            f"WebSocket connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                f"WebSocket disconnected. Total connections: {len(self.active_connections)}"
            )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """向所有连接的客户端广播消息"""
        if not self.active_connections:
            return

        disconnected_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected_connections.append(connection)

        # 移除断开的连接
        for connection in disconnected_connections:
            self.disconnect(connection)


# 全局连接管理器
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI server starting up...")
    yield
    logger.info("FastAPI server shutting down...")


def create_fastapi_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例"""
    app = FastAPI(
        title="PyWebview Demo API",
        description="HTTP API for PyWebview Demo Application",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],  # Next.js 开发服务器
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 自动注册 API 路由
    register_routes(app)

    # 注册 WebSocket 端点
    register_websocket_endpoint(app)

    return app


def register_routes(app: FastAPI):
    """
    注册 API 路由
    使用自动注册机制来发现并注册所有标记了 @expose_api 装饰器的方法
    """

    # 自动注册所有暴露的 API 端点
    try:
        APIRegistry.register_fastapi_routes(app, api_core)
        logger.info("自动 API 注册完成")
    except Exception as e:
        logger.error(f"自动 API 注册失败: {e}")


def register_websocket_endpoint(app: FastAPI):
    """注册 WebSocket 端点"""

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                # 保持连接活跃
                data = await websocket.receive_text()
                logger.info(f"Received WebSocket message: {data}")

                # 可以在这里处理来自前端的 WebSocket 消息
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_text(
                            json.dumps({"type": "pong", "event_type": "pong"})
                        )
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {data}")

        except WebSocketDisconnect:
            manager.disconnect(websocket)
            logger.info("WebSocket disconnected normally")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            manager.disconnect(websocket)


def get_fastapi_app() -> FastAPI:
    """获取 FastAPI 应用实例（单例模式）"""
    global fastapi_app
    if fastapi_app is None:
        fastapi_app = create_fastapi_app()
    return fastapi_app


async def run_fastapi_server(host: str = "127.0.0.1", port: int = 8000):
    """运行 FastAPI 服务器"""
    import uvicorn

    app = get_fastapi_app()
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
    )

    server = uvicorn.Server(config)

    logger.info(f"Starting FastAPI server on http://{host}:{port}")
    await server.serve()
