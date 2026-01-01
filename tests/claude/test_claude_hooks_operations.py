"""
Claude Hooks Operations 模块的单元测试
测试 Hooks 配置的扫描、添加、删除、更新等功能
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.claude.claude_hooks_operations import ClaudeHooksOperations
from src.claude.models import (
    ConfigScope,
    HookConfig,
    HookEvent,
    HooksInfo,
)


class TestClaudeHooksOperations:
    """测试 ClaudeHooksOperations 类"""

    @pytest.fixture
    def temp_project_dir(self):
        """创建临时项目目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            # 创建 .claude 目录
            (project_path / ".claude").mkdir(parents=True, exist_ok=True)
            yield project_path

    @pytest.fixture
    def temp_user_home(self):
        """创建临时用户主目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_home = Path(tmpdir)
            # 创建 .claude 目录
            (user_home / ".claude").mkdir(parents=True, exist_ok=True)
            yield user_home

    @pytest.fixture
    def hooks_ops(self, temp_project_dir, temp_user_home):
        """创建 ClaudeHooksOperations 实例"""
        return ClaudeHooksOperations(temp_project_dir, temp_user_home)

    # ========== 测试 scan_hooks_info ==========

    def test_scan_hooks_info_empty_configs(self, hooks_ops):
        """测试扫描空的 Hooks 配置"""
        hooks_info = hooks_ops.scan_hooks_info()

        assert isinstance(hooks_info, HooksInfo)
        assert hooks_info.matchers == []
        assert hooks_info.disable_all_hooks.value is None
        assert hooks_info.disable_all_hooks.scope is None

    def test_scan_hooks_info_with_user_hooks(self, temp_user_home, hooks_ops):
        """测试扫描 user Hooks 配置"""
        settings_file = temp_user_home / ".claude" / "settings.json"
        test_data = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "bash.exec",
                        "hooks": [
                            {"type": "command", "command": "echo 'test'"},
                        ],
                    }
                ]
            }
        }

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        hooks_info = hooks_ops.scan_hooks_info()

        assert len(hooks_info.matchers) == 1
        assert hooks_info.matchers[0].scope == ConfigScope.user
        assert hooks_info.matchers[0].event == HookEvent.PreToolUse
        assert hooks_info.matchers[0].matcher == "bash.exec"
        assert hooks_info.matchers[0].hook_config.type == "command"

    def test_scan_hooks_info_with_project_hooks(self, temp_project_dir, hooks_ops):
        """测试扫描 project Hooks 配置"""
        settings_file = temp_project_dir / ".claude" / "settings.json"
        test_data = {
            "hooks": {
                "PostToolUse": [
                    {
                        "hooks": [
                            {"type": "prompt", "prompt": "Review the output"},
                        ]
                    }
                ]
            }
        }

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        hooks_info = hooks_ops.scan_hooks_info()

        assert len(hooks_info.matchers) == 1
        assert hooks_info.matchers[0].scope == ConfigScope.project
        assert hooks_info.matchers[0].event == HookEvent.PostToolUse
        assert hooks_info.matchers[0].matcher is None
        assert hooks_info.matchers[0].hook_config.type == "prompt"

    def test_scan_hooks_info_with_local_hooks(self, temp_project_dir, hooks_ops):
        """测试扫描 local Hooks 配置（最高优先级）"""
        settings_file = temp_project_dir / ".claude" / "settings.local.json"
        test_data = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {"type": "command", "command": "echo 'Started'"},
                        ],
                    }
                ]
            }
        }

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        hooks_info = hooks_ops.scan_hooks_info()

        assert len(hooks_info.matchers) == 1
        assert hooks_info.matchers[0].scope == ConfigScope.local

    def test_scan_hooks_info_priority_override(
        self, temp_user_home, temp_project_dir, hooks_ops
    ):
        """测试 Hooks 配置优先级：local > project > user"""
        # User 配置
        user_settings = temp_user_home / ".claude" / "settings.json"
        user_data = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "test.tool",
                        "hooks": [
                            {"type": "command", "command": "echo 'user'"},
                        ],
                    }
                ]
            }
        }
        with open(user_settings, "w", encoding="utf-8") as f:
            json.dump(user_data, f)

        # Project 配置
        project_settings = temp_project_dir / ".claude" / "settings.json"
        project_data = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "test.tool",
                        "hooks": [
                            {"type": "command", "command": "echo 'project'"},
                        ],
                    }
                ]
            }
        }
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(project_data, f)

        # Local 配置
        local_settings = temp_project_dir / ".claude" / "settings.local.json"
        local_data = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "test.tool",
                        "hooks": [
                            {"type": "command", "command": "echo 'local'"},
                        ],
                    }
                ]
            }
        }
        with open(local_settings, "w", encoding="utf-8") as f:
            json.dump(local_data, f)

        hooks_info = hooks_ops.scan_hooks_info()

        # 应该返回所有三个配置，按优先级排序：local > project > user
        assert len(hooks_info.matchers) == 3
        assert hooks_info.matchers[0].scope == ConfigScope.local
        assert hooks_info.matchers[0].hook_config.command == "echo 'local'"
        assert hooks_info.matchers[1].scope == ConfigScope.project
        assert hooks_info.matchers[1].hook_config.command == "echo 'project'"
        assert hooks_info.matchers[2].scope == ConfigScope.user
        assert hooks_info.matchers[2].hook_config.command == "echo 'user'"

    def test_scan_hooks_info_disable_all_hooks_priority(
        self, temp_user_home, temp_project_dir, hooks_ops
    ):
        """测试 disableAllHooks 优先级：local > project > user"""
        # User 配置
        user_settings = temp_user_home / ".claude" / "settings.json"
        user_data = {"disableAllHooks": False}
        with open(user_settings, "w", encoding="utf-8") as f:
            json.dump(user_data, f)

        # Project 配置
        project_settings = temp_project_dir / ".claude" / "settings.json"
        project_data = {"disableAllHooks": True}
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(project_data, f)

        # Local 配置（最高优先级）
        local_settings = temp_project_dir / ".claude" / "settings.local.json"
        local_data = {"disableAllHooks": False}
        with open(local_settings, "w", encoding="utf-8") as f:
            json.dump(local_data, f)

        hooks_info = hooks_ops.scan_hooks_info()

        # Local 配置应该覆盖其他配置
        assert hooks_info.disable_all_hooks.value is False
        assert hooks_info.disable_all_hooks.scope == ConfigScope.local

    # ========== 测试 add_hook ==========

    def test_add_hook_to_project_scope(self, hooks_ops, temp_project_dir):
        """测试添加 Hook 到 project 作用域"""
        hook = HookConfig(type="command", command="echo 'test'")
        event = HookEvent.PreToolUse

        hooks_ops.add_hook(event, hook, matcher="test.tool", scope=ConfigScope.project)

        # 验证文件已创建
        settings_file = temp_project_dir / ".claude" / "settings.json"
        assert settings_file.exists()

        # 验证内容
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "hooks" in config
        assert "PreToolUse" in config["hooks"]
        assert len(config["hooks"]["PreToolUse"]) == 1
        assert config["hooks"]["PreToolUse"][0]["matcher"] == "test.tool"
        assert len(config["hooks"]["PreToolUse"][0]["hooks"]) == 1
        assert config["hooks"]["PreToolUse"][0]["hooks"][0]["type"] == "command"

    def test_add_hook_without_matcher(self, hooks_ops, temp_project_dir):
        """测试添加不带 matcher 的 Hook"""
        hook = HookConfig(type="prompt", prompt="Review this")
        event = HookEvent.PostToolUse

        hooks_ops.add_hook(event, hook, scope=ConfigScope.project)

        settings_file = temp_project_dir / ".claude" / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # matcher 不应该存在于配置中
        assert "matcher" not in config["hooks"]["PostToolUse"][0]
        assert config["hooks"]["PostToolUse"][0]["hooks"][0]["type"] == "prompt"

    def test_add_hook_to_user_scope(self, hooks_ops, temp_user_home):
        """测试添加 Hook 到 user 作用域"""
        hook = HookConfig(type="command", command="ls -la")
        event = HookEvent.SessionStart

        hooks_ops.add_hook(event, hook, scope=ConfigScope.user)

        settings_file = temp_user_home / ".claude" / "settings.json"
        assert settings_file.exists()

        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "hooks" in config
        assert "SessionStart" in config["hooks"]

    def test_add_hook_to_local_scope(self, hooks_ops, temp_project_dir):
        """测试添加 Hook 到 local 作用域"""
        hook = HookConfig(type="command", command="echo 'local'")
        event = HookEvent.SessionEnd

        hooks_ops.add_hook(event, hook, scope=ConfigScope.local)

        settings_file = temp_project_dir / ".claude" / "settings.local.json"
        assert settings_file.exists()

        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "hooks" in config
        assert "SessionEnd" in config["hooks"]

    def test_add_multiple_hooks_to_same_matcher(self, hooks_ops, temp_project_dir):
        """测试向同一个 matcher 添加多个 hooks"""
        hook1 = HookConfig(type="command", command="echo 'first'")
        hook2 = HookConfig(type="prompt", prompt="Check this")
        event = HookEvent.PreToolUse

        hooks_ops.add_hook(event, hook1, matcher="test.tool", scope=ConfigScope.project)
        hooks_ops.add_hook(event, hook2, matcher="test.tool", scope=ConfigScope.project)

        settings_file = temp_project_dir / ".claude" / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        matcher_config = config["hooks"]["PreToolUse"][0]
        assert len(matcher_config["hooks"]) == 2
        assert matcher_config["hooks"][0]["type"] == "command"
        assert matcher_config["hooks"][1]["type"] == "prompt"

    # ========== 测试 remove_hook ==========

    def test_remove_hook_success(self, hooks_ops, temp_project_dir):
        """测试成功删除 Hook"""
        # 先添加一个 Hook
        hook = HookConfig(type="command", command="echo 'test'")
        event = HookEvent.PreToolUse
        hooks_ops.add_hook(event, hook, matcher="test.tool", scope=ConfigScope.project)

        # 获取 hook_id
        hooks_info = hooks_ops.scan_hooks_info()
        hook_id = hooks_info.matchers[0].id

        # 删除 Hook
        result = hooks_ops.remove_hook(hook_id, scope=ConfigScope.project)
        assert result is True

        # 验证删除
        hooks_info_after = hooks_ops.scan_hooks_info()
        assert len(hooks_info_after.matchers) == 0

    def test_remove_hook_invalid_id(self, hooks_ops):
        """测试删除无效的 Hook ID"""
        result = hooks_ops.remove_hook("$invalid-id", scope=ConfigScope.project)
        assert result is False

    def test_remove_hook_nonexistent_file(self, hooks_ops):
        """测试删除不存在的 Hook（文件不存在）"""
        result = hooks_ops.remove_hook(
            "$command-project-PreToolUse-abc123-def456", scope=ConfigScope.project
        )
        # 应该返回 False 而不是抛出异常
        assert result is False

    def test_remove_hook_with_multiple_hooks_in_matcher(
        self, hooks_ops, temp_project_dir
    ):
        """测试删除 matcher 中的单个 hook"""
        # 添加两个 hooks 到同一个 matcher
        hook1 = HookConfig(type="command", command="echo 'first'")
        hook2 = HookConfig(type="prompt", prompt="Check this")
        event = HookEvent.PreToolUse

        hooks_ops.add_hook(event, hook1, matcher="test.tool", scope=ConfigScope.project)
        hooks_ops.add_hook(event, hook2, matcher="test.tool", scope=ConfigScope.project)

        # 获取第一个 hook 的 ID 并删除
        hooks_info = hooks_ops.scan_hooks_info()
        hook_id = hooks_info.matchers[0].id  # 第一个 hook

        hooks_ops.remove_hook(hook_id, scope=ConfigScope.project)

        # 验证只剩下一个 hook
        hooks_info_after = hooks_ops.scan_hooks_info()
        assert len(hooks_info_after.matchers) == 1
        assert hooks_info_after.matchers[0].hook_config.type == "prompt"

    # ========== 测试 update_hook ==========

    def test_update_hook_success(self, hooks_ops, temp_project_dir):
        """测试成功更新 Hook"""
        # 先添加一个 Hook
        original_hook = HookConfig(type="command", command="echo 'old'")
        event = HookEvent.PreToolUse
        hooks_ops.add_hook(
            event, original_hook, matcher="test.tool", scope=ConfigScope.project
        )

        # 获取 hook_id
        hooks_info = hooks_ops.scan_hooks_info()
        hook_id = hooks_info.matchers[0].id

        # 更新 Hook
        updated_hook = HookConfig(type="command", command="echo 'new'", timeout=30)
        result = hooks_ops.update_hook(hook_id, updated_hook, scope=ConfigScope.project)
        assert result is True

        # 验证更新
        hooks_info_after = hooks_ops.scan_hooks_info()
        assert hooks_info_after.matchers[0].hook_config.command == "echo 'new'"
        assert hooks_info_after.matchers[0].hook_config.timeout == 30

    def test_update_hook_invalid_id(self, hooks_ops):
        """测试更新无效的 Hook ID"""
        hook = HookConfig(type="command", command="echo 'test'")
        result = hooks_ops.update_hook("$invalid-id", hook, scope=ConfigScope.project)
        assert result is False

    def test_update_hook_change_type(self, hooks_ops, temp_project_dir):
        """测试更新 Hook 类型（command -> prompt）"""
        # 添加 command 类型的 hook
        original_hook = HookConfig(type="command", command="echo 'test'")
        event = HookEvent.PostToolUse
        hooks_ops.add_hook(event, original_hook, scope=ConfigScope.project)

        # 获取 hook_id
        hooks_info = hooks_ops.scan_hooks_info()
        hook_id = hooks_info.matchers[0].id

        # 更新为 prompt 类型
        updated_hook = HookConfig(type="prompt", prompt="New prompt")
        hooks_ops.update_hook(hook_id, updated_hook, scope=ConfigScope.project)

        # 验证更新
        hooks_info_after = hooks_ops.scan_hooks_info()
        assert hooks_info_after.matchers[0].hook_config.type == "prompt"
        assert hooks_info_after.matchers[0].hook_config.prompt == "New prompt"

    # ========== 测试 update_disable_all_hooks ==========

    def test_update_disable_all_hooks(self, hooks_ops, temp_project_dir):
        """测试更新 disableAllHooks 配置"""
        hooks_ops.update_disable_all_hooks(True)

        settings_file = temp_project_dir / ".claude" / "settings.local.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config.get("disableAllHooks") is True

    def test_update_disable_all_hooks_to_false(self, hooks_ops, temp_project_dir):
        """测试将 disableAllHooks 设置为 False"""
        hooks_ops.update_disable_all_hooks(False)

        settings_file = temp_project_dir / ".claude" / "settings.local.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config.get("disableAllHooks") is False

    def test_update_disable_all_hooks_overwrites_existing(
        self, hooks_ops, temp_project_dir
    ):
        """测试更新 disableAllHooks 覆盖现有值"""
        # 先设置为 True
        hooks_ops.update_disable_all_hooks(True)

        # 再设置为 False
        hooks_ops.update_disable_all_hooks(False)

        settings_file = temp_project_dir / ".claude" / "settings.local.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config.get("disableAllHooks") is False

    # ========== 测试集成场景 ==========

    def test_full_crud_workflow(self, hooks_ops):
        """测试完整的 CRUD 工作流"""
        # Create: 添加 Hook
        hook = HookConfig(type="command", command="echo 'test'")
        event = HookEvent.PreToolUse
        hooks_ops.add_hook(event, hook, matcher="crud.test", scope=ConfigScope.project)

        hooks_info = hooks_ops.scan_hooks_info()
        assert len(hooks_info.matchers) == 1
        original_hook_id = hooks_info.matchers[0].id

        # Update: 更新 Hook（添加 timeout 而不是改变命令内容，以保持 ID 不变）
        updated_hook = HookConfig(type="command", command="echo 'test'", timeout=30)
        hooks_ops.update_hook(original_hook_id, updated_hook, scope=ConfigScope.project)

        hooks_info = hooks_ops.scan_hooks_info()
        assert hooks_info.matchers[0].hook_config.timeout == 30

        # Delete: 删除 Hook（使用原始 ID）
        hooks_ops.remove_hook(original_hook_id, scope=ConfigScope.project)

        hooks_info = hooks_ops.scan_hooks_info()
        assert len(hooks_info.matchers) == 0

    def test_multiple_events_with_different_hooks(self, hooks_ops, temp_project_dir):
        """测试多个事件类型的 Hooks"""
        # 添加不同事件的 hooks
        hooks_ops.add_hook(
            HookEvent.PreToolUse,
            HookConfig(type="command", command="echo 'before'"),
            scope=ConfigScope.project,
        )
        hooks_ops.add_hook(
            HookEvent.PostToolUse,
            HookConfig(type="command", command="echo 'after'"),
            scope=ConfigScope.project,
        )
        hooks_ops.add_hook(
            HookEvent.SessionStart,
            HookConfig(type="prompt", prompt="Welcome"),
            scope=ConfigScope.project,
        )

        hooks_info = hooks_ops.scan_hooks_info()
        assert len(hooks_info.matchers) == 3

        # 验证不同事件类型
        events = [m.event for m in hooks_info.matchers]
        assert HookEvent.PreToolUse in events
        assert HookEvent.PostToolUse in events
        assert HookEvent.SessionStart in events

    def test_hook_with_timeout(self, hooks_ops, temp_project_dir):
        """测试带超时配置的 Hook"""
        hook = HookConfig(type="command", command="sleep 10", timeout=5)
        event = HookEvent.PreToolUse

        hooks_ops.add_hook(event, hook, scope=ConfigScope.project)

        settings_file = temp_project_dir / ".claude" / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        added_hook = config["hooks"]["PreToolUse"][0]["hooks"][0]
        assert added_hook["timeout"] == 5
