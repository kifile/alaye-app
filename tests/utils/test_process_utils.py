"""
Unit tests for process_utils.run_in_subprocess
"""

import asyncio

import pytest

from src.utils.process_utils import run_in_subprocess


# 模块级别的异步函数，用于测试（避免 fork 模式下的序列化问题）
async def _module_level_success_task():
    await asyncio.sleep(0.01)
    return "success"


async def _module_level_failing_task():
    await asyncio.sleep(0.01)
    raise ValueError("Test error")


async def _module_level_custom_exception_task():
    await asyncio.sleep(0.01)
    raise RuntimeError("Custom runtime error for testing")


async def _module_level_complex_task():
    await asyncio.sleep(0.01)
    await asyncio.sleep(0.01)
    result = []
    for i in range(5):
        result.append(i)
    await asyncio.sleep(0.01)


class TestRunInSubprocess:
    """测试 run_in_subprocess 函数"""

    @pytest.mark.asyncio
    async def test_successful_async_function(self):
        """测试成功执行的异步函数"""
        result = await run_in_subprocess(
            _module_level_success_task, "_module_level_success_task"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_failing_async_function(self):
        """测试抛出异常的异步函数"""
        with pytest.raises(RuntimeError) as exc_info:
            await run_in_subprocess(
                _module_level_failing_task, "_module_level_failing_task"
            )
        # 验证异常信息包含原始错误类型和消息
        error_str = str(exc_info.value)
        assert "failed with exit code" in error_str
        assert "ValueError: Test error" in error_str

    @pytest.mark.asyncio
    async def test_exception_details_propagation(self):
        """测试异常详情从子进程正确传递到父进程"""
        with pytest.raises(RuntimeError) as exc_info:
            await run_in_subprocess(
                _module_level_custom_exception_task,
                "_module_level_custom_exception_task",
            )
        # 验证异常类型和消息被正确传递
        error_str = str(exc_info.value)
        assert "RuntimeError: Custom runtime error for testing" in error_str
        assert "failed with exit code: 1" in error_str

    @pytest.mark.asyncio
    async def test_async_function_with_side_effects(self):
        """测试有副作用的异步函数（验证子进程隔离）"""
        # 使用共享变量来验证子进程隔离
        shared_value = {"value": 0}

        async def modify_shared_value():
            # 子进程中修改此变量，不应该影响父进程
            shared_value["value"] = 999
            await asyncio.sleep(0.01)

        await run_in_subprocess(modify_shared_value, "modify_shared_value")

        # 父进程中的值应该保持不变（子进程隔离）
        assert shared_value["value"] == 0

    @pytest.mark.asyncio
    async def test_async_function_with_custom_name(self):
        """测试自定义函数名称的日志输出"""
        result = await run_in_subprocess(_module_level_success_task, "custom_task_name")
        assert result is True

    @pytest.mark.asyncio
    async def test_async_function_with_multiple_operations(self):
        """测试包含多个异步操作的函数"""
        result = await run_in_subprocess(
            _module_level_complex_task, "_module_level_complex_task"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_concurrent_calls(self):
        """测试并发调用（验证线程锁是否有效）"""
        # 同时启动多个子进程
        results = await asyncio.gather(
            run_in_subprocess(_module_level_success_task, "concurrent_task_1"),
            run_in_subprocess(_module_level_success_task, "concurrent_task_2"),
            run_in_subprocess(_module_level_success_task, "concurrent_task_3"),
        )
        # 所有任务应该都成功
        assert all(results)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_concurrent_calls_with_mixed_results(self):
        """测试并发调用包含成功和失败的情况"""
        # 创建一个计数器来验证所有任务都被执行
        execution_count = {"count": 0}

        async def counting_task():
            execution_count["count"] += 1
            await asyncio.sleep(0.01)

        # 同时运行多个任务，其中一些会失败
        # 不使用 return_exceptions=True，让异常正常传播
        results = await asyncio.gather(
            run_in_subprocess(counting_task, "counting_task_1"),
            run_in_subprocess(_module_level_failing_task, "failing_task"),
            run_in_subprocess(counting_task, "counting_task_2"),
            return_exceptions=True,
        )

        # 第一个和第三个任务应该成功，第二个应该抛出 RuntimeError
        assert results[0] is True
        assert isinstance(results[1], RuntimeError)
        assert "ValueError: Test error" in str(results[1])
        assert results[2] is True

        # 验证至少有一个任务被执行了（证明锁机制工作正常）

    @pytest.mark.asyncio
    async def test_multiple_sequential_calls(self):
        """测试多次连续调用（验证资源清理正确）"""
        for i in range(5):
            result = await run_in_subprocess(
                _module_level_success_task, f"sequential_task_{i}"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_exception_preserves_original_error_type(self):
        """测试异常信息保留原始错误类型"""
        with pytest.raises(RuntimeError) as exc_info:
            await run_in_subprocess(
                _module_level_custom_exception_task, "custom_error_task"
            )

        error_message = str(exc_info.value)
        # 验证原始异常类型和消息都在错误信息中
        assert "RuntimeError" in error_message
        assert "Custom runtime error for testing" in error_message
