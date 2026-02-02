"""
Claude Markdown Operations 模块的单元测试
测试 Markdown 文件的读取、写入、重命名、删除等功能
"""

import tempfile
from pathlib import Path

import pytest

from src.claude.claude_markdown_operations import ClaudeMarkdownOperations
from src.claude.models import (
    AgentInfo,
    ClaudeMemoryInfo,
    CommandInfo,
    ConfigScope,
    FileType,
    MarkdownContentDTO,
    SkillFileNotFoundError,
    SkillInfo,
    SkillNotFoundError,
    SkillOperationError,
    SkillPathTraversalError,
)


class TestClaudeMarkdownOperations:
    """测试 ClaudeMarkdownOperations 类"""

    @pytest.fixture
    def temp_project_dir(self):
        """创建临时项目目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            # 创建 .claude 目录结构
            (project_path / ".claude" / "commands").mkdir(parents=True, exist_ok=True)
            (project_path / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
            (project_path / ".claude" / "skills").mkdir(parents=True, exist_ok=True)
            yield project_path

    @pytest.fixture
    def temp_user_home(self):
        """创建临时用户主目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_home = Path(tmpdir)
            # 创建 .claude 目录结构
            (user_home / ".claude" / "commands").mkdir(parents=True, exist_ok=True)
            (user_home / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
            (user_home / ".claude" / "CLAUDE.md").parent.mkdir(
                parents=True, exist_ok=True
            )
            yield user_home

    @pytest.fixture
    def markdown_ops(self, temp_project_dir, temp_user_home):
        """创建 ClaudeMarkdownOperations 实例"""
        return ClaudeMarkdownOperations(temp_project_dir, temp_user_home)

    # ========== 测试 load_markdown_content ==========

    @pytest.mark.asyncio
    async def test_load_memory_project_claude_md(self, markdown_ops, temp_project_dir):
        """测试加载项目根目录的 CLAUDE.md"""
        content = "# Test Project\n\nThis is a test project."
        (temp_project_dir / "CLAUDE.md").write_text(content, encoding="utf-8")

        result = await markdown_ops.load_markdown_content("memory", "project_claude_md")

        assert isinstance(result, MarkdownContentDTO)
        assert result.content == content
        assert result.md5 is not None
        assert len(result.md5) == 32  # MD5 hash length

    @pytest.mark.asyncio
    async def test_load_memory_claude_dir_claude_md(
        self, markdown_ops, temp_project_dir
    ):
        """测试加载 .claude 目录下的 CLAUDE.md"""
        content = "# Claude Dir Config"
        (temp_project_dir / ".claude" / "CLAUDE.md").write_text(
            content, encoding="utf-8"
        )

        result = await markdown_ops.load_markdown_content(
            "memory", "claude_dir_claude_md"
        )

        assert result.content == content

    @pytest.mark.asyncio
    async def test_load_memory_local_claude_md(self, markdown_ops, temp_project_dir):
        """测试加载 CLAUDE.local.md"""
        content = "# Local Config"
        (temp_project_dir / "CLAUDE.local.md").write_text(content, encoding="utf-8")

        result = await markdown_ops.load_markdown_content("memory", "local_claude_md")

        assert result.content == content

    @pytest.mark.asyncio
    async def test_load_memory_user_global_claude_md(
        self, markdown_ops, temp_user_home
    ):
        """测试加载用户全局的 CLAUDE.md"""
        content = "# Global Config"
        (temp_user_home / ".claude" / "CLAUDE.md").write_text(content, encoding="utf-8")

        result = await markdown_ops.load_markdown_content(
            "memory", "user_global_claude_md"
        )

        assert result.content == content

    @pytest.mark.asyncio
    async def test_load_nonexistent_file_returns_empty(self, markdown_ops):
        """测试加载不存在的文件返回空内容"""
        result = await markdown_ops.load_markdown_content("memory", "project_claude_md")

        assert result.content == ""
        assert result.md5 == "d41d8cd98f00b204e9800998ecf8427e"  # MD5 of empty string

    @pytest.mark.asyncio
    async def test_load_command_with_nested_path(self, markdown_ops, temp_project_dir):
        """测试加载嵌套路径的 command"""
        content = "# Test Command"
        command_dir = temp_project_dir / ".claude" / "commands" / "features" / "value"
        command_dir.mkdir(parents=True, exist_ok=True)
        (command_dir / "test.md").write_text(content, encoding="utf-8")

        result = await markdown_ops.load_markdown_content(
            "command", "features:value:test", scope=ConfigScope.project
        )

        assert result.content == content

    @pytest.mark.asyncio
    async def test_load_agent_project_scope(self, markdown_ops, temp_project_dir):
        """测试加载 project scope 的 agent"""
        content = "# Test Agent"
        (temp_project_dir / ".claude" / "agents" / "test-agent.md").write_text(
            content, encoding="utf-8"
        )

        result = await markdown_ops.load_markdown_content(
            "agent", "test-agent", scope=ConfigScope.project
        )

        assert result.content == content

    @pytest.mark.asyncio
    async def test_load_agent_user_scope(self, markdown_ops, temp_user_home):
        """测试加载 user scope 的 agent"""
        content = "# User Agent"
        (temp_user_home / ".claude" / "agents" / "user-agent.md").write_text(
            content, encoding="utf-8"
        )

        result = await markdown_ops.load_markdown_content(
            "agent", "user-agent", scope=ConfigScope.user
        )

        assert result.content == content

    @pytest.mark.asyncio
    async def test_load_skill(self, markdown_ops, temp_project_dir):
        """测试加载 skill"""
        content = "# Test Skill"
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

        result = await markdown_ops.load_markdown_content(
            "skill", "test-skill", scope=ConfigScope.project
        )

        assert result.content == content

    @pytest.mark.asyncio
    async def test_load_invalid_content_type_raises_error(self, markdown_ops):
        """测试加载无效的 content_type 抛出异常"""
        with pytest.raises(ValueError, match="不支持的 content_type"):
            await markdown_ops.load_markdown_content("invalid", "test")

    # ========== 测试 update_markdown_content ==========

    @pytest.mark.asyncio
    async def test_update_markdown_content_success(
        self, markdown_ops, temp_project_dir
    ):
        """测试成功更新 Markdown 内容"""
        # 先创建文件
        original_content = "# Original"
        (temp_project_dir / "CLAUDE.md").write_text(original_content, encoding="utf-8")

        # 获取 MD5
        original_result = await markdown_ops.load_markdown_content(
            "memory", "project_claude_md"
        )

        # 更新内容
        new_content = "# Updated Content"
        await markdown_ops.update_markdown_content(
            "memory",
            "project_claude_md",
            from_md5=original_result.md5,
            content=new_content,
            scope=ConfigScope.project,
        )

        # 验证更新
        result = await markdown_ops.load_markdown_content("memory", "project_claude_md")
        assert result.content == new_content

    @pytest.mark.asyncio
    async def test_update_markdown_content_with_md5_mismatch(
        self, markdown_ops, temp_project_dir
    ):
        """测试 MD5 不匹配时抛出异常"""
        (temp_project_dir / "CLAUDE.md").write_text("Original", encoding="utf-8")

        with pytest.raises(ValueError, match="文件已变化"):
            await markdown_ops.update_markdown_content(
                "memory",
                "project_claude_md",
                from_md5="wrong_md5",
                content="New content",
                scope=ConfigScope.project,
            )

    @pytest.mark.asyncio
    async def test_update_markdown_content_creates_directory(
        self, markdown_ops, temp_project_dir
    ):
        """测试更新时自动创建目录"""
        await markdown_ops.update_markdown_content(
            "command", "features:test", content="# Test", scope=ConfigScope.project
        )

        command_file = (
            temp_project_dir / ".claude" / "commands" / "features" / "test.md"
        )
        assert command_file.exists()
        assert command_file.read_text(encoding="utf-8") == "# Test"

    @pytest.mark.asyncio
    async def test_update_markdown_content_same_content_no_change(
        self, markdown_ops, temp_project_dir
    ):
        """测试更新相同内容时不修改文件"""
        original_content = "# Test"
        (temp_project_dir / "CLAUDE.md").write_text(original_content, encoding="utf-8")

        original_result = await markdown_ops.load_markdown_content(
            "memory", "project_claude_md"
        )
        original_stat = (temp_project_dir / "CLAUDE.md").stat()

        # 更新相同内容
        await markdown_ops.update_markdown_content(
            "memory",
            "project_claude_md",
            from_md5=original_result.md5,
            content=original_content,
            scope=ConfigScope.project,
        )

        # 验证文件未修改（mtime 应该相同）
        new_stat = (temp_project_dir / "CLAUDE.md").stat()
        assert original_stat.st_mtime == new_stat.st_mtime

    # ========== 测试 save_markdown_content ==========

    @pytest.mark.asyncio
    async def test_save_markdown_content_new_file(self, markdown_ops, temp_project_dir):
        """测试保存新的 Markdown 内容"""
        content = "# New Command"
        result = await markdown_ops.save_markdown_content(
            "command", "test-command", content=content, scope=ConfigScope.project
        )

        assert isinstance(result, MarkdownContentDTO)
        assert result.content == content

        # 验证文件已创建
        command_file = temp_project_dir / ".claude" / "commands" / "test-command.md"
        assert command_file.exists()
        assert command_file.read_text(encoding="utf-8") == content

    @pytest.mark.asyncio
    async def test_save_markdown_content_file_exists_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试保存已存在的文件抛出异常"""
        # 先创建文件
        (temp_project_dir / ".claude" / "commands" / "test.md").write_text(
            "Existing", encoding="utf-8"
        )

        with pytest.raises(ValueError, match="已存在"):
            await markdown_ops.save_markdown_content(
                "command", "test", content="New", scope=ConfigScope.project
            )

    @pytest.mark.asyncio
    async def test_save_skill_creates_directory(self, markdown_ops, temp_project_dir):
        """测试保存 skill 时创建目录结构"""
        content = "# Test Skill"
        await markdown_ops.save_markdown_content(
            "skill", "test-skill", content=content, scope=ConfigScope.project
        )

        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_file = skill_dir / "SKILL.md"
        assert skill_dir.exists()
        assert skill_file.exists()
        assert skill_file.read_text(encoding="utf-8") == content

    # ========== 测试 rename_markdown_content ==========

    @pytest.mark.asyncio
    async def test_rename_command_success(self, markdown_ops, temp_project_dir):
        """测试成功重命名 command"""
        # 创建原始文件
        (temp_project_dir / ".claude" / "commands" / "old.md").write_text(
            "# Old", encoding="utf-8"
        )

        await markdown_ops.rename_markdown_content(
            "command", "old", "new", scope=ConfigScope.project
        )

        # 验证重命名
        old_file = temp_project_dir / ".claude" / "commands" / "old.md"
        new_file = temp_project_dir / ".claude" / "commands" / "new.md"
        assert not old_file.exists()
        assert new_file.exists()

    @pytest.mark.asyncio
    async def test_rename_agent_with_scope_change(
        self, markdown_ops, temp_project_dir, temp_user_home
    ):
        """测试重命名 agent 并更改作用域"""
        # 在 project scope 创建 agent
        (temp_project_dir / ".claude" / "agents" / "test.md").write_text(
            "# Test", encoding="utf-8"
        )

        await markdown_ops.rename_markdown_content(
            "agent",
            "test",
            "renamed",
            scope=ConfigScope.project,
            new_scope=ConfigScope.user,
        )

        # 验证文件已移动
        old_file = temp_project_dir / ".claude" / "agents" / "test.md"
        new_file = temp_user_home / ".claude" / "agents" / "renamed.md"
        assert not old_file.exists()
        assert new_file.exists()

    @pytest.mark.asyncio
    async def test_rename_skill_moves_directory(self, markdown_ops, temp_project_dir):
        """测试重命名 skill 会移动整个目录"""
        # 创建 skill 目录
        skill_dir = temp_project_dir / ".claude" / "skills" / "old-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")
        (skill_dir / "extra.txt").write_text("Extra file", encoding="utf-8")

        await markdown_ops.rename_markdown_content(
            "skill", "old-skill", "new-skill", scope=ConfigScope.project
        )

        # 验证目录已移动
        old_dir = temp_project_dir / ".claude" / "skills" / "old-skill"
        new_dir = temp_project_dir / ".claude" / "skills" / "new-skill"

        assert not old_dir.exists()
        assert (new_dir / "SKILL.md").exists()

    @pytest.mark.asyncio
    async def test_rename_nonexistent_file_raises_error(self, markdown_ops):
        """测试重命名不存在的文件抛出异常"""
        with pytest.raises(ValueError, match="不存在"):
            await markdown_ops.rename_markdown_content(
                "command", "nonexistent", "new", scope=ConfigScope.project
            )

    @pytest.mark.asyncio
    async def test_rename_to_existing_name_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试重命名到已存在的名称抛出异常"""
        # 创建两个文件
        (temp_project_dir / ".claude" / "commands" / "old.md").write_text(
            "# Old", encoding="utf-8"
        )
        (temp_project_dir / ".claude" / "commands" / "new.md").write_text(
            "# New", encoding="utf-8"
        )

        with pytest.raises(ValueError, match="已存在"):
            await markdown_ops.rename_markdown_content(
                "command", "old", "new", scope=ConfigScope.project
            )

    @pytest.mark.asyncio
    async def test_rename_updates_name_in_frontmatter(
        self, markdown_ops, temp_project_dir
    ):
        """测试重命名时会更新文件内容中的 name 字段"""
        # 创建包含 frontmatter 的文件
        original_content = """---
name: old-command
description: Original description
---
# Command Content"""
        (temp_project_dir / ".claude" / "commands" / "old.md").write_text(
            original_content, encoding="utf-8"
        )

        # 重命名
        await markdown_ops.rename_markdown_content(
            "command", "old", "new", scope=ConfigScope.project
        )

        # 验证文件已移动
        new_file = temp_project_dir / ".claude" / "commands" / "new.md"
        assert new_file.exists()

        # 验证 name 字段已更新
        updated_content = new_file.read_text(encoding="utf-8")
        assert "name: new" in updated_content
        assert "name: old-command" not in updated_content
        assert "Original description" in updated_content  # 其他内容保持不变
        assert "# Command Content" in updated_content

    @pytest.mark.asyncio
    async def test_rename_with_colon_in_name_extracts_last_part(
        self, markdown_ops, temp_project_dir
    ):
        """测试当名称包含冒号时，只保存冒号后的最后一部分到 frontmatter"""
        # 创建包含 frontmatter 的文件
        original_content = """---
name: old-name
description: Test
---
# Content"""
        (temp_project_dir / ".claude" / "commands" / "test.md").write_text(
            original_content, encoding="utf-8"
        )

        # 重命名为带冒号的名称（模拟 plugin 作用域）
        # 冒号会被转换为路径分隔符: my-plugin:new-name -> my-plugin/new-name.md
        await markdown_ops.rename_markdown_content(
            "command", "test", "my-plugin:new-name", scope=ConfigScope.project
        )

        # 验证文件已移动到嵌套目录
        new_file = (
            temp_project_dir / ".claude" / "commands" / "my-plugin" / "new-name.md"
        )
        assert new_file.exists()

        # 验证 name 字段只包含冒号后的最后一部分
        updated_content = new_file.read_text(encoding="utf-8")
        assert "name: new-name" in updated_content  # 只有冒号后的部分
        assert "name: my-plugin:new-name" not in updated_content  # 不包含完整名称

    @pytest.mark.asyncio
    async def test_rename_with_same_name_skips_update(
        self, markdown_ops, temp_project_dir
    ):
        """测试当新旧名称相同时，跳过 name 字段更新"""
        # 创建文件（只有作用域变化，名称不变）
        original_content = """---
name: test
description: Test description
---
# Content"""
        (temp_project_dir / ".claude" / "commands" / "test.md").write_text(
            original_content, encoding="utf-8"
        )

        # 使用不同的用户主目录
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            user_home = Path(tmpdir)
            (user_home / ".claude" / "commands").mkdir(parents=True, exist_ok=True)

            markdown_ops_with_user_home = ClaudeMarkdownOperations(
                temp_project_dir, user_home=user_home
            )

            # 重命名（名称相同，只是移动到 user 作用域）
            await markdown_ops_with_user_home.rename_markdown_content(
                "command",
                "test",
                "test",  # 名称相同
                scope=ConfigScope.project,
                new_scope=ConfigScope.user,
            )

            # 验证文件已移动
            new_file = user_home / ".claude" / "commands" / "test.md"
            assert new_file.exists()

            # 验证内容未被修改（因为名称相同）
            updated_content = new_file.read_text(encoding="utf-8")
            assert updated_content == original_content

    # ========== 测试 delete_markdown_content ==========

    @pytest.mark.asyncio
    async def test_delete_command_success(self, markdown_ops, temp_project_dir):
        """测试成功删除 command"""
        (temp_project_dir / ".claude" / "commands" / "test.md").write_text(
            "# Test", encoding="utf-8"
        )

        await markdown_ops.delete_markdown_content(
            "command", "test", scope=ConfigScope.project
        )

        command_file = temp_project_dir / ".claude" / "commands" / "test.md"
        assert not command_file.exists()

    @pytest.mark.asyncio
    async def test_delete_skill_removes_directory(self, markdown_ops, temp_project_dir):
        """测试删除 skill 会移除整个目录"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")
        (skill_dir / "extra.txt").write_text("Extra", encoding="utf-8")

        await markdown_ops.delete_markdown_content(
            "skill", "test-skill", scope=ConfigScope.project
        )

        # 验证整个目录被删除
        assert not skill_dir.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file_raises_error(self, markdown_ops):
        """测试删除不存在的文件抛出异常"""
        with pytest.raises(ValueError, match="不存在"):
            await markdown_ops.delete_markdown_content(
                "command", "nonexistent", scope=ConfigScope.project
            )

    # ========== 测试 scan_memory ==========

    @pytest.mark.asyncio
    async def test_scan_memory_all_files_exist(
        self, markdown_ops, temp_project_dir, temp_user_home
    ):
        """测试扫描所有存在的 memory 文件"""
        # 创建所有 memory 文件
        (temp_project_dir / "CLAUDE.md").write_text("# Project", encoding="utf-8")
        (temp_project_dir / ".claude" / "CLAUDE.md").write_text(
            "# Claude Dir", encoding="utf-8"
        )
        (temp_project_dir / "CLAUDE.local.md").write_text("# Local", encoding="utf-8")
        (temp_user_home / ".claude" / "CLAUDE.md").write_text(
            "# Global", encoding="utf-8"
        )

        result = await markdown_ops.scan_memory()

        assert isinstance(result, ClaudeMemoryInfo)
        assert result.project_claude_md is True
        assert result.claude_dir_claude_md is True
        assert result.local_claude_md is True
        assert result.user_global_claude_md is True

    @pytest.mark.asyncio
    async def test_scan_memory_no_files_exist(self, markdown_ops):
        """测试扫描不存在的 memory 文件"""
        result = await markdown_ops.scan_memory()

        assert result.project_claude_md is False
        assert result.claude_dir_claude_md is False
        assert result.local_claude_md is False
        assert result.user_global_claude_md is False

    # ========== 测试 scan_agents ==========

    @pytest.mark.asyncio
    async def test_scan_agents_project_scope(self, markdown_ops, temp_project_dir):
        """测试扫描 project scope 的 agents"""
        # 创建 agents
        agents_dir = temp_project_dir / ".claude" / "agents"
        (agents_dir / "agent1.md").write_text("# Agent 1", encoding="utf-8")
        (agents_dir / "agent2.md").write_text("# Agent 2", encoding="utf-8")

        result = await markdown_ops.scan_agents()

        assert len(result) == 2
        assert all(isinstance(agent, AgentInfo) for agent in result)
        assert all(agent.scope == ConfigScope.project for agent in result)
        agent_names = {agent.name for agent in result}
        assert agent_names == {"agent1", "agent2"}

    @pytest.mark.asyncio
    async def test_scan_agents_user_scope(self, markdown_ops, temp_user_home):
        """测试扫描 user scope 的 agents"""
        agents_dir = temp_user_home / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "user-agent.md").write_text("# User", encoding="utf-8")

        result = await markdown_ops.scan_agents()

        assert len(result) == 1
        assert result[0].scope == ConfigScope.user
        assert result[0].name == "user-agent"

    @pytest.mark.asyncio
    async def test_scan_agents_mixed_scopes(
        self, markdown_ops, temp_project_dir, temp_user_home
    ):
        """测试扫描混合作用域的 agents"""
        # Project agents
        (temp_project_dir / ".claude" / "agents" / "project-agent.md").write_text(
            "# Project", encoding="utf-8"
        )

        # User agents
        (temp_user_home / ".claude" / "agents" / "user-agent.md").write_text(
            "# User", encoding="utf-8"
        )

        result = await markdown_ops.scan_agents()

        assert len(result) == 2
        scopes = {agent.scope for agent in result}
        assert scopes == {ConfigScope.project, ConfigScope.user}

    @pytest.mark.asyncio
    async def test_scan_agents_with_description(self, markdown_ops, temp_project_dir):
        """测试扫描带描述的 agents"""
        agent_content = """---
description: A test agent for testing
---

# Test Agent

This is a test agent.
"""
        (temp_project_dir / ".claude" / "agents" / "test-agent.md").write_text(
            agent_content, encoding="utf-8"
        )

        result = await markdown_ops.scan_agents()

        assert len(result) == 1
        assert result[0].description == "A test agent for testing"

    # ========== 测试 scan_commands ==========

    @pytest.mark.asyncio
    async def test_scan_commands_simple(self, markdown_ops, temp_project_dir):
        """测试扫描简单的 commands"""
        (temp_project_dir / ".claude" / "commands" / "test.md").write_text(
            "# Test", encoding="utf-8"
        )

        result = await markdown_ops.scan_commands()

        assert len(result) == 1
        assert isinstance(result[0], CommandInfo)
        assert result[0].name == "test"
        assert result[0].scope == ConfigScope.project

    @pytest.mark.asyncio
    async def test_scan_commands_nested_path(self, markdown_ops, temp_project_dir):
        """测试扫描嵌套路径的 commands"""
        nested_dir = temp_project_dir / ".claude" / "commands" / "features" / "value"
        nested_dir.mkdir(parents=True, exist_ok=True)
        (nested_dir / "test.md").write_text("# Test", encoding="utf-8")

        result = await markdown_ops.scan_commands()

        assert len(result) == 1
        assert result[0].name == "features:value:test"

    @pytest.mark.asyncio
    async def test_scan_commands_with_description(self, markdown_ops, temp_project_dir):
        """测试扫描带描述的 commands"""
        command_content = """---
description: Test command description
---

# Test Command
"""
        (temp_project_dir / ".claude" / "commands" / "test.md").write_text(
            command_content, encoding="utf-8"
        )

        result = await markdown_ops.scan_commands()

        assert len(result) == 1
        assert result[0].description == "Test command description"

    @pytest.mark.asyncio
    async def test_scan_commands_multiple_scopes(
        self, markdown_ops, temp_project_dir, temp_user_home
    ):
        """测试扫描多个作用域的 commands"""
        # Project commands
        (temp_project_dir / ".claude" / "commands" / "project-cmd.md").write_text(
            "# Project", encoding="utf-8"
        )

        # User commands
        user_dir = temp_user_home / ".claude" / "commands"
        user_dir.mkdir(parents=True, exist_ok=True)
        (user_dir / "user-cmd.md").write_text("# User", encoding="utf-8")

        result = await markdown_ops.scan_commands()

        assert len(result) == 2
        scopes = {cmd.scope for cmd in result}
        assert scopes == {ConfigScope.project, ConfigScope.user}

    # ========== 测试 scan_skills ==========

    @pytest.mark.asyncio
    async def test_scan_skills_simple(self, markdown_ops, temp_project_dir):
        """测试扫描简单的 skills"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

        result = await markdown_ops.scan_skills()

        assert len(result) == 1
        assert isinstance(result[0], SkillInfo)
        assert result[0].name == "test-skill"
        assert result[0].scope == ConfigScope.project

    @pytest.mark.asyncio
    async def test_scan_skills_multiple(self, markdown_ops, temp_project_dir):
        """测试扫描多个 skills"""
        for skill_name in ["skill1", "skill2", "skill3"]:
            skill_dir = temp_project_dir / ".claude" / "skills" / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(f"# {skill_name}", encoding="utf-8")

        result = await markdown_ops.scan_skills()

        assert len(result) == 3
        skill_names = {skill.name for skill in result}
        assert skill_names == {"skill1", "skill2", "skill3"}

    @pytest.mark.asyncio
    async def test_scan_skills_with_description(self, markdown_ops, temp_project_dir):
        """测试扫描带描述的 skills"""
        skill_content = """---
description: A test skill for testing
---

# Test Skill
"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

        result = await markdown_ops.scan_skills()

        assert len(result) == 1
        assert result[0].description == "A test skill for testing"

    @pytest.mark.asyncio
    async def test_scan_skills_ignores_non_skill_dirs(
        self, markdown_ops, temp_project_dir
    ):
        """测试扫描 skills 时忽略非 skill 目录"""
        skills_dir = temp_project_dir / ".claude" / "skills"
        # 创建 skill 目录
        skill_dir = skills_dir / "valid-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Valid", encoding="utf-8")

        # 创建非 skill 的文件
        (skills_dir / "readme.txt").write_text("Readme", encoding="utf-8")
        # 创建没有 SKILL.md 的目录
        empty_dir = skills_dir / "empty-skill"
        empty_dir.mkdir(parents=True, exist_ok=True)

        result = await markdown_ops.scan_skills()

        assert len(result) == 1
        assert result[0].name == "valid-skill"

    # ========== 测试 list_skill_content ==========

    @pytest.mark.asyncio
    async def test_list_skill_content_simple(self, markdown_ops, temp_project_dir):
        """测试列出简单 skill 的文件树"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

        result = await markdown_ops.list_skill_content("test-skill")

        assert len(result) == 1
        assert result[0].name == "SKILL.md"
        assert result[0].type == "file"
        assert result[0].path == "SKILL.md"
        assert result[0].size == 12  # "# Test Skill" 的字节数

    @pytest.mark.asyncio
    async def test_list_skill_content_with_nested_structure(
        self, markdown_ops, temp_project_dir
    ):
        """测试列出包含嵌套结构的 skill 文件树"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        # 创建嵌套目录和文件
        lib_dir = skill_dir / "lib"
        lib_dir.mkdir(parents=True, exist_ok=True)
        (lib_dir / "helper.py").write_text("def helper(): pass", encoding="utf-8")

        docs_dir = skill_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "guide.md").write_text("# Guide", encoding="utf-8")

        result = await markdown_ops.list_skill_content("test-skill")

        # 应该有 3 个节点：SKILL.md, lib (目录), docs (目录)
        # 目录优先，然后按名称排序
        assert len(result) == 3
        [node.name for node in result]

        # 目录应该在前面
        assert result[0].type == "directory"
        assert result[1].type == "directory"
        assert result[2].type == "file"

    @pytest.mark.asyncio
    async def test_list_skill_content_directories_before_files(
        self, markdown_ops, temp_project_dir
    ):
        """测试目录优先于文件排序"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)

        # 创建混合的文件和目录
        (skill_dir / "a.txt").write_text("A", encoding="utf-8")
        (skill_dir / "z.txt").write_text("Z", encoding="utf-8")

        dir_b = skill_dir / "b-dir"
        dir_b.mkdir(parents=True, exist_ok=True)
        (dir_b / "file.txt").write_text("B", encoding="utf-8")

        dir_m = skill_dir / "m-dir"
        dir_m.mkdir(parents=True, exist_ok=True)
        (dir_m / "file.txt").write_text("M", encoding="utf-8")

        result = await markdown_ops.list_skill_content("test-skill")

        # 目录应该在前，按名称排序：b-dir, m-dir, a.txt, z.txt
        assert len(result) == 4
        assert result[0].type == "directory"
        assert result[0].name == "b-dir"
        assert result[1].type == "directory"
        assert result[1].name == "m-dir"
        assert result[2].type == "file"
        assert result[2].name == "a.txt"
        assert result[3].type == "file"
        assert result[3].name == "z.txt"

    @pytest.mark.asyncio
    async def test_list_skill_content_ignores_hidden_files(
        self, markdown_ops, temp_project_dir
    ):
        """测试忽略隐藏文件"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")
        (skill_dir / ".hidden.txt").write_text("Hidden", encoding="utf-8")

        hidden_dir = skill_dir / ".hidden_dir"
        hidden_dir.mkdir(parents=True, exist_ok=True)
        (hidden_dir / "file.txt").write_text("File", encoding="utf-8")

        result = await markdown_ops.list_skill_content("test-skill")

        # 只应该返回 SKILL.md，不应该包含隐藏文件
        assert len(result) == 1
        assert result[0].name == "SKILL.md"
        assert all(".hidden" not in node.name for node in result)

    @pytest.mark.asyncio
    async def test_list_skill_content_nonexistent_skill_raises_error(
        self, markdown_ops
    ):
        """测试列出不存在的 skill 抛出异常"""
        with pytest.raises(SkillNotFoundError, match="不存在"):
            await markdown_ops.list_skill_content("nonexistent-skill")

    @pytest.mark.asyncio
    async def test_list_skill_content_plugin_scope_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试 plugin 作用域抛出异常（plugin_ops 未初始化时抛出 ValueError）"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        # plugin_ops 未初始化时会抛出 ValueError
        with pytest.raises(ValueError, match="plugin_ops 未初始化"):
            await markdown_ops.list_skill_content(
                "test-skill", scope=ConfigScope.plugin
            )

    # ========== 测试 read_skill_file_content ==========

    @pytest.mark.asyncio
    async def test_read_skill_file_content_success(
        self, markdown_ops, temp_project_dir
    ):
        """测试成功读取文件内容"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "# Test Skill\n\nContent here", encoding="utf-8"
        )

        result = await markdown_ops.read_skill_file_content("test-skill", "SKILL.md")

        assert result == "# Test Skill\n\nContent here"

    @pytest.mark.asyncio
    async def test_read_skill_file_content_nested_path(
        self, markdown_ops, temp_project_dir
    ):
        """测试读取嵌套路径的文件"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)

        lib_dir = skill_dir / "lib"
        lib_dir.mkdir(parents=True, exist_ok=True)
        (lib_dir / "helper.py").write_text("def helper():\n    pass", encoding="utf-8")

        result = await markdown_ops.read_skill_file_content(
            "test-skill", "lib/helper.py"
        )

        assert result == "def helper():\n    pass"

    @pytest.mark.asyncio
    async def test_read_skill_file_content_nonexistent_skill_raises_error(
        self, markdown_ops
    ):
        """测试读取不存在的 skill 抛出异常"""
        with pytest.raises(SkillNotFoundError, match="不存在"):
            await markdown_ops.read_skill_file_content("nonexistent-skill", "SKILL.md")

    @pytest.mark.asyncio
    async def test_read_skill_file_content_nonexistent_file_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试读取不存在的文件抛出异常"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        with pytest.raises(SkillFileNotFoundError, match="不存在"):
            await markdown_ops.read_skill_file_content("test-skill", "nonexistent.md")

    @pytest.mark.asyncio
    async def test_read_skill_file_content_path_traversal_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试路径遍历攻击被阻止"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        # 尝试路径遍历攻击
        with pytest.raises(SkillPathTraversalError, match="超出了 skill 目录范围"):
            await markdown_ops.read_skill_file_content("test-skill", "../SKILL.md")

    @pytest.mark.asyncio
    async def test_read_skill_file_content_symlink_attack_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试符号链接攻击被阻止"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        # 在项目根目录创建一个敏感文件
        sensitive_file = temp_project_dir / "sensitive.txt"
        sensitive_file.write_text("Secret data", encoding="utf-8")

        # 在 skill 目录中创建指向项目根目录的符号链接
        link_dir = skill_dir / "link_to_parent"
        try:
            link_dir.symlink_to(temp_project_dir)
        except OSError:
            # Windows 可能需要管理员权限创建符号链接，跳过此测试
            pytest.skip("需要管理员权限创建符号链接")

        # 尝试通过符号链接读取敏感文件
        with pytest.raises(SkillPathTraversalError, match="超出了 skill 目录范围"):
            await markdown_ops.read_skill_file_content(
                "test-skill", "link_to_parent/sensitive.txt"
            )

        # 验证敏感文件没有被读取
        assert sensitive_file.read_text(encoding="utf-8") == "Secret data"

    @pytest.mark.asyncio
    async def test_read_skill_file_content_with_utf8_encoding(
        self, markdown_ops, temp_project_dir
    ):
        """测试读取 UTF-8 编码的文件"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)

        # 包含中文和 emoji 的内容
        content = "# 测试 Skill\n\n这是一个测试文件，包含中文和 emoji: 🚀"
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

        result = await markdown_ops.read_skill_file_content("test-skill", "SKILL.md")

        assert result == content

    # ========== 测试 update_skill_file_content ==========

    @pytest.mark.asyncio
    async def test_update_skill_file_content_success(
        self, markdown_ops, temp_project_dir
    ):
        """测试成功更新文件内容"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Original", encoding="utf-8")

        new_content = "# Updated Content\n\nNew content here"
        await markdown_ops.update_skill_file_content(
            "test-skill", "SKILL.md", new_content
        )

        # 验证更新
        result = await markdown_ops.read_skill_file_content("test-skill", "SKILL.md")
        assert result == new_content

    @pytest.mark.asyncio
    async def test_update_skill_file_content_creates_directory(
        self, markdown_ops, temp_project_dir
    ):
        """测试更新时自动创建目录"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)

        # 更新不存在的文件（在子目录中）
        content = "# New File"
        await markdown_ops.update_skill_file_content(
            "test-skill", "lib/helper.py", content
        )

        # 验证文件已创建
        lib_dir = skill_dir / "lib"
        assert lib_dir.exists()
        assert (lib_dir / "helper.py").exists()
        assert (lib_dir / "helper.py").read_text(encoding="utf-8") == content

    @pytest.mark.asyncio
    async def test_update_skill_file_content_nonexistent_skill_raises_error(
        self, markdown_ops
    ):
        """测试更新不存在的 skill 抛出异常"""
        with pytest.raises(SkillOperationError, match="不存在"):
            await markdown_ops.update_skill_file_content(
                "nonexistent-skill", "SKILL.md", "content"
            )

    @pytest.mark.asyncio
    async def test_update_skill_file_content_path_traversal_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试路径遍历攻击被阻止"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        # 尝试路径遍历攻击
        with pytest.raises(SkillPathTraversalError, match="超出了 skill 目录范围"):
            await markdown_ops.update_skill_file_content(
                "test-skill", "../SKILL.md", "content"
            )

    @pytest.mark.asyncio
    async def test_update_skill_file_content_plugin_scope_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试 plugin 作用域抛出异常（不允许修改）"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        with pytest.raises(SkillOperationError, match="不允许修改插件作用域"):
            await markdown_ops.update_skill_file_content(
                "test-skill", "SKILL.md", "content", scope=ConfigScope.plugin
            )

    # ========== 测试 delete_skill_file ==========

    @pytest.mark.asyncio
    async def test_delete_skill_file_success(self, markdown_ops, temp_project_dir):
        """测试成功删除文件"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "extra.txt").write_text("Extra", encoding="utf-8")

        await markdown_ops.delete_skill_file("test-skill", "extra.txt")

        # 验证文件已删除
        assert not (skill_dir / "extra.txt").exists()

    @pytest.mark.asyncio
    async def test_delete_skill_file_directory_success(
        self, markdown_ops, temp_project_dir
    ):
        """测试成功删除目录"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)

        lib_dir = skill_dir / "lib"
        lib_dir.mkdir(parents=True, exist_ok=True)
        (lib_dir / "helper.py").write_text("Helper", encoding="utf-8")
        (lib_dir / "utils.py").write_text("Utils", encoding="utf-8")

        await markdown_ops.delete_skill_file("test-skill", "lib")

        # 验证目录已删除
        assert not lib_dir.exists()

    @pytest.mark.asyncio
    async def test_delete_skill_file_nonexistent_skill_raises_error(self, markdown_ops):
        """测试删除不存在的 skill 抛出异常"""
        with pytest.raises(SkillOperationError, match="不存在"):
            await markdown_ops.delete_skill_file("nonexistent-skill", "SKILL.md")

    @pytest.mark.asyncio
    async def test_delete_skill_file_nonexistent_file_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试删除不存在的文件抛出异常"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        with pytest.raises(SkillFileNotFoundError, match="不存在"):
            await markdown_ops.delete_skill_file("test-skill", "nonexistent.md")

    @pytest.mark.asyncio
    async def test_delete_skill_file_path_traversal_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试路径遍历攻击被阻止"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "extra.txt").write_text("Extra", encoding="utf-8")

        # 尝试路径遍历攻击
        with pytest.raises(SkillPathTraversalError, match="超出了 skill 目录范围"):
            await markdown_ops.delete_skill_file("test-skill", "../extra.txt")

        # 验证原文件仍然存在
        assert (skill_dir / "extra.txt").exists()

    @pytest.mark.asyncio
    async def test_delete_skill_file_plugin_scope_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试 plugin 作用域抛出异常（不允许删除）"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "extra.txt").write_text("Extra", encoding="utf-8")

        with pytest.raises(SkillOperationError, match="不允许删除插件作用域"):
            await markdown_ops.delete_skill_file(
                "test-skill", "extra.txt", scope=ConfigScope.plugin
            )

    # ========== 测试 create_skill_file ==========

    @pytest.mark.asyncio
    async def test_create_skill_file_success(self, markdown_ops, temp_project_dir):
        """测试成功创建文件"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        await markdown_ops.create_skill_file(
            "test-skill", "", "new_file.md", FileType.FILE
        )

        # 验证文件已创建
        assert (skill_dir / "new_file.md").exists()

    @pytest.mark.asyncio
    async def test_create_skill_directory_success(self, markdown_ops, temp_project_dir):
        """测试成功创建目录"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        await markdown_ops.create_skill_file(
            "test-skill", "", "new_dir", FileType.DIRECTORY
        )

        # 验证目录已创建
        assert (skill_dir / "new_dir").exists()
        assert (skill_dir / "new_dir").is_dir()

    @pytest.mark.asyncio
    async def test_create_skill_file_in_subdirectory(
        self, markdown_ops, temp_project_dir
    ):
        """测试在子目录中创建文件"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        # 先创建子目录
        lib_dir = skill_dir / "lib"
        lib_dir.mkdir(parents=True, exist_ok=True)

        # 在子目录中创建文件
        await markdown_ops.create_skill_file(
            "test-skill", "lib", "helper.py", FileType.FILE
        )

        # 验证文件已创建
        assert (lib_dir / "helper.py").exists()

    @pytest.mark.asyncio
    async def test_create_skill_file_nonexistent_skill_raises_error(self, markdown_ops):
        """测试在不存在的 skill 中创建文件抛出异常"""
        with pytest.raises(SkillOperationError, match="不存在"):
            await markdown_ops.create_skill_file(
                "nonexistent-skill", "", "new.md", FileType.FILE
            )

    @pytest.mark.asyncio
    async def test_create_skill_file_nonexistent_parent_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试在不存在的父目录中创建文件抛出异常"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        with pytest.raises(SkillOperationError, match="父目录.*不存在"):
            await markdown_ops.create_skill_file(
                "test-skill", "nonexistent_dir", "new.md", FileType.FILE
            )

    @pytest.mark.asyncio
    async def test_create_skill_file_already_exists_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试创建已存在的文件抛出异常"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")
        (skill_dir / "existing.md").write_text("Content", encoding="utf-8")

        with pytest.raises(SkillOperationError, match="已存在"):
            await markdown_ops.create_skill_file(
                "test-skill", "", "existing.md", FileType.FILE
            )

    @pytest.mark.asyncio
    async def test_create_skill_file_path_traversal_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试路径遍历攻击被阻止"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        # 尝试路径遍历攻击
        with pytest.raises(SkillPathTraversalError, match="超出了 skill 目录范围"):
            await markdown_ops.create_skill_file(
                "test-skill", "../", "new.md", FileType.FILE
            )

    @pytest.mark.asyncio
    async def test_create_skill_file_plugin_scope_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试 plugin 作用域抛出异常（不允许创建）"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        with pytest.raises(SkillOperationError, match="不允许在插件作用域创建内容"):
            await markdown_ops.create_skill_file(
                "test-skill", "", "new.md", FileType.FILE, scope=ConfigScope.plugin
            )

    # ========== 测试 move_skill_file ==========

    @pytest.mark.asyncio
    async def test_move_skill_file_success(self, markdown_ops, temp_project_dir):
        """测试成功移动文件"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")
        (skill_dir / "source.txt").write_text("Content", encoding="utf-8")

        # 创建目标目录
        target_dir = skill_dir / "target"
        target_dir.mkdir(parents=True, exist_ok=True)

        await markdown_ops.move_skill_file("test-skill", "source.txt", "target")

        # 验证文件已移动
        assert not (skill_dir / "source.txt").exists()
        assert (target_dir / "source.txt").exists()

    @pytest.mark.asyncio
    async def test_move_skill_directory_success(self, markdown_ops, temp_project_dir):
        """测试成功移动目录"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        # 创建源目录
        source_dir = skill_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "file.txt").write_text("Content", encoding="utf-8")

        # 创建目标目录
        target_dir = skill_dir / "target"
        target_dir.mkdir(parents=True, exist_ok=True)

        await markdown_ops.move_skill_file("test-skill", "source", "target")

        # 验证目录已移动
        assert not source_dir.exists()
        assert (target_dir / "source").exists()
        assert (target_dir / "source" / "file.txt").exists()

    @pytest.mark.asyncio
    async def test_move_skill_file_to_subdirectory_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试不能将目录移动到其子目录中"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        # 创建源目录和子目录
        source_dir = skill_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "subdir").mkdir(parents=True, exist_ok=True)

        with pytest.raises(
            SkillOperationError, match="不能将文件或文件夹移动到其子目录中"
        ):
            await markdown_ops.move_skill_file("test-skill", "source", "source/subdir")

    @pytest.mark.asyncio
    async def test_move_skill_file_nonexistent_source_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试移动不存在的文件抛出异常"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        with pytest.raises(SkillFileNotFoundError, match="不存在"):
            await markdown_ops.move_skill_file("test-skill", "nonexistent.txt", "")

    @pytest.mark.asyncio
    async def test_move_skill_file_nonexistent_target_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试移动到不存在的目标目录抛出异常"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")
        (skill_dir / "source.txt").write_text("Content", encoding="utf-8")

        with pytest.raises(SkillOperationError, match="目标文件夹.*不存在"):
            await markdown_ops.move_skill_file(
                "test-skill", "source.txt", "nonexistent_dir"
            )

    @pytest.mark.asyncio
    async def test_move_skill_file_target_not_directory_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试移动到非目录目标抛出异常"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")
        (skill_dir / "source.txt").write_text("Content", encoding="utf-8")
        (skill_dir / "target.txt").write_text("Target", encoding="utf-8")

        with pytest.raises(SkillOperationError, match="不是文件夹"):
            await markdown_ops.move_skill_file("test-skill", "source.txt", "target.txt")

    @pytest.mark.asyncio
    async def test_move_skill_file_name_conflict_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试移动到已存在同名文件的位置抛出异常"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        # 创建目标目录和同名文件
        target_dir = skill_dir / "target"
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "source.txt").write_text("Existing", encoding="utf-8")

        (skill_dir / "source.txt").write_text("Content", encoding="utf-8")

        with pytest.raises(SkillOperationError, match="已存在同名"):
            await markdown_ops.move_skill_file("test-skill", "source.txt", "target")

    @pytest.mark.asyncio
    async def test_move_skill_file_path_traversal_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试源路径遍历攻击被阻止"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        # 尝试路径遍历攻击
        with pytest.raises(SkillPathTraversalError, match="超出了 skill 目录范围"):
            await markdown_ops.move_skill_file("test-skill", "../source.txt", "")

    @pytest.mark.asyncio
    async def test_move_skill_file_plugin_scope_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试 plugin 作用域抛出异常（不允许移动）"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        with pytest.raises(SkillOperationError, match="不允许移动插件作用域"):
            await markdown_ops.move_skill_file(
                "test-skill", "source.txt", "", scope=ConfigScope.plugin
            )

    # ========== 测试 rename_skill_file ==========

    @pytest.mark.asyncio
    async def test_rename_skill_file_success(self, markdown_ops, temp_project_dir):
        """测试成功重命名文件"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "old_name.txt").write_text("Content", encoding="utf-8")

        await markdown_ops.rename_skill_file(
            "test-skill", "old_name.txt", "new_name.txt"
        )

        # 验证文件已重命名
        assert not (skill_dir / "old_name.txt").exists()
        assert (skill_dir / "new_name.txt").exists()

    @pytest.mark.asyncio
    async def test_rename_skill_directory_success(self, markdown_ops, temp_project_dir):
        """测试成功重命名目录"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        lib_dir = skill_dir / "lib"
        lib_dir.mkdir(parents=True, exist_ok=True)
        (lib_dir / "helper.py").write_text("Helper", encoding="utf-8")

        await markdown_ops.rename_skill_file("test-skill", "lib", "utils")

        # 验证目录已重命名
        assert not lib_dir.exists()
        assert (skill_dir / "utils").exists()
        assert (skill_dir / "utils" / "helper.py").exists()

    @pytest.mark.asyncio
    async def test_rename_skill_file_nonexistent_skill_raises_error(self, markdown_ops):
        """测试重命名不存在的 skill 抛出异常"""
        with pytest.raises(SkillOperationError, match="不存在"):
            await markdown_ops.rename_skill_file(
                "nonexistent-skill", "old.txt", "new.txt"
            )

    @pytest.mark.asyncio
    async def test_rename_skill_file_nonexistent_file_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试重命名不存在的文件抛出异常"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        with pytest.raises(SkillFileNotFoundError, match="不存在"):
            await markdown_ops.rename_skill_file(
                "test-skill", "nonexistent.txt", "new.txt"
            )

    @pytest.mark.asyncio
    async def test_rename_skill_file_already_exists_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试重命名为已存在的名称抛出异常"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "file1.txt").write_text("Content1", encoding="utf-8")
        (skill_dir / "file2.txt").write_text("Content2", encoding="utf-8")

        with pytest.raises(SkillOperationError, match="已存在同名"):
            await markdown_ops.rename_skill_file("test-skill", "file1.txt", "file2.txt")

    @pytest.mark.asyncio
    async def test_rename_skill_file_path_traversal_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试路径遍历攻击被阻止（超出 skill 目录）"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "file.txt").write_text("Content", encoding="utf-8")

        # 尝试使用 ../ 超出 skill 目录
        with pytest.raises(SkillPathTraversalError, match="超出了.*目录范围"):
            await markdown_ops.rename_skill_file("test-skill", "file.txt", "../new.txt")

    @pytest.mark.asyncio
    async def test_rename_skill_file_move_to_subdirectory_success(
        self, markdown_ops, temp_project_dir
    ):
        """测试重命名文件到子目录（移动文件）"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "file.txt").write_text("Content", encoding="utf-8")
        (skill_dir / "subdir").mkdir()

        # 重命名到子目录
        await markdown_ops.rename_skill_file(
            "test-skill", "file.txt", "subdir/new_file.txt"
        )

        # 验证文件已被移动
        assert not (skill_dir / "file.txt").exists()
        assert (skill_dir / "subdir" / "new_file.txt").exists()
        assert (skill_dir / "subdir" / "new_file.txt").read_text(
            encoding="utf-8"
        ) == "Content"

    @pytest.mark.asyncio
    async def test_rename_skill_file_move_to_subdirectory_creates_directory(
        self, markdown_ops, temp_project_dir
    ):
        """测试重命名文件到不存在的子目录时自动创建目录"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "file.txt").write_text("Content", encoding="utf-8")

        # 重命名到不存在的子目录
        await markdown_ops.rename_skill_file(
            "test-skill", "file.txt", "newdir/subdir/file.txt"
        )

        # 验证目录和文件都已创建
        assert not (skill_dir / "file.txt").exists()
        assert (skill_dir / "newdir" / "subdir" / "file.txt").exists()
        assert (skill_dir / "newdir" / "subdir" / "file.txt").read_text(
            encoding="utf-8"
        ) == "Content"

    @pytest.mark.asyncio
    async def test_rename_skill_file_move_out_of_subdirectory_success(
        self, markdown_ops, temp_project_dir
    ):
        """测试重命名文件从子目录移动到根目录"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "subdir").mkdir()
        (skill_dir / "subdir" / "file.txt").write_text("Content", encoding="utf-8")

        # 从子目录移动到根目录
        await markdown_ops.rename_skill_file(
            "test-skill", "subdir/file.txt", "new_file.txt"
        )

        # 验证文件已被移动
        assert not (skill_dir / "subdir" / "file.txt").exists()
        assert (skill_dir / "new_file.txt").exists()
        assert (skill_dir / "new_file.txt").read_text(encoding="utf-8") == "Content"

    @pytest.mark.asyncio
    async def test_rename_skill_file_main_file_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试重命名 SKILL.md 主文件抛出异常"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

        with pytest.raises(SkillOperationError, match="不允许重命名 SKILL.md"):
            await markdown_ops.rename_skill_file("test-skill", "SKILL.md", "NEW.md")

    @pytest.mark.asyncio
    async def test_rename_skill_file_plugin_scope_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试 plugin 作用域抛出异常（不允许重命名）"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "file.txt").write_text("Content", encoding="utf-8")

        with pytest.raises(SkillOperationError, match="不允许重命名插件作用域"):
            await markdown_ops.rename_skill_file(
                "test-skill", "file.txt", "new.txt", scope=ConfigScope.plugin
            )
