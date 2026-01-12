"""
ProjectService 模块的单元测试
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.claude.claude_projects_scanner import (
    ClaudeProject,
    ClaudeProjectsScanner,
)
from src.database.schemas.ai_project import AiToolType
from src.project.project_service import ProjectService


class TestScanAndSaveAllProjects:
    """测试 scan_and_save_all_projects 方法"""

    @pytest.mark.asyncio
    async def test_scan_no_projects(self):
        """测试扫描时没有项目"""
        # Mock scanner to return empty list
        with patch.object(
            ProjectService, "__init__", lambda self, claude_projects_path=None: None
        ):
            service = ProjectService()
            service.scanner = Mock()
            service.scanner.scan_all_projects = Mock(return_value=[])

            # Mock database operations
            mock_db = AsyncMock()
            mock_db.commit = AsyncMock()

            async def mock_get_db():
                yield mock_db

            with patch("src.project.project_service.get_db", side_effect=mock_get_db):
                result = await service.scan_and_save_all_projects()

            assert result is True
            service.scanner.scan_all_projects.assert_called_once()

    @pytest.mark.asyncio
    async def test_scan_with_projects_creates_new(self, tmp_path):
        """测试扫描到新项目并创建"""
        # 创建临时项目目录和配置
        user_home = tmp_path / "home"
        user_home.mkdir()
        projects_dir = user_home / ".claude" / "projects"
        projects_dir.mkdir(parents=True)

        # 创建 .claude.json 配置文件
        claude_json = user_home / ".claude.json"
        test_config = {
            "projects": {
                "C:/Users/test/test-project": {
                    "allowedTools": [],
                    "mcpServers": {},
                }
            }
        }
        with open(claude_json, "w") as f:
            json.dump(test_config, f)

        # 创建模拟的 session 文件
        project_session_dir = projects_dir / "C--Users-test-test-project"
        project_session_dir.mkdir()
        session_file = project_session_dir / "session1.jsonl"
        session_content = [
            {
                "timestamp": "2024-01-01T10:00:00Z",
                "cwd": "C:/Users/test/test-project",
                "message": "test",
            }
        ]
        with open(session_file, "w") as f:
            for line in session_content:
                f.write(json.dumps(line) + "\n")

        # Mock scanner with custom user_home
        scanner = ClaudeProjectsScanner(user_home=user_home)

        # Mock database operations
        mock_project = Mock()
        mock_project.id = 1
        mock_project.project_path = None

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = Mock()

        async def mock_get_db():
            yield mock_db

        with patch("src.project.project_service.get_db", side_effect=mock_get_db):
            # Mock CRUD operations
            with (
                patch("src.project.project_service.ai_project_crud") as mock_crud,
                patch(
                    "src.project.project_service.ai_project_session_crud"
                ) as mock_session_crud,
            ):
                mock_crud.read_by_path = AsyncMock(return_value=None)
                mock_crud.create = AsyncMock(return_value=mock_project)
                mock_session_crud.get_by_project_session = AsyncMock(return_value=None)
                mock_session_crud.create = AsyncMock()

                service = ProjectService()
                service.scanner = scanner

                result = await service.scan_and_save_all_projects()

                assert result is True
                mock_crud.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_scan_with_projects_updates_existing(self, tmp_path):
        """测试扫描到已存在的项目并更新"""
        # 创建临时项目目录和配置
        user_home = tmp_path / "home"
        user_home.mkdir()
        projects_dir = user_home / ".claude" / "projects"
        projects_dir.mkdir(parents=True)

        # 创建 .claude.json 配置文件
        claude_json = user_home / ".claude.json"
        test_config = {
            "projects": {
                "C:/Users/test/test-project": {
                    "allowedTools": [],
                    "mcpServers": {},
                }
            }
        }
        with open(claude_json, "w") as f:
            json.dump(test_config, f)

        # 创建模拟的 session 文件
        project_session_dir = projects_dir / "C--Users-test-test-project"
        project_session_dir.mkdir()
        session_file = project_session_dir / "session1.jsonl"
        session_content = [
            {
                "timestamp": "2024-01-01T10:00:00Z",
                "cwd": "C:/Users/test/test-project",
                "message": "test",
            }
        ]
        with open(session_file, "w") as f:
            for line in session_content:
                f.write(json.dumps(line) + "\n")

        # Mock scanner with custom user_home
        scanner = ClaudeProjectsScanner(user_home=user_home)

        # Mock database operations
        mock_existing_project = Mock()
        mock_existing_project.id = 1
        mock_updated_project = Mock()
        mock_updated_project.id = 1

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        async def mock_get_db():
            yield mock_db

        with patch("src.project.project_service.get_db", side_effect=mock_get_db):
            # Mock CRUD operations - 项目已存在
            with (
                patch("src.project.project_service.ai_project_crud") as mock_crud,
                patch(
                    "src.project.project_service.ai_project_session_crud"
                ) as mock_session_crud,
            ):
                mock_crud.read_by_path = AsyncMock(return_value=mock_existing_project)
                mock_crud.update = AsyncMock(return_value=mock_updated_project)
                mock_session_crud.get_by_project_session = AsyncMock(return_value=None)
                mock_session_crud.create = AsyncMock()

                service = ProjectService()
                service.scanner = scanner

                result = await service.scan_and_save_all_projects()

                assert result is True
                mock_crud.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_scan_with_invalid_session_path(self, tmp_path):
        """测试 session 目录无法解析项目路径时返回 None"""
        # 创建临时项目目录和配置
        user_home = tmp_path / "home"
        user_home.mkdir()
        projects_dir = user_home / ".claude" / "projects"
        projects_dir.mkdir(parents=True)

        # 创建 .claude.json 配置文件
        claude_json = user_home / ".claude.json"
        test_config = {
            "projects": {
                "C:/Users/test/test-project": {
                    "allowedTools": [],
                    "mcpServers": {},
                }
            }
        }
        with open(claude_json, "w") as f:
            json.dump(test_config, f)

        # 创建没有 cwd 的 session 文件
        project_session_dir = projects_dir / "C--Users-test-test-project"
        project_session_dir.mkdir()
        session_file = project_session_dir / "session1.jsonl"
        session_content = [
            {
                "timestamp": "2024-01-01T10:00:00Z",
                # 没有 cwd 字段
                "message": "test",
            }
        ]
        with open(session_file, "w") as f:
            for line in session_content:
                f.write(json.dumps(line) + "\n")

        # Mock scanner with custom user_home
        scanner = ClaudeProjectsScanner(user_home=user_home)

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        async def mock_get_db():
            yield mock_db

        with patch("src.project.project_service.get_db", side_effect=mock_get_db):

            service = ProjectService()
            service.scanner = scanner

            result = await service.scan_and_save_all_projects()

            # 应该成功，但没有项目被保存
            assert result is True

    @pytest.mark.asyncio
    async def test_scan_database_error(self, tmp_path):
        """测试数据库错误时回滚"""
        # 创建临时项目目录和配置
        user_home = tmp_path / "home"
        user_home.mkdir()
        projects_dir = user_home / ".claude" / "projects"
        projects_dir.mkdir(parents=True)

        # 创建 .claude.json 配置文件
        claude_json = user_home / ".claude.json"
        test_config = {
            "projects": {
                "C:/Users/test/test-project": {
                    "allowedTools": [],
                    "mcpServers": {},
                }
            }
        }
        with open(claude_json, "w") as f:
            json.dump(test_config, f)

        # 创建模拟的 session 文件
        project_session_dir = projects_dir / "C--Users-test-test-project"
        project_session_dir.mkdir()
        session_file = project_session_dir / "session1.jsonl"
        session_content = [
            {
                "timestamp": "2024-01-01T10:00:00Z",
                "cwd": "C:/Users/test/test-project",
                "message": "test",
            }
        ]
        with open(session_file, "w") as f:
            for line in session_content:
                f.write(json.dumps(line) + "\n")

        # Mock scanner with custom user_home
        scanner = ClaudeProjectsScanner(user_home=user_home)

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock(side_effect=Exception("DB Error"))
        mock_db.rollback = AsyncMock()

        async def mock_get_db():
            yield mock_db

        with patch("src.project.project_service.get_db", side_effect=mock_get_db):
            with patch("src.project.project_service.ai_project_crud") as mock_crud:
                mock_crud.read_by_path = AsyncMock(return_value=None)
                mock_crud.create = AsyncMock(side_effect=Exception("DB Error"))

                service = ProjectService()
                service.scanner = scanner

                with pytest.raises(Exception, match="DB Error"):
                    await service.scan_and_save_all_projects()

                mock_db.rollback.assert_called_once()


class TestScanAndSaveSingleProject:
    """测试 scan_and_save_single_project 方法"""

    @pytest.mark.asyncio
    async def test_scan_nonexistent_project(self):
        """测试扫描不存在的项目"""
        with patch.object(
            ProjectService, "__init__", lambda self, claude_projects_path=None: None
        ):
            service = ProjectService()

            mock_db = AsyncMock()

            async def mock_get_db():
                yield mock_db

            with patch("src.project.project_service.get_db", side_effect=mock_get_db):
                with patch("src.project.project_service.ai_project_crud") as mock_crud:
                    mock_crud._read_by_id = AsyncMock(return_value=None)

                    result = await service.scan_and_save_single_project("999")

                    assert result is None

    @pytest.mark.asyncio
    async def test_scan_project_no_path(self):
        """测试项目没有配置路径"""
        with patch.object(
            ProjectService, "__init__", lambda self, claude_projects_path=None: None
        ):
            service = ProjectService()

            mock_db = AsyncMock()
            mock_project = Mock()
            mock_project.project_path = None

            async def mock_get_db():
                yield mock_db

            with patch("src.project.project_service.get_db", side_effect=mock_get_db):
                with patch("src.project.project_service.ai_project_crud") as mock_crud:
                    mock_crud._read_by_id = AsyncMock(return_value=mock_project)

                    result = await service.scan_and_save_single_project("1")

                    assert result is None


class TestGetProjectStatus:
    """测试 get_project_status 方法"""

    @pytest.mark.asyncio
    async def test_get_status_nonexistent_project(self):
        """测试获取不存在项目的状态"""
        with patch.object(
            ProjectService, "__init__", lambda self, claude_projects_path=None: None
        ):
            service = ProjectService()

            mock_db = AsyncMock()

            async def mock_get_db():
                yield mock_db

            with patch("src.project.project_service.get_db", side_effect=mock_get_db):
                with patch("src.project.project_service.ai_project_crud") as mock_crud:
                    mock_crud._read_by_id = AsyncMock(return_value=None)

                    result = await service.get_project_status("999")

                    assert result is None

    @pytest.mark.asyncio
    async def test_get_status_success(self):
        """测试成功获取项目状态"""
        with patch.object(
            ProjectService, "__init__", lambda self, claude_projects_path=None: None
        ):
            service = ProjectService()

            mock_project = Mock()
            mock_project.id = 1
            mock_project.project_name = "test-project"
            mock_project.project_path = "/path/to/project"
            mock_project.ai_tools = [AiToolType.CLAUDE]
            mock_project.created_at = datetime(2024, 1, 1, 10, 0, 0)
            mock_project.updated_at = datetime(2024, 1, 2, 10, 0, 0)

            mock_session = Mock()
            mock_session.session_id = "session1"
            mock_session.ai_tool = AiToolType.CLAUDE
            mock_session.is_agent_session = False
            mock_session.created_at = datetime(2024, 1, 1, 10, 0, 0)
            mock_session.updated_at = datetime(2024, 1, 2, 10, 0, 0)

            mock_db = AsyncMock()

            async def mock_get_db():
                yield mock_db

            with patch("src.project.project_service.get_db", side_effect=mock_get_db):
                with (
                    patch("src.project.project_service.ai_project_crud") as mock_crud,
                    patch(
                        "src.project.project_service.ai_project_session_crud"
                    ) as mock_session_crud,
                ):
                    mock_crud._read_by_id = AsyncMock(return_value=mock_project)
                    mock_session_crud.get_by_project_id = AsyncMock(
                        return_value=[mock_session]
                    )

                    result = await service.get_project_status("1")

                    assert result is not None
                    assert result["project_key"] == 1
                    assert result["project_name"] == "test-project"
                    assert result["project_path"] == "/path/to/project"
                    assert len(result["sessions"]) == 1
                    assert result["sessions"][0]["session_id"] == "session1"


class TestListProjects:
    """测试 list_projects 方法"""

    @pytest.mark.asyncio
    async def test_list_projects_empty(self):
        """测试列出空项目列表"""
        with patch.object(
            ProjectService, "__init__", lambda self, claude_projects_path=None: None
        ):
            service = ProjectService()

            mock_db = AsyncMock()

            async def mock_get_db():
                yield mock_db

            with patch("src.project.project_service.get_db", side_effect=mock_get_db):
                with patch("src.project.project_service.ai_project_crud") as mock_crud:
                    mock_crud.read_all = AsyncMock(return_value=[])

                    result = await service.list_projects()

                    assert result == []

    @pytest.mark.asyncio
    async def test_list_projects_success(self):
        """测试成功列出项目"""
        with patch.object(
            ProjectService, "__init__", lambda self, claude_projects_path=None: None
        ):
            service = ProjectService()

            mock_project1 = Mock()
            mock_project1.id = 1
            mock_project1.project_name = "project1"

            mock_project2 = Mock()
            mock_project2.id = 2
            mock_project2.project_name = "project2"

            mock_db = AsyncMock()

            async def mock_get_db():
                yield mock_db

            with patch("src.project.project_service.get_db", side_effect=mock_get_db):
                with patch("src.project.project_service.ai_project_crud") as mock_crud:
                    mock_crud.read_all = AsyncMock(
                        return_value=[mock_project1, mock_project2]
                    )

                    result = await service.list_projects()

                    assert len(result) == 2
                    assert result[0].id == 1
                    assert result[1].id == 2


class TestGetProjectById:
    """测试 get_project_by_id 方法"""

    @pytest.mark.asyncio
    async def test_get_by_id_nonexistent(self):
        """测试获取不存在的项目"""
        with patch.object(
            ProjectService, "__init__", lambda self, claude_projects_path=None: None
        ):
            service = ProjectService()

            mock_db = AsyncMock()

            async def mock_get_db():
                yield mock_db

            with patch("src.project.project_service.get_db", side_effect=mock_get_db):
                with patch("src.project.project_service.ai_project_crud") as mock_crud:
                    mock_crud.get_by_id = AsyncMock(return_value=None)

                    result = await service.get_project_by_id(999)

                    assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_success(self):
        """测试成功获取项目"""
        with patch.object(
            ProjectService, "__init__", lambda self, claude_projects_path=None: None
        ):
            service = ProjectService()

            mock_project = Mock()
            mock_project.id = 1
            mock_project.project_name = "test-project"

            mock_db = AsyncMock()

            async def mock_get_db():
                yield mock_db

            with patch("src.project.project_service.get_db", side_effect=mock_get_db):
                with patch("src.project.project_service.ai_project_crud") as mock_crud:
                    mock_crud.get_by_id = AsyncMock(return_value=mock_project)

                    result = await service.get_project_by_id(1)

                    assert result is not None
                    assert result.id == 1
                    assert result.project_name == "test-project"


class TestSaveProjectToDb:
    """测试 _save_project_to_db 私有方法"""

    @pytest.mark.asyncio
    async def test_save_project_with_session_path(self):
        """测试保存项目时包含 claude_session_path"""
        with patch.object(
            ProjectService, "__init__", lambda self, claude_projects_path=None: None
        ):
            service = ProjectService()

            # 创建模拟的 ClaudeProject，包含 project_session_path
            mock_claude_project = Mock(spec=ClaudeProject)
            mock_claude_project.project_name = "test-project"
            mock_claude_project.project_path = "/path/to/project"
            mock_claude_project.project_session_path = (
                "/path/to/.claude/projects/session"
            )
            mock_claude_project.first_active_at = datetime(2024, 1, 1, 10, 0, 0)
            mock_claude_project.last_active_at = datetime(2024, 1, 2, 10, 0, 0)
            mock_claude_project.sessions = {}

            mock_db = AsyncMock()

            with patch("src.project.project_service.ai_project_crud") as mock_crud:
                # 项目不存在，创建新项目
                mock_crud.read_by_path = AsyncMock(return_value=None)
                mock_crud.create = AsyncMock()

                await service._save_project_to_db(
                    mock_db, mock_claude_project, AiToolType.CLAUDE
                )

                # 验证 create 被调用，并且包含了 claude_session_path
                mock_crud.create.assert_called_once()
                call_args = mock_crud.create.call_args
                assert call_args is not None
                # 验证传入的对象包含 claude_session_path
                create_obj = call_args[1]["obj_in"]
                assert (
                    create_obj.claude_session_path
                    == "/path/to/.claude/projects/session"
                )

    @pytest.mark.asyncio
    async def test_update_project_with_session_path(self):
        """测试更新项目时包含 claude_session_path"""
        with patch.object(
            ProjectService, "__init__", lambda self, claude_projects_path=None: None
        ):
            service = ProjectService()

            # 创建模拟的 ClaudeProject，包含 project_session_path
            mock_claude_project = Mock(spec=ClaudeProject)
            mock_claude_project.project_name = "test-project"
            mock_claude_project.project_path = "/path/to/project"
            mock_claude_project.project_session_path = (
                "/path/to/.claude/projects/session"
            )
            mock_claude_project.first_active_at = datetime(2024, 1, 1, 10, 0, 0)
            mock_claude_project.last_active_at = datetime(2024, 1, 2, 10, 0, 0)
            mock_claude_project.sessions = {}

            mock_existing_project = Mock()
            mock_existing_project.id = 1

            mock_db = AsyncMock()

            with patch("src.project.project_service.ai_project_crud") as mock_crud:
                # 项目已存在，更新项目
                mock_crud.read_by_path = AsyncMock(return_value=mock_existing_project)
                mock_crud.update = AsyncMock()

                await service._save_project_to_db(
                    mock_db, mock_claude_project, AiToolType.CLAUDE
                )

                # 验证 update 被调用，并且包含了 claude_session_path
                mock_crud.update.assert_called_once()
                call_args = mock_crud.update.call_args
                assert call_args is not None
                # 验证传入的对象包含 claude_session_path
                update_obj = call_args[1]["obj_update"]
                assert (
                    update_obj.claude_session_path
                    == "/path/to/.claude/projects/session"
                )
