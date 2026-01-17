"""
Claude Projects Scanner 模块的单元测试
测试项目的扫描、检测和验证功能
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.claude.claude_projects_scanner import (
    ClaudeProjectsScanner,
)


class TestClaudeProjectsScanner:
    """测试 ClaudeProjectsScanner 类"""

    @pytest.fixture
    def temp_user_home(self):
        """创建临时用户主目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            yield home

    @pytest.fixture
    def temp_projects_dir(self, temp_user_home):
        """创建临时 Claude projects 目录"""
        projects_dir = temp_user_home / ".claude" / "projects"
        projects_dir.mkdir(parents=True)
        return projects_dir

    @pytest.fixture
    def scanner(self, temp_user_home):
        """创建 ClaudeProjectsScanner 实例"""
        return ClaudeProjectsScanner(user_home=temp_user_home)

    @pytest.fixture
    def valid_project_config(self, temp_user_home):
        """创建合法的项目配置文件"""
        config_path = temp_user_home / ".claude.json"
        test_config = {
            "projects": {
                "/Users/test/project1": {
                    "allowedTools": [],
                    "mcpServers": {},
                },
                "/Users/test/project2": {
                    "allowedTools": ["claude"],
                    "mcpServers": {},
                },
            }
        }
        with open(config_path, "w") as f:
            json.dump(test_config, f)
        return test_config

    # ========== 测试初始化 ==========

    def test_init_with_default_path(self):
        """测试使用默认路径初始化"""
        scanner = ClaudeProjectsScanner()
        assert scanner.projects_path == Path.home() / ".claude" / "projects"
        assert scanner.user_home == Path.home()

    def test_init_with_custom_path(self, temp_user_home):
        """测试使用自定义路径初始化"""
        custom_path = temp_user_home / "custom" / "projects"
        scanner = ClaudeProjectsScanner(
            claude_projects_path=custom_path, user_home=temp_user_home
        )
        assert scanner.projects_path == custom_path
        assert scanner.user_home == temp_user_home

    # ========== 测试 load_valid_projects ==========

    def test_load_valid_projects_success(self, scanner, valid_project_config):
        """测试成功加载合法项目列表"""
        valid_projects = scanner.load_valid_projects()

        assert len(valid_projects) == 2
        # 验证路径被标准化
        assert any("project1" in p for p in valid_projects)
        assert any("project2" in p for p in valid_projects)

    def test_load_valid_projects_no_config_file(self, temp_user_home):
        """测试配置文件不存在"""
        scanner = ClaudeProjectsScanner(user_home=temp_user_home)
        valid_projects = scanner.load_valid_projects()

        assert valid_projects == set()

    def test_load_valid_projects_invalid_json(self, temp_user_home):
        """测试配置文件不是有效的 JSON"""
        config_path = temp_user_home / ".claude.json"
        with open(config_path, "w") as f:
            f.write("invalid json {")

        scanner = ClaudeProjectsScanner(user_home=temp_user_home)
        valid_projects = scanner.load_valid_projects()

        assert valid_projects == set()

    def test_load_valid_projects_empty_projects(self, temp_user_home):
        """测试配置文件中没有项目"""
        config_path = temp_user_home / ".claude.json"
        test_config = {"projects": {}}
        with open(config_path, "w") as f:
            json.dump(test_config, f)

        scanner = ClaudeProjectsScanner(user_home=temp_user_home)
        valid_projects = scanner.load_valid_projects()

        assert valid_projects == set()

    # ========== 测试 _create_claude_project ==========

    def test_create_claude_project_existing(self, scanner, tmp_path):
        """测试创建存在的项目对象"""
        project_path = str(tmp_path / "test-project")
        Path(project_path).mkdir(parents=True)

        project = scanner._create_claude_project(project_path, "/sessions/path")

        assert project.project_name == "test-project"
        assert project.project_path == project_path
        assert project.project_session_path == "/sessions/path"
        assert project.removed is False
        assert project.first_active_at is None
        assert project.last_active_at is None

    def test_create_claude_project_removed(self, scanner):
        """测试创建已移除的项目对象"""
        project_path = "/nonexistent/project"

        project = scanner._create_claude_project(project_path, None)

        assert project.project_name == "project"
        assert project.project_path == project_path
        assert project.project_session_path is None
        assert project.removed is True

    # ========== 测试 scan_project_info ==========

    @pytest.mark.asyncio
    async def test_scan_project_info_success(
        self, temp_projects_dir, scanner, valid_project_config, tmp_path
    ):
        """测试成功扫描项目信息"""
        # 创建实际存在的项目路径
        real_project_path = tmp_path / "project1"
        real_project_path.mkdir(parents=True)

        # 创建项目 session 目录
        project_session_dir = temp_projects_dir / "Users-test-project1"
        project_session_dir.mkdir()

        # 创建包含 cwd 的 session 文件（使用实际路径）
        session_file = project_session_dir / "session1.jsonl"
        with open(session_file, "w") as f:
            f.write(
                json.dumps(
                    {"timestamp": "2024-01-01T10:00:00Z", "cwd": str(real_project_path)}
                )
                + "\n"
            )

        # 更新配置以包含实际路径
        config_path = scanner.user_home / ".claude.json"
        test_config = {
            "projects": {
                str(real_project_path): {
                    "allowedTools": [],
                    "mcpServers": {},
                }
            }
        }
        with open(config_path, "w") as f:
            json.dump(test_config, f)

        valid_projects = scanner.load_valid_projects()
        project = await scanner.scan_project_info(project_session_dir, valid_projects)

        assert project is not None
        assert project.project_name == "project1"
        assert str(real_project_path) in project.project_path
        assert project.project_session_path == str(project_session_dir)
        assert project.removed is False  # 项目路径存在

    @pytest.mark.asyncio
    async def test_scan_project_info_not_in_valid_list(
        self, temp_projects_dir, scanner
    ):
        """测试项目不在合法列表中"""
        project_session_dir = temp_projects_dir / "unknown-project"
        project_session_dir.mkdir()

        # 创建 session 文件
        session_file = project_session_dir / "session1.jsonl"
        with open(session_file, "w") as f:
            f.write(json.dumps({"timestamp": "2024-01-01T10:00:00Z"}) + "\n")

        valid_projects = {"/valid/project"}
        project = await scanner.scan_project_info(project_session_dir, valid_projects)

        assert project is None

    @pytest.mark.asyncio
    async def test_scan_project_info_no_cwd(self, temp_projects_dir, scanner):
        """测试 session 文件中没有 cwd"""
        project_session_dir = temp_projects_dir / "Users-test-project1"
        project_session_dir.mkdir()

        # 创建没有 cwd 的 session 文件
        session_file = project_session_dir / "session1.jsonl"
        with open(session_file, "w") as f:
            f.write(json.dumps({"timestamp": "2024-01-01T10:00:00Z"}) + "\n")

        valid_projects = {"/Users/test/project1"}
        project = await scanner.scan_project_info(project_session_dir, valid_projects)

        # 没有找到项目路径，应该返回 None
        assert project is None

    @pytest.mark.asyncio
    async def test_scan_project_info_nonexistent_directory(self, scanner):
        """测试扫描不存在的目录"""
        nonexistent = Path("/tmp/nonexistent-12345")
        valid_projects = set()

        project = await scanner.scan_project_info(nonexistent, valid_projects)

        assert project is None

    # ========== 测试 detect_git_worktree ==========

    def test_detect_git_worktree_regular_repo(self, tmp_path):
        """测试检测普通 git 仓库（非 worktree）"""
        scanner = ClaudeProjectsScanner()

        # 创建一个普通的 git 仓库
        import subprocess

        repo_path = tmp_path / "normal_repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
        )

        is_worktree, main_path = scanner.detect_git_worktree(str(repo_path))

        assert is_worktree is False
        assert main_path is None

    def test_detect_git_worktree_not_git_repo(self, tmp_path):
        """测试检测非 git 目录"""
        scanner = ClaudeProjectsScanner()

        non_git_path = tmp_path / "not_a_repo"
        non_git_path.mkdir()

        is_worktree, main_path = scanner.detect_git_worktree(str(non_git_path))

        assert is_worktree is False
        assert main_path is None

    def test_detect_git_worktree_nonexistent_path(self):
        """测试检测不存在的路径"""
        scanner = ClaudeProjectsScanner()

        is_worktree, main_path = scanner.detect_git_worktree("/tmp/nonexistent-12345")

        assert is_worktree is False
        assert main_path is None

    # ========== 测试 scan_all_projects ==========

    @pytest.mark.asyncio
    async def test_scan_all_projects_success(
        self, temp_projects_dir, scanner, valid_project_config
    ):
        """测试成功扫描所有项目"""
        # 创建两个项目的 session 目录
        for i in range(1, 3):
            project_session_dir = temp_projects_dir / f"Users-test-project{i}"
            project_session_dir.mkdir()
            session_file = project_session_dir / "session1.jsonl"
            with open(session_file, "w") as f:
                f.write(
                    json.dumps(
                        {
                            "timestamp": "2024-01-01T10:00:00Z",
                            "cwd": f"/Users/test/project{i}",
                        }
                    )
                    + "\n"
                )

        projects = await scanner.scan_all_projects()

        assert len(projects) == 2
        project_names = {p.project_name for p in projects}
        assert "project1" in project_names
        assert "project2" in project_names

    @pytest.mark.asyncio
    async def test_scan_all_projects_no_projects_directory(self, temp_user_home):
        """测试 projects 目录不存在"""
        scanner = ClaudeProjectsScanner(user_home=temp_user_home)
        # 不创建 projects 目录

        projects = await scanner.scan_all_projects()

        # 应该返回空列表
        assert projects == []

    @pytest.mark.asyncio
    async def test_scan_all_projects_empty_directory(self, temp_projects_dir, scanner):
        """测试空的 projects 目录"""
        # 创建配置文件但不创建任何 session 目录
        config_path = scanner.user_home / ".claude.json"
        test_config = {"projects": {}}
        with open(config_path, "w") as f:
            json.dump(test_config, f)

        projects = await scanner.scan_all_projects()

        assert projects == []

    @pytest.mark.asyncio
    async def test_scan_all_projects_with_removed_path(
        self, temp_projects_dir, scanner, valid_project_config
    ):
        """测试包含已移除路径的项目"""
        # 创建一个项目的 session 目录，但项目路径本身不存在
        project_session_dir = temp_projects_dir / "Users-test-removed-project"
        project_session_dir.mkdir()
        session_file = project_session_dir / "session1.jsonl"
        with open(session_file, "w") as f:
            f.write(
                json.dumps(
                    {"timestamp": "2024-01-01T10:00:00Z", "cwd": "/nonexistent/path"}
                )
                + "\n"
            )

        projects = await scanner.scan_all_projects()

        # 应该扫描到项目，但标记为 removed
        assert len(projects) > 0
        removed_projects = [p for p in projects if p.removed]
        assert len(removed_projects) > 0


class TestScanprojectsWithoutSessions:
    """测试 _scan_projects_without_sessions 方法"""

    @pytest.fixture
    def scanner(self, temp_user_home):
        """创建 scanner 实例"""
        return ClaudeProjectsScanner(user_home=temp_user_home)

    @pytest.fixture
    def temp_user_home(self):
        """创建临时用户主目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            yield home

    def test_scan_projects_without_sessions_existing(self, scanner, tmp_path):
        """测试扫描存在的项目（但没有 session 数据）"""
        project_paths = {str(tmp_path / "project1"), str(tmp_path / "project2")}

        # 创建项目目录
        for project_path in project_paths:
            Path(project_path).mkdir(parents=True)

        projects = scanner._scan_projects_without_sessions(project_paths)

        assert len(projects) == 2
        assert all(p.removed is False for p in projects)
        assert all(p.project_session_path is None for p in projects)

    def test_scan_projects_without_sessions_removed(self, scanner):
        """测试扫描已被移除的项目"""
        project_paths = {"/nonexistent/path1", "/nonexistent/path2"}

        projects = scanner._scan_projects_without_sessions(project_paths)

        assert len(projects) == 2
        assert all(p.removed is True for p in projects)
        assert all(p.project_session_path is None for p in projects)

    def test_scan_projects_without_sessions_mixed(self, scanner, tmp_path):
        """测试混合存在和移除的项目"""
        existing_path = str(tmp_path / "existing")
        Path(existing_path).mkdir(parents=True)

        project_paths = {existing_path, "/nonexistent/path"}

        projects = scanner._scan_projects_without_sessions(project_paths)

        assert len(projects) == 2
        removed_count = sum(1 for p in projects if p.removed)
        existing_count = sum(1 for p in projects if not p.removed)
        assert removed_count == 1
        assert existing_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
