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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
