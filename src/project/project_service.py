"""
扫描服务模块

负责调用 Claude 项目扫描器，并将扫描结果保存到数据库
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..claude.claude_projects_scanner import (
    ClaudeProject,
    ClaudeProjectsScanner,
    ClaudeSession,
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

# 配置日志
logging.basicConfig(level=logging.INFO)
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

    async def scan_and_save_all_projects(self) -> bool:
        """
        扫描所有项目并保存到数据库

        Returns:
            操作是否成功
        """
        logger.info("Starting to scan Claude projects...")

        # 执行扫描
        projects = self.scanner.scan_all_projects()

        if not projects:
            logger.info("No projects found")
            return True

        # 获取数据库会话
        async for db in get_db():
            try:
                # 处理每个项目
                for claude_project in projects:
                    await self._save_project_to_db(
                        db, claude_project, AiToolType.CLAUDE
                    )

                await db.commit()
                logger.info(f"Scan completed, processed {len(projects)} projects")
                return True

            except Exception as e:
                await db.rollback()
                logger.error(f"Error occurred during scan: {e}")
                raise e

    async def scan_and_save_single_project(self, project_id: str) -> bool:
        """
        扫描单个项目并保存到数据库

        Args:
            project_id: 项目ID

        Returns:
            操作是否成功
        """
        logger.info(f"Starting to scan project: {project_id}")

        # 先从数据库获取项目信息
        async for db in get_db():
            try:
                # 获取项目信息
                project = await ai_project_crud._read_by_id(db, id=project_id)
                if not project:
                    logger.warning(f"Project does not exist: {project_id}")
                    return None

                # 从项目信息获取项目路径
                project_path = project.project_path
                if not project_path:
                    logger.warning(
                        f"Project {project_id} has no project path configured"
                    )
                    return None

                # 构建项目目录路径（从完整路径提取目录名）
                path_obj = Path(project_path)
                project_dir = path_obj.name

                logger.info(f"Scanning project path: {project_dir}")

                # 调用扫描器扫描指定项目
                claude_project = self.scanner.scan_project_sessions(
                    project_dir, Path(project_path)
                )

                if claude_project is None:
                    logger.warning(f"Failed to scan project: {project_id}")
                    return False

                # 保存项目到数据库
                await self._save_project_to_db(db, claude_project, AiToolType.CLAUDE)
                await db.commit()
                logger.info(f"Project scan completed: {project_id}")

                return True

            except Exception as e:
                await db.rollback()
                logger.error(f"Error occurred while scanning project {project_id}: {e}")
                raise e

    async def _save_project_to_db(
        self, db: AsyncSession, claude_project: ClaudeProject, ai_tool_type: AiToolType
    ):
        """
        将 Claude 项目保存到数据库

        Args:
            db: 数据库会话
            claude_project: Claude 项目对象
            ai_tool_type: AI工具类型
        """

        # 检查项目是否已存在
        existing_project = await ai_project_crud.read_by_path(
            db, project_path=claude_project.project_path
        )

        if existing_project:
            # 创建更新数据
            update_data = AIProjectUpdate(
                project_name=claude_project.project_name,
                claude_session_path=claude_project.project_session_path,
                ai_tools=[ai_tool_type],
                first_active_at=claude_project.first_active_at,
                last_active_at=claude_project.last_active_at,
            )
            existing_project = await ai_project_crud.update(
                db, id=existing_project.id, obj_update=update_data
            )
            logger.debug(f"Updating project: {claude_project.project_name}")
        else:
            # 创建新项目数据
            create_data = AIProjectCreate(
                project_name=claude_project.project_name,
                project_path=claude_project.project_path,
                claude_session_path=claude_project.project_session_path,
                ai_tools=[ai_tool_type],
                first_active_at=claude_project.first_active_at,
                last_active_at=claude_project.last_active_at,
            )
            existing_project = await ai_project_crud.create(db, obj_in=create_data)
            logger.debug(f"Creating new project: {claude_project.project_name}")

        # 处理项目会话
        for session_key, claude_session in claude_project.sessions.items():
            await self._save_session_to_db(
                db, claude_session, existing_project.id, ai_tool_type
            )

    async def _save_session_to_db(
        self,
        db: AsyncSession,
        claude_session: ClaudeSession,
        project_id: int,
        ai_tool_type: AiToolType,
    ):
        """
        将 Claude 会话保存到数据库

        Args:
            db: 数据库会话
            claude_session: Claude 会话对象
            project_id: 项目ID
            ai_tool_type: AI工具类型
        """

        # 检查会话是否已存在
        existing_session = await ai_project_session_crud.get_by_project_session(
            db, project_id=project_id, session_id=claude_session.session_id
        )

        if existing_session:
            # 检查文件是否有变化（通过 MD5）
            if existing_session.session_file_md5 != claude_session.session_file_md5:
                # 创建更新数据
                update_data = AIProjectSessionUpdate(
                    session_file_md5=claude_session.session_file_md5,
                    ai_tool=ai_tool_type,
                    first_active_at=claude_session.first_active_at,
                    last_active_at=claude_session.last_active_at,
                )
                await ai_project_session_crud.update(
                    db, id=existing_session.id, obj_update=update_data
                )
                logger.debug(f"Updating session: {claude_session.session_id}")
            else:
                logger.debug(f"Session unchanged: {claude_session.session_id}")
        else:
            # 创建新会话数据
            create_data = AIProjectSessionCreate(
                session_id=claude_session.session_id,
                project_id=project_id,
                session_file=claude_session.session_file,
                session_file_md5=claude_session.session_file_md5,
                is_agent_session=claude_session.is_agent_session,
                ai_tool=ai_tool_type,
                project_path=claude_session.project_path,
                git_branch=claude_session.git_branch,
                first_active_at=claude_session.first_active_at,
                last_active_at=claude_session.last_active_at,
            )
            await ai_project_session_crud.create(db, obj_in=create_data)
            logger.debug(f"Creating new session: {claude_session.session_id}")

    async def get_project_status(self, project_id: str) -> Optional[Dict]:
        """
        获取项目状态信息

        Args:
            project_id: 项目ID

        Returns:
            项目状态信息字典，如果项目不存在则返回 None
        """
        async for db in get_db():
            try:
                project = await ai_project_crud._read_by_id(db, id=project_id)
                if not project:
                    return None

                # 获取项目的所有会话
                sessions = await ai_project_session_crud.get_by_project_id(
                    db, project_id=project_id
                )

                return {
                    "project_key": project.id,
                    "project_name": project.project_name,
                    "project_path": project.project_path,
                    "ai_tools": project.ai_tools,
                    "created_at": project.created_at,
                    "updated_at": project.updated_at,
                    "sessions": [
                        {
                            "session_id": s.session_id,
                            "ai_tool": s.ai_tool,
                            "is_agent_session": s.is_agent_session,
                            "created_at": s.created_at,
                            "updated_at": s.updated_at,
                        }
                        for s in sessions
                    ],
                }

            except Exception as e:
                logger.error(f"Error occurred while getting project status: {e}")
                raise

    async def list_projects(self) -> List[AIProjectInDB]:
        """
        获取所有项目列表，按照 last_active_at 逆序排序

        Returns:
            项目列表，按照 last_active_at 逆序排序
        """
        async for db in get_db():
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
        async for db in get_db():
            project = await ai_project_crud.get_by_id(db, id=project_id)
            return project


# 创建全局扫描服务实例
project_service = ProjectService()
