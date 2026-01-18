"""
ProjectService 模块的单元测试
测试项目扫描和会话管理功能
"""

from datetime import datetime

import pytest

from src.database.cruds import ai_project_crud, ai_project_session_crud
from src.database.schemas.ai_project import AIProjectCreate, AiToolType
from src.database.schemas.ai_project_session import AIProjectSessionCreate
from src.project.project_service import ProjectService


class TestProjectService:
    """测试 ProjectService 基本功能"""

    def test_init(self):
        """测试初始化"""
        service = ProjectService()
        assert service.scanner is not None
        assert service.projects_path is not None
        assert service._background_tasks == set()


class TestShouldUpdateSession:
    """测试 _should_update_session 方法"""

    @pytest.fixture
    def service(self):
        """创建 ProjectService 实例"""
        return ProjectService()

    def test_should_update_true_mtime(self, service):
        """测试文件修改时间不同"""
        from unittest.mock import Mock

        existing = Mock()
        existing.file_mtime = datetime(2024, 1, 1, 10, 0, 0)
        existing.file_size = 1000

        session_info = Mock()
        session_info.file_mtime = datetime(2024, 1, 1, 11, 0, 0)
        session_info.file_size = 1000

        result = service._should_update_session(existing, session_info)
        assert result is True

    def test_should_update_true_size(self, service):
        """测试文件大小不同"""
        from unittest.mock import Mock

        existing = Mock()
        existing.file_mtime = datetime(2024, 1, 1, 10, 0, 0)
        existing.file_size = 1000

        session_info = Mock()
        session_info.file_mtime = datetime(2024, 1, 1, 10, 0, 0)
        session_info.file_size = 2000

        result = service._should_update_session(existing, session_info)
        assert result is True

    def test_should_update_false(self, service):
        """测试文件未变化"""
        from unittest.mock import Mock

        existing = Mock()
        existing.file_mtime = datetime(2024, 1, 1, 10, 0, 0)
        existing.file_size = 1000

        session_info = Mock()
        session_info.file_mtime = datetime(2024, 1, 1, 10, 0, 0)
        session_info.file_size = 1000

        result = service._should_update_session(existing, session_info)
        assert result is False


class TestSaveSessionFromInfo:
    """测试 _save_session_from_info 方法"""

    @pytest.fixture
    def service(self):
        """创建 ProjectService 实例"""
        return ProjectService()

    @pytest.fixture
    def mock_session_info(self):
        """创建模拟的 session 信息"""
        from datetime import datetime
        from unittest.mock import Mock

        info = Mock()
        info.session_id = "test-session"
        info.session_file = "/path/to/session.jsonl"
        info.title = "Test Session"
        info.file_mtime = datetime(2024, 1, 1, 10, 0, 0)
        info.file_size = 1000
        info.is_agent_session = False
        return info

    @pytest.mark.asyncio
    async def test_save_new_session(self, service, mock_get_db, mock_session_info):
        """测试保存新会话"""
        # 先创建项目
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path="/path/to/project",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        # 保存新会话
        await service._save_session_from_info(
            mock_get_db,
            mock_session_info,
            project.id,
            AiToolType.CLAUDE,
        )
        await mock_get_db.commit()

        # 验证会话已创建
        sessions = await ai_project_session_crud.get_by_project_id(
            mock_get_db, project_id=project.id
        )
        assert len(sessions) == 1
        assert sessions[0].session_id == "test-session"
        assert sessions[0].title == "Test Session"

    @pytest.mark.asyncio
    async def test_update_existing_session(
        self, service, mock_get_db, mock_session_info
    ):
        """测试更新现有会话"""
        from datetime import datetime

        # 先创建项目和会话
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path="/path/to/project",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )

        session = await ai_project_session_crud.create(
            mock_get_db,
            obj_in=AIProjectSessionCreate(
                session_id="test-session",
                project_id=project.id,
                session_file="/path/to/session.jsonl",
                title="Old Title",
                file_mtime=datetime(2023, 1, 1, 10, 0, 0),  # 旧时间
                file_size=500,  # 旧大小
                is_agent_session=False,
                ai_tool=AiToolType.CLAUDE,
                project_path=None,
                git_branch=None,
                session_file_md5=None,
                first_active_at=None,
                last_active_at=None,
            ),
        )
        await mock_get_db.commit()

        # 更新会话（文件已变化）
        await service._save_session_from_info(
            mock_get_db,
            mock_session_info,
            project.id,
            AiToolType.CLAUDE,
        )
        await mock_get_db.commit()

        # 验证会话已更新
        sessions = await ai_project_session_crud.get_by_project_id(
            mock_get_db, project_id=project.id
        )
        assert len(sessions) == 1
        assert sessions[0].file_size == 1000  # 新大小

    @pytest.mark.asyncio
    async def test_skip_unchanged_session(
        self, service, mock_get_db, mock_session_info
    ):
        """测试跳过未变化的会话"""
        # 先创建项目和会话
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path="/path/to/project",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )

        session = await ai_project_session_crud.create(
            mock_get_db,
            obj_in=AIProjectSessionCreate(
                session_id="test-session",
                project_id=project.id,
                session_file="/path/to/session.jsonl",
                title="Test Session",
                file_mtime=mock_session_info.file_mtime,  # 相同时间
                file_size=mock_session_info.file_size,  # 相同大小
                is_agent_session=False,
                ai_tool=AiToolType.CLAUDE,
                project_path=None,
                git_branch=None,
                session_file_md5=None,
                first_active_at=None,
                last_active_at=None,
            ),
        )
        await mock_get_db.commit()

        original_file_size = session.file_size

        # 尝试更新会话（文件未变化）
        await service._save_session_from_info(
            mock_get_db,
            mock_session_info,
            project.id,
            AiToolType.CLAUDE,
        )
        await mock_get_db.commit()

        # 验证会话未被修改
        sessions = await ai_project_session_crud.get_by_project_id(
            mock_get_db, project_id=project.id
        )
        assert len(sessions) == 1
        assert sessions[0].file_size == original_file_size


class TestListProjects:
    """测试 list_projects 方法"""

    @pytest.mark.asyncio
    async def test_list_projects_empty(self, mock_get_db):
        """测试列出空项目列表"""
        service = ProjectService()
        result = await service.list_projects()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_projects_success(self, mock_get_db):
        """测试成功列出项目"""
        # 创建测试项目
        await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="project1",
                project_path="/path/to/project1",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 2, 10, 0, 0),
            ),
        )

        await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="project2",
                project_path="/path/to/project2",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        service = ProjectService()
        result = await service.list_projects()

        assert len(result) == 2
        # 验证排序（按 last_active_at 降序）
        assert result[0].project_name == "project1"
        assert result[1].project_name == "project2"


class TestGetProjectById:
    """测试 get_project_by_id 方法"""

    @pytest.mark.asyncio
    async def test_get_by_id_nonexistent(self, mock_get_db):
        """测试获取不存在的项目"""
        service = ProjectService()
        result = await service.get_project_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, mock_get_db):
        """测试成功获取项目"""
        # 创建测试项目
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path="/path/to/project",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 2, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        service = ProjectService()
        result = await service.get_project_by_id(project.id)

        assert result is not None
        assert result.id == project.id
        assert result.project_name == "test-project"


class TestCleanupStaleSessions:
    """测试 _cleanup_stale_sessions 方法"""

    @pytest.fixture
    def service(self):
        """创建 ProjectService 实例"""
        return ProjectService()

    @pytest.mark.asyncio
    async def test_cleanup_deleted_sessions(self, service, mock_get_db):
        """测试删除不存在的会话"""
        # 创建项目
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path="/path/to/project",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )

        # 创建三个会话
        session1 = await ai_project_session_crud.create(
            mock_get_db,
            obj_in=AIProjectSessionCreate(
                session_id="session-1",
                project_id=project.id,
                session_file="/path/session1.jsonl",
                title="Session 1",
                file_mtime=datetime(2024, 1, 1, 10, 0, 0),
                file_size=1000,
                is_agent_session=False,
                ai_tool=AiToolType.CLAUDE,
                project_path=None,
                git_branch=None,
                session_file_md5=None,
                first_active_at=None,
                last_active_at=None,
            ),
        )

        session2 = await ai_project_session_crud.create(
            mock_get_db,
            obj_in=AIProjectSessionCreate(
                session_id="session-2",
                project_id=project.id,
                session_file="/path/session2.jsonl",
                title="Session 2",
                file_mtime=datetime(2024, 1, 1, 10, 0, 0),
                file_size=1000,
                is_agent_session=False,
                ai_tool=AiToolType.CLAUDE,
                project_path=None,
                git_branch=None,
                session_file_md5=None,
                first_active_at=None,
                last_active_at=None,
            ),
        )

        session3 = await ai_project_session_crud.create(
            mock_get_db,
            obj_in=AIProjectSessionCreate(
                session_id="session-3",
                project_id=project.id,
                session_file="/path/session3.jsonl",
                title="Session 3",
                file_mtime=datetime(2024, 1, 1, 10, 0, 0),
                file_size=1000,
                is_agent_session=False,
                ai_tool=AiToolType.CLAUDE,
                project_path=None,
                git_branch=None,
                session_file_md5=None,
                first_active_at=None,
                last_active_at=None,
            ),
        )
        await mock_get_db.commit()

        # 标记 session-3 为已删除
        await ai_project_session_crud.delete(mock_get_db, id=str(session3.id))
        await mock_get_db.commit()

        # 获取现有会话
        existing_sessions = await ai_project_session_crud.get_by_project_id(
            mock_get_db, project_id=project.id, include_removed=True
        )
        existing_sessions_map = {s.session_id: s for s in existing_sessions}

        # 新的扫描结果只包含 session-2
        new_session_ids = {"session-2"}

        # 执行清理
        deleted, restored = await service._cleanup_stale_sessions(
            mock_get_db,
            existing_sessions_map,
            new_session_ids,
            "test-project",
        )
        await mock_get_db.commit()

        # session-1 应该被删除
        assert deleted == 1
        # session-3 仍然是删除状态，没有恢复
        assert restored == 0

    @pytest.mark.asyncio
    async def test_restore_sessions(self, service, mock_get_db):
        """测试恢复重新出现的会话"""
        # 创建项目
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path="/path/to/project",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )

        # 创建会话并标记为删除
        session = await ai_project_session_crud.create(
            mock_get_db,
            obj_in=AIProjectSessionCreate(
                session_id="session-1",
                project_id=project.id,
                session_file="/path/session1.jsonl",
                title="Session 1",
                file_mtime=datetime(2024, 1, 1, 10, 0, 0),
                file_size=1000,
                is_agent_session=False,
                ai_tool=AiToolType.CLAUDE,
                project_path=None,
                git_branch=None,
                session_file_md5=None,
                first_active_at=None,
                last_active_at=None,
            ),
        )
        await mock_get_db.commit()

        # 标记为删除
        await ai_project_session_crud.delete(mock_get_db, id=str(session.id))
        await mock_get_db.commit()

        # 获取现有会话
        existing_sessions = await ai_project_session_crud.get_by_project_id(
            mock_get_db, project_id=project.id, include_removed=True
        )
        existing_sessions_map = {s.session_id: s for s in existing_sessions}

        # 会话重新出现
        new_session_ids = {"session-1"}

        # 执行清理
        deleted, restored = await service._cleanup_stale_sessions(
            mock_get_db,
            existing_sessions_map,
            new_session_ids,
            "test-project",
        )
        await mock_get_db.commit()

        # 没有会话被删除
        assert deleted == 0
        # session-1 应该被恢复
        assert restored == 1


class TestDeleteProject:
    """测试 delete_project 方法"""

    @pytest.fixture
    def service(self, tmp_path):
        """创建使用临时目录的 ProjectService 实例"""
        # 使用临时目录作为 user_home，避免影响真实环境
        temp_user_home = tmp_path / "user_home"
        temp_user_home.mkdir()
        return ProjectService(user_home=temp_user_home)

    @pytest.mark.asyncio
    async def test_delete_project_success(self, service, mock_get_db, tmp_path):
        """测试成功删除项目"""
        import json

        # 创建临时目录
        temp_dir = tmp_path / "temp_test"
        temp_dir.mkdir()

        # 创建项目路径
        project_path = temp_dir / "test-project"
        project_path.mkdir()

        # 创建 session 目录
        session_path = temp_dir / "sessions" / "test-session"
        session_path.mkdir(parents=True)
        (session_path / "session1.jsonl").write_text("{}\n")

        # 创建临时 .claude.json 配置（使用临时目录）
        # service fixture 已经创建了 user_home 目录，这里直接使用
        temp_user_home = tmp_path / "user_home"
        claude_json_path = temp_user_home / ".claude.json"

        # 创建测试配置
        test_config = {
            "projects": {
                str(project_path): {
                    "allowedTools": ["claude"],
                    "mcpServers": {},
                }
            }
        }
        with open(claude_json_path, "w") as f:
            json.dump(test_config, f)

        # 创建数据库项目
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path=str(project_path),
                claude_session_path=str(session_path),
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                favorited=False,
                favorited_at=None,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        # 验证项目存在
        existing_project = await ai_project_crud.get_by_id(mock_get_db, id=project.id)
        assert existing_project is not None

        # 删除项目
        result = await service.delete_project(project.id)
        await mock_get_db.commit()

        assert result is True

        # 验证数据库中的项目已删除
        deleted_project = await ai_project_crud.get_by_id(mock_get_db, id=project.id)
        assert deleted_project is None

        # 验证临时 .claude.json 中的配置已删除
        with open(claude_json_path, "r") as f:
            config = json.load(f)
        assert str(project_path) not in config.get("projects", {})

        # 验证 session 目录已删除
        assert not session_path.exists()

    @pytest.mark.asyncio
    async def test_delete_project_nonexistent(self, service, mock_get_db):
        """测试删除不存在的项目"""
        result = await service.delete_project(99999)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_project_without_path_or_session(self, service, mock_get_db):
        """测试删除没有路径和 session 的项目"""
        # 创建没有路径信息的测试项目
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path=None,
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        # 删除项目
        result = await service.delete_project(project.id)
        await mock_get_db.commit()

        assert result is True

        # 验证数据库中的项目已删除
        deleted_project = await ai_project_crud.get_by_id(mock_get_db, id=project.id)
        assert deleted_project is None


class TestFavoriteProject:
    """测试 favorite_project 方法"""

    @pytest.fixture
    def service(self):
        """创建 ProjectService 实例"""
        return ProjectService()

    @pytest.mark.asyncio
    async def test_favorite_project_success(self, service, mock_get_db):
        """测试成功收藏项目"""
        # 创建测试项目
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path="/path/to/project",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        # 收藏项目
        result = await service.favorite_project(project.id)
        await mock_get_db.commit()

        assert result is not None
        assert result.id == project.id
        assert result.favorited is True
        assert result.favorited_at is not None

    @pytest.mark.asyncio
    async def test_favorite_project_nonexistent(self, service, mock_get_db):
        """测试收藏不存在的项目"""
        result = await service.favorite_project(99999)

        assert result is None

    @pytest.mark.asyncio
    async def test_favorite_project_already_favorited(self, service, mock_get_db):
        """测试收藏已收藏的项目（更新收藏时间）"""

        # 创建测试项目
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path="/path/to/project",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        # 第一次收藏
        result1 = await service.favorite_project(project.id)
        await mock_get_db.commit()
        first_favorited_at = result1.favorited_at

        # 等待一小段时间（确保时间戳不同）
        import asyncio

        await asyncio.sleep(0.01)

        # 第二次收藏（更新时间）
        result2 = await service.favorite_project(project.id)
        await mock_get_db.commit()

        assert result2.favorited is True
        assert result2.favorited_at is not None
        # 验证时间已更新
        assert result2.favorited_at >= first_favorited_at


class TestUnfavoriteProject:
    """测试 unfavorite_project 方法"""

    @pytest.fixture
    def service(self):
        """创建 ProjectService 实例"""
        return ProjectService()

    @pytest.mark.asyncio
    async def test_unfavorite_project_success(self, service, mock_get_db):
        """测试成功取消收藏"""
        # 创建测试项目并收藏
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path="/path/to/project",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        # 先收藏
        await service.favorite_project(project.id)
        await mock_get_db.commit()

        # 取消收藏
        result = await service.unfavorite_project(project.id)
        await mock_get_db.commit()

        assert result is not None
        assert result.id == project.id
        assert result.favorited is False
        # favorited_at 可以保留原来的值，不强制要求为 None

    @pytest.mark.asyncio
    async def test_unfavorite_project_nonexistent(self, service, mock_get_db):
        """测试取消收藏不存在的项目"""
        result = await service.unfavorite_project(99999)

        assert result is None

    @pytest.mark.asyncio
    async def test_unfavorite_project_not_favorited(self, service, mock_get_db):
        """测试取消未收藏的项目"""
        # 创建测试项目
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path="/path/to/project",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        # 取消收藏（项目未收藏）
        result = await service.unfavorite_project(project.id)
        await mock_get_db.commit()

        assert result is not None
        assert result.favorited is False
        # favorited_at 可以保留原来的值（或为 None），不强制要求


class TestClearRemovedProjects:
    """测试 clear_removed_projects 方法"""

    @pytest.fixture
    def service(self):
        """创建 ProjectService 实例"""
        return ProjectService()

    @pytest.mark.asyncio
    async def test_clear_removed_projects_success(self, service, mock_get_db):
        """测试成功清理已移除的项目"""
        # 创建三个项目：两个已移除，一个未移除
        project1 = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="removed-project-1",
                project_path="/path/to/project1",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=True,
                favorited=False,
                favorited_at=None,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )

        project2 = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="removed-project-2",
                project_path="/path/to/project2",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=True,
                favorited=False,
                favorited_at=None,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )

        project3 = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="active-project",
                project_path="/path/to/project3",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        # Mock scan_and_save_all_projects 方法（避免实际扫描）
        async def mock_scan():
            pass

        service.scan_and_save_all_projects = mock_scan

        # Mock delete_project 方法（避免实际删除文件系统）
        deleted_ids = []

        async def mock_delete(project_id):
            deleted_ids.append(project_id)
            return True

        service.delete_project = mock_delete

        # 清理已移除的项目
        result = await service.clear_removed_projects()
        await mock_get_db.commit()

        # 应该成功删除
        assert result is True
        # 应该删除了两个项目
        assert len(deleted_ids) == 2
        # 验证删除的是已移除的项目
        assert project1.id in deleted_ids
        assert project2.id in deleted_ids
        assert project3.id not in deleted_ids

    @pytest.mark.asyncio
    async def test_clear_removed_projects_empty(self, service, mock_get_db):
        """测试清理没有已移除项目的情况"""
        # 创建未移除的项目
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="active-project",
                project_path="/path/to/project",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        # Mock scan_and_save_all_projects 方法
        async def mock_scan():
            pass

        service.scan_and_save_all_projects = mock_scan

        # 清理已移除的项目
        result = await service.clear_removed_projects()

        # 应该成功（没有项目需要删除）
        assert result is True

    @pytest.mark.asyncio
    async def test_clear_removed_projects_partial_failure(self, service, mock_get_db):
        """测试部分删除失败的情况"""
        # 创建两个已移除的项目
        project1 = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="removed-project-1",
                project_path="/path/to/project1",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=True,
                favorited=False,
                favorited_at=None,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )

        project2 = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="removed-project-2",
                project_path="/path/to/project2",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=True,
                favorited=False,
                favorited_at=None,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        # Mock scan_and_save_all_projects 方法
        async def mock_scan():
            pass

        service.scan_and_save_all_projects = mock_scan

        # Mock delete_project 方法（第一个成功，第二个失败）
        call_count = 0

        async def mock_delete(project_id):
            nonlocal call_count
            call_count += 1
            return call_count == 1  # 只有第一次返回 True

        service.delete_project = mock_delete

        # 清理已移除的项目
        result = await service.clear_removed_projects()

        # 应该返回 False（有失败）
        assert result is False


class TestListProjectsFavorited:
    """测试 list_projects 方法对收藏项目的排序"""

    @pytest.mark.asyncio
    async def test_list_projects_with_favorited(self, mock_get_db):
        """测试列出项目时收藏项目优先排序"""
        # 创建三个项目：一个收藏，两个未收藏
        await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="normal-project-1",
                project_path="/path/to/project1",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                favorited=False,
                favorited_at=None,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 3, 10, 0, 0),  # 最新
            ),
        )

        await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="favorited-project",
                project_path="/path/to/project2",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                favorited=True,
                favorited_at=datetime(2024, 1, 2, 10, 0, 0),
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )

        await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="normal-project-2",
                project_path="/path/to/project3",
                claude_session_path=None,
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                favorited=False,
                favorited_at=None,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 2, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        service = ProjectService()
        result = await service.list_projects()

        assert len(result) == 3
        # 收藏项目应该排在第一位
        assert result[0].project_name == "favorited-project"
        assert result[0].favorited is True
        # 未收藏项目按 last_active_at 降序
        assert result[1].project_name == "normal-project-1"
        assert result[2].project_name == "normal-project-2"


class TestScanSessions:
    """测试 scan_sessions 方法"""

    @pytest.fixture
    def service(self):
        """创建 ProjectService 实例"""
        return ProjectService()

    @pytest.mark.asyncio
    async def test_scan_sessions_project_not_found(self, service):
        """测试扫描不存在的项目"""
        with pytest.raises(ValueError, match="项目 '999' 不存在"):
            await service.scan_sessions(999)

    @pytest.mark.asyncio
    async def test_scan_sessions_no_session_path(self, service, mock_get_db):
        """测试项目没有 session 路径"""
        # 创建没有 session 路径的项目
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path="/path/to/project",
                claude_session_path=None,  # 没有 session 路径
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        # 应该返回空列表（不抛出异常）
        result = await service.scan_sessions(project.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_scan_sessions_nonexistent_path(self, service, mock_get_db, tmp_path):
        """测试 session 路径不存在"""
        # 创建项目，session 路径不存在
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path="/path/to/project",
                claude_session_path=str(
                    tmp_path / "nonexistent" / "sessions"
                ),  # 不存在的路径
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        # 应该返回空列表
        result = await service.scan_sessions(project.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_scan_sessions_with_existing_titles(
        self, service, mock_get_db, tmp_path
    ):
        """测试使用数据库中的 title，减少文件读取"""
        import json

        # 创建 session 目录和文件
        session_path = tmp_path / "sessions"
        session_path.mkdir()

        # 创建两个 session 文件
        session1_file = session_path / "session1.jsonl"
        session2_file = session_path / "session2.jsonl"

        # 写入简单的 session 数据（使用 user 消息而不是 summary）
        session1_data = [
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:00Z",
                "message": {"role": "user", "content": "Session 1 Title"},
            }
        ]
        session2_data = [
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:00Z",
                "message": {"role": "user", "content": "Session 2 Title"},
            }
        ]

        session1_file.write_text("\n".join(json.dumps(d) for d in session1_data) + "\n")
        session2_file.write_text("\n".join(json.dumps(d) for d in session2_data) + "\n")

        # 创建项目
        project = await ai_project_crud.create(
            mock_get_db,
            obj_in=AIProjectCreate(
                project_name="test-project",
                project_path="/path/to/project",
                claude_session_path=str(session_path),
                git_worktree_project=False,
                git_main_project_path=None,
                removed=False,
                ai_tools=[AiToolType.CLAUDE],
                first_active_at=datetime(2024, 1, 1, 10, 0, 0),
                last_active_at=datetime(2024, 1, 1, 10, 0, 0),
            ),
        )
        await mock_get_db.commit()

        # 在数据库中创建 session1 的记录（带 title）
        await ai_project_session_crud.create(
            mock_get_db,
            obj_in=AIProjectSessionCreate(
                session_id="session1",
                project_id=project.id,
                session_file=str(session1_file),
                title="DB Title for Session 1",  # 数据库中的 title
                file_mtime=datetime(2024, 1, 1, 10, 0, 0),
                file_size=100,
                is_agent_session=False,
                ai_tool=AiToolType.CLAUDE,
                project_path=None,
                git_branch=None,
                session_file_md5=None,
                first_active_at=None,
                last_active_at=None,
            ),
        )
        await mock_get_db.commit()

        # 扫描 sessions
        result = await service.scan_sessions(project.id)

        # 验证结果
        assert len(result) == 2

        # 找到 session1 和 session2
        session1_result = next((s for s in result if s.session_id == "session1"), None)
        session2_result = next((s for s in result if s.session_id == "session2"), None)

        assert session1_result is not None
        assert session2_result is not None

        # session1 应该使用数据库中的 title
        assert session1_result.title == "DB Title for Session 1"

        # session2 应该从文件中读取 title（因为数据库中没有）
        assert session2_result.title == "Session 2 Title"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
