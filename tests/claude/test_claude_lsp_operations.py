"""
Claude LSP Operations 模块的单元测试
测试 LSP 操作类从插件获取 LSP 服务器的功能
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.claude.claude_lsp_operations import ClaudeLSPOperations
from src.claude.claude_plugin_operations import ClaudePluginOperations
from src.claude.models import ConfigScope


class TestClaudeLSPOperations:
    """测试 ClaudeLSPOperations 类"""

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

    @pytest.fixture
    def lsp_ops(self, temp_project_dir, temp_user_home, plugin_ops):
        """创建 ClaudeLSPOperations 实例，传入 plugin_ops"""
        return ClaudeLSPOperations(
            temp_project_dir, temp_user_home, plugin_ops=plugin_ops
        )

    # ========== 测试 scan_lsp ==========

    async def test_scan_lsp_without_plugin_ops(self, temp_project_dir, temp_user_home):
        """测试没有传入 plugin_ops 时的扫描"""
        lsp_ops = ClaudeLSPOperations(temp_project_dir, temp_user_home, plugin_ops=None)
        lsp_servers = await lsp_ops.scan_lsp()
        assert lsp_servers == []

    async def test_scan_lsp_empty_marketplaces(self, lsp_ops):
        """测试扫描空的 marketplace"""
        lsp_servers = await lsp_ops.scan_lsp()
        assert lsp_servers == []

    async def test_scan_lsp_from_enabled_plugins(
        self, lsp_ops, plugin_ops, temp_user_home, temp_project_dir
    ):
        """测试从已启用插件扫描 LSP 服务器"""
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
                    "name": "go-lsp",
                    "description": "Go LSP plugin",
                    "source": "go-lsp",
                },
                {
                    "name": "python-lsp",
                    "description": "Python LSP plugin",
                    "source": "python-lsp",
                },
            ]
        }

        with open(marketplace_json, "w", encoding="utf-8") as f:
            json.dump(marketplace_data_content, f)

        # 创建 go-lsp 插件目录和 .lsp.json
        go_plugin_root = install_location / "go-lsp"
        go_plugin_root.mkdir(parents=True, exist_ok=True)

        go_lsp_file = go_plugin_root / ".lsp.json"
        go_lsp_data = {
            "gopls": {
                "command": "gopls",
                "args": ["serve"],
                "extensionToLanguage": {".go": "go"},
            }
        }

        with open(go_lsp_file, "w", encoding="utf-8") as f:
            json.dump(go_lsp_data, f)

        # 创建 python-lsp 插件目录和 .lsp.json
        python_plugin_root = install_location / "python-lsp"
        python_plugin_root.mkdir(parents=True, exist_ok=True)

        python_lsp_file = python_plugin_root / ".lsp.json"
        python_lsp_data = {
            "pyright": {
                "command": "pyright",
                "extensionToLanguage": {".py": "python"},
            }
        }

        with open(python_lsp_file, "w", encoding="utf-8") as f:
            json.dump(python_lsp_data, f)

        # 启用两个插件
        settings_file = temp_project_dir / ".claude" / "settings.json"
        settings_data = {
            "enabledPlugins": {
                "go-lsp@test-marketplace": True,
                "python-lsp@test-marketplace": True,
            }
        }
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)

        # 扫描 LSP 服务器
        lsp_servers = await lsp_ops.scan_lsp()

        # 验证结果
        assert len(lsp_servers) == 2
        server_names = {s.name for s in lsp_servers}
        assert server_names == {"gopls", "pyright"}

        # 验证 gopls
        gopls = next(s for s in lsp_servers if s.name == "gopls")
        assert gopls.plugin_name == "go-lsp"
        assert gopls.marketplace_name == "test-marketplace"
        assert gopls.scope == ConfigScope.plugin

        # 验证 pyright
        pyright = next(s for s in lsp_servers if s.name == "pyright")
        assert pyright.plugin_name == "python-lsp"
        assert pyright.marketplace_name == "test-marketplace"

    async def test_scan_lsp_only_enabled_plugins(
        self, lsp_ops, temp_user_home, temp_project_dir
    ):
        """测试只扫描已启用的插件"""
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
                    "source": "enabled-plugin",
                },
                {
                    "name": "disabled-plugin",
                    "description": "Disabled plugin",
                    "source": "disabled-plugin",
                },
            ]
        }

        with open(marketplace_json, "w", encoding="utf-8") as f:
            json.dump(marketplace_data_content, f)

        # 创建两个插件的 LSP 配置
        enabled_plugin_root = install_location / "enabled-plugin"
        enabled_plugin_root.mkdir(parents=True, exist_ok=True)

        enabled_lsp_file = enabled_plugin_root / ".lsp.json"
        enabled_lsp_data = {
            "enabled-server": {
                "command": "enabled-server",
                "extensionToLanguage": {".ext": "language"},
            }
        }
        with open(enabled_lsp_file, "w", encoding="utf-8") as f:
            json.dump(enabled_lsp_data, f)

        disabled_plugin_root = install_location / "disabled-plugin"
        disabled_plugin_root.mkdir(parents=True, exist_ok=True)

        disabled_lsp_file = disabled_plugin_root / ".lsp.json"
        disabled_lsp_data = {
            "disabled-server": {
                "command": "disabled-server",
                "extensionToLanguage": {".ext": "language"},
            }
        }
        with open(disabled_lsp_file, "w", encoding="utf-8") as f:
            json.dump(disabled_lsp_data, f)

        # 只启用一个插件
        settings_file = temp_project_dir / ".claude" / "settings.json"
        settings_data = {
            "enabledPlugins": {
                "enabled-plugin@test-marketplace": True,
                "disabled-plugin@test-marketplace": False,
            }
        }
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)

        # 扫描 LSP 服务器
        lsp_servers = await lsp_ops.scan_lsp()

        # 应该只返回已启用插件的 LSP 服务器
        assert len(lsp_servers) == 1
        assert lsp_servers[0].name == "enabled-server"
        assert lsp_servers[0].plugin_name == "enabled-plugin"

    async def test_scan_lsp_with_plugin_scope_filter(
        self, lsp_ops, temp_user_home, temp_project_dir
    ):
        """测试使用 plugin 作用域过滤"""
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

        plugin_root = install_location / "lsp-plugin"
        plugin_root.mkdir(parents=True, exist_ok=True)

        lsp_file = plugin_root / ".lsp.json"
        lsp_data = {
            "test-server": {
                "command": "test-server",
                "extensionToLanguage": {".test": "test"},
            }
        }
        with open(lsp_file, "w", encoding="utf-8") as f:
            json.dump(lsp_data, f)

        settings_file = temp_project_dir / ".claude" / "settings.json"
        settings_data = {"enabledPlugins": {"lsp-plugin@test-marketplace": True}}
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)

        # 使用 plugin scope 过滤
        lsp_servers = await lsp_ops.scan_lsp(scope=ConfigScope.plugin)

        assert len(lsp_servers) == 1
        assert lsp_servers[0].name == "test-server"

    async def test_scan_lsp_with_user_scope_filter(
        self, lsp_ops, temp_user_home, temp_project_dir
    ):
        """测试使用 user 作用域过滤（应该返回空）"""
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

        plugin_root = install_location / "lsp-plugin"
        plugin_root.mkdir(parents=True, exist_ok=True)

        lsp_file = plugin_root / ".lsp.json"
        lsp_data = {
            "test-server": {
                "command": "test-server",
                "extensionToLanguage": {".test": "test"},
            }
        }
        with open(lsp_file, "w", encoding="utf-8") as f:
            json.dump(lsp_data, f)

        settings_file = temp_project_dir / ".claude" / "settings.json"
        settings_data = {"enabledPlugins": {"lsp-plugin@test-marketplace": True}}
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)

        # LSP 只支持 plugin 作用域，user scope 应该返回空
        lsp_servers = await lsp_ops.scan_lsp(scope=ConfigScope.user)
        assert lsp_servers == []
