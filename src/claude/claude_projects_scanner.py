"""
Claude Projects Scanner

This module provides functionality to scan and analyze Claude projects
stored in $USER/.claude/projects, extracting project information and session data.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from ..utils.process_utils import run_process
from .claude_session_operations import ClaudeSessionOperations
from .settings_helper import load_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("claude")


class ClaudeProject(BaseModel):
    """Pydantic model representing a Claude project."""

    project_name: str
    project_path: str = Field(exclude=True)  # Exclude from serialization
    project_session_path: Optional[str] = None  # Session storage path
    first_active_at: Optional[datetime] = Field(
        default=None, exclude=True
    )  # Exclude from serialization
    last_active_at: Optional[datetime] = Field(
        default=None, exclude=True
    )  # Exclude from serialization
    git_worktree_project: Optional[bool] = Field(
        default=None, description="是否为 git worktree 项目"
    )
    git_main_project_path: Optional[str] = Field(
        default=None, description="git worktree 项目的主项目路径"
    )
    removed: Optional[bool] = Field(default=None, description="项目路径是否已被移除")


class ClaudeProjectsScanner:
    """Main scanner class for Claude projects with all business logic."""

    def __init__(
        self,
        claude_projects_path: Optional[Path] = None,
        user_home: Optional[Path] = None,
    ):
        """
        Initialize the Claude projects scanner.

        Args:
            claude_projects_path: Path to the Claude projects directory.
                If None, defaults to $USER_HOME/.claude/projects
            user_home: Custom user home directory for testing purposes.
                If None, defaults to Path.home()
        """
        # Use custom user_home if provided, otherwise use system home
        home_dir = user_home if user_home is not None else Path.home()

        if claude_projects_path is None:
            # Default to $USER_HOME/.claude/projects
            claude_projects_path = home_dir / ".claude" / "projects"

        self.projects_path = claude_projects_path
        self.user_home = home_dir

    def load_valid_projects(self) -> set:
        """从 ~/.claude.json 加载合法项目路径集合"""
        config_path = self.user_home / ".claude.json"
        try:
            config = load_config(config_path)
            projects_dict = config.get("projects", {})
            # 返回项目路径的集合，并进行标准化处理以便匹配
            valid_projects = set()
            for proj_path in projects_dict.keys():
                try:
                    # 使用 Path.resolve() 标准化路径
                    normalized_path = str(Path(proj_path).resolve())
                    valid_projects.add(normalized_path)
                except Exception:
                    # 如果路径解析失败，保留原始路径
                    valid_projects.add(proj_path)
            return valid_projects
        except Exception as e:
            logger.error(f"Failed to load valid projects: {e}")
            return set()

    def _create_claude_project(
        self,
        project_path: str,
        project_session_path: Optional[str],
        last_active_at: Optional[datetime] = None,
    ) -> ClaudeProject:
        """
        创建 ClaudeProject 对象的辅助方法

        Args:
            project_path: 项目路径
            project_session_path: 项目 session 路径（可能为 None）
            last_active_at: 最后活跃时间（可能为 None）

        Returns:
            ClaudeProject: 创建的项目对象
        """
        proj_path = Path(project_path)
        project_name = proj_path.name if proj_path.name else proj_path.parts[-1]

        # 检测是否为 worktree
        is_worktree, main_project_path = self.detect_git_worktree(project_path)

        # 检查路径是否存在
        is_removed = not proj_path.exists()
        if is_removed:
            logger.info(f"Project path has been removed: {project_path}")

        return ClaudeProject(
            project_name=project_name,
            project_path=project_path,
            project_session_path=project_session_path,
            first_active_at=None,
            last_active_at=last_active_at,
            git_worktree_project=is_worktree,
            git_main_project_path=main_project_path,
            removed=is_removed,
        )

    async def scan_project_info(
        self, project_session_path: Path, valid_projects: set
    ) -> Optional[ClaudeProject]:
        """
        快速扫描项目基本信息（使用 session_ops 快速提取路径和活跃时间）

        Args:
            project_session_path: 项目 session 目录路径
            valid_projects: 合法项目路径集合

        Returns:
            Optional[ClaudeProject]: 项目基本信息，sessions 为空字典
        """
        if not project_session_path.exists():
            return None

        # 使用 ClaudeSessionOperations 快速扫描项目路径和最后活跃时间
        session_ops = ClaudeSessionOperations(project_session_path)
        project_display_path, last_active_at = await session_ops.detect_project_info()

        # 如果没有找到项目路径，返回 None
        if not project_display_path:
            return None

        # 检查项目是否在合法项目列表中
        try:
            normalized_project_path = str(Path(project_display_path).resolve())
            if normalized_project_path not in valid_projects:
                logger.debug(
                    f"Project not in valid list, skipping: {project_display_path}"
                )
                return None
        except Exception as e:
            logger.warning(
                f"Failed to normalize project path {project_display_path}: {e}"
            )
            return None

        # 创建 ClaudeProject 对象
        return self._create_claude_project(
            project_display_path, str(project_session_path), last_active_at
        )

    def detect_git_worktree(self, project_path: str) -> tuple[bool, Optional[str]]:
        """
        检测项目是否为 git worktree 并返回主项目路径

        Args:
            project_path: 项目路径

        Returns:
            (is_worktree, main_project_path): 是否为 worktree 和主项目路径
        """
        try:
            proj_path = Path(project_path)
            if not proj_path.exists():
                return False, None

            # 使用 git worktree list 命令来准确检测
            result = run_process(
                command=["git", "worktree", "list", "--porcelain"],
                cwd=proj_path,
            )

            if not result.success:
                # 不是 git 仓库或者命令执行失败
                return False, None

            # 解析 git worktree 输出
            # 格式：
            # worktree /path/to/worktree
            # HEAD abcd123...
            # branch refs/heads/xxx
            # ...
            # worktree /path/to/main
            # HEAD abcd123...
            # branch refs/heads/main
            lines = result.stdout.strip().split("\n")

            current_worktree_path = None
            main_worktree_path = None

            for line in lines:
                if line.startswith("worktree "):
                    worktree_path = line[9:].strip()  # 去掉 "worktree " 前缀

                    if current_worktree_path is None:
                        # 第一个 worktree 是当前正在检测的
                        current_worktree_path = worktree_path
                    else:
                        # 后续的是主 worktree（main worktree）
                        main_worktree_path = worktree_path
                        break

            # 如果找到了主 worktree 路径，说明当前是 worktree
            if main_worktree_path:
                return True, main_worktree_path

            return False, None

        except Exception as e:
            logger.warning(f"Failed to detect git worktree: {e}")
            return False, None

    async def scan_all_projects(self) -> List[ClaudeProject]:
        """快速扫描所有项目基本信息（不加载 session 详情）"""
        # 1. 加载合法项目列表
        valid_projects = self.load_valid_projects()

        if not self.projects_path.exists():
            logger.warning(
                f"Claude projects directory does not exist: {self.projects_path}"
            )
            # 即使 session 目录不存在，也需要检查 valid_projects 中的项目
            return self._scan_projects_without_sessions(valid_projects)

        projects = []
        scanned_project_paths = set()

        # 2. 快速遍历 projects 目录下的所有子目录（只读取项目路径）
        for project_dir in self.projects_path.iterdir():
            if project_dir.is_dir():
                # 3. 快速扫描项目信息（不加载 session 详情，提前过滤）
                project = await self.scan_project_info(project_dir, valid_projects)
                if project:
                    # 4. 添加到结果列表（已经在 scan_project_info 中验证过合法性）
                    try:
                        normalized_project_path = str(
                            Path(project.project_path).resolve()
                        )
                        scanned_project_paths.add(normalized_project_path)
                        projects.append(project)
                    except Exception as e:
                        logger.warning(
                            f"Failed to process project {project.project_path}: {e}"
                        )

        # 5. 处理在 valid_projects 中但没有 session 数据的项目
        missing_projects = valid_projects - scanned_project_paths
        if missing_projects:
            missing_projects_list = self._scan_projects_without_sessions(
                missing_projects
            )
            projects.extend(missing_projects_list)

        logger.info(f"Quick scan completed, found {len(projects)} projects")

        return projects

    def _scan_projects_without_sessions(
        self, project_paths: set
    ) -> List[ClaudeProject]:
        """扫描没有 session 数据的项目（包括被移除的和存在的）"""
        projects = []
        for project_path in project_paths:
            try:
                project = self._create_claude_project(project_path, None)

                if not project.removed:
                    logger.info(f"Project has no Claude session data: {project_path}")

                projects.append(project)

            except Exception as e:
                logger.warning(f"Failed to process project {project_path}: {e}")

        return projects

    def delete_project(
        self, project_path: str, session_path: Optional[str] = None
    ) -> bool:
        """
        从 Claude 配置中永久删除项目

        Args:
            project_path: 项目路径
            session_path: 可选的 session 路径，如果提供则删除 session 目录

        Returns:
            bool: 是否成功删除
        """
        import shutil

        from .settings_helper import load_config, save_config

        claude_json_path = self.user_home / ".claude.json"

        # 1. 从 ~/.claude.json 中移除项目配置
        if claude_json_path.exists():
            config = load_config(claude_json_path)

            # 查找并删除项目配置
            proj_key = None
            for proj_path in list(config.get("projects", {}).keys()):
                try:
                    if Path(proj_path).resolve() == Path(project_path).resolve():
                        proj_key = proj_path
                        break
                except Exception:
                    continue

            if proj_key:
                if "projects" in config:
                    del config["projects"][proj_key]
                    # 如果 projects 为空，删除 projects 键
                    if not config["projects"]:
                        del config["projects"]
                save_config(claude_json_path, config)
                logger.info(f"Removed project from ~/.claude.json: {project_path}")

        # 2. 删除 session 目录（如果提供）
        if session_path:
            session_dir = Path(session_path)
            if session_dir.exists():
                try:
                    shutil.rmtree(session_dir)
                    logger.info(f"Deleted session directory: {session_dir}")
                except Exception as e:
                    logger.error(
                        f"Failed to delete session directory {session_dir}: {e}"
                    )
                    return False

        return True
