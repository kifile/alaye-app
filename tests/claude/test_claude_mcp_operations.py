"""
Claude MCP Operations 模块的单元测试
测试 MCP 服务器的扫描、添加、删除、更新、启用/禁用等功能
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.claude.claude_mcp_operations import ClaudeMCPOperations
from src.claude.models import (
    ConfigScope,
    MCPServer,
    McpServerType,
)


class TestClaudeMCPOperations:
    """测试 ClaudeMCPOperations 类"""

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
    def mcp_ops(self, temp_project_dir, temp_user_home):
        """创建 ClaudeMCPOperations 实例"""
        return ClaudeMCPOperations(temp_project_dir, temp_user_home)

    @pytest.fixture
    def sample_mcp_server(self):
        """创建示例 MCP 服务器配置"""
        return MCPServer(
            type=McpServerType.stdio,
            command="node",
            args=["server.js"],
            env={"NODE_ENV": "production"},
            description="Test MCP server",
        )

    # ========== 测试 scan_mcp ==========

    def test_scan_mcp_empty_configs(self, mcp_ops):
        """测试扫描空的 MCP 配置"""
        mcp_info = mcp_ops.scan_mcp()

        assert mcp_info.servers == []
        assert mcp_info.enable_all_project_mcp_servers.value is None

    def test_scan_mcp_user_servers(self, temp_user_home, mcp_ops):
        """测试扫描 user scope 的 MCP 服务器"""
        claude_json = temp_user_home / ".claude.json"
        test_data = {
            "mcpServers": {"user-server": {"command": "python", "args": ["server.py"]}}
        }

        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        mcp_info = mcp_ops.scan_mcp()

        assert len(mcp_info.servers) == 1
        assert mcp_info.servers[0].name == "user-server"
        assert mcp_info.servers[0].scope == ConfigScope.user

    def test_scan_mcp_project_servers(self, temp_project_dir, mcp_ops):
        """测试扫描 project scope 的 MCP 服务器"""
        mcp_json = temp_project_dir / ".mcp.json"
        test_data = {
            "mcpServers": {"project-server": {"command": "node", "args": ["server.js"]}}
        }

        with open(mcp_json, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        mcp_info = mcp_ops.scan_mcp()

        assert len(mcp_info.servers) == 1
        assert mcp_info.servers[0].name == "project-server"
        assert mcp_info.servers[0].scope == ConfigScope.project

    def test_scan_mcp_local_servers(self, temp_user_home, temp_project_dir, mcp_ops):
        """测试扫描 local scope 的 MCP 服务器"""
        claude_json = temp_user_home / ".claude.json"
        test_data = {
            "mcpServers": {"global-server": {"command": "python"}},
            "projects": {
                str(temp_project_dir): {
                    "mcpServers": {"local-server": {"command": "node"}}
                }
            },
        }

        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        mcp_info = mcp_ops.scan_mcp()

        # 应该有两个服务器：global (user) 和 local
        assert len(mcp_info.servers) == 2
        scopes = {server.scope for server in mcp_info.servers}
        assert scopes == {ConfigScope.user, ConfigScope.local}

    def test_scan_mcp_server_priority_and_override(
        self, temp_user_home, temp_project_dir, mcp_ops
    ):
        """测试 MCP 服务器优先级和覆盖（local > project > user）"""
        # User 配置
        claude_json = temp_user_home / ".claude.json"
        user_data = {
            "mcpServers": {"server1": {"command": "python", "args": ["user.py"]}}
        }
        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(user_data, f)

        # Project 配置
        mcp_json = temp_project_dir / ".mcp.json"
        project_data = {
            "mcpServers": {
                "server1": {"command": "node", "args": ["project.js"]},
                "server2": {"command": "python", "args": ["server2.py"]},
            }
        }
        with open(mcp_json, "w", encoding="utf-8") as f:
            json.dump(project_data, f)

        mcp_info = mcp_ops.scan_mcp()

        # 应该有 3 个服务器
        assert len(mcp_info.servers) == 3

        # server1 应该出现两次（user 和 project）
        server1_entries = [s for s in mcp_info.servers if s.name == "server1"]
        assert len(server1_entries) == 2

        # project 的 server1 应该标记为 override（因为 local 中没有，但优先级高于 uwer）
        # 注意：这里的 override=True 是因为同名的 project 服务器优先级高于 user
        project_server1 = next(
            s for s in server1_entries if s.scope == ConfigScope.project
        )
        user_server1 = next(s for s in server1_entries if s.scope == ConfigScope.user)
        # 按照代码逻辑，user 的服务器会因为被 project 覆盖而标记为 override
        assert user_server1.override is True

    def test_scan_mcp_enable_all_project_mcp_servers(self, temp_project_dir, mcp_ops):
        """测试扫描 enableAllProjectMcpServers 配置"""
        settings_file = temp_project_dir / ".claude" / "settings.json"
        test_data = {"enableAllProjectMcpServers": True}

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        mcp_info = mcp_ops.scan_mcp()

        assert mcp_info.enable_all_project_mcp_servers.value is True
        assert mcp_info.enable_all_project_mcp_servers.scope == ConfigScope.project

    def test_scan_mcp_enable_all_priority(self, temp_project_dir, mcp_ops):
        """测试 enableAllProjectMcpServers 优先级（local > project）"""
        # Project settings
        project_settings = temp_project_dir / ".claude" / "settings.json"
        project_data = {"enableAllProjectMcpServers": False}
        with open(project_settings, "w", encoding="utf-8") as f:
            json.dump(project_data, f)

        # Local settings（更高优先级）
        local_settings = temp_project_dir / ".claude" / "settings.local.json"
        local_data = {"enableAllProjectMcpServers": True}
        with open(local_settings, "w", encoding="utf-8") as f:
            json.dump(local_data, f)

        mcp_info = mcp_ops.scan_mcp()

        # Local 配置应该覆盖 project 配置
        assert mcp_info.enable_all_project_mcp_servers.value is True
        assert mcp_info.enable_all_project_mcp_servers.scope == ConfigScope.local

    # ========== 测试 add_mcp_server ==========

    def test_add_mcp_server_to_project_scope(
        self, mcp_ops, temp_project_dir, sample_mcp_server
    ):
        """测试添加 MCP 服务器到 project scope"""
        mcp_ops.add_mcp_server("test-server", sample_mcp_server, ConfigScope.project)

        mcp_file = temp_project_dir / ".mcp.json"
        assert mcp_file.exists()

        with open(mcp_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "test-server" in config["mcpServers"]
        assert config["mcpServers"]["test-server"]["command"] == "node"

    def test_add_mcp_server_to_user_scope(
        self, mcp_ops, temp_user_home, sample_mcp_server
    ):
        """测试添加 MCP 服务器到 user scope"""
        mcp_ops.add_mcp_server("global-server", sample_mcp_server, ConfigScope.user)

        claude_json = temp_user_home / ".claude.json"
        with open(claude_json, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "global-server" in config["mcpServers"]

    def test_add_mcp_server_to_local_scope(
        self, mcp_ops, temp_user_home, temp_project_dir, sample_mcp_server
    ):
        """测试添加 MCP 服务器到 local scope"""
        # 先创建项目配置
        claude_json = temp_user_home / ".claude.json"
        claude_json.parent.mkdir(parents=True, exist_ok=True)
        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump({"projects": {str(temp_project_dir): {"mcpServers": {}}}}, f)

        mcp_ops.add_mcp_server("local-server", sample_mcp_server, ConfigScope.local)

        with open(claude_json, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert str(temp_project_dir) in config["projects"]
        assert "local-server" in config["projects"][str(temp_project_dir)]["mcpServers"]

    def test_add_mcp_server_with_special_chars_in_name(self, mcp_ops, temp_project_dir):
        """测试添加包含特殊字符的服务器名称"""
        server = MCPServer(type=McpServerType.stdio, command="test")
        mcp_ops.add_mcp_server("my.custom.server", server, ConfigScope.project)

        mcp_file = temp_project_dir / ".mcp.json"
        with open(mcp_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "my.custom.server" in config["mcpServers"]

    # ========== 测试 remove_mcp_server ==========

    def test_remove_mcp_server_from_project_scope(self, mcp_ops, temp_project_dir):
        """测试从 project scope 删除 MCP 服务器"""
        # 先添加服务器
        mcp_json = temp_project_dir / ".mcp.json"
        test_data = {
            "mcpServers": {
                "server1": {"command": "node"},
                "server2": {"command": "python"},
            }
        }
        with open(mcp_json, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        # 删除 server1
        result = mcp_ops.remove_mcp_server("server1", ConfigScope.project)
        assert result is True

        # 验证删除
        with open(mcp_json, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "server1" not in config["mcpServers"]
        assert "server2" in config["mcpServers"]

    def test_remove_mcp_server_from_user_scope(self, mcp_ops, temp_user_home):
        """测试从 user scope 删除 MCP 服务器"""
        claude_json = temp_user_home / ".claude.json"
        test_data = {"mcpServers": {"global-server": {"command": "python"}}}
        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = mcp_ops.remove_mcp_server("global-server", ConfigScope.user)
        assert result is True

        with open(claude_json, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "global-server" not in config.get("mcpServers", {})

    def test_remove_mcp_server_last_server_cleanup(self, mcp_ops, temp_project_dir):
        """测试删除最后一个服务器时清理 mcpServers"""
        mcp_json = temp_project_dir / ".mcp.json"
        test_data = {"mcpServers": {"only-server": {"command": "node"}}}
        with open(mcp_json, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        mcp_ops.remove_mcp_server("only-server", ConfigScope.project)

        with open(mcp_json, "r", encoding="utf-8") as f:
            config = json.load(f)

        # mcpServers 应该被清理
        assert "mcpServers" not in config or len(config.get("mcpServers", {})) == 0

    # ========== 测试 update_mcp_server ==========

    def test_update_mcp_server_success(self, mcp_ops, temp_project_dir):
        """测试成功更新 MCP 服务器"""
        # 先创建服务器
        mcp_json = temp_project_dir / ".mcp.json"
        test_data = {
            "mcpServers": {"test-server": {"command": "node", "args": ["old.js"]}}
        }
        with open(mcp_json, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        # 更新服务器
        updated_server = MCPServer(
            type=McpServerType.stdio,
            command="python",
            args=["new.py"],
            env={"PYTHONPATH": "/app"},
        )
        result = mcp_ops.update_mcp_server(
            "test-server", updated_server, ConfigScope.project
        )
        assert result is True

        # 验证更新
        with open(mcp_json, "r", encoding="utf-8") as f:
            config = json.load(f)

        server_config = config["mcpServers"]["test-server"]
        assert server_config["command"] == "python"
        assert server_config["args"] == ["new.py"]
        assert server_config["env"]["PYTHONPATH"] == "/app"

    def test_update_mcp_server_nonexistent(self, mcp_ops, temp_project_dir):
        """测试更新不存在的服务器"""
        server = MCPServer(type=McpServerType.stdio, command="test")
        # 更新不存在的服务器应该创建它
        mcp_ops.update_mcp_server("new-server", server, ConfigScope.project)

        mcp_json = temp_project_dir / ".mcp.json"
        with open(mcp_json, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "new-server" in config["mcpServers"]

    # ========== 测试 rename_mcp_server ==========

    def test_rename_mcp_server_same_scope(self, mcp_ops, temp_project_dir):
        """测试在同一作用域内重命名 MCP 服务器"""
        # 创建原始服务器
        mcp_json = temp_project_dir / ".mcp.json"
        test_data = {
            "mcpServers": {
                "old-name": {
                    "command": "node",
                    "args": ["server.js"],
                }
            }
        }
        with open(mcp_json, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        # 重命名
        result = mcp_ops.rename_mcp_server("old-name", "new-name", ConfigScope.project)
        assert result is True

        # 验证重命名
        with open(mcp_json, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "old-name" not in config["mcpServers"]
        assert "new-name" in config["mcpServers"]

    def test_rename_mcp_server_change_scope(
        self, mcp_ops, temp_user_home, temp_project_dir
    ):
        """测试重命名并更改 MCP 服务器作用域"""
        # User 服务器
        claude_json = temp_user_home / ".claude.json"
        test_data = {"mcpServers": {"user-server": {"command": "python"}}}
        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        # 重命名并移动到 project scope
        result = mcp_ops.rename_mcp_server(
            "user-server",
            "project-server",
            old_scope=ConfigScope.user,
            new_scope=ConfigScope.project,
        )
        assert result is True

        # 验证：user 中不存在，project 中存在
        with open(claude_json, "r", encoding="utf-8") as f:
            user_config = json.load(f)
        assert "user-server" not in user_config.get("mcpServers", {})

        mcp_json = temp_project_dir / ".mcp.json"
        with open(mcp_json, "r", encoding="utf-8") as f:
            project_config = json.load(f)
        assert "project-server" in project_config["mcpServers"]

    def test_rename_mcp_server_target_exists_raises_error(
        self, mcp_ops, temp_project_dir
    ):
        """测试重命名到已存在的名称抛出异常"""
        mcp_json = temp_project_dir / ".mcp.json"
        test_data = {
            "mcpServers": {
                "server1": {"command": "node"},
                "server2": {"command": "python"},
            }
        }
        with open(mcp_json, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        with pytest.raises(ValueError, match="已存在"):
            mcp_ops.rename_mcp_server("server1", "server2", ConfigScope.project)

    def test_rename_mcp_server_nonexistent_source_raises_error(self, mcp_ops):
        """测试重命名不存在的服务器抛出异常"""
        with pytest.raises(ValueError, match="不存在"):
            mcp_ops.rename_mcp_server("nonexistent", "new-name", ConfigScope.project)

    # ========== 测试 enable_mcp_server / disable_mcp_server ==========

    def test_disable_mcp_server_adds_to_disabled_list(
        self, mcp_ops, temp_user_home, temp_project_dir
    ):
        """测试禁用 MCP 服务器添加到禁用列表"""
        # 创建项目配置
        claude_json = temp_user_home / ".claude.json"
        test_data = {
            "projects": {
                str(temp_project_dir): {"mcpServers": {}, "disabledMcpServers": []}
            }
        }
        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        # 禁用服务器
        mcp_ops.disable_mcp_server("test-server")

        with open(claude_json, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert (
            "test-server"
            in config["projects"][str(temp_project_dir)]["disabledMcpServers"]
        )

    def test_disable_mcp_server_fallback_to_settings_local(
        self, mcp_ops, temp_project_dir
    ):
        """测试禁用服务器时回退到 settings.local.json"""
        # 不创建项目配置，直接禁用
        mcp_ops.disable_mcp_server("test-server")

        settings_file = temp_project_dir / ".claude" / "settings.local.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "test-server" in config["disabledMcpjsonServers"]

    def test_enable_mcp_server_removes_from_disabled(
        self, mcp_ops, temp_user_home, temp_project_dir
    ):
        """测试启用 MCP 服务器从禁用列表移除"""
        # 创建项目配置，服务器已在禁用列表
        claude_json = temp_user_home / ".claude.json"
        test_data = {
            "projects": {str(temp_project_dir): {"disabledMcpServers": ["test-server"]}}
        }
        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        # 启用服务器
        mcp_ops.enable_mcp_server("test-server")

        with open(claude_json, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "test-server" not in config["projects"][str(temp_project_dir)].get(
            "disabledMcpServers", []
        )

    def test_enable_mcp_server_adds_to_enabled_list(self, mcp_ops, temp_project_dir):
        """测试启用服务器添加到启用列表"""
        settings_file = temp_project_dir / ".claude" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        test_data = {
            "disabledMcpjsonServers": ["test-server"],
            "enabledMcpjsonServers": [],
        }
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        mcp_ops.enable_mcp_server("test-server")

        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 应该从 disabled 移除，添加到 enabled
        assert "test-server" not in config.get("disabledMcpjsonServers", [])
        assert "test-server" in config["enabledMcpjsonServers"]

    # ========== 测试 update_enable_all_project_mcp_servers ==========

    def test_update_enable_all_project_mcp_servers(self, mcp_ops, temp_project_dir):
        """测试更新 enableAllProjectMcpServers 配置"""
        mcp_ops.update_enable_all_project_mcp_servers(True)

        settings_file = temp_project_dir / ".claude" / "settings.local.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config.get("enableAllProjectMcpServers") is True

    def test_update_enable_all_project_mcp_servers_to_false(
        self, mcp_ops, temp_project_dir
    ):
        """测试将 enableAllProjectMcpServers 设置为 False"""
        mcp_ops.update_enable_all_project_mcp_servers(False)

        settings_file = temp_project_dir / ".claude" / "settings.local.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config.get("enableAllProjectMcpServers") is False

    # ========== 测试集成场景 ==========

    def test_full_mcp_server_lifecycle(self, mcp_ops, temp_project_dir):
        """测试 MCP 服务器的完整生命周期"""
        server = MCPServer(
            type=McpServerType.stdio,
            command="node",
            args=["server.js"],
            description="Lifecycle test server",
        )

        # Create: 添加服务器
        mcp_ops.add_mcp_server("lifecycle-server", server, ConfigScope.project)

        mcp_info = mcp_ops.scan_mcp()
        assert len(mcp_info.servers) == 1
        assert mcp_info.servers[0].name == "lifecycle-server"

        # Update: 更新服务器
        updated_server = MCPServer(
            type=McpServerType.stdio,
            command="python",
            args=["server.py"],
            description="Updated server",
        )
        mcp_ops.update_mcp_server(
            "lifecycle-server", updated_server, ConfigScope.project
        )

        mcp_info = mcp_ops.scan_mcp()
        assert mcp_info.servers[0].mcpServer.command == "python"

        # Delete: 删除服务器
        mcp_ops.remove_mcp_server("lifecycle-server", ConfigScope.project)

        mcp_info = mcp_ops.scan_mcp()
        assert len(mcp_info.servers) == 0

    def test_http_mcp_server(self, mcp_ops, temp_project_dir):
        """测试 HTTP 类型的 MCP 服务器"""
        http_server = MCPServer(
            type=McpServerType.http,
            url="https://example.com/mcp",
            headers={"Authorization": "Bearer token"},
        )

        mcp_ops.add_mcp_server("http-server", http_server, ConfigScope.project)

        mcp_json = temp_project_dir / ".mcp.json"
        with open(mcp_json, "r", encoding="utf-8") as f:
            config = json.load(f)

        server_config = config["mcpServers"]["http-server"]
        assert server_config["type"] == "http"
        assert server_config["url"] == "https://example.com/mcp"
        assert server_config["headers"]["Authorization"] == "Bearer token"
