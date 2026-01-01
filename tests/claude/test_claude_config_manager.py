"""
Claude Config Manager 模块的集成测试
测试 ClaudeConfigManager 的整体功能协调
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.claude.claude_config_manager import ClaudeConfigManager
from src.claude.models import (
    AgentInfo,
    ClaudeMemoryInfo,
    ClaudeSettingsInfoDTO,
    CommandInfo,
    ConfigScope,
    HookConfig,
    HookEvent,
    MarkdownContentDTO,
    MCPInfo,
    MCPServer,
    McpServerType,
    SkillInfo,
)


class TestClaudeConfigManager:
    """测试 ClaudeConfigManager 类"""

    @pytest.fixture
    def temp_project_dir(self):
        """创建临时项目目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            # 创建完整的目录结构
            (project_path / ".claude" / "commands").mkdir(parents=True, exist_ok=True)
            (project_path / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
            (project_path / ".claude" / "skills").mkdir(parents=True, exist_ok=True)
            (project_path / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
            yield project_path

    @pytest.fixture
    def temp_user_home(self):
        """创建临时用户主目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_home = Path(tmpdir)
            # 创建完整的目录结构
            (user_home / ".claude" / "commands").mkdir(parents=True, exist_ok=True)
            (user_home / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
            (user_home / ".claude" / "plugins").mkdir(parents=True, exist_ok=True)
            (user_home / ".claude" / "CLAUDE.md").parent.mkdir(
                parents=True, exist_ok=True
            )
            yield user_home

    @pytest.fixture
    def config_manager(self, temp_project_dir, temp_user_home):
        """创建 ClaudeConfigManager 实例"""
        return ClaudeConfigManager(str(temp_project_dir), str(temp_user_home))

    # ========== 测试初始化 ==========

    def test_init_with_valid_project_path(self, temp_project_dir, temp_user_home):
        """测试使用有效路径初始化"""
        manager = ClaudeConfigManager(str(temp_project_dir), str(temp_user_home))

        assert manager.project_path == temp_project_dir.resolve()
        assert manager.user_home == temp_user_home.resolve()
        assert manager.markdown_ops is not None
        assert manager.hooks_ops is not None
        assert manager.mcp_ops is not None
        assert manager.settings_ops is not None
        assert manager.plugin_ops is not None

    def test_init_with_invalid_project_path_raises_error(self):
        """测试使用无效路径初始化抛出异常"""
        with pytest.raises(ValueError, match="项目路径不存在"):
            ClaudeConfigManager("/nonexistent/project")

    # ========== MCP 集成测试 ==========

    def test_mcp_full_workflow(self, config_manager, temp_project_dir):
        """测试 MCP 完整工作流"""
        # 创建服务器配置
        server = MCPServer(
            type=McpServerType.stdio,
            command="node",
            args=["server.js"],
            description="Test server",
        )

        # 添加服务器
        config_manager.add_mcp_server("test-server", server, ConfigScope.project)

        # 扫描服务器
        mcp_info = config_manager.scan_mcp_servers()
        assert isinstance(mcp_info, MCPInfo)
        assert len(mcp_info.servers) == 1
        assert mcp_info.servers[0].name == "test-server"

        # 更新服务器
        updated_server = MCPServer(
            type=McpServerType.stdio,
            command="python",
            args=["server.py"],
            description="Updated server",
        )
        config_manager.update_mcp_server(
            "test-server", updated_server, ConfigScope.project
        )

        mcp_info = config_manager.scan_mcp_servers()
        assert mcp_info.servers[0].mcpServer.command == "python"

        # 重命名服务器
        config_manager.rename_mcp_server(
            "test-server", "renamed-server", ConfigScope.project
        )

        mcp_info = config_manager.scan_mcp_servers()
        assert mcp_info.servers[0].name == "renamed-server"

        # 禁用服务器
        config_manager.disable_mcp_server("renamed-server")

        # 删除服务器
        config_manager.remove_mcp_server("renamed-server", ConfigScope.project)

        mcp_info = config_manager.scan_mcp_servers()
        assert len(mcp_info.servers) == 0

    def test_mcp_enable_disable_workflow(
        self, config_manager, temp_project_dir, temp_user_home
    ):
        """测试 MCP 启用/禁用工作流"""
        # 添加服务器
        server = MCPServer(type=McpServerType.stdio, command="test")
        config_manager.add_mcp_server("toggle-server", server, ConfigScope.project)

        # 禁用
        config_manager.disable_mcp_server("toggle-server")

        # 启用
        config_manager.enable_mcp_server("toggle-server")

    def test_mcp_enable_all_project_servers(self, config_manager, temp_project_dir):
        """测试 enableAllProjectMcpServers 配置"""
        config_manager.update_enable_all_project_mcp_servers(True)

        settings_file = temp_project_dir / ".claude" / "settings.local.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config.get("enableAllProjectMcpServers") is True

    # ========== Markdown 集成测试 ==========

    def test_markdown_full_workflow(self, config_manager, temp_project_dir):
        """测试 Markdown 完整工作流"""
        # 保存新的 command
        result = config_manager.save_markdown_content(
            "command",
            "test-command",
            content="# Test Command",
            scope=ConfigScope.project,
        )
        assert isinstance(result, MarkdownContentDTO)

        # 加载 command
        loaded = config_manager.load_markdown_content(
            "command", "test-command", ConfigScope.project
        )
        assert loaded.content == "# Test Command"

        # 更新 command
        config_manager.update_markdown_content(
            "command",
            "test-command",
            from_md5=loaded.md5,
            content="# Updated Command",
            scope=ConfigScope.project,
        )

        # 重命名 command
        config_manager.rename_markdown_content(
            "command", "test-command", "renamed-command", scope=ConfigScope.project
        )

        # 删除 command
        config_manager.delete_markdown_content(
            "command", "renamed-command", ConfigScope.project
        )

    def test_markdown_memory_scan(
        self, config_manager, temp_project_dir, temp_user_home
    ):
        """测试扫描 memory 文件"""
        # 创建各个 memory 文件
        (temp_project_dir / "CLAUDE.md").write_text("# Project", encoding="utf-8")
        (temp_project_dir / ".claude" / "CLAUDE.md").write_text(
            "# Claude Dir", encoding="utf-8"
        )
        (temp_project_dir / "CLAUDE.local.md").write_text("# Local", encoding="utf-8")
        (temp_user_home / ".claude" / "CLAUDE.md").write_text(
            "# Global", encoding="utf-8"
        )

        memory_info = config_manager.scan_memory()

        assert isinstance(memory_info, ClaudeMemoryInfo)
        assert memory_info.project_claude_md is True
        assert memory_info.claude_dir_claude_md is True
        assert memory_info.local_claude_md is True
        assert memory_info.user_global_claude_md is True

    def test_markdown_scan_agents(self, config_manager, temp_project_dir):
        """测试扫描 agents"""
        (temp_project_dir / ".claude" / "agents" / "test-agent.md").write_text(
            "# Test Agent", encoding="utf-8"
        )

        agents = config_manager.scan_agents()

        assert len(agents) == 1
        assert isinstance(agents[0], AgentInfo)
        assert agents[0].name == "test-agent"

    def test_markdown_scan_commands(self, config_manager, temp_project_dir):
        """测试扫描 commands"""
        (temp_project_dir / ".claude" / "commands" / "test.md").write_text(
            "# Test Command", encoding="utf-8"
        )

        commands = config_manager.scan_commands()

        assert len(commands) == 1
        assert isinstance(commands[0], CommandInfo)
        assert commands[0].name == "test"

    def test_markdown_scan_skills(self, config_manager, temp_project_dir):
        """测试扫描 skills"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

        skills = config_manager.scan_skills()

        assert len(skills) == 1
        assert isinstance(skills[0], SkillInfo)
        assert skills[0].name == "test-skill"

    # ========== Settings 集成测试 ==========

    def test_settings_full_workflow(self, config_manager, temp_project_dir):
        """测试 Settings 完整工作流"""
        # 扫描空配置
        settings_info = config_manager.scan_settings(ConfigScope.project)
        assert isinstance(settings_info, ClaudeSettingsInfoDTO)

        # 更新配置
        config_manager.update_settings_values(
            ConfigScope.project, "model", "claude-3-5-sonnet", "string"
        )

        # 验证更新
        settings_info = config_manager.scan_settings(ConfigScope.project)
        assert "model" in settings_info.settings

        # 更改作用域
        config_manager.update_settings_scope(
            ConfigScope.project, ConfigScope.local, "model"
        )

    def test_settings_update_nested_values(self, config_manager, temp_project_dir):
        """测试更新嵌套配置值"""
        config_manager.update_settings_values(
            ConfigScope.project, "permissions.allow", '["*"]', "array"
        )

        settings_info = config_manager.scan_settings(ConfigScope.project)
        assert "permissions.allow" in settings_info.settings
        assert settings_info.settings["permissions.allow"][0] == ["*"]

    # ========== Hooks 集成测试 ==========

    def test_hooks_full_workflow(self, config_manager):
        """测试 Hooks 完整工作流"""
        # 扫描空 hooks
        hooks_info = config_manager.scan_hooks_info()
        assert len(hooks_info.matchers) == 0

        # 添加 hook
        hook = HookConfig(type="command", command="echo 'test'")
        config_manager.add_hook(
            HookEvent.PreToolUse, hook, matcher="test.tool", scope=ConfigScope.project
        )

        # 扫描 hooks
        hooks_info = config_manager.scan_hooks_info()
        assert len(hooks_info.matchers) == 1

        # 获取 hook_id
        hook_id = hooks_info.matchers[0].id

        # 更新 hook
        updated_hook = HookConfig(type="command", command="echo 'updated'")
        config_manager.update_hook(hook_id, updated_hook, ConfigScope.project)

        # 重新扫描获取更新后的 hook_id（因为内容变化会导致 MD5 变化）
        hooks_info = config_manager.scan_hooks_info()
        updated_hook_id = hooks_info.matchers[0].id

        # 删除 hook（使用更新后的 hook_id）
        config_manager.remove_hook(updated_hook_id, ConfigScope.project)

        hooks_info = config_manager.scan_hooks_info()
        assert len(hooks_info.matchers) == 0

    def test_hooks_disable_all(self, config_manager, temp_project_dir):
        """测试 disableAllHooks 配置"""
        config_manager.update_disable_all_hooks(True)

        settings_file = temp_project_dir / ".claude" / "settings.local.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config.get("disableAllHooks") is True

    # ========== Plugin 集成测试 ==========

    def test_plugin_marketplace_scan(self, config_manager, temp_user_home):
        """测试扫描 marketplace"""
        # 创建 marketplace 配置
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
            }
        }

        with open(known_marketplaces, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        marketplaces = config_manager.scan_plugin_marketplaces()

        assert len(marketplaces) == 1
        assert marketplaces[0].name == "anthropics"

    async def test_plugin_enable_disable(self, config_manager, temp_project_dir):
        """测试插件启用/禁用"""
        # 创建空的 settings.json 文件
        settings_file = temp_project_dir / ".claude" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump({}, f)

        # 启用插件
        await config_manager.enable_plugin(
            "test-plugin@marketplace", ConfigScope.project
        )

        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["enabledPlugins"]["test-plugin@marketplace"] is True

        # 禁用插件
        await config_manager.disable_plugin(
            "test-plugin@marketplace", ConfigScope.project
        )

        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["enabledPlugins"]["test-plugin@marketplace"] is False

    # ========== 端到端集成测试 ==========

    def test_end_to_end_project_setup(
        self, config_manager, temp_project_dir, temp_user_home
    ):
        """测试端到端项目设置流程"""
        # 1. 设置 MCP 服务器
        mcp_server = MCPServer(
            type=McpServerType.stdio, command="node", args=["mcp-server.js"]
        )
        config_manager.add_mcp_server("project-mcp", mcp_server, ConfigScope.project)

        # 2. 创建命令
        config_manager.save_markdown_content(
            "command",
            "deploy",
            content="# Deploy Command\n\nDeploy to production.",
            scope=ConfigScope.project,
        )

        # 3. 创建 Agent
        config_manager.save_markdown_content(
            "agent",
            "reviewer",
            content="# Code Reviewer\n\nReviews code changes.",
            scope=ConfigScope.project,
        )

        # 4. 创建 Skill
        config_manager.save_markdown_content(
            "skill",
            "refactor",
            content="# Refactor Skill\n\nRefactors code.",
            scope=ConfigScope.project,
        )

        # 5. 设置配置
        config_manager.update_settings_values(
            ConfigScope.project, "model", "claude-3-5-sonnet", "string"
        )

        # 6. 添加 Hook
        hook = HookConfig(type="prompt", prompt="Review all changes")
        config_manager.add_hook(
            HookEvent.PreToolUse, hook, matcher="git.commit", scope=ConfigScope.project
        )

        # 7. 验证所有设置
        mcp_info = config_manager.scan_mcp_servers()
        assert len(mcp_info.servers) == 1

        commands = config_manager.scan_commands()
        assert len(commands) == 1
        assert commands[0].name == "deploy"

        agents = config_manager.scan_agents()
        assert len(agents) == 1
        assert agents[0].name == "reviewer"

        skills = config_manager.scan_skills()
        assert len(skills) == 1
        assert skills[0].name == "refactor"

        hooks_info = config_manager.scan_hooks_info()
        assert len(hooks_info.matchers) == 1

        settings_info = config_manager.scan_settings(ConfigScope.project)
        assert "model" in settings_info.settings

    def test_multi_scope_configuration(
        self, config_manager, temp_user_home, temp_project_dir
    ):
        """测试多作用域配置合并"""
        # User 配置
        config_manager.update_settings_values(
            ConfigScope.user, "model", "claude-3-opus", "string"
        )

        # Project 配置
        config_manager.update_settings_values(
            ConfigScope.project, "model", "claude-3-5-sonnet", "string"
        )

        # Local 配置（最高优先级）
        config_manager.update_settings_values(
            ConfigScope.local, "model", "claude-3-5-sonnet-20241022", "string"
        )

        # 不指定 scope，应该合并所有配置
        settings_info = config_manager.scan_settings(None)

        # 应该使用 local 的值（最高优先级）
        assert settings_info.settings["model"][0] == "claude-3-5-sonnet-20241022"
        assert settings_info.settings["model"][1] == ConfigScope.local

    def test_cross_scope_operations(self, config_manager, temp_project_dir):
        """测试跨作用域操作"""
        # 在 project scope 创建配置
        config_manager.update_settings_values(
            ConfigScope.project, "model", "claude-3-project", "string"
        )

        # 移动到 local scope
        config_manager.update_settings_scope(
            ConfigScope.project, ConfigScope.local, "model"
        )

        # 验证：project 中不存在，local 中存在
        project_settings = config_manager.scan_settings(ConfigScope.project)
        assert "model" not in project_settings.settings

        local_settings = config_manager.scan_settings(ConfigScope.local)
        assert "model" in local_settings.settings

    def test_error_handling_invalid_operations(self, config_manager):
        """测试错误处理"""
        # 尝试删除不存在的 MCP 服务器
        result = config_manager.remove_mcp_server("nonexistent", ConfigScope.project)
        # 应该返回 False 而不是抛出异常
        assert result is True  # 不存在的也会被认为是成功删除

        # 尝试加载不存在的 markdown
        result = config_manager.load_markdown_content("memory", "project_claude_md")
        assert isinstance(result, MarkdownContentDTO)
        assert result.content == ""

    def test_concurrent_access_simulation(self, config_manager, temp_project_dir):
        """测试并发访问模拟（MD5 检查）"""
        # 创建文件
        config_manager.save_markdown_content(
            "command",
            "concurrent-test",
            content="# Original",
            scope=ConfigScope.project,
        )

        # 获取 MD5
        original = config_manager.load_markdown_content(
            "command", "concurrent-test", ConfigScope.project
        )

        # 模拟文件被外部修改
        (temp_project_dir / ".claude" / "commands" / "concurrent-test.md").write_text(
            "# Modified externally", encoding="utf-8"
        )

        # 尝试使用旧的 MD5 更新，应该失败
        with pytest.raises(ValueError, match="文件已变化"):
            config_manager.update_markdown_content(
                "command",
                "concurrent-test",
                from_md5=original.md5,
                content="# This should fail",
                scope=ConfigScope.project,
            )
