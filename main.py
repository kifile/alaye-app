import logging
import os
import sys

# 必须在所有其他导入之前配置日志，否则其他模块导入时会初始化默认日志处理器
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,  # 强制重新配置，覆盖已有的日志配置
)

import asyncio
import threading
import time

import webview
from dotenv import load_dotenv

from src.api.async_executor import background_thread_async_executor
from src.api.event_bus_listener_adapter import init_event_bus_listener_adapter
from src.api.fastapi_adapter import run_fastapi_server
from src.api.webview_event_bus import get_event_bus, init_event_bus
from src.config import (
    app_config_listener,
    config_change_manager,
    config_service,
    tool_config_listener,
)
from src.database import close_db, init_db
from src.project.project_service import project_service
from src.terminal.terminal_manager_service import get_terminal_manager

load_dotenv()

# 解决 Linux 下 Qt WebEngine 样式渲染问题
if os.getenv("APP_ENV", "").lower() != "browser" and sys.platform.startswith("linux"):
    # 强制使用 Qt 后端
    os.environ["PYWEBVIEW_GUI"] = "qt"

    # 禁用沙盒模式（解决某些 Linux 发行版的白屏问题）
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

    # 启用现代渲染特性和性能优化
    qt_flags = [
        "--enable-features=CssGridLayout,UseSkiaRenderer",
        "--disable-gpu",  # 禁用GPU加速（解决兼容性问题）
        "--disable-software-rasterizer",
        "--enable-precise-memory-info",
        "--disable-dev-shm-usage",  # 解决内存限制问题
        "--no-first-run",
        "--no-default-browser-check",
    ]
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(qt_flags)

    # Qt 平台设置优化
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        os.environ["QT_QPA_PLATFORM"] = "wayland"
    else:
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    # 设置软件渲染（如果硬件兼容有问题）
    os.environ["QT_QPA_PLATFORMTHEME"] = ""

    # 字体和渲染设置
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_SCALE_FACTOR"] = "1"

    # 禁用不必要的Qt功能以提高性能
    os.environ["QT_DISABLE_DEPRECATED_WARNINGS"] = "1"

# 获取主模块日志记录器
logger = logging.getLogger(__name__)


async def initialize_app():
    """初始化应用程序"""
    logger.info("正在初始化应用...")

    # 初始化数据库
    logger.info("初始化数据库...")
    await init_db()
    logger.info("数据库初始化完成")

    # 注册工具配置监听器
    logger.info("注册工具配置监听器...")
    config_change_manager.add_listener(tool_config_listener)

    # 注册应用配置监听器
    logger.info("注册应用配置监听器...")
    config_change_manager.add_listener(app_config_listener)

    # 初始化配置服务
    logger.info("初始化配置服务...")
    await config_service.initialize()
    logger.info("配置服务初始化完成")

    # 扫描所有 Claude 项目
    logger.info("扫描 Claude 项目...")
    try:
        await project_service.scan_and_save_all_projects()
        logger.info("Claude 项目扫描完成")
    except Exception as e:
        logger.warning(f"Claude 项目扫描失败: {e}")

    logger.info("应用初始化完成")


def get_resource_path(relative_path: str) -> str:
    """获取资源文件的绝对路径，支持开发环境和 Nuitka 打包后的环境"""
    return os.path.join(os.path.dirname(__file__), relative_path)


def get_app_url():
    """根据环境判断使用的 URL"""

    # 检查是否设置了环境变量
    env_mode = os.getenv("APP_ENV", "").lower()

    if env_mode == "browser":
        # FastAPI 模式：不在窗口中运行，只需启动 FastAPI 服务器
        logger.info("FastAPI 模式：将在 http://127.0.0.1:8000 启动 HTTP 服务")
        return None
    elif env_mode == "development":
        logger.info("使用开发模式: http://localhost:3000")
        return "http://localhost:3000"
    else:
        # 静态文件模式：使用相对路径让 pywebview 自动启动 HTTP 服务器
        # 相对路径会以 main.py 所在目录为根目录
        static_path = "frontend/out/index.html"

        # 获取绝对路径用于文件存在性检查
        absolute_path = get_resource_path(static_path)

        # 检查文件是否存在
        if not os.path.exists(absolute_path):
            logger.error(f"错误: 静态文件不存在: {absolute_path}")
            logger.error("请先构建前端: cd frontend && npm run build")
            sys.exit(1)

        logger.info(f"使用静态资源模式（通过 HTTP 服务器）: {static_path}")
        return static_path


def setup_terminal_system(window):
    """设置终端系统架构：终端管理器 + 事件监听器"""
    # 初始化事件总线
    init_event_bus(window)

    event_bus = get_event_bus()

    # 初始化终端管理器
    terminal_manager = get_terminal_manager()

    # 初始化事件总线监听器适配器，并连接到事件总线
    event_listener = init_event_bus_listener_adapter(event_bus)

    # 将事件监听器设置到终端管理器中
    terminal_manager.set_event_listener(event_listener)


def start_async_event_loop():
    """在后台线程中启动 asyncio 事件循环"""

    async def run_event_loop():
        """运行事件循环，保持应用生命周期"""
        try:
            # 事件循环一直运行，直到被停止
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Async event loop stopped")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 设置事件循环给异步执行器
    background_thread_async_executor.set_loop(loop)

    # 在事件循环中运行协程
    task = loop.create_task(run_event_loop())

    try:
        loop.run_forever()
    finally:
        task.cancel()
        loop.run_until_complete(asyncio.sleep(0.1))  # 给任务时间取消
        loop.close()


def setup_fastapi_terminal_system():
    """设置 FastAPI 模式的终端系统架构：终端管理器 + 事件总线监听器适配器"""
    # 初始化终端管理器
    terminal_manager = get_terminal_manager()

    # 初始化 FastAPI 事件总线（用于 WebSocket 广播）
    from src.api.fastapi_event_bus import get_fastapi_event_bus

    fastapi_event_bus = get_fastapi_event_bus()

    # 初始化事件总线监听器适配器，并连接到 FastAPI 事件总线
    event_listener = init_event_bus_listener_adapter(fastapi_event_bus)

    # 将事件监听器设置到终端管理器中
    terminal_manager.set_event_listener(event_listener)

    logger.info("FastAPI 模式终端系统已初始化")


async def run_fastapi_mode():
    logger.info("启动 FastAPI 模式...")

    # 初始化应用
    await initialize_app()

    # 设置 FastAPI 模式的终端系统
    setup_fastapi_terminal_system()

    logger.info("启动 FastAPI 服务器...")
    logger.info("服务地址: http://127.0.0.1:8000")
    logger.info("提示: 按 Ctrl+C 退出服务器")
    logger.info("API 文档: http://127.0.0.1:8000/docs")

    try:
        await run_fastapi_server()
    except KeyboardInterrupt:
        logger.warning("收到中断信号，正在关闭服务器...")
    finally:
        # 清理终端管理服务
        logger.info("正在清理终端管理服务...")
        terminal_manager = get_terminal_manager()
        terminal_manager.cleanup()

        # 关闭数据库连接
        await close_db()
        logger.info("服务器已关闭")


def run_pywebview_mode(app_url):
    # 启动后台事件循环
    event_loop_thread = threading.Thread(target=start_async_event_loop, daemon=True)
    event_loop_thread.start()

    # 给事件循环一点时间启动
    time.sleep(0.1)

    # 初始化应用（在事件循环中）
    loop = background_thread_async_executor.get_loop()
    if loop:
        asyncio.run_coroutine_threadsafe(initialize_app(), loop)
        time.sleep(1)  # 等待初始化完成

    # 创建自定义 Bottle 服务器以正确处理 SPA 路由
    import bottle

    # 在 PyWebView 模式下导入 API
    from src.api.webview_adapter import webview_api

    # 设置静态文件根目录为 frontend/out
    static_root = get_resource_path("frontend/out")

    # 创建 Bottle 应用
    app = bottle.Bottle()

    # 配置静态文件路由
    @app.route("/<filepath:path>")
    def serve_static(filepath):
        """处理静态文件请求，支持 SPA 路由回退"""
        # 尝试直接访问文件
        return bottle.static_file(filepath, root=static_root)

    @app.route("/")
    def serve_index():
        """根路径重定向到 index.html"""
        return bottle.static_file("index.html", root=static_root)

    # 创建窗口，使用自定义 Bottle 服务器
    window = webview.create_window(
        "Alaye App",
        app,  # 使用 Bottle 应用而不是文件路径
        width=1200,
        height=800,
        resizable=True,
        min_size=(900, 600),
        js_api=webview_api,
    )

    # 设置 window 实例到 API
    webview_api.set_window(window)

    # 设置完整的终端系统架构
    setup_terminal_system(window)
    logger.info("终端系统已初始化")

    logger.info("启动应用...")
    logger.info(f"窗口标题: Alaye App")
    logger.info(f"使用 HTTP 服务器模式，根目录: {static_root}")
    logger.info("提示: 按 Ctrl+C 或关闭窗口退出应用")

    try:
        # 启动应用
        webview.start()
    except KeyboardInterrupt:
        logger.warning("收到中断信号，正在关闭应用...")
    finally:
        # 清理终端管理服务
        logger.info("正在清理终端管理服务...")
        terminal_manager = get_terminal_manager()
        terminal_manager.cleanup()

        # 关闭数据库连接
        if loop:
            asyncio.run_coroutine_threadsafe(close_db(), loop)

        logger.info("应用已关闭")


def main():
    """主函数"""
    app_url = get_app_url()
    env_mode = os.getenv("APP_ENV", "").lower()

    if env_mode == "browser":
        # FastAPI 模式
        asyncio.run(run_fastapi_mode())
    else:
        # PyWebView 模式
        run_pywebview_mode(app_url)


if __name__ == "__main__":
    main()
