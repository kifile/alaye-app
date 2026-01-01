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
    MarkdownContentDTO,
    SkillInfo,
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

    def test_load_memory_project_claude_md(self, markdown_ops, temp_project_dir):
        """测试加载项目根目录的 CLAUDE.md"""
        content = "# Test Project\n\nThis is a test project."
        (temp_project_dir / "CLAUDE.md").write_text(content, encoding="utf-8")

        result = markdown_ops.load_markdown_content("memory", "project_claude_md")

        assert isinstance(result, MarkdownContentDTO)
        assert result.content == content
        assert result.md5 is not None
        assert len(result.md5) == 32  # MD5 hash length

    def test_load_memory_claude_dir_claude_md(self, markdown_ops, temp_project_dir):
        """测试加载 .claude 目录下的 CLAUDE.md"""
        content = "# Claude Dir Config"
        (temp_project_dir / ".claude" / "CLAUDE.md").write_text(
            content, encoding="utf-8"
        )

        result = markdown_ops.load_markdown_content("memory", "claude_dir_claude_md")

        assert result.content == content

    def test_load_memory_local_claude_md(self, markdown_ops, temp_project_dir):
        """测试加载 CLAUDE.local.md"""
        content = "# Local Config"
        (temp_project_dir / "CLAUDE.local.md").write_text(content, encoding="utf-8")

        result = markdown_ops.load_markdown_content("memory", "local_claude_md")

        assert result.content == content

    def test_load_memory_user_global_claude_md(self, markdown_ops, temp_user_home):
        """测试加载用户全局的 CLAUDE.md"""
        content = "# Global Config"
        (temp_user_home / ".claude" / "CLAUDE.md").write_text(content, encoding="utf-8")

        result = markdown_ops.load_markdown_content("memory", "user_global_claude_md")

        assert result.content == content

    def test_load_nonexistent_file_returns_empty(self, markdown_ops):
        """测试加载不存在的文件返回空内容"""
        result = markdown_ops.load_markdown_content("memory", "project_claude_md")

        assert result.content == ""
        assert result.md5 == "d41d8cd98f00b204e9800998ecf8427e"  # MD5 of empty string

    def test_load_command_with_nested_path(self, markdown_ops, temp_project_dir):
        """测试加载嵌套路径的 command"""
        content = "# Test Command"
        command_dir = temp_project_dir / ".claude" / "commands" / "features" / "value"
        command_dir.mkdir(parents=True, exist_ok=True)
        (command_dir / "test.md").write_text(content, encoding="utf-8")

        result = markdown_ops.load_markdown_content(
            "command", "features:value:test", scope=ConfigScope.project
        )

        assert result.content == content

    def test_load_agent_project_scope(self, markdown_ops, temp_project_dir):
        """测试加载 project scope 的 agent"""
        content = "# Test Agent"
        (temp_project_dir / ".claude" / "agents" / "test-agent.md").write_text(
            content, encoding="utf-8"
        )

        result = markdown_ops.load_markdown_content(
            "agent", "test-agent", scope=ConfigScope.project
        )

        assert result.content == content

    def test_load_agent_user_scope(self, markdown_ops, temp_user_home):
        """测试加载 user scope 的 agent"""
        content = "# User Agent"
        (temp_user_home / ".claude" / "agents" / "user-agent.md").write_text(
            content, encoding="utf-8"
        )

        result = markdown_ops.load_markdown_content(
            "agent", "user-agent", scope=ConfigScope.user
        )

        assert result.content == content

    def test_load_skill(self, markdown_ops, temp_project_dir):
        """测试加载 skill"""
        content = "# Test Skill"
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

        result = markdown_ops.load_markdown_content(
            "skill", "test-skill", scope=ConfigScope.project
        )

        assert result.content == content

    def test_load_invalid_content_type_raises_error(self, markdown_ops):
        """测试加载无效的 content_type 抛出异常"""
        with pytest.raises(ValueError, match="不支持的 content_type"):
            markdown_ops.load_markdown_content("invalid", "test")

    # ========== 测试 update_markdown_content ==========

    def test_update_markdown_content_success(self, markdown_ops, temp_project_dir):
        """测试成功更新 Markdown 内容"""
        # 先创建文件
        original_content = "# Original"
        (temp_project_dir / "CLAUDE.md").write_text(original_content, encoding="utf-8")

        # 获取 MD5
        original_result = markdown_ops.load_markdown_content(
            "memory", "project_claude_md"
        )

        # 更新内容
        new_content = "# Updated Content"
        markdown_ops.update_markdown_content(
            "memory",
            "project_claude_md",
            from_md5=original_result.md5,
            content=new_content,
            scope=ConfigScope.project,
        )

        # 验证更新
        result = markdown_ops.load_markdown_content("memory", "project_claude_md")
        assert result.content == new_content

    def test_update_markdown_content_with_md5_mismatch(
        self, markdown_ops, temp_project_dir
    ):
        """测试 MD5 不匹配时抛出异常"""
        (temp_project_dir / "CLAUDE.md").write_text("Original", encoding="utf-8")

        with pytest.raises(ValueError, match="文件已变化"):
            markdown_ops.update_markdown_content(
                "memory",
                "project_claude_md",
                from_md5="wrong_md5",
                content="New content",
                scope=ConfigScope.project,
            )

    def test_update_markdown_content_creates_directory(
        self, markdown_ops, temp_project_dir
    ):
        """测试更新时自动创建目录"""
        markdown_ops.update_markdown_content(
            "command", "features:test", content="# Test", scope=ConfigScope.project
        )

        command_file = (
            temp_project_dir / ".claude" / "commands" / "features" / "test.md"
        )
        assert command_file.exists()
        assert command_file.read_text(encoding="utf-8") == "# Test"

    def test_update_markdown_content_same_content_no_change(
        self, markdown_ops, temp_project_dir
    ):
        """测试更新相同内容时不修改文件"""
        original_content = "# Test"
        (temp_project_dir / "CLAUDE.md").write_text(original_content, encoding="utf-8")

        original_result = markdown_ops.load_markdown_content(
            "memory", "project_claude_md"
        )
        original_stat = (temp_project_dir / "CLAUDE.md").stat()

        # 更新相同内容
        markdown_ops.update_markdown_content(
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

    def test_save_markdown_content_new_file(self, markdown_ops, temp_project_dir):
        """测试保存新的 Markdown 内容"""
        content = "# New Command"
        result = markdown_ops.save_markdown_content(
            "command", "test-command", content=content, scope=ConfigScope.project
        )

        assert isinstance(result, MarkdownContentDTO)
        assert result.content == content

        # 验证文件已创建
        command_file = temp_project_dir / ".claude" / "commands" / "test-command.md"
        assert command_file.exists()
        assert command_file.read_text(encoding="utf-8") == content

    def test_save_markdown_content_file_exists_raises_error(
        self, markdown_ops, temp_project_dir
    ):
        """测试保存已存在的文件抛出异常"""
        # 先创建文件
        (temp_project_dir / ".claude" / "commands" / "test.md").write_text(
            "Existing", encoding="utf-8"
        )

        with pytest.raises(ValueError, match="已存在"):
            markdown_ops.save_markdown_content(
                "command", "test", content="New", scope=ConfigScope.project
            )

    def test_save_skill_creates_directory(self, markdown_ops, temp_project_dir):
        """测试保存 skill 时创建目录结构"""
        content = "# Test Skill"
        markdown_ops.save_markdown_content(
            "skill", "test-skill", content=content, scope=ConfigScope.project
        )

        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_file = skill_dir / "SKILL.md"
        assert skill_dir.exists()
        assert skill_file.exists()
        assert skill_file.read_text(encoding="utf-8") == content

    # ========== 测试 rename_markdown_content ==========

    def test_rename_command_success(self, markdown_ops, temp_project_dir):
        """测试成功重命名 command"""
        # 创建原始文件
        (temp_project_dir / ".claude" / "commands" / "old.md").write_text(
            "# Old", encoding="utf-8"
        )

        markdown_ops.rename_markdown_content(
            "command", "old", "new", scope=ConfigScope.project
        )

        # 验证重命名
        old_file = temp_project_dir / ".claude" / "commands" / "old.md"
        new_file = temp_project_dir / ".claude" / "commands" / "new.md"
        assert not old_file.exists()
        assert new_file.exists()

    def test_rename_agent_with_scope_change(
        self, markdown_ops, temp_project_dir, temp_user_home
    ):
        """测试重命名 agent 并更改作用域"""
        # 在 project scope 创建 agent
        (temp_project_dir / ".claude" / "agents" / "test.md").write_text(
            "# Test", encoding="utf-8"
        )

        markdown_ops.rename_markdown_content(
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

    def test_rename_skill_moves_directory(self, markdown_ops, temp_project_dir):
        """测试重命名 skill 会移动整个目录"""
        # 创建 skill 目录
        skill_dir = temp_project_dir / ".claude" / "skills" / "old-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")
        (skill_dir / "extra.txt").write_text("Extra file", encoding="utf-8")

        markdown_ops.rename_markdown_content(
            "skill", "old-skill", "new-skill", scope=ConfigScope.project
        )

        # 验证目录已移动
        old_dir = temp_project_dir / ".claude" / "skills" / "old-skill"
        new_dir = temp_project_dir / ".claude" / "skills" / "new-skill"

        assert not old_dir.exists()
        assert (new_dir / "SKILL.md").exists()

    def test_rename_nonexistent_file_raises_error(self, markdown_ops):
        """测试重命名不存在的文件抛出异常"""
        with pytest.raises(ValueError, match="不存在"):
            markdown_ops.rename_markdown_content(
                "command", "nonexistent", "new", scope=ConfigScope.project
            )

    def test_rename_to_existing_name_raises_error(self, markdown_ops, temp_project_dir):
        """测试重命名到已存在的名称抛出异常"""
        # 创建两个文件
        (temp_project_dir / ".claude" / "commands" / "old.md").write_text(
            "# Old", encoding="utf-8"
        )
        (temp_project_dir / ".claude" / "commands" / "new.md").write_text(
            "# New", encoding="utf-8"
        )

        with pytest.raises(ValueError, match="已存在"):
            markdown_ops.rename_markdown_content(
                "command", "old", "new", scope=ConfigScope.project
            )

    def test_rename_updates_name_in_frontmatter(self, markdown_ops, temp_project_dir):
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
        markdown_ops.rename_markdown_content(
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

    def test_rename_with_colon_in_name_extracts_last_part(
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
        markdown_ops.rename_markdown_content(
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

    def test_rename_with_same_name_skips_update(self, markdown_ops, temp_project_dir):
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
            markdown_ops_with_user_home.rename_markdown_content(
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

    def test_delete_command_success(self, markdown_ops, temp_project_dir):
        """测试成功删除 command"""
        (temp_project_dir / ".claude" / "commands" / "test.md").write_text(
            "# Test", encoding="utf-8"
        )

        markdown_ops.delete_markdown_content(
            "command", "test", scope=ConfigScope.project
        )

        command_file = temp_project_dir / ".claude" / "commands" / "test.md"
        assert not command_file.exists()

    def test_delete_skill_removes_directory(self, markdown_ops, temp_project_dir):
        """测试删除 skill 会移除整个目录"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")
        (skill_dir / "extra.txt").write_text("Extra", encoding="utf-8")

        markdown_ops.delete_markdown_content(
            "skill", "test-skill", scope=ConfigScope.project
        )

        # 验证整个目录被删除
        assert not skill_dir.exists()

    def test_delete_nonexistent_file_raises_error(self, markdown_ops):
        """测试删除不存在的文件抛出异常"""
        with pytest.raises(ValueError, match="不存在"):
            markdown_ops.delete_markdown_content(
                "command", "nonexistent", scope=ConfigScope.project
            )

    # ========== 测试 scan_memory ==========

    def test_scan_memory_all_files_exist(
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

        result = markdown_ops.scan_memory()

        assert isinstance(result, ClaudeMemoryInfo)
        assert result.project_claude_md is True
        assert result.claude_dir_claude_md is True
        assert result.local_claude_md is True
        assert result.user_global_claude_md is True

    def test_scan_memory_no_files_exist(self, markdown_ops):
        """测试扫描不存在的 memory 文件"""
        result = markdown_ops.scan_memory()

        assert result.project_claude_md is False
        assert result.claude_dir_claude_md is False
        assert result.local_claude_md is False
        assert result.user_global_claude_md is False

    # ========== 测试 scan_agents ==========

    def test_scan_agents_project_scope(self, markdown_ops, temp_project_dir):
        """测试扫描 project scope 的 agents"""
        # 创建 agents
        agents_dir = temp_project_dir / ".claude" / "agents"
        (agents_dir / "agent1.md").write_text("# Agent 1", encoding="utf-8")
        (agents_dir / "agent2.md").write_text("# Agent 2", encoding="utf-8")

        result = markdown_ops.scan_agents()

        assert len(result) == 2
        assert all(isinstance(agent, AgentInfo) for agent in result)
        assert all(agent.scope == ConfigScope.project for agent in result)
        agent_names = {agent.name for agent in result}
        assert agent_names == {"agent1", "agent2"}

    def test_scan_agents_user_scope(self, markdown_ops, temp_user_home):
        """测试扫描 user scope 的 agents"""
        agents_dir = temp_user_home / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "user-agent.md").write_text("# User", encoding="utf-8")

        result = markdown_ops.scan_agents()

        assert len(result) == 1
        assert result[0].scope == ConfigScope.user
        assert result[0].name == "user-agent"

    def test_scan_agents_mixed_scopes(
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

        result = markdown_ops.scan_agents()

        assert len(result) == 2
        scopes = {agent.scope for agent in result}
        assert scopes == {ConfigScope.project, ConfigScope.user}

    def test_scan_agents_with_description(self, markdown_ops, temp_project_dir):
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

        result = markdown_ops.scan_agents()

        assert len(result) == 1
        assert result[0].description == "A test agent for testing"

    # ========== 测试 scan_commands ==========

    def test_scan_commands_simple(self, markdown_ops, temp_project_dir):
        """测试扫描简单的 commands"""
        (temp_project_dir / ".claude" / "commands" / "test.md").write_text(
            "# Test", encoding="utf-8"
        )

        result = markdown_ops.scan_commands()

        assert len(result) == 1
        assert isinstance(result[0], CommandInfo)
        assert result[0].name == "test"
        assert result[0].scope == ConfigScope.project

    def test_scan_commands_nested_path(self, markdown_ops, temp_project_dir):
        """测试扫描嵌套路径的 commands"""
        nested_dir = temp_project_dir / ".claude" / "commands" / "features" / "value"
        nested_dir.mkdir(parents=True, exist_ok=True)
        (nested_dir / "test.md").write_text("# Test", encoding="utf-8")

        result = markdown_ops.scan_commands()

        assert len(result) == 1
        assert result[0].name == "features:value:test"

    def test_scan_commands_with_description(self, markdown_ops, temp_project_dir):
        """测试扫描带描述的 commands"""
        command_content = """---
description: Test command description
---

# Test Command
"""
        (temp_project_dir / ".claude" / "commands" / "test.md").write_text(
            command_content, encoding="utf-8"
        )

        result = markdown_ops.scan_commands()

        assert len(result) == 1
        assert result[0].description == "Test command description"

    def test_scan_commands_multiple_scopes(
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

        result = markdown_ops.scan_commands()

        assert len(result) == 2
        scopes = {cmd.scope for cmd in result}
        assert scopes == {ConfigScope.project, ConfigScope.user}

    # ========== 测试 scan_skills ==========

    def test_scan_skills_simple(self, markdown_ops, temp_project_dir):
        """测试扫描简单的 skills"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

        result = markdown_ops.scan_skills()

        assert len(result) == 1
        assert isinstance(result[0], SkillInfo)
        assert result[0].name == "test-skill"
        assert result[0].scope == ConfigScope.project

    def test_scan_skills_multiple(self, markdown_ops, temp_project_dir):
        """测试扫描多个 skills"""
        for skill_name in ["skill1", "skill2", "skill3"]:
            skill_dir = temp_project_dir / ".claude" / "skills" / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(f"# {skill_name}", encoding="utf-8")

        result = markdown_ops.scan_skills()

        assert len(result) == 3
        skill_names = {skill.name for skill in result}
        assert skill_names == {"skill1", "skill2", "skill3"}

    def test_scan_skills_with_description(self, markdown_ops, temp_project_dir):
        """测试扫描带描述的 skills"""
        skill_content = """---
description: A test skill for testing
---

# Test Skill
"""
        skill_dir = temp_project_dir / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

        result = markdown_ops.scan_skills()

        assert len(result) == 1
        assert result[0].description == "A test skill for testing"

    def test_scan_skills_ignores_non_skill_dirs(self, markdown_ops, temp_project_dir):
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

        result = markdown_ops.scan_skills()

        assert len(result) == 1
        assert result[0].name == "valid-skill"
