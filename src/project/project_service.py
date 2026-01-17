"""
扫描服务模块

负责调用 Claude 项目扫描器，并将扫描结果保存到数据库
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from ..claude.claude_projects_scanner import (
    ClaudeProject,
    ClaudeProjectsScanner,
)
from ..claude.claude_session_operations import (
    ClaudeSessionInfo,
    ClaudeSessionOperations,
)
from ..database.connection import get_db
from ..database.cruds import ai_project_crud, ai_project_session_crud
from ..database.orms.ai_project import AIProject
from ..database.schemas.ai_project import (
    AIProjectCreate,
    AIProjectInDB,
    AIProjectUpdate,
    AiToolType,
)
from ..database.schemas.ai_project_session import (
    AIProjectSessionCreate,
    AIProjectSessionUpdate,
)

logger = logging.getLogger(__name__)


class ProjectService:
    """扫描服务类，处理 Claude 项目的扫描和数据持久化"""

    def __init__(self, claude_projects_path: Optional[Path] = None):
        """
        初始化扫描服务

        Args:
            claude_projects_path: Claude 项目目录路径，默认为 $USER/.claude/projects
        """
        self.scanner = ClaudeProjectsScanner(claude_projects_path)
        self.projects_path = self.scanner.projects_path
        self._background_tasks: Set[asyncio.Task] = set()

    async def _run_background_task(self, coro):
        """
        运行后台任务并自动清理完成的任务

        Args:
            coro: 要执行的协程
        """
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    async def _cleanup_stale_sessions(
        self,
        db: AsyncSession,
        existing_sessions_map: dict,
        new_session_ids: Set[str],
        project_name: str,
    ) -> tuple[int, int]:
        """
        清理会话：删除不再存在的会话，恢复重新出现的会话

        Args:
            db: 数据库会话
            existing_sessions_map: 数据库中现有会话的映射 {session_id: session}
            new_session_ids: 新扫描到的会话ID集合
            project_name: 项目名称（用于日志）

        Returns:
            (deleted_count, restored_count): 删除的会话数量和恢复的会话数量
        """
        deleted_count = 0
        restored_count = 0

        for session_id, existing_session in existing_sessions_map.items():
            if session_id not in new_session_ids:
                # 会话不再存在，软删除（如果还未删除）
                if not existing_session.removed:
                    try:
                        await ai_project_session_crud.delete(
                            db, id=str(existing_session.id)
                        )
                        deleted_count += 1
                        logger.debug(
                            f"Soft deleted stale session: {session_id} from project {project_name}"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to delete session {session_id}: {e}")
            else:
                # 会话重新出现，恢复（如果已删除）
                if existing_session.removed:
                    try:
                        await ai_project_session_crud.restore(
                            db, id=str(existing_session.id)
                        )
                        restored_count += 1
                        logger.debug(
                            f"Restored session: {session_id} in project {project_name}"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to restore session {session_id}: {e}")

        return deleted_count, restored_count

    async def _get_existing_sessions_map(
        self, db: AsyncSession, project_id: int
    ) -> tuple[dict, dict]:
        """
        获取项目的现有会话映射

        Args:
            db: 数据库会话
            project_id: 项目ID

        Returns:
            (sessions_map, titles_map): (session_id -> session, session_id -> title)
        """
        existing_sessions = await ai_project_session_crud.get_by_project_id(
            db, project_id=project_id, include_removed=True
        )

        sessions_map = {s.session_id: s for s in existing_sessions}
        titles_map = {
            s.session_id: s.title
            for s in existing_sessions
            if s.title and not s.removed
        }

        return sessions_map, titles_map

    async def _process_session_list(
        self,
        db: AsyncSession,
        scanned_session_infos: List,
        existing_sessions_map: dict,
        db_project,
        ai_tool_type: AiToolType,
        project_name: str,
    ) -> tuple[int, int]:
        """
        处理会话列表，保存或更新会话

        Args:
            db: 数据库会话
            scanned_session_infos: 扫描到的会话信息列表
            existing_sessions_map: 现有会话映射
            db_project: 数据库中的项目信息
            ai_tool_type: AI工具类型
            project_name: 项目名称

        Returns:
            (scanned_count, skipped_count): 扫描的会话数量和跳过的会话数量
        """
        scanned_count = 0
        skipped_count = 0

        for session_info in scanned_session_infos:
            session_id = session_info.session_id
            existing_session = existing_sessions_map.get(session_id)

            # 检查是否需要跳过（文件未变化）
            if existing_session and not existing_session.removed:
                if not self._should_update_session(existing_session, session_info):
                    skipped_count += 1
                    logger.debug(
                        f"Skipping unchanged session: {session_id} in project {project_name}"
                    )
                    continue

            # 保存或更新会话
            await self._save_session_from_info(
                db, session_info, db_project.id, ai_tool_type
            )
            scanned_count += 1

        return scanned_count, skipped_count

    async def scan_and_save_all_project_sessions(
        self, projects: List[ClaudeProject]
    ) -> bool:
        """
        扫描所有项目的 session 列表（只加载元数据，支持增量扫描）

        Args:
            projects: 项目列表

        Returns:
            操作是否成功
        """
        logger.info("Starting to scan all project sessions...")

        if not projects:
            logger.info("No projects to scan sessions for")
            return True

        total_scanned = 0
        total_skipped = 0
        total_processed = 0
        failed_projects = 0

        # 每个项目独立处理数据库逻辑
        for project in projects:
            try:
                scanned, skipped = await self._scan_project_sessions(
                    project, AiToolType.CLAUDE
                )
                total_scanned += scanned
                total_skipped += skipped
                total_processed += 1
            except Exception as e:
                failed_projects += 1
                logger.error(
                    f"Failed to scan sessions for project {project.project_name}: {e}"
                )

        logger.info(
            f"Session scan completed: processed {total_processed} projects, "
            f"scanned {total_scanned} sessions, skipped {total_skipped} unchanged sessions"
        )
        if failed_projects > 0:
            logger.warning(f"Failed to scan {failed_projects} projects")

        return True

    async def _scan_project_sessions(
        self, project: ClaudeProject, ai_tool_type: AiToolType
    ) -> tuple[int, int]:
        """
        增量扫描并保存项目的 sessions（每个项目独立管理数据库连接）

        Args:
            project: 项目信息（来自 scanner）
            ai_tool_type: AI工具类型

        Returns:
            (scanned_count, skipped_count): 扫描的 session 数量和跳过的 session 数量
        """
        # 检查项目是否有 session 路径
        if not project.project_session_path:
            logger.debug(
                f"Project {project.project_name} has no session path, skipping"
            )
            return 0, 0

        session_path = Path(project.project_session_path)
        if not session_path.exists():
            logger.debug(f"Session directory does not exist: {session_path}")
            return 0, 0

        # 每个项目独立管理数据库事务
        async with get_db() as db:
            try:
                # 从数据库读取项目信息以获取 project_id
                db_project = await ai_project_crud.read_by_path(
                    db, project_path=project.project_path
                )
                if not db_project:
                    logger.warning(
                        f"Project not found in database: {project.project_name}"
                    )
                    return 0, 0

                # 获取现有会话映射
                existing_sessions_map, existing_titles = (
                    await self._get_existing_sessions_map(db, db_project.id)
                )

                logger.debug(
                    f"Project {project.project_name}: found {len(existing_titles)} sessions with existing titles"
                )

                # 扫描所有 session 元数据（传入已有 title，避免重复读取文件）
                session_ops = ClaudeSessionOperations(session_path)
                scanned_session_infos = await session_ops.scan_sessions(existing_titles)

                # 获取扫描到的 session ID 集合（可能为空）
                scanned_session_ids = {
                    info.session_id for info in scanned_session_infos
                }

                # 删除不再存在的会话，恢复重新出现的会话
                deleted_count, restored_count = await self._cleanup_stale_sessions(
                    db,
                    existing_sessions_map,
                    scanned_session_ids,
                    project.project_name,
                )

                # 如果扫描结果为空，只进行清理，不需要保存新会话
                if not scanned_session_infos:
                    await db.commit()
                    logger.debug(
                        f"Project {project.project_name}: no sessions found, "
                        f"deleted {deleted_count} existing sessions"
                    )
                    return 0, 0

                # 处理会话列表（保存或更新）
                scanned_count, skipped_count = await self._process_session_list(
                    db,
                    scanned_session_infos,
                    existing_sessions_map,
                    db_project,
                    ai_tool_type,
                    project.project_name,
                )

                await db.commit()
                logger.debug(
                    f"Project {project.project_name}: scanned {scanned_count} sessions, "
                    f"skipped {skipped_count} unchanged, deleted {deleted_count}, restored {restored_count}"
                )

            except Exception as e:
                await db.rollback()
                logger.error(
                    f"Failed to scan sessions for project {project.project_name}: {e}"
                )
                raise

        return scanned_count, skipped_count

    def _should_update_session(
        self, existing_session, session_info: ClaudeSessionInfo
    ) -> bool:
        """
        检查会话是否需要更新

        Args:
            existing_session: 数据库中已存在的会话
            session_info: 扫描到的会话信息

        Returns:
            bool: 是否需要更新
        """
        return (
            existing_session.file_mtime != session_info.file_mtime
            or existing_session.file_size != session_info.file_size
        )

    async def _save_session_from_info(
        self,
        db: AsyncSession,
        session_info: ClaudeSessionInfo,
        project_id: int,
        ai_tool_type: AiToolType,
    ):
        """
        从 ClaudeSessionInfo 保存或更新会话

        Args:
            db: 数据库会话
            session_info: Session 简要信息
            project_id: 项目ID
            ai_tool_type: AI工具类型
        """
        existing_session = await ai_project_session_crud.get_by_project_session(
            db, project_id=str(project_id), session_id=session_info.session_id
        )

        # 通用字段（用于 create 和 update）
        common_fields = {
            "file_mtime": session_info.file_mtime,
            "file_size": session_info.file_size,
            "ai_tool": ai_tool_type,
            "session_file_md5": None,
            "first_active_at": None,
            "last_active_at": None,
        }

        if existing_session:
            # 更新已存在的会话
            if self._should_update_session(existing_session, session_info):
                update_data = AIProjectSessionUpdate(**common_fields)
                await ai_project_session_crud.update(
                    db, id=existing_session.id, obj_update=update_data
                )
                logger.debug(f"Updated session: {session_info.session_id}")
        else:
            # 创建新会话
            create_data = AIProjectSessionCreate(
                session_id=session_info.session_id,
                project_id=project_id,
                session_file=session_info.session_file,
                title=session_info.title,
                is_agent_session=session_info.is_agent_session,
                project_path=None,
                git_branch=None,
                **common_fields,
            )
            await ai_project_session_crud.create(db, obj_in=create_data)
            logger.debug(f"Created new session: {session_info.session_id}")

    async def scan_and_save_all_projects(self) -> bool:
        """
        扫描所有项目并保存到数据库
        完成后会自动在后台启动 session 扫描任务

        Returns:
            操作是否成功
        """
        logger.info("Starting to scan Claude projects...")

        # 执行扫描（异步）
        projects = await self.scanner.scan_all_projects()

        # 获取数据库会话
        async with get_db() as db:
            try:
                # 获取数据库中所有现有项目
                existing_projects = await ai_project_crud.read_all(db)

                # 构建现有项目的project_path集合和新扫描到的project_path集合
                existing_project_paths = {
                    p.project_path for p in existing_projects if p.project_path
                }
                new_project_paths = {p.project_path for p in projects}

                # 找出需要标记为移除的项目（数据库中存在但扫描结果中不存在）
                projects_to_mark_removed = existing_project_paths - new_project_paths

                # 批量标记不再存在的项目为 removed=True
                if projects_to_mark_removed:
                    project_ids_to_remove = [
                        p.id
                        for p in existing_projects
                        if p.project_path in projects_to_mark_removed
                    ]
                    affected_count = await ai_project_crud.remove_projects(
                        db, project_ids=project_ids_to_remove
                    )
                    logger.info(
                        f"Marked {affected_count} projects as removed: {projects_to_mark_removed}"
                    )

                if not projects:
                    logger.info("No projects found")
                    await db.commit()
                    return True

                # 处理每个项目
                for claude_project in projects:
                    await self._save_project_to_db(
                        db, claude_project, AiToolType.CLAUDE
                    )

                await db.commit()
                logger.info(f"Scan completed, processed {len(projects)} projects")

                # 自动在后台启动 session 扫描任务
                try:
                    await self._run_background_task(
                        self.scan_and_save_all_project_sessions(projects)
                    )
                    logger.info("Started background session scanning task")
                except Exception as e:
                    logger.warning(f"Failed to start session scanning: {e}")

                return True

            except Exception as e:
                await db.rollback()
                logger.error(f"Error occurred during scan: {e}")
                raise e

    async def _save_project_to_db(
        self,
        db: AsyncSession,
        claude_project: ClaudeProject,
        ai_tool_type: AiToolType,
    ):
        """
        将 Claude 项目保存到数据库（不包括 session）

        Args:
            db: 数据库会话
            claude_project: Claude 项目对象
            ai_tool_type: AI工具类型

        Returns:
            保存后的项目对象
        """
        existing_project = await ai_project_crud.read_by_path(
            db, project_path=claude_project.project_path
        )

        if existing_project:
            update_data = AIProjectUpdate(
                project_name=claude_project.project_name,
                claude_session_path=claude_project.project_session_path,
                git_worktree_project=claude_project.git_worktree_project,
                git_main_project_path=claude_project.git_main_project_path,
                removed=claude_project.removed,
                ai_tools=[ai_tool_type],
                first_active_at=claude_project.first_active_at,
                last_active_at=claude_project.last_active_at,
            )
            existing_project = await ai_project_crud.update(
                db, id=existing_project.id, obj_update=update_data
            )
            logger.debug(f"Updated project: {claude_project.project_name}")
        else:
            create_data = AIProjectCreate(
                project_name=claude_project.project_name,
                project_path=claude_project.project_path,
                claude_session_path=claude_project.project_session_path,
                git_worktree_project=claude_project.git_worktree_project,
                git_main_project_path=claude_project.git_main_project_path,
                removed=claude_project.removed,
                ai_tools=[ai_tool_type],
                first_active_at=claude_project.first_active_at,
                last_active_at=claude_project.last_active_at,
            )
            existing_project = await ai_project_crud.create(db, obj_in=create_data)
            logger.debug(f"Created new project: {claude_project.project_name}")

        return existing_project

    async def list_projects(self) -> List[AIProjectInDB]:
        """
        获取所有项目列表，按照 last_active_at 逆序排序

        Returns:
            项目列表，按照 last_active_at 逆序排序
        """
        async with get_db() as db:
            # 查询所有项目，按照 last_active_at 逆序排序
            # NULL 值排在最后
            projects = await ai_project_crud.read_all(
                db, order_by=AIProject.last_active_at.desc()
            )

            return projects

    async def get_project_by_id(self, project_id: int) -> Optional[AIProjectInDB]:
        """
        根据ID获取单个项目

        Args:
            project_id: 项目ID

        Returns:
            项目信息，如果不存在则返回None
        """
        async with get_db() as db:
            project = await ai_project_crud.get_by_id(db, id=project_id)
            return project


# 创建全局扫描服务实例
project_service = ProjectService()
