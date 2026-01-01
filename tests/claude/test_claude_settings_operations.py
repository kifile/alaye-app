"""
Claude Settings Operations 模块的单元测试
测试 Settings 配置的扫描、更新、作用域切换等功能
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.claude.claude_settings_operations import ClaudeSettingsOperations
from src.claude.models import ClaudeSettingsInfoDTO, ConfigScope


class TestClaudeSettingsOperations:
    """测试 ClaudeSettingsOperations 类"""

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
    def settings_ops(self, temp_project_dir, temp_user_home):
        """创建 ClaudeSettingsOperations 实例"""
        return ClaudeSettingsOperations(temp_project_dir, temp_user_home)

    # ========== 测试 scan_settings ==========

    def test_scan_settings_empty_configs(self, settings_ops):
        """测试扫描空的 Settings 配置"""
        result = settings_ops.scan_settings()

        assert isinstance(result, ClaudeSettingsInfoDTO)
        assert result.settings == {}
        assert result.env == []

    def test_scan_settings_single_scope(self, settings_ops, temp_project_dir):
        """测试扫描单个作用域的配置"""
        settings_file = temp_project_dir / ".claude" / "settings.json"
        test_data = {
            "model": "claude-3-5-sonnet-20241022",
            "env": {"HTTP_PROXY": "http://proxy.com"},
        }

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = settings_ops.scan_settings(ConfigScope.project)

        assert "model" in result.settings
        assert result.settings["model"][0] == "claude-3-5-sonnet-20241022"
        assert result.settings["model"][1] == ConfigScope.project

        assert len(result.env) == 1
        assert result.env[0][0] == "HTTP_PROXY"
        assert result.env[0][1] == "http://proxy.com"
        assert result.env[0][2] == ConfigScope.project

    def test_scan_settings_nested_values(self, settings_ops, temp_project_dir):
        """测试扫描嵌套的配置值"""
        settings_file = temp_project_dir / ".claude" / "settings.json"
        test_data = {
            "permissions": {"allow": ["*"], "ask": ["~/Downloads"]},
            "sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True},
        }

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = settings_ops.scan_settings(ConfigScope.project)

        # 验证嵌套值被展平
        assert "permissions.allow" in result.settings
        assert result.settings["permissions.allow"][0] == ["*"]
        assert "sandbox.enabled" in result.settings
        assert result.settings["sandbox.enabled"][0] is True

    def test_scan_settings_merge_all_scopes(
        self, settings_ops, temp_user_home, temp_project_dir
    ):
        """测试合并所有作用域的配置（local > project > user）"""
        # User 配置
        user_settings = temp_user_home / ".claude" / "settings.json"
        user_data = {
            "model": "claude-3-opus",
            "env": {"USER_VAR": "user_value"},
        }
        with open(user_settings, "w", encoding="utf-8") as f:
            json.dump(user_data, f)

        # Project 配置
        project_settings = temp_project_dir / ".claude" / "settings.json"
        project_data = {
            "model": "claude-3-5-sonnet",
            "env": {"PROJECT_VAR": "project_value"},
        }
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(project_data, f)

        # Local 配置（最高优先级）
        local_settings = temp_project_dir / ".claude" / "settings.local.json"
        local_data = {
            "model": "claude-3-5-sonnet-20241022",
            "env": {"LOCAL_VAR": "local_value"},
        }
        with open(local_settings, "w", encoding="utf-8") as f:
            json.dump(local_data, f)

        # 不指定 scope，合并所有
        result = settings_ops.scan_settings()

        # model 应该使用 local 的值（最高优先级）
        assert result.settings["model"][0] == "claude-3-5-sonnet-20241022"
        assert result.settings["model"][1] == ConfigScope.local

        # env 变量应该包含所有作用域的
        env_dict = {env[0]: env for env in result.env}
        assert "USER_VAR" in env_dict
        assert env_dict["USER_VAR"][2] == ConfigScope.user
        assert "PROJECT_VAR" in env_dict
        assert env_dict["PROJECT_VAR"][2] == ConfigScope.project
        assert "LOCAL_VAR" in env_dict
        assert env_dict["LOCAL_VAR"][2] == ConfigScope.local

    def test_scan_settings_with_enum_values(self, settings_ops, temp_project_dir):
        """测试扫描包含枚举值的配置"""
        settings_file = temp_project_dir / ".claude" / "settings.json"
        test_data = {"permissions": {"defaultMode": "acceptEdits"}}

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = settings_ops.scan_settings(ConfigScope.project)

        # 枚举值应该被转换为字符串
        assert "permissions.defaultMode" in result.settings
        assert result.settings["permissions.defaultMode"][0] == "acceptEdits"

    # ========== 测试 update_settings_values ==========

    def test_update_settings_values_string_type(self, settings_ops, temp_project_dir):
        """测试更新字符串类型的配置"""
        settings_ops.update_settings_values(
            ConfigScope.project, "model", "claude-3-5-sonnet-20241022", "string"
        )

        settings_file = temp_project_dir / ".claude" / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["model"] == "claude-3-5-sonnet-20241022"

    def test_update_settings_values_boolean_type(self, settings_ops, temp_project_dir):
        """测试更新布尔类型的配置"""
        settings_ops.update_settings_values(
            ConfigScope.project, "sandbox.enabled", "true", "boolean"
        )

        settings_file = temp_project_dir / ".claude" / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["sandbox"]["enabled"] is True

    def test_update_settings_values_integer_type(self, settings_ops, temp_project_dir):
        """测试更新整数类型的配置"""
        settings_ops.update_settings_values(
            ConfigScope.project, "network.httpProxyPort", "8080", "integer"
        )

        settings_file = temp_project_dir / ".claude" / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["network"]["httpProxyPort"] == 8080

    def test_update_settings_values_array_type(self, settings_ops, temp_project_dir):
        """测试更新数组类型的配置"""
        settings_ops.update_settings_values(
            ConfigScope.project, "permissions.allow", '["*"]', "array"
        )

        settings_file = temp_project_dir / ".claude" / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["permissions"]["allow"] == ["*"]

    def test_update_settings_values_array_comma_separated(
        self, settings_ops, temp_project_dir
    ):
        """测试更新数组类型（逗号分隔）"""
        settings_ops.update_settings_values(
            ConfigScope.project, "permissions.allow", "*,~/.ssh", "array"
        )

        settings_file = temp_project_dir / ".claude" / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["permissions"]["allow"] == ["*", "~/.ssh"]

    def test_update_settings_values_object_type(self, settings_ops, temp_project_dir):
        """测试更新对象类型的配置"""
        settings_ops.update_settings_values(
            ConfigScope.project, "network", '{"allowUnixSockets": ["/tmp/*"]}', "object"
        )

        settings_file = temp_project_dir / ".claude" / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["network"]["allowUnixSockets"] == ["/tmp/*"]

    def test_update_settings_values_env_variable(self, settings_ops, temp_project_dir):
        """测试更新环境变量"""
        settings_ops.update_settings_values(
            ConfigScope.project, "env.HTTP_PROXY", "http://proxy.example.com", "string"
        )

        settings_file = temp_project_dir / ".claude" / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["env"]["HTTP_PROXY"] == "http://proxy.example.com"

    def test_update_settings_values_delete_with_empty_string(
        self, settings_ops, temp_project_dir
    ):
        """测试使用空字符串删除配置"""
        # 先创建配置
        settings_file = temp_project_dir / ".claude" / "settings.json"
        test_data = {"model": "claude-3-opus"}
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        # 删除配置
        settings_ops.update_settings_values(ConfigScope.project, "model", "", "string")

        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "model" not in config

    def test_update_settings_values_invalid_boolean_raises_error(self, settings_ops):
        """测试更新无效的布尔值抛出异常"""
        with pytest.raises(ValueError, match="无法将.*转换为布尔类型"):
            settings_ops.update_settings_values(
                ConfigScope.project, "sandbox.enabled", "invalid", "boolean"
            )

    def test_update_settings_values_invalid_integer_raises_error(self, settings_ops):
        """测试更新无效的整数抛出异常"""
        with pytest.raises(ValueError, match="无法将.*转换为整数类型"):
            settings_ops.update_settings_values(
                ConfigScope.project, "test.value", "not_a_number", "integer"
            )

    def test_update_settings_values_to_user_scope(self, settings_ops, temp_user_home):
        """测试更新 user scope 的配置"""
        settings_ops.update_settings_values(
            ConfigScope.user, "model", "claude-3-opus", "string"
        )

        settings_file = temp_user_home / ".claude" / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["model"] == "claude-3-opus"

    def test_update_settings_values_to_local_scope(
        self, settings_ops, temp_project_dir
    ):
        """测试更新 local scope 的配置"""
        settings_ops.update_settings_values(
            ConfigScope.local, "model", "claude-3-5-sonnet", "string"
        )

        settings_file = temp_project_dir / ".claude" / "settings.local.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["model"] == "claude-3-5-sonnet"

    # ========== 测试 update_settings_scope ==========

    def test_update_settings_scope_project_to_local(
        self, settings_ops, temp_project_dir
    ):
        """测试将配置从 project scope 移动到 local scope"""
        # 在 project scope 创建配置
        project_settings = temp_project_dir / ".claude" / "settings.json"
        test_data = {"model": "claude-3-5-sonnet"}
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        # 移动到 local scope
        settings_ops.update_settings_scope(
            ConfigScope.project, ConfigScope.local, "model"
        )

        # 验证：project 中不存在，local 中存在
        with open(project_settings, "r", encoding="utf-8") as f:
            project_config = json.load(f)
        assert "model" not in project_config

        local_settings = temp_project_dir / ".claude" / "settings.local.json"
        with open(local_settings, "r", encoding="utf-8") as f:
            local_config = json.load(f)
        assert local_config["model"] == "claude-3-5-sonnet"

    def test_update_settings_scope_user_to_project(
        self, settings_ops, temp_user_home, temp_project_dir
    ):
        """测试将配置从 user scope 移动到 project scope"""
        # 在 user scope 创建配置
        user_settings = temp_user_home / ".claude" / "settings.json"
        test_data = {"model": "claude-3-opus"}
        with open(user_settings, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        # 移动到 project scope
        settings_ops.update_settings_scope(
            ConfigScope.user, ConfigScope.project, "model"
        )

        # 验证：user 中不存在，project 中存在
        with open(user_settings, "r", encoding="utf-8") as f:
            user_config = json.load(f)
        assert "model" not in user_config

        project_settings = temp_project_dir / ".claude" / "settings.json"
        with open(project_settings, "r", encoding="utf-8") as f:
            project_config = json.load(f)
        assert project_config["model"] == "claude-3-opus"

    def test_update_settings_scope_nested_key(self, settings_ops, temp_project_dir):
        """测试移动嵌套配置的作用域"""
        # 创建嵌套配置
        project_settings = temp_project_dir / ".claude" / "settings.json"
        test_data = {"sandbox": {"enabled": True}}
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        # 移动嵌套配置
        settings_ops.update_settings_scope(
            ConfigScope.project, ConfigScope.local, "sandbox.enabled"
        )

        # 验证
        with open(project_settings, "r", encoding="utf-8") as f:
            project_config = json.load(f)
        assert "sandbox" not in project_config or "enabled" not in project_config.get(
            "sandbox", {}
        )

        local_settings = temp_project_dir / ".claude" / "settings.local.json"
        with open(local_settings, "r", encoding="utf-8") as f:
            local_config = json.load(f)
        assert local_config["sandbox"]["enabled"] is True

    def test_update_settings_scope_env_variable(self, settings_ops, temp_project_dir):
        """测试移动环境变量的作用域"""
        # 创建环境变量
        project_settings = temp_project_dir / ".claude" / "settings.json"
        test_data = {"env": {"HTTP_PROXY": "http://proxy.com"}}
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        # 移动环境变量
        settings_ops.update_settings_scope(
            ConfigScope.project, ConfigScope.local, "env.HTTP_PROXY"
        )

        # 验证
        with open(project_settings, "r", encoding="utf-8") as f:
            project_config = json.load(f)
        assert "HTTP_PROXY" not in project_config.get("env", {})

        local_settings = temp_project_dir / ".claude" / "settings.local.json"
        with open(local_settings, "r", encoding="utf-8") as f:
            local_config = json.load(f)
        assert local_config["env"]["HTTP_PROXY"] == "http://proxy.com"

    def test_update_settings_scope_nonexistent_key_no_change(
        self, settings_ops, temp_project_dir
    ):
        """测试移动不存在的键不产生任何变化"""
        # 创建配置文件
        project_settings = temp_project_dir / ".claude" / "settings.json"
        test_data = {"model": "claude-3"}
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        original_stat = project_settings.stat()

        # 尝试移动不存在的键
        settings_ops.update_settings_scope(
            ConfigScope.project, ConfigScope.local, "nonexistent.key"
        )

        # 验证文件未被修改
        new_stat = project_settings.stat()
        assert original_stat.st_mtime == new_stat.st_mtime

    def test_update_settings_scope_same_scope_no_change(
        self, settings_ops, temp_project_dir
    ):
        """测试移动到相同作用域不产生任何变化"""
        project_settings = temp_project_dir / ".claude" / "settings.json"
        test_data = {"model": "claude-3"}
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        original_stat = project_settings.stat()

        # 移动到相同作用域
        settings_ops.update_settings_scope(
            ConfigScope.project, ConfigScope.project, "model"
        )

        # 验证文件未被修改
        new_stat = project_settings.stat()
        assert original_stat.st_mtime == new_stat.st_mtime

    # ========== 测试集成场景 ==========

    def test_full_settings_workflow(self, settings_ops):
        """测试完整的 Settings 工作流"""
        # Create: 添加配置
        settings_ops.update_settings_values(
            ConfigScope.project, "model", "claude-3-5-sonnet", "string"
        )

        result = settings_ops.scan_settings(ConfigScope.project)
        assert "model" in result.settings
        assert result.settings["model"][0] == "claude-3-5-sonnet"

        # Update: 更新配置
        settings_ops.update_settings_values(
            ConfigScope.project, "model", "claude-3-opus", "string"
        )

        result = settings_ops.scan_settings(ConfigScope.project)
        assert result.settings["model"][0] == "claude-3-opus"

        # Move Scope: 移动到 user
        settings_ops.update_settings_scope(
            ConfigScope.project, ConfigScope.user, "model"
        )

        result = settings_ops.scan_settings(ConfigScope.project)
        assert "model" not in result.settings

        result = settings_ops.scan_settings(ConfigScope.user)
        assert result.settings["model"][0] == "claude-3-opus"

        # Delete: 删除配置
        settings_ops.update_settings_values(ConfigScope.user, "model", "", "string")

        result = settings_ops.scan_settings(ConfigScope.user)
        assert "model" not in result.settings

    def test_complex_nested_configuration(self, settings_ops, temp_project_dir):
        """测试复杂的嵌套配置"""
        # 创建复杂的嵌套配置
        settings_file = temp_project_dir / ".claude" / "settings.json"
        test_data = {
            "permissions": {
                "allow": ["*"],
                "ask": ["~/Downloads", "~/Documents"],
                "deny": ["/etc"],
                "defaultMode": "plan",
                "disableBypassPermissionsMode": "disable",
            },
            "sandbox": {
                "enabled": True,
                "autoAllowBashIfSandboxed": False,
                "network": {"allowLocalBinding": True, "httpProxyPort": 8080},
            },
        }

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = settings_ops.scan_settings(ConfigScope.project)

        # 验证所有嵌套值都被正确展平
        assert result.settings["permissions.allow"][0] == ["*"]
        assert result.settings["permissions.ask"][0] == ["~/Downloads", "~/Documents"]
        assert result.settings["permissions.defaultMode"][0] == "plan"
        assert result.settings["sandbox.enabled"][0] is True
        assert result.settings["sandbox.network.allowLocalBinding"][0] is True
        assert result.settings["sandbox.network.httpProxyPort"][0] == 8080
