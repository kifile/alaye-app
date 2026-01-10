"""
Claude Plugin Operations 模块的单元测试
测试插件市场和插件的扫描、启用、禁用等功能
注意：插件安装/卸载需要真实的 claude 命令，这些测试会跳过实际执行
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.claude.claude_plugin_operations import ClaudePluginOperations
from src.claude.models import ConfigScope


class TestClaudePluginOperations:
    """测试 ClaudePluginOperations 类"""

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
            # 创建插件目录结构
            (user_home / ".claude" / "plugins").mkdir(parents=True, exist_ok=True)
            yield user_home

    @pytest.fixture
    def plugin_ops(self, temp_project_dir, temp_user_home):
        """创建 ClaudePluginOperations 实例"""
        return ClaudePluginOperations(temp_project_dir, temp_user_home)

    # ========== 测试 scan_marketplaces ==========

    def test_scan_marketplaces_empty(self, plugin_ops):
        """测试扫描空的 marketplace 列表"""
        result = plugin_ops.scan_marketplaces()

        assert result == []

    def test_scan_marketplaces_single(self, plugin_ops, temp_user_home):
        """测试扫描单个 marketplace"""
        known_marketplaces = (
            temp_user_home / ".claude" / "plugins" / "known_marketplaces.json"
        )
        test_data = {
            "anthropics": {
                "source": {
                    "source": "github",
                    "repo": "anthropics/claude-plugins-official",
                },
                "installLocation": "/path/to/anthropics",
                "lastUpdated": "2024-01-01T00:00:00Z",
            }
        }

        with open(known_marketplaces, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = plugin_ops.scan_marketplaces()

        assert len(result) == 1
        assert result[0].name == "anthropics"
        assert result[0].source.source == "github"
        assert result[0].source.repo == "anthropics/claude-plugins-official"

    def test_scan_marketplaces_multiple(self, plugin_ops, temp_user_home):
        """测试扫描多个 marketplaces"""
        known_marketplaces = (
            temp_user_home / ".claude" / "plugins" / "known_marketplaces.json"
        )
        test_data = {
            "anthropics": {
                "source": {
                    "source": "github",
                    "repo": "anthropics/claude-plugins-official",
                },
                "installLocation": "/path/to/anthropics",
            },
            "community": {
                "source": {"source": "url", "url": "https://example.com/plugins"},
                "installLocation": "/path/to/community",
            },
        }

        with open(known_marketplaces, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = plugin_ops.scan_marketplaces()

        assert len(result) == 2
        marketplace_names = {m.name for m in result}
        assert marketplace_names == {"anthropics", "community"}

    def test_scan_marketplaces_ignores_invalid_entries(
        self, plugin_ops, temp_user_home
    ):
        """测试扫描时忽略无效的 marketplace 条目"""
        known_marketplaces = (
            temp_user_home / ".claude" / "plugins" / "known_marketplaces.json"
        )
        test_data = {
            "valid-marketplace": {
                "source": {"source": "github", "repo": "test/repo"},
                "installLocation": "/path/to/test",
            },
            "invalid-entry": "not a dict",
        }

        with open(known_marketplaces, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = plugin_ops.scan_marketplaces()

        # 应该跳过无效条目
        assert len(result) == 1
        assert result[0].name == "valid-marketplace"

    # ========== 测试 scan_plugins ==========

    @pytest.mark.asyncio
    async def test_scan_plugins_no_marketplaces(self, plugin_ops):
        """测试扫描没有 marketplace 时的插件列表"""
        result = await plugin_ops.scan_plugins()

        assert result == []

    @pytest.mark.asyncio
    async def test_scan_plugins_with_marketplace(self, plugin_ops, temp_user_home):
        """测试扫描指定 marketplace 的插件"""
        # 创建 marketplace 配置
        known_marketplaces = (
            temp_user_home / ".claude" / "plugins" / "known_marketplaces.json"
        )
        marketplace_data = {
            "test-marketplace": {
                "source": {"source": "github", "repo": "test/repo"},
                "installLocation": str(temp_user_home / "test-marketplace"),
            }
        }
        with open(known_marketplaces, "w", encoding="utf-8") as f:
            json.dump(marketplace_data, f)

        # 创建 marketplace.json
        install_location = temp_user_home / "test-marketplace"
        install_location.mkdir(parents=True, exist_ok=True)
        marketplace_json = install_location / ".claude-plugin" / "marketplace.json"
        marketplace_json.parent.mkdir(parents=True, exist_ok=True)

        marketplace_data_content = {
            "plugins": [
                {
                    "name": "test-plugin",
                    "description": "A test plugin",
                    "version": "1.0.0",
                    "source": "plugin",
                }
            ]
        }

        with open(marketplace_json, "w", encoding="utf-8") as f:
            json.dump(marketplace_data_content, f)

        # 创建安装计数缓存
        install_counts = (
            temp_user_home / ".claude" / "plugins" / "install-counts-cache.json"
        )
        cache_data = {
            "counts": [
                {"plugin": "test-plugin@test-marketplace", "unique_installs": 100}
            ]
        }
        with open(install_counts, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        result = await plugin_ops.scan_plugins()

        assert len(result) == 1
        assert result[0].config.name == "test-plugin"
        assert result[0].marketplace == "test-marketplace"
        assert result[0].unique_installs == 100
        assert result[0].installed is False  # 未在 enabledPlugins 中

    @pytest.mark.asyncio
    async def test_scan_plugins_with_enabled_status(
        self, plugin_ops, temp_user_home, temp_project_dir
    ):
        """测试扫描插件时检查启用状态"""
        # 创建 marketplace
        known_marketplaces = (
            temp_user_home / ".claude" / "plugins" / "known_marketplaces.json"
        )
        marketplace_data = {
            "test-marketplace": {
                "source": {"source": "github", "repo": "test/repo"},
                "installLocation": str(temp_user_home / "test-marketplace"),
            }
        }
        with open(known_marketplaces, "w", encoding="utf-8") as f:
            json.dump(marketplace_data, f)

        # 创建 marketplace.json
        install_location = temp_user_home / "test-marketplace"
        install_location.mkdir(parents=True, exist_ok=True)
        marketplace_json = install_location / ".claude-plugin" / "marketplace.json"
        marketplace_json.parent.mkdir(parents=True, exist_ok=True)

        marketplace_data_content = {
            "plugins": [
                {
                    "name": "enabled-plugin",
                    "description": "Enabled plugin",
                    "source": "plugin",
                },
                {
                    "name": "disabled-plugin",
                    "description": "Disabled plugin",
                    "source": "plugin",
                },
            ]
        }

        with open(marketplace_json, "w", encoding="utf-8") as f:
            json.dump(marketplace_data_content, f)

        # 创建 installed_plugins.json，标记两个插件都已安装
        installed_plugins_file = (
            temp_user_home / ".claude" / "plugins" / "installed_plugins.json"
        )
        installed_plugins_file.parent.mkdir(parents=True, exist_ok=True)
        installed_data = {
            "plugins": {
                "enabled-plugin@test-marketplace": [
                    {
                        "scope": "project",
                        "projectPath": str(temp_project_dir),
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    }
                ],
                "disabled-plugin@test-marketplace": [
                    {
                        "scope": "project",
                        "projectPath": str(temp_project_dir),
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    }
                ],
            }
        }
        with open(installed_plugins_file, "w", encoding="utf-8") as f:
            json.dump(installed_data, f)

        # 在 settings.json 中启用一个插件，禁用另一个
        settings_file = temp_project_dir / ".claude" / "settings.json"
        settings_data = {
            "enabledPlugins": {
                "enabled-plugin@test-marketplace": True,
                "disabled-plugin@test-marketplace": False,
            }
        }
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)

        result = await plugin_ops.scan_plugins()

        assert len(result) == 2

        # 查找启用的插件
        enabled_plugin = next(p for p in result if p.config.name == "enabled-plugin")
        assert enabled_plugin.enabled is True
        assert enabled_plugin.installed is True

        # 查找禁用的插件
        disabled_plugin = next(p for p in result if p.config.name == "disabled-plugin")
        # 已安装但禁用的插件
        assert disabled_plugin.enabled is False
        assert disabled_plugin.installed is True

    @pytest.mark.asyncio
    async def test_scan_plugins_filters_by_marketplace(
        self, plugin_ops, temp_user_home
    ):
        """测试按 marketplace 名称过滤插件"""
        # 创建两个 marketplaces
        known_marketplaces = (
            temp_user_home / ".claude" / "plugins" / "known_marketplaces.json"
        )
        marketplace_data = {
            "marketplace1": {
                "source": {"source": "github", "repo": "test/repo1"},
                "installLocation": str(temp_user_home / "marketplace1"),
            },
            "marketplace2": {
                "source": {"source": "github", "repo": "test/repo2"},
                "installLocation": str(temp_user_home / "marketplace2"),
            },
        }
        with open(known_marketplaces, "w", encoding="utf-8") as f:
            json.dump(marketplace_data, f)

        # 为 marketplace1 创建插件
        m1_location = temp_user_home / "marketplace1"
        m1_location.mkdir(parents=True, exist_ok=True)
        m1_json = m1_location / ".claude-plugin" / "marketplace.json"
        m1_json.parent.mkdir(parents=True, exist_ok=True)

        with open(m1_json, "w", encoding="utf-8") as f:
            json.dump({"plugins": [{"name": "plugin1", "source": "plugin"}]}, f)

        # 为 marketplace2 创建插件
        m2_location = temp_user_home / "marketplace2"
        m2_location.mkdir(parents=True, exist_ok=True)
        m2_json = m2_location / ".claude-plugin" / "marketplace.json"
        m2_json.parent.mkdir(parents=True, exist_ok=True)

        with open(m2_json, "w", encoding="utf-8") as f:
            json.dump({"plugins": [{"name": "plugin2", "source": "plugin"}]}, f)

        # 只扫描 marketplace1
        result = await plugin_ops.scan_plugins(marketplace_names=["marketplace1"])

        assert len(result) == 1
        assert result[0].config.name == "plugin1"
        assert result[0].marketplace == "marketplace1"

    @pytest.mark.asyncio
    async def test_scan_plugins_sorting_order(self, plugin_ops, temp_user_home):
        """测试插件列表排序（installed > enabled > installs > name）"""
        # 创建 marketplace 和插件
        known_marketplaces = (
            temp_user_home / ".claude" / "plugins" / "known_marketplaces.json"
        )
        marketplace_data = {
            "test-marketplace": {
                "source": {"source": "github", "repo": "test/repo"},
                "installLocation": str(temp_user_home / "test-marketplace"),
            }
        }
        with open(known_marketplaces, "w", encoding="utf-8") as f:
            json.dump(marketplace_data, f)

        install_location = temp_user_home / "test-marketplace"
        install_location.mkdir(parents=True, exist_ok=True)
        marketplace_json = install_location / ".claude-plugin" / "marketplace.json"
        marketplace_json.parent.mkdir(parents=True, exist_ok=True)

        # 创建多个插件，不同的安装数量
        marketplace_data_content = {
            "plugins": [
                {"name": "plugin-a", "source": "plugin"},
                {"name": "plugin-b", "source": "plugin"},
                {"name": "plugin-c", "source": "plugin"},
            ]
        }

        with open(marketplace_json, "w", encoding="utf-8") as f:
            json.dump(marketplace_data_content, f)

        # 创建安装计数（plugin-b 最多，plugin-a 最少）
        install_counts = (
            temp_user_home / ".claude" / "plugins" / "install-counts-cache.json"
        )
        cache_data = {
            "counts": [
                {"plugin": "plugin-a@test-marketplace", "unique_installs": 10},
                {"plugin": "plugin-b@test-marketplace", "unique_installs": 100},
                {"plugin": "plugin-c@test-marketplace", "unique_installs": 50},
            ]
        }
        with open(install_counts, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        result = await plugin_ops.scan_plugins()

        # 应该按安装数量降序排列：b > c > a
        assert result[0].config.name == "plugin-b"
        assert result[1].config.name == "plugin-c"
        assert result[2].config.name == "plugin-a"

    # ========== 测试 enable_plugin / disable_plugin ==========

    def test_enable_plugin(self, plugin_ops, temp_project_dir):
        """测试启用插件"""
        plugin_ops.enable_plugin("test-plugin@test-marketplace", ConfigScope.project)

        settings_file = temp_project_dir / ".claude" / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "enabledPlugins" in config
        assert config["enabledPlugins"]["test-plugin@test-marketplace"] is True

    def test_enable_plugin_user_scope(self, plugin_ops, temp_user_home):
        """测试在 user scope 启用插件"""
        plugin_ops.enable_plugin("test-plugin@test-marketplace", ConfigScope.user)

        settings_file = temp_user_home / ".claude" / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["enabledPlugins"]["test-plugin@test-marketplace"] is True

    def test_enable_plugin_local_scope(self, plugin_ops, temp_project_dir):
        """测试在 local scope 启用插件"""
        plugin_ops.enable_plugin("test-plugin@test-marketplace", ConfigScope.local)

        settings_file = temp_project_dir / ".claude" / "settings.local.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["enabledPlugins"]["test-plugin@test-marketplace"] is True

    def test_disable_plugin(self, plugin_ops, temp_project_dir):
        """测试禁用插件"""
        # 先启用插件
        settings_file = temp_project_dir / ".claude" / "settings.json"
        settings_data = {"enabledPlugins": {"test-plugin@test-marketplace": True}}
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)

        # 禁用插件
        plugin_ops.disable_plugin("test-plugin@test-marketplace", ConfigScope.project)

        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 禁用时设置值为 False
        assert config["enabledPlugins"]["test-plugin@test-marketplace"] is False

    def test_enable_plugin_with_special_chars(self, plugin_ops, temp_project_dir):
        """测试启用包含特殊字符的插件名"""
        plugin_ops.enable_plugin("my.plugin@special-marketplace", ConfigScope.project)

        settings_file = temp_project_dir / ".claude" / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "my.plugin@special-marketplace" in config["enabledPlugins"]

    def test_check_plugin_in_installed_plugins_installed(
        self, plugin_ops, temp_user_home, temp_project_dir
    ):
        """测试检查已安装的插件"""
        # 创建 installed_plugins.json
        installed_plugins_file = (
            temp_user_home / ".claude" / "plugins" / "installed_plugins.json"
        )
        installed_plugins_file.parent.mkdir(parents=True, exist_ok=True)

        installed_data = {
            "plugins": {
                "test-plugin@test-marketplace": [
                    {
                        "scope": "project",
                        "projectPath": str(temp_project_dir),
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }
        with open(installed_plugins_file, "w", encoding="utf-8") as f:
            json.dump(installed_data, f)

        result = plugin_ops._check_plugin_in_installed_plugins(
            "test-plugin@test-marketplace"
        )

        assert result is True

    def test_check_plugin_in_installed_plugins_not_installed(
        self, plugin_ops, temp_user_home
    ):
        """测试检查未安装的插件"""
        # 创建空的 installed_plugins.json
        installed_plugins_file = (
            temp_user_home / ".claude" / "plugins" / "installed_plugins.json"
        )
        installed_plugins_file.parent.mkdir(parents=True, exist_ok=True)
        installed_data = {"plugins": {}}
        with open(installed_plugins_file, "w", encoding="utf-8") as f:
            json.dump(installed_data, f)

        result = plugin_ops._check_plugin_in_installed_plugins(
            "test-plugin@test-marketplace"
        )

        assert result is False

    def test_check_plugin_in_installed_plugins_user_scope(
        self, plugin_ops, temp_user_home
    ):
        """测试检查 user 作用域的插件"""
        # 创建 installed_plugins.json，包含 user 作用域的插件
        installed_plugins_file = (
            temp_user_home / ".claude" / "plugins" / "installed_plugins.json"
        )
        installed_plugins_file.parent.mkdir(parents=True, exist_ok=True)

        installed_data = {
            "plugins": {
                "user-plugin@test-marketplace": [
                    {
                        "scope": "user",
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }
        with open(installed_plugins_file, "w", encoding="utf-8") as f:
            json.dump(installed_data, f)

        result = plugin_ops._check_plugin_in_installed_plugins(
            "user-plugin@test-marketplace"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_uninstall_plugin_not_installed_cleanups_settings(
        self, plugin_ops, temp_user_home, temp_project_dir
    ):
        """测试卸载未安装的插件时只清理 settings"""
        # 在 settings 中启用插件，但不在 installed_plugins.json 中
        settings_file = temp_project_dir / ".claude" / "settings.json"
        settings_data = {"enabledPlugins": {"test-plugin@test-marketplace": True}}
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)

        # 卸载插件
        result = await plugin_ops.uninstall_plugin(
            "test-plugin@test-marketplace", ConfigScope.project
        )

        # 应该成功
        assert result.success is True

        # settings 中的插件应该被删除
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 插件应该从 settings 中删除
        assert "test-plugin@test-marketplace" not in config.get("enabledPlugins", {})

    # ========== 测试 _load_enabled_plugins ==========

    def test_load_enabled_plugins_priority(
        self, plugin_ops, temp_user_home, temp_project_dir
    ):
        """测试加载已启用插件的优先级（local > project > user）"""
        # User 配置
        user_settings = temp_user_home / ".claude" / "settings.json"
        user_data = {"enabledPlugins": {"plugin@marketplace": False}}
        with open(user_settings, "w", encoding="utf-8") as f:
            json.dump(user_data, f)

        # Project 配置
        project_settings = temp_project_dir / ".claude" / "settings.json"
        project_data = {"enabledPlugins": {"plugin@marketplace": True}}
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(project_data, f)

        # Local 配置（最高优先级）
        local_settings = temp_project_dir / ".claude" / "settings.local.json"
        local_data = {"enabledPlugins": {"plugin@marketplace": False}}
        with open(local_settings, "w", encoding="utf-8") as f:
            json.dump(local_data, f)

        enabled_plugins = plugin_ops._load_enabled_plugins()

        # 应该使用 local 的值
        assert enabled_plugins["plugin@marketplace"]["enabled"] is False
        assert (
            enabled_plugins["plugin@marketplace"]["enabled_scope"] == ConfigScope.local
        )

    def test_load_enabled_plugins_with_installed_plugins_json(
        self, plugin_ops, temp_user_home, temp_project_dir
    ):
        """测试从 installed_plugins.json 读取已安装的插件"""
        # 创建 installed_plugins.json
        installed_plugins_file = (
            temp_user_home / ".claude" / "plugins" / "installed_plugins.json"
        )
        installed_plugins_file.parent.mkdir(parents=True, exist_ok=True)

        installed_data = {
            "plugins": {
                "installed-plugin@test-marketplace": [
                    {
                        "scope": "project",
                        "projectPath": str(temp_project_dir),
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    }
                ],
                "user-plugin@test-marketplace": [
                    {
                        "scope": "user",
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    }
                ],
            }
        }
        with open(installed_plugins_file, "w", encoding="utf-8") as f:
            json.dump(installed_data, f)

        # 在 settings.json 中启用一个插件
        project_settings = temp_project_dir / ".claude" / "settings.json"
        project_settings.parent.mkdir(parents=True, exist_ok=True)
        settings_data = {
            "enabledPlugins": {
                "installed-plugin@test-marketplace": True,
                "user-plugin@test-marketplace": True,
            }
        }
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)

        enabled_plugins = plugin_ops._load_enabled_plugins()

        # 验证已安装的插件
        assert "installed-plugin@test-marketplace" in enabled_plugins
        assert enabled_plugins["installed-plugin@test-marketplace"]["installed"] is True
        assert enabled_plugins["installed-plugin@test-marketplace"]["enabled"] is True
        assert (
            enabled_plugins["installed-plugin@test-marketplace"]["scope"]
            == ConfigScope.project
        )
        assert (
            enabled_plugins["installed-plugin@test-marketplace"]["enabled_scope"]
            == ConfigScope.project
        )

        # 验证 user 作用域的插件
        assert "user-plugin@test-marketplace" in enabled_plugins
        assert enabled_plugins["user-plugin@test-marketplace"]["installed"] is True
        assert enabled_plugins["user-plugin@test-marketplace"]["enabled"] is True
        assert (
            enabled_plugins["user-plugin@test-marketplace"]["scope"] == ConfigScope.user
        )
        assert (
            enabled_plugins["user-plugin@test-marketplace"]["enabled_scope"]
            == ConfigScope.project
        )

    def test_load_enabled_plugins_not_in_installed_plugins(
        self, plugin_ops, temp_user_home, temp_project_dir
    ):
        """测试未在 installed_plugins.json 中的插件不被认为是已安装"""
        # 创建空的 installed_plugins.json
        installed_plugins_file = (
            temp_user_home / ".claude" / "plugins" / "installed_plugins.json"
        )
        installed_plugins_file.parent.mkdir(parents=True, exist_ok=True)
        installed_data = {"plugins": {}}
        with open(installed_plugins_file, "w", encoding="utf-8") as f:
            json.dump(installed_data, f)

        # 在 settings.json 中启用一个插件
        project_settings = temp_project_dir / ".claude" / "settings.json"
        project_settings.parent.mkdir(parents=True, exist_ok=True)
        settings_data = {
            "enabledPlugins": {"uninstalled-plugin@test-marketplace": True}
        }
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)

        enabled_plugins = plugin_ops._load_enabled_plugins()

        # 插件应该在列表中，但标记为未安装
        assert "uninstalled-plugin@test-marketplace" in enabled_plugins
        assert (
            enabled_plugins["uninstalled-plugin@test-marketplace"]["installed"] is False
        )
        assert enabled_plugins["uninstalled-plugin@test-marketplace"]["enabled"] is True
        assert enabled_plugins["uninstalled-plugin@test-marketplace"]["scope"] is None
        assert (
            enabled_plugins["uninstalled-plugin@test-marketplace"]["enabled_scope"]
            == ConfigScope.project
        )

    def test_load_enabled_plugins_installed_but_disabled(
        self, plugin_ops, temp_user_home, temp_project_dir
    ):
        """测试已安装但未启用的插件"""
        # 创建 installed_plugins.json
        installed_plugins_file = (
            temp_user_home / ".claude" / "plugins" / "installed_plugins.json"
        )
        installed_plugins_file.parent.mkdir(parents=True, exist_ok=True)

        installed_data = {
            "plugins": {
                "disabled-plugin@test-marketplace": [
                    {
                        "scope": "project",
                        "projectPath": str(temp_project_dir),
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }
        with open(installed_plugins_file, "w", encoding="utf-8") as f:
            json.dump(installed_data, f)

        # 在 settings.json 中禁用该插件（False 值表示明确禁用）
        project_settings = temp_project_dir / ".claude" / "settings.json"
        project_settings.parent.mkdir(parents=True, exist_ok=True)
        settings_data = {"enabledPlugins": {"disabled-plugin@test-marketplace": False}}
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)

        enabled_plugins = plugin_ops._load_enabled_plugins()

        # 插件应该标记为已安装但未启用
        assert "disabled-plugin@test-marketplace" in enabled_plugins
        assert enabled_plugins["disabled-plugin@test-marketplace"]["installed"] is True
        assert enabled_plugins["disabled-plugin@test-marketplace"]["enabled"] is False
        assert (
            enabled_plugins["disabled-plugin@test-marketplace"]["scope"]
            == ConfigScope.project
        )
        # enabled_scope 应该被设置，因为插件在 settings.json 中有记录
        assert (
            enabled_plugins["disabled-plugin@test-marketplace"]["enabled_scope"]
            == ConfigScope.project
        )

    def test_load_enabled_plugins_no_installed_plugins_file(
        self, plugin_ops, temp_project_dir
    ):
        """测试 installed_plugins.json 不存在的情况"""
        # 不创建 installed_plugins.json

        # 在 settings.json 中启用一个插件
        project_settings = temp_project_dir / ".claude" / "settings.json"
        project_settings.parent.mkdir(parents=True, exist_ok=True)
        settings_data = {"enabledPlugins": {"some-plugin@test-marketplace": True}}
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)

        enabled_plugins = plugin_ops._load_enabled_plugins()

        # 插件应该标记为未安装
        assert "some-plugin@test-marketplace" in enabled_plugins
        assert enabled_plugins["some-plugin@test-marketplace"]["installed"] is False
        assert enabled_plugins["some-plugin@test-marketplace"]["enabled"] is True

    def test_load_enabled_plugins_multiple_projects_in_installed_json(
        self, plugin_ops, temp_user_home, temp_project_dir
    ):
        """测试 installed_plugins.json 中有多个项目记录时只匹配当前项目"""
        # 创建 installed_plugins.json
        installed_plugins_file = (
            temp_user_home / ".claude" / "plugins" / "installed_plugins.json"
        )
        installed_plugins_file.parent.mkdir(parents=True, exist_ok=True)

        # 模拟两个不同的项目
        other_project_path = "/some/other/project/path"

        installed_data = {
            "plugins": {
                "multi-project-plugin@test-marketplace": [
                    {
                        "scope": "project",
                        "projectPath": other_project_path,
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    },
                    {
                        "scope": "project",
                        "projectPath": str(temp_project_dir),
                        "lastUpdated": "2024-01-02T00:00:00Z",
                    },
                ]
            }
        }
        with open(installed_plugins_file, "w", encoding="utf-8") as f:
            json.dump(installed_data, f)

        enabled_plugins = plugin_ops._load_enabled_plugins()

        # 应该只匹配当前项目的记录
        assert "multi-project-plugin@test-marketplace" in enabled_plugins
        assert (
            enabled_plugins["multi-project-plugin@test-marketplace"]["installed"]
            is True
        )
        assert (
            enabled_plugins["multi-project-plugin@test-marketplace"]["scope"]
            == ConfigScope.project
        )

    def test_load_enabled_plugins_user_scope_no_project_path(
        self, plugin_ops, temp_user_home, temp_project_dir
    ):
        """测试 user 作用域的插件没有 projectPath"""
        # 创建 installed_plugins.json
        installed_plugins_file = (
            temp_user_home / ".claude" / "plugins" / "installed_plugins.json"
        )
        installed_plugins_file.parent.mkdir(parents=True, exist_ok=True)

        installed_data = {
            "plugins": {
                "user-scope-plugin@test-marketplace": [
                    {
                        "scope": "user",
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }
        with open(installed_plugins_file, "w", encoding="utf-8") as f:
            json.dump(installed_data, f)

        enabled_plugins = plugin_ops._load_enabled_plugins()

        # user 作用域的插件应该被正确识别
        assert "user-scope-plugin@test-marketplace" in enabled_plugins
        assert (
            enabled_plugins["user-scope-plugin@test-marketplace"]["installed"] is True
        )
        assert (
            enabled_plugins["user-scope-plugin@test-marketplace"]["scope"]
            == ConfigScope.user
        )
        assert enabled_plugins["user-scope-plugin@test-marketplace"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_scan_plugins_with_installed_plugins_json(
        self, plugin_ops, temp_user_home, temp_project_dir
    ):
        """测试 scan_plugins 使用 installed_plugins.json 判断安装状态"""
        # 创建 marketplace
        known_marketplaces = (
            temp_user_home / ".claude" / "plugins" / "known_marketplaces.json"
        )
        marketplace_data = {
            "test-marketplace": {
                "source": {"source": "github", "repo": "test/repo"},
                "installLocation": str(temp_user_home / "test-marketplace"),
            }
        }
        with open(known_marketplaces, "w", encoding="utf-8") as f:
            json.dump(marketplace_data, f)

        # 创建 marketplace.json
        install_location = temp_user_home / "test-marketplace"
        install_location.mkdir(parents=True, exist_ok=True)
        marketplace_json = install_location / ".claude-plugin" / "marketplace.json"
        marketplace_json.parent.mkdir(parents=True, exist_ok=True)

        marketplace_data_content = {
            "plugins": [
                {
                    "name": "installed-plugin",
                    "description": "Installed plugin",
                    "source": "installed-plugin",
                },
                {
                    "name": "not-installed-plugin",
                    "description": "Not installed plugin",
                    "source": "not-installed-plugin",
                },
            ]
        }

        with open(marketplace_json, "w", encoding="utf-8") as f:
            json.dump(marketplace_data_content, f)

        # 创建 installed_plugins.json，只标记一个插件为已安装
        installed_plugins_file = (
            temp_user_home / ".claude" / "plugins" / "installed_plugins.json"
        )
        installed_data = {
            "plugins": {
                "installed-plugin@test-marketplace": [
                    {
                        "scope": "project",
                        "projectPath": str(temp_project_dir),
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }
        with open(installed_plugins_file, "w", encoding="utf-8") as f:
            json.dump(installed_data, f)

        # 在 settings.json 中启用两个插件
        project_settings = temp_project_dir / ".claude" / "settings.json"
        project_settings.parent.mkdir(parents=True, exist_ok=True)
        settings_data = {
            "enabledPlugins": {
                "installed-plugin@test-marketplace": True,
                "not-installed-plugin@test-marketplace": True,
            }
        }
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)

        # 扫描所有插件（installed_only=False）
        result = await plugin_ops.scan_plugins()

        # 应该返回两个插件
        assert len(result) == 2

        # 找到已安装的插件
        installed_plugin = next(
            p for p in result if p.config.name == "installed-plugin"
        )
        assert installed_plugin.installed is True
        assert installed_plugin.enabled is True

        # 找到未安装的插件
        not_installed_plugin = next(
            p for p in result if p.config.name == "not-installed-plugin"
        )
        assert not_installed_plugin.installed is False
        # 未安装的插件在 settings.json 中有启用记录，但因为 installed_only=False，所以会返回
        assert not_installed_plugin.enabled is True

    @pytest.mark.asyncio
    async def test_scan_plugins_installed_only_filters_correctly(
        self, plugin_ops, temp_user_home, temp_project_dir
    ):
        """测试 scan_plugins 返回所有插件并按安装状态排序"""
        # 创建 marketplace
        known_marketplaces = (
            temp_user_home / ".claude" / "plugins" / "known_marketplaces.json"
        )
        marketplace_data = {
            "test-marketplace": {
                "source": {"source": "github", "repo": "test/repo"},
                "installLocation": str(temp_user_home / "test-marketplace"),
            }
        }
        with open(known_marketplaces, "w", encoding="utf-8") as f:
            json.dump(marketplace_data, f)

        # 创建 marketplace.json
        install_location = temp_user_home / "test-marketplace"
        install_location.mkdir(parents=True, exist_ok=True)
        marketplace_json = install_location / ".claude-plugin" / "marketplace.json"
        marketplace_json.parent.mkdir(parents=True, exist_ok=True)

        marketplace_data_content = {
            "plugins": [
                {
                    "name": "installed-plugin",
                    "description": "Installed plugin",
                    "source": "installed-plugin",
                },
                {
                    "name": "not-installed-plugin",
                    "description": "Not installed plugin",
                    "source": "not-installed-plugin",
                },
            ]
        }

        with open(marketplace_json, "w", encoding="utf-8") as f:
            json.dump(marketplace_data_content, f)

        # 创建 installed_plugins.json，只标记一个插件为已安装
        installed_plugins_file = (
            temp_user_home / ".claude" / "plugins" / "installed_plugins.json"
        )
        installed_data = {
            "plugins": {
                "installed-plugin@test-marketplace": [
                    {
                        "scope": "project",
                        "projectPath": str(temp_project_dir),
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }
        with open(installed_plugins_file, "w", encoding="utf-8") as f:
            json.dump(installed_data, f)

        # scan_plugins 默认返回所有插件（包括未安装的），但会按 installed 状态排序
        result = await plugin_ops.scan_plugins()

        # 应该返回所有插件，但已安装的插件排在前面
        assert len(result) == 2
        # 第一个应该是已安装的插件
        assert result[0].config.name == "installed-plugin"
        assert result[0].installed is True
        # 第二个应该是未安装的插件
        assert result[1].config.name == "not-installed-plugin"
        assert result[1].installed is False

    @pytest.mark.asyncio
    async def test_scan_plugins_sorting_with_enabled_uninstalled(
        self, plugin_ops, temp_user_home, temp_project_dir
    ):
        """测试未安装但 enabled=True 的插件与已安装插件排在一起"""
        # 创建 marketplace
        known_marketplaces = (
            temp_user_home / ".claude" / "plugins" / "known_marketplaces.json"
        )
        marketplace_data = {
            "test-marketplace": {
                "source": {"source": "github", "repo": "test/repo"},
                "installLocation": str(temp_user_home / "test-marketplace"),
            }
        }
        with open(known_marketplaces, "w", encoding="utf-8") as f:
            json.dump(marketplace_data, f)

        # 创建 marketplace.json
        install_location = temp_user_home / "test-marketplace"
        install_location.mkdir(parents=True, exist_ok=True)
        marketplace_json = install_location / ".claude-plugin" / "marketplace.json"
        marketplace_json.parent.mkdir(parents=True, exist_ok=True)

        # 创建4个插件：
        # 1. installed-enabled: 已安装且已启用
        # 2. installed-disabled: 已安装但未启用
        # 3. uninstalled-enabled: 未安装但已启用（历史插件）
        # 4. uninstalled-disabled: 未安装且未启用
        marketplace_data_content = {
            "plugins": [
                {
                    "name": "installed-disabled",
                    "description": "Installed but disabled",
                    "source": "installed-disabled",
                },
                {
                    "name": "uninstalled-enabled",
                    "description": "Uninstalled but enabled (historical)",
                    "source": "uninstalled-enabled",
                },
                {
                    "name": "installed-enabled",
                    "description": "Installed and enabled",
                    "source": "installed-enabled",
                },
                {
                    "name": "uninstalled-disabled",
                    "description": "Uninstalled and disabled",
                    "source": "uninstalled-disabled",
                },
            ]
        }

        with open(marketplace_json, "w", encoding="utf-8") as f:
            json.dump(marketplace_data_content, f)

        # 创建 installed_plugins.json，只标记两个插件为已安装
        installed_plugins_file = (
            temp_user_home / ".claude" / "plugins" / "installed_plugins.json"
        )
        installed_data = {
            "plugins": {
                "installed-enabled@test-marketplace": [
                    {
                        "scope": "project",
                        "projectPath": str(temp_project_dir),
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    }
                ],
                "installed-disabled@test-marketplace": [
                    {
                        "scope": "project",
                        "projectPath": str(temp_project_dir),
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    }
                ],
            }
        }
        with open(installed_plugins_file, "w", encoding="utf-8") as f:
            json.dump(installed_data, f)

        # 在 settings.json 中配置启用状态
        project_settings = temp_project_dir / ".claude" / "settings.json"
        project_settings.parent.mkdir(parents=True, exist_ok=True)
        settings_data = {
            "enabledPlugins": {
                "installed-enabled@test-marketplace": True,
                "uninstalled-enabled@test-marketplace": True,
                "installed-disabled@test-marketplace": False,
                # uninstalled-disabled 不在 enabledPlugins 中
            }
        }
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)

        # 扫描所有插件
        result = await plugin_ops.scan_plugins()

        # 应该返回所有4个插件
        assert len(result) == 4

        # 验证排序：
        # 1. 已启用的插件排在前面（enabled=True）
        #    - 在已启用的插件中，已安装的排前面
        # 2. 未启用的插件排在后面
        # 排序应该是：
        # 1. installed-enabled (installed=True, enabled=True)
        # 2. uninstalled-enabled (installed=False, enabled=True) <- 历史插件，和已安装的排在一起
        # 3. installed-disabled (installed=True, enabled=False)
        # 4. uninstalled-disabled (installed=False, enabled=False)

        assert result[0].config.name == "installed-enabled"
        assert result[0].installed is True
        assert result[0].enabled is True

        assert result[1].config.name == "uninstalled-enabled"
        assert result[1].installed is False
        assert result[1].enabled is True  # 未安装但已启用，排在已启用的组里

        assert result[2].config.name == "installed-disabled"
        assert result[2].installed is True
        assert result[2].enabled is False

        assert result[3].config.name == "uninstalled-disabled"
        assert result[3].installed is False
        assert result[3].enabled is False

    # ========== 测试 _scan_plugin_tools ==========

    @pytest.mark.asyncio
    async def test_scan_plugin_tools_with_commands(self, plugin_ops, temp_user_home):
        """测试扫描插件的 commands"""
        # 创建 marketplace 安装目录
        marketplace_install = (
            temp_user_home / ".claude" / "plugins" / "test-marketplace"
        )
        marketplace_install.mkdir(parents=True, exist_ok=True)

        # 创建插件目录 (在 marketplace 安装目录下的相对路径)
        plugin_root = marketplace_install / "test-plugin"
        commands_dir = plugin_root / "commands"
        commands_dir.mkdir(parents=True, exist_ok=True)

        # 创建 command 文件
        command_file = commands_dir / "test.md"
        command_content = """---
description: A test command
---

# Test Command

This is a test command.
"""
        command_file.write_text(command_content, encoding="utf-8")

        from src.claude.models import PluginConfig

        plugin_config = PluginConfig(name="test-plugin", source="test-plugin")

        tools = await plugin_ops._scan_plugin_tools(
            plugin_config, "test-marketplace", str(marketplace_install)
        )

        assert tools is not None
        assert tools.commands is not None
        assert len(tools.commands) == 1
        assert tools.commands[0].name == "test"
        assert tools.commands[0].description == "A test command"

    @pytest.mark.asyncio
    async def test_scan_plugin_tools_with_skills(self, plugin_ops, temp_user_home):
        """测试扫描插件的 skills"""
        marketplace_install = (
            temp_user_home / ".claude" / "plugins" / "test-marketplace"
        )
        marketplace_install.mkdir(parents=True, exist_ok=True)

        plugin_root = marketplace_install / "test-plugin"
        skill_dir = plugin_root / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_file = skill_dir / "SKILL.md"
        skill_content = """---
description: A test skill
---

# Test Skill

This is a test skill.
"""
        skill_file.write_text(skill_content, encoding="utf-8")

        from src.claude.models import PluginConfig

        plugin_config = PluginConfig(name="test-plugin", source="test-plugin")

        tools = await plugin_ops._scan_plugin_tools(
            plugin_config, "test-marketplace", str(marketplace_install)
        )

        assert tools is not None
        assert tools.skills is not None
        assert len(tools.skills) == 1
        assert tools.skills[0].name == "test-skill"

    @pytest.mark.asyncio
    async def test_scan_plugin_tools_with_agents(self, plugin_ops, temp_user_home):
        """测试扫描插件的 agents"""
        marketplace_install = (
            temp_user_home / ".claude" / "plugins" / "test-marketplace"
        )
        marketplace_install.mkdir(parents=True, exist_ok=True)

        plugin_root = marketplace_install / "test-plugin"
        agents_dir = plugin_root / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        agent_file = agents_dir / "test-agent.md"
        agent_content = """---
description: A test agent
---

# Test Agent

This is a test agent.
"""
        agent_file.write_text(agent_content, encoding="utf-8")

        from src.claude.models import PluginConfig

        plugin_config = PluginConfig(name="test-plugin", source="test-plugin")

        tools = await plugin_ops._scan_plugin_tools(
            plugin_config, "test-marketplace", str(marketplace_install)
        )

        assert tools is not None
        assert tools.agents is not None
        assert len(tools.agents) == 1
        assert tools.agents[0].name == "test-agent"

    @pytest.mark.asyncio
    async def test_scan_plugin_tools_with_mcp_servers(self, plugin_ops, temp_user_home):
        """测试扫描插件的 MCP servers"""
        marketplace_install = (
            temp_user_home / ".claude" / "plugins" / "test-marketplace"
        )
        marketplace_install.mkdir(parents=True, exist_ok=True)

        plugin_root = marketplace_install / "test-plugin"
        plugin_root.mkdir(parents=True, exist_ok=True)

        mcp_file = plugin_root / ".mcp.json"
        mcp_data = {"test-server": {"command": "node", "args": ["server.js"]}}

        with open(mcp_file, "w", encoding="utf-8") as f:
            json.dump(mcp_data, f)

        from src.claude.models import PluginConfig

        plugin_config = PluginConfig(name="test-plugin", source="test-plugin")

        tools = await plugin_ops._scan_plugin_tools(
            plugin_config, "test-marketplace", str(marketplace_install)
        )

        assert tools is not None
        assert tools.mcp_servers is not None
        assert len(tools.mcp_servers) == 1
        assert tools.mcp_servers[0].name == "test-server"

    @pytest.mark.asyncio
    async def test_scan_plugin_tools_with_hooks(self, plugin_ops, temp_user_home):
        """测试扫描插件的 hooks"""
        marketplace_install = (
            temp_user_home / ".claude" / "plugins" / "test-marketplace"
        )
        marketplace_install.mkdir(parents=True, exist_ok=True)

        plugin_root = marketplace_install / "test-plugin"
        hooks_dir = plugin_root / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)

        hooks_file = hooks_dir / "hooks.json"
        hooks_data = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "bash.exec",
                        "hooks": [{"type": "command", "command": "echo 'test'"}],
                    }
                ]
            }
        }

        with open(hooks_file, "w", encoding="utf-8") as f:
            json.dump(hooks_data, f)

        from src.claude.models import PluginConfig

        plugin_config = PluginConfig(name="test-plugin", source="test-plugin")

        tools = await plugin_ops._scan_plugin_tools(
            plugin_config, "test-marketplace", str(marketplace_install)
        )

        assert tools is not None
        assert tools.hooks is not None
        assert len(tools.hooks) == 1

    @pytest.mark.asyncio
    async def test_scan_plugin_tools_with_lsp_servers_from_lsp_json(
        self, plugin_ops, temp_user_home
    ):
        """测试扫描插件的 LSP servers（从 .lsp.json）"""
        marketplace_install = (
            temp_user_home / ".claude" / "plugins" / "test-marketplace"
        )
        marketplace_install.mkdir(parents=True, exist_ok=True)

        plugin_root = marketplace_install / "test-plugin"
        plugin_root.mkdir(parents=True, exist_ok=True)

        lsp_file = plugin_root / ".lsp.json"
        lsp_data = {
            "gopls": {
                "command": "gopls",
                "args": ["serve"],
                "extensionToLanguage": {".go": "go"},
            },
            "pyright": {
                "command": "pyright",
                "extensionToLanguage": {".py": "python"},
            },
        }

        with open(lsp_file, "w", encoding="utf-8") as f:
            json.dump(lsp_data, f)

        from src.claude.models import PluginConfig

        plugin_config = PluginConfig(name="test-plugin", source="test-plugin")

        tools = await plugin_ops._scan_plugin_tools(
            plugin_config, "test-marketplace", str(marketplace_install)
        )

        assert tools is not None
        assert tools.lsp_servers is not None
        assert len(tools.lsp_servers) == 2
        assert tools.lsp_servers[0].name == "gopls"
        assert tools.lsp_servers[0].lspServer.command == "gopls"
        assert tools.lsp_servers[0].scope.value == "plugin"

    @pytest.mark.asyncio
    async def test_scan_plugin_tools_with_lsp_servers_from_plugin_json(
        self, plugin_ops, temp_user_home
    ):
        """测试扫描插件的 LSP servers（从 plugin.json）"""
        marketplace_install = (
            temp_user_home / ".claude" / "plugins" / "test-marketplace"
        )
        marketplace_install.mkdir(parents=True, exist_ok=True)

        plugin_root = marketplace_install / "test-plugin"
        plugin_root.mkdir(parents=True, exist_ok=True)

        from src.claude.models import PluginConfig

        lsp_servers_config = {
            "typescript": {
                "command": "typescript-language-server",
                "args": ["--stdio"],
                "extensionToLanguage": {".ts": "typescript", ".tsx": "typescript"},
            }
        }

        plugin_config = PluginConfig(
            name="test-plugin", source="test-plugin", lspServers=lsp_servers_config
        )

        tools = await plugin_ops._scan_plugin_tools(
            plugin_config, "test-marketplace", str(marketplace_install)
        )

        assert tools is not None
        assert tools.lsp_servers is not None
        assert len(tools.lsp_servers) == 1
        assert tools.lsp_servers[0].name == "typescript"
        assert tools.lsp_servers[0].file_path == "plugin.json"

    @pytest.mark.asyncio
    async def test_scan_plugin_tools_with_lsp_servers_merge_both_sources(
        self, plugin_ops, temp_user_home
    ):
        """测试合并 .lsp.json 和 plugin.json 中的 LSP servers"""
        marketplace_install = (
            temp_user_home / ".claude" / "plugins" / "test-marketplace"
        )
        marketplace_install.mkdir(parents=True, exist_ok=True)

        plugin_root = marketplace_install / "test-plugin"
        plugin_root.mkdir(parents=True, exist_ok=True)

        # 创建 .lsp.json（基础配置）
        lsp_file = plugin_root / ".lsp.json"
        lsp_file_data = {
            "gopls": {
                "command": "gopls",
                "extensionToLanguage": {".go": "go"},
            },
            "pyright": {
                "command": "pyright",
                "extensionToLanguage": {".py": "python"},
            },
        }

        with open(lsp_file, "w", encoding="utf-8") as f:
            json.dump(lsp_file_data, f)

        # plugin.json 中的配置（会覆盖 gopls，添加 rust-analyzer）
        lsp_servers_config = {
            "gopls": {
                "command": "gopls-custom",  # 覆盖 .lsp.json
                "args": ["serve"],
                "extensionToLanguage": {".go": "go"},
            },
            "rust-analyzer": {
                "command": "rust-analyzer",
                "extensionToLanguage": {".rs": "rust"},
            },
        }

        from src.claude.models import PluginConfig

        plugin_config = PluginConfig(
            name="test-plugin", source="test-plugin", lspServers=lsp_servers_config
        )

        tools = await plugin_ops._scan_plugin_tools(
            plugin_config, "test-marketplace", str(marketplace_install)
        )

        assert tools is not None
        assert tools.lsp_servers is not None
        assert len(tools.lsp_servers) == 3

        # 验证服务器名称
        server_names = {s.name for s in tools.lsp_servers}
        assert server_names == {"gopls", "pyright", "rust-analyzer"}

        # 验证 gopls 被 plugin.json 覆盖
        gopls_server = next(s for s in tools.lsp_servers if s.name == "gopls")
        assert gopls_server.lspServer.command == "gopls-custom"
        assert gopls_server.file_path == "plugin.json"

        # 验证 pyright 来自 .lsp.json
        pyright_server = next(s for s in tools.lsp_servers if s.name == "pyright")
        assert pyright_server.lspServer.command == "pyright"
        assert pyright_server.file_path == str(lsp_file.absolute())

    @pytest.mark.asyncio
    async def test_get_plugin_lsp_servers(
        self, plugin_ops, temp_user_home, temp_project_dir
    ):
        """测试获取已启用插件的 LSP servers"""
        # 创建 marketplace
        known_marketplaces = (
            temp_user_home / ".claude" / "plugins" / "known_marketplaces.json"
        )
        marketplace_data = {
            "test-marketplace": {
                "source": {"source": "github", "repo": "test/repo"},
                "installLocation": str(temp_user_home / "test-marketplace"),
            }
        }
        with open(known_marketplaces, "w", encoding="utf-8") as f:
            json.dump(marketplace_data, f)

        # 创建 marketplace.json
        install_location = temp_user_home / "test-marketplace"
        install_location.mkdir(parents=True, exist_ok=True)
        marketplace_json = install_location / ".claude-plugin" / "marketplace.json"
        marketplace_json.parent.mkdir(parents=True, exist_ok=True)

        marketplace_data_content = {
            "plugins": [
                {
                    "name": "lsp-plugin",
                    "description": "LSP plugin",
                    "source": "lsp-plugin",
                }
            ]
        }

        with open(marketplace_json, "w", encoding="utf-8") as f:
            json.dump(marketplace_data_content, f)

        # 创建插件目录和 .lsp.json
        plugin_root = install_location / "lsp-plugin"
        plugin_root.mkdir(parents=True, exist_ok=True)

        lsp_file = plugin_root / ".lsp.json"
        lsp_data = {
            "gopls": {
                "command": "gopls",
                "extensionToLanguage": {".go": "go"},
            }
        }

        with open(lsp_file, "w", encoding="utf-8") as f:
            json.dump(lsp_data, f)

        # 创建 installed_plugins.json，标记插件为已安装
        installed_plugins_file = (
            temp_user_home / ".claude" / "plugins" / "installed_plugins.json"
        )
        installed_plugins_file.parent.mkdir(parents=True, exist_ok=True)
        installed_data = {
            "plugins": {
                "lsp-plugin@test-marketplace": [
                    {
                        "scope": "project",
                        "projectPath": str(temp_project_dir),
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        }
        with open(installed_plugins_file, "w", encoding="utf-8") as f:
            json.dump(installed_data, f)

        # 启用插件
        settings_file = temp_project_dir / ".claude" / "settings.json"
        settings_data = {"enabledPlugins": {"lsp-plugin@test-marketplace": True}}
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)

        # 获取 LSP servers
        lsp_servers = await plugin_ops.get_plugin_lsp_servers()

        assert len(lsp_servers) == 1
        assert lsp_servers[0].name == "gopls"
        assert lsp_servers[0].plugin_name == "lsp-plugin"
        assert lsp_servers[0].marketplace_name == "test-marketplace"

    @pytest.mark.asyncio
    async def test_scan_plugin_tools_nonexistent_plugin(
        self, plugin_ops, temp_user_home
    ):
        """测试扫描不存在的插件工具"""
        marketplace_install = (
            temp_user_home / ".claude" / "plugins" / "test-marketplace"
        )
        # 不创建任何插件目录

        from src.claude.models import PluginConfig

        plugin_config = PluginConfig(name="nonexistent", source="nonexistent")

        tools = await plugin_ops._scan_plugin_tools(
            plugin_config, "test-marketplace", str(marketplace_install)
        )

        # 应该返回 None
        assert tools is None

    # ========== 测试 _load_install_counts ==========

    def test_load_install_counts(self, plugin_ops, temp_user_home):
        """测试加载安装计数"""
        install_counts_file = (
            temp_user_home / ".claude" / "plugins" / "install-counts-cache.json"
        )
        cache_data = {
            "counts": [
                {"plugin": "plugin1@marketplace1", "unique_installs": 100},
                {"plugin": "plugin2@marketplace2", "unique_installs": 200},
            ]
        }

        with open(install_counts_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        counts = plugin_ops._load_install_counts()

        assert counts["plugin1@marketplace1"] == 100
        assert counts["plugin2@marketplace2"] == 200

    def test_load_install_counts_nonexistent_file(self, plugin_ops):
        """测试加载不存在的安装计数文件"""
        counts = plugin_ops._load_install_counts()

        assert counts == {}

    def test_load_install_counts_invalid_json(self, plugin_ops, temp_user_home):
        """测试加载无效的安装计数文件"""
        install_counts_file = (
            temp_user_home / ".claude" / "plugins" / "install-counts-cache.json"
        )
        install_counts_file.write_text("invalid json", encoding="utf-8")

        counts = plugin_ops._load_install_counts()

        # 应该返回空字典
        assert counts == {}

    # ========== 测试 _get_claude_command ==========

    @pytest.mark.asyncio
    async def test_get_claude_command_disabled(self, plugin_ops):
        """测试 claude 功能被禁用时抛出异常"""
        with patch("src.claude.claude_plugin_operations.config_service") as mock_config:
            mock_config.get_setting = AsyncMock(return_value="false")

            with pytest.raises(RuntimeError, match="claude 功能已禁用"):
                await plugin_ops._get_claude_command()

    @pytest.mark.asyncio
    async def test_get_claude_command_no_path(self, plugin_ops):
        """测试未配置 claude 路径时抛出异常"""
        with patch("src.claude.claude_plugin_operations.config_service") as mock_config:
            mock_config.get_setting = AsyncMock(return_value=None)

            with pytest.raises(RuntimeError, match="未配置 claude.path"):
                await plugin_ops._get_claude_command()

    @pytest.mark.asyncio
    async def test_get_claude_command_path_not_exists(self, plugin_ops):
        """测试 claude 路径不存在时抛出异常"""
        with patch("src.claude.claude_plugin_operations.config_service") as mock_config:
            mock_config.get_setting = AsyncMock(return_value="true")
            mock_config.get_setting = AsyncMock(
                side_effect=["true", "/nonexistent/claude"]
            )

            with pytest.raises(RuntimeError, match="claude 路径不存在"):
                await plugin_ops._get_claude_command()
