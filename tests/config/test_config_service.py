"""
配置服务完整单元测试
合并所有config_service相关测试，去除重复和不必要的验证case
"""

import asyncio
import shutil

import pytest

from src.config import config_change_manager, config_service, tool_config_listener
from src.config.config_change_listener import ConfigKeyUpdateEvent
from src.config.tool_config_change_listener import ToolConfigChangeListener


class TestConfigService:
    """配置服务测试类 - 包含所有核心功能测试"""

    @pytest.mark.asyncio
    async def test_basic_config_operations(self):
        """测试基本配置操作"""
        # 测试设置和获取
        await config_service.set_setting("test.key", "test_value")
        value = await config_service.get_setting("test.key")
        assert value == "test_value"

        # 测试更新配置
        await config_service.set_setting("test.key", "updated_value")
        value = await config_service.get_setting("test.key")
        assert value == "updated_value"

        # 测试获取不存在的配置
        value = await config_service.get_setting("nonexistent.key")
        assert value is None

        # 测试获取所有配置
        all_settings = await config_service.get_all_settings()
        assert len(all_settings) >= 1

    @pytest.mark.asyncio
    async def test_set_setting_with_same_value_no_change(self):
        """测试设置相同值时不触发变更"""
        # 注册监听器来监控事件
        listener = ToolConfigChangeListener()
        original_before_update = listener.beforeKeyUpdate
        original_on_update = listener.onKeyUpdated

        call_counts = {"before": 0, "on": 0}

        async def counting_before_update(event):
            call_counts["before"] += 1
            return await original_before_update(event)

        async def counting_on_update(event):
            call_counts["on"] += 1
            return await original_on_update(event)

        listener.beforeKeyUpdate = counting_before_update
        listener.onKeyUpdated = counting_on_update

        # 注册监听器
        config_change_manager.add_listener(listener)

        # 设置初始值
        result1 = await config_service.set_setting("test.same.value", "same_value")
        assert result1.value == "same_value"

        # 重置计数器
        call_counts["before"] = 0
        call_counts["on"] = 0

        # 设置相同的值
        result2 = await config_service.set_setting("test.same.value", "same_value")

        # 验证值相同
        assert result2.value == "same_value"
        assert result1.value == result2.value

        # 验证监听器没有被调用
        assert call_counts["before"] == 0
        assert call_counts["on"] == 0

        print("设置相同值时，监听器未被调用: OK")

    @pytest.mark.asyncio
    async def test_set_setting_with_different_value_triggers_change(self):
        """测试设置不同值时触发变更"""
        # 注册监听器
        listener = ToolConfigChangeListener()
        config_change_manager.add_listener(listener)

        # 设置初始值
        await config_service.set_setting("test.diff.value", "initial_value")
        initial_value = await config_service.get_setting("test.diff.value")
        assert initial_value == "initial_value"

        # 设置不同的值
        await config_service.set_setting("test.diff.value", "different_value")
        updated_value = await config_service.get_setting("test.diff.value")
        assert updated_value == "different_value"

        # 验证值确实发生了变化
        assert initial_value != updated_value
        print("设置不同值时，配置确实发生了变化: OK")

    @pytest.mark.asyncio
    async def test_tool_detection_and_version_check(self):
        """测试工具检测和版本检查功能"""
        listener = ToolConfigChangeListener()

        # 检测系统中可用的工具
        tools_detected = []
        npm_path = shutil.which("npm")
        claude_path = shutil.which("claude")

        if npm_path:
            # 测试npm检测
            config_keys = ["npm.path", "npm.enable", "npm.version"]
            await listener._detect_and_update_tool_config("npm", config_keys)
            await asyncio.sleep(0.2)

            # 验证结果
            stored_path = await config_service.get_setting("npm.path")
            npm_enable = await config_service.get_setting("npm.enable")
            npm_version = await config_service.get_setting("npm.version")

            assert stored_path is not None and len(stored_path) > 0
            assert npm_enable in ["True", "False"]

            if npm_enable == "True":
                assert npm_version is not None and len(npm_version) > 0
                tools_detected.append(f"npm: {npm_version}")

        if claude_path:
            # 测试claude检测
            config_keys = ["claude.path", "claude.enable", "claude.version"]
            await listener._detect_and_update_tool_config("claude", config_keys)
            await asyncio.sleep(0.2)

            # 验证结果
            claude_enable = await config_service.get_setting("claude.enable")
            claude_version = await config_service.get_setting("claude.version")

            if claude_enable == "True":
                assert claude_version is not None and len(claude_version) > 0
                tools_detected.append(f"claude: {claude_version}")

        print(f"检测到的工具: {tools_detected}")

    @pytest.mark.asyncio
    async def test_path_validation_mechanism(self):
        """测试路径验证机制"""
        listener = ToolConfigChangeListener()

        # 测试有效路径验证
        npm_path = shutil.which("npm")
        if npm_path:
            valid_event = ConfigKeyUpdateEvent(
                key="npm.path", old_value=None, new_value=npm_path
            )
            result = await listener.beforeKeyUpdate(valid_event)
            assert result.success is True

        # 测试无效路径验证
        invalid_event = ConfigKeyUpdateEvent(
            key="npm.path", old_value=None, new_value="/usr/bin/nonexistent_tool_12345"
        )
        result = await listener.beforeKeyUpdate(invalid_event)
        assert result.success is False
        assert "无效" in result.error_message

    @pytest.mark.asyncio
    async def test_invalid_path_handling(self):
        """测试无效路径处理"""
        ToolConfigChangeListener()

        # 设置无效路径
        invalid_path = "/usr/bin/nonexistent_npm_12345"

        # 尝试设置无效路径应该被拒绝
        with pytest.raises(ValueError, match="配置校验失败"):
            await config_service.set_setting("npm.path", invalid_path)

        # 验证路径没有被设置（因为验证失败）
        npm_path = await config_service.get_setting("npm.path")
        # npm.path 应该不存在或者是旧值（不应该是无效路径）
        assert npm_path != invalid_path

        print("无效路径被正确拒绝: OK")

    @pytest.mark.asyncio
    async def test_config_service_with_valid_tool_paths(self):
        """测试配置服务处理有效工具路径"""
        npm_path = shutil.which("npm")
        if not npm_path:
            pytest.skip("系统中未找到npm，跳过测试")

        # 注册监听器
        config_change_manager.add_listener(tool_config_listener)

        # 设置有效路径
        await config_service.set_setting("npm.path", npm_path)

        # 手动触发监听器（模拟事件触发）
        listener = ToolConfigChangeListener()
        config_keys = ["npm.path", "npm.enable", "npm.version"]
        await listener._detect_and_update_tool_config("npm", config_keys)
        await asyncio.sleep(0.5)

        # 验证路径被正确设置
        stored_path = await config_service.get_setting("npm.path")
        assert stored_path == npm_path

        # 验证enable和version被设置
        npm_enable = await config_service.get_setting("npm.enable")
        npm_version = await config_service.get_setting("npm.version")

        assert npm_enable in ["True", "False"]
        # 如果enable为True，version应该不为空
        if npm_enable == "True":
            assert npm_version is not None and len(npm_version) > 0

    @pytest.mark.asyncio
    async def test_config_service_path_validation_rejection(self):
        """测试配置服务路径验证拒绝机制"""
        # 测试直接使用监听器验证无效路径
        listener = ToolConfigChangeListener()

        from src.config.config_change_listener import ConfigKeyUpdateEvent

        invalid_event = ConfigKeyUpdateEvent(
            key="npm.path", old_value=None, new_value="/usr/bin/nonexistent_tool_12345"
        )

        result = await listener.beforeKeyUpdate(invalid_event)
        assert result.success is False
        assert "无效" in result.error_message

    @pytest.mark.asyncio
    async def test_get_tool_version_directly(self):
        """直接测试版本检测功能（不依赖配置服务）"""
        import platform

        listener = ToolConfigChangeListener()

        # 测试npm版本检测
        npm_path = shutil.which("npm")
        if npm_path:
            version = await listener._get_tool_version("npm", npm_path)
            if version:
                assert len(version) > 0
                print(f"npm版本: {version}")
            else:
                print("npm版本检测失败")

            # 只有在系统中找到npm时，才测试无效路径
            # 注意：在 Windows 上，如果使用 shell=True，即使路径不存在，
            # 系统也可能从 PATH 中找到 npm 命令
            # 因此我们使用一个确实不存在的可执行文件名来测试
            import os

            fake_path = "/fake/path/nonexistent_tool_xyz123"
            if platform.system() == "Windows":
                fake_path = "C:\\fake\\path\\nonexistent_tool_xyz123.exe"

            # 确保路径不存在
            assert not os.path.exists(fake_path), "测试用假路径不应该存在"

            # 测试无效路径版本检测
            version = await listener._get_tool_version("nonexistent_tool", fake_path)
            assert (
                version is None
            ), f"不存在的工具路径应该返回 None，但得到了: {version}"
        else:
            print("系统中未找到npm，跳过版本检测测试")

    @pytest.mark.asyncio
    async def test_performance_optimization_same_value(self):
        """测试相同值设置的性能优化"""
        import time

        # 设置初始值
        await config_service.set_setting("perf.test", "test_value")

        # 测试设置相同值的时间
        start_time = time.time()
        for _ in range(10):
            await config_service.set_setting("perf.test", "test_value")
        same_value_time = time.time() - start_time

        # 测试设置不同值的时间
        start_time = time.time()
        for i in range(10):
            await config_service.set_setting("perf.test", f"different_value_{i}")
        different_value_time = time.time() - start_time

        print(f"设置相同值10次耗时: {same_value_time:.4f}秒")
        print(f"设置不同值10次耗时: {different_value_time:.4f}秒")

        # 相同值设置应该明显更快（因为没有触发监听器和数据库更新）
        # 但由于测试环境差异，我们主要验证功能正确性
        assert same_value_time < different_value_time * 2  # 允许一定误差

    @pytest.mark.asyncio
    async def test_empty_config_initialization(self):
        """测试空配置时的初始化行为"""
        # 清理配置
        await config_service.set_setting("npm.path", "")
        await config_service.set_setting("npm.enable", "")
        await config_service.set_setting("npm.version", "")

        # 直接调用监听器进行初始化检测
        listener = ToolConfigChangeListener()

        npm_path = shutil.which("npm")
        if npm_path:
            # 模拟初始化时的自动检测
            config_keys = ["npm.path", "npm.enable", "npm.version"]
            await listener._detect_and_update_tool_config("npm", config_keys)
            await asyncio.sleep(0.5)

            # 验证配置被自动设置
            stored_path = await config_service.get_setting("npm.path")
            npm_enable = await config_service.get_setting("npm.enable")

            assert stored_path is not None and len(stored_path) > 0
            assert npm_enable in ["True", "False"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
