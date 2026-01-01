"""
PyWebview 适配器
为 PyWebview API 核心业务逻辑提供 JavaScript 桥接器支持
"""

import os
from typing import Any, Callable, Dict, TypeVar

import webview

# 导入 API 核心业务逻辑
from .api import api_core

# 导入特殊 API 的模型（需要手动处理的）
from .api_models import (
    ApiResponse,
    ShowFileDialogData,
    ShowFileDialogRequest,
)

# 导入异步执行器和装饰器
from .async_executor import api_async

# 导入自动注册机制
from .auto_register import apply_auto_registration

# 导入事件总线模块
from .webview_event_bus import get_event_bus

F = TypeVar("F", bound=Callable[..., Dict[str, Any]])


class PyWebViewAPI:
    """PyWebview API 接口类"""

    def __init__(self):
        """初始化API实例"""
        self._event_bus = get_event_bus()  # 私有属性，避免被JavaScript桥接器访问
        self._window = None  # 存储window实例

        # 应用自动注册，添加所有标记了 @expose_api 的方法
        apply_auto_registration(self.__class__, api_core)

    def set_window(self, window):
        """设置window实例"""
        self._window = window

    @api_async(ShowFileDialogRequest)
    async def show_file_dialog(
        self, input_data: ShowFileDialogRequest
    ) -> ApiResponse[ShowFileDialogData]:
        """
        显示原生文件选择对话框

        Args:
            input_data: 文件选择对话框选项
                - title: 对话框标题
                - default_path: 默认路径
                - filters: 文件过滤器列表
                - multiple: 是否允许多选

        Returns:
            文件选择结果
        """
        # 检查window实例是否可用
        if not self._window:
            return ApiResponse.error_response(1, "Window实例未初始化")

        # 转换过滤器格式为 webview 需要的格式
        file_types = ()
        if input_data.filters:
            for filter_item in input_data.filters:
                if filter_item.extensions:
                    # 处理 "*" 通配符情况
                    if "*" in filter_item.extensions:
                        # 如果包含 "*"，使用 "All Files (*.*)"
                        file_types += ("All files (*.*)",)
                    else:
                        # 正常的扩展名列表
                        extensions = [
                            ext.lstrip(".").strip()
                            for ext in filter_item.extensions
                            if ext and ext != "*"
                        ]
                        if extensions:
                            # PyWebView 使用分号分隔扩展名
                            file_types += (
                                f"{filter_item.name} (*.{';*.'.join(extensions)})",
                            )

        # 显示文件选择对话框
        file_paths = self._window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=input_data.multiple,
            file_types=file_types if file_types else (),
            directory=(
                input_data.default_path
                if input_data.default_path and os.path.isabs(input_data.default_path)
                else ""
            ),
        )

        if file_paths and len(file_paths) > 0:
            # 处理多个文件路径
            processed_paths = []
            for file_path in file_paths:
                # 确保返回的是绝对路径
                if not os.path.isabs(file_path):
                    file_path = os.path.abspath(file_path)

                # 标准化路径（处理路径分隔符等）
                file_path = os.path.normpath(file_path)
                processed_paths.append(file_path)

            # 创建响应数据
            data = ShowFileDialogData(
                file_path=(
                    processed_paths[0]
                    if not input_data.multiple and processed_paths
                    else None
                ),
                file_paths=processed_paths,
                message=f"已选择 {len(processed_paths)} 个文件",
            )

            return ApiResponse.success_response(data)
        else:
            # 用户取消选择
            data = ShowFileDialogData(file_paths=[], message="用户取消了文件选择")
            return ApiResponse.success_response(data)


# 创建全局 PyWebView API 实例
webview_api = PyWebViewAPI()
