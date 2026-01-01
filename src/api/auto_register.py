"""
API 自动注册机制
通过装饰器和反射机制自动生成 FastAPI 路由和 PyWebView 接口，减少重复代码
"""

from typing import Any, Callable, Dict, List, Type, TypeVar

from fastapi import FastAPI

from .api_models import ApiResponse

T = TypeVar("T")


class APIEndpoint:
    """API 端点信息"""

    def __init__(
        self,
        name: str,
        method: Callable,
        request_model: Type,
        response_model: Type,
        description: str = "",
    ):
        self.name = name
        self.method = method
        self.request_model = request_model
        self.response_model = response_model
        self.description = description


def expose_api(
    request_model: Type, response_model: Type, description: str = ""
) -> Callable:
    """
    API 暴露装饰器，标记需要自动注册的 API 方法

    Args:
        request_model: 请求模型类型
        response_model: 响应模型类型
        description: API 描述

    Returns:
        装饰器函数
    """

    def decorator(method: Callable) -> Callable:
        # 为方法添加 API 元数据
        method._is_api_exposed = True
        method._request_model = request_model
        method._response_model = response_model
        method._api_description = description
        return method

    return decorator


class APIRegistry:
    """API 注册器，用于自动发现和注册 API 端点"""

    @staticmethod
    def discover_endpoints(api_core_instance: Any) -> List[APIEndpoint]:
        """
        发现 API 核心实例中的所有暴露端点

        Args:
            api_core_instance: API 核心实例

        Returns:
            发现的端点列表
        """
        endpoints = []

        # 遍历实例的所有属性
        for name in dir(api_core_instance):
            # 跳过私有属性和特殊方法
            if name.startswith("_"):
                continue

            attr = getattr(api_core_instance, name)

            # 检查是否为可调用方法且被标记为暴露
            if (
                callable(attr)
                and hasattr(attr, "_is_api_exposed")
                and attr._is_api_exposed
            ):
                endpoint = APIEndpoint(
                    name=name,
                    method=attr,
                    request_model=attr._request_model,
                    response_model=attr._response_model,
                    description=attr._api_description,
                )
                endpoints.append(endpoint)

        return endpoints

    @staticmethod
    def register_fastapi_routes(app: FastAPI, api_core_instance: Any) -> None:
        """
        自动注册 FastAPI 路由

        Args:
            app: FastAPI 应用实例
            api_core_instance: API 核心实例
        """
        endpoints = APIRegistry.discover_endpoints(api_core_instance)

        for endpoint in endpoints:
            # 使用工厂函数避免闭包变量捕获问题
            def create_route_factory(ep):
                async def route_func(request: ep.request_model) -> ApiResponse[ep.response_model]:  # type: ignore
                    """动态生成的路由函数"""
                    return await ep.method(request)

                return route_func

            # 创建路由函数
            route_func = create_route_factory(endpoint)

            # 设置路由函数的签名和文档
            route_func.__name__ = endpoint.name
            route_func.__doc__ = endpoint.description or f"{endpoint.name} API"

            # 注册路由
            app.post(f"/api/{endpoint.name}")(route_func)

    @staticmethod
    def generate_webview_methods(api_core_class: Type) -> Dict[str, Callable]:
        """
        为 PyWebView API 生成方法

        Args:
            api_core_class: API 核心类

        Returns:
            方法名字典
        """
        methods = {}

        # 创建一个临时实例来发现端点
        temp_instance = api_core_class()
        endpoints = APIRegistry.discover_endpoints(temp_instance)

        def create_method_factory(endpoint):
            """工厂函数，避免闭包变量捕获问题"""

            def create_wrapper():
                # 导入装饰器
                from .async_executor import api_async

                @api_async(endpoint.request_model)
                async def wrapper(self: Any, input_data: endpoint.request_model) -> ApiResponse[endpoint.response_model]:  # type: ignore
                    """动态生成的包装方法"""
                    return await endpoint.method(input_data)

                # 设置方法的元数据
                wrapper.__name__ = endpoint.name
                wrapper.__doc__ = (
                    endpoint.description or f"动态生成的 {endpoint.name} 方法"
                )

                return wrapper

            return create_wrapper

        for endpoint in endpoints:
            # 使用工厂函数创建方法，避免闭包变量捕获
            wrapper = create_method_factory(endpoint)()
            methods[endpoint.name] = wrapper

        return methods


def apply_auto_registration(webview_api_class: Type, api_core_instance: Any) -> None:
    """
    为 PyWebView API 类应用自动注册

    Args:
        webview_api_class: PyWebView API 类
        api_core_instance: API 核心实例
    """
    methods = APIRegistry.generate_webview_methods(type(api_core_instance))

    # 为每个方法添加到类中
    for name, method in methods.items():
        setattr(webview_api_class, name, method)
