"""
Claude Projects Scanner

This module provides functionality to scan and analyze Claude projects
stored in $USER/.claude/projects, extracting project information and session data.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("claude")


class ClaudeSession(BaseModel):
    """Pydantic model representing a single Claude session/conversation."""

    session_id: str
    session_file: str
    session_file_md5: Optional[str] = None
    is_agent_session: bool = False
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    first_active_at: Optional[datetime] = Field(
        default=None, exclude=True
    )  # Exclude from serialization
    last_active_at: Optional[datetime] = Field(
        default=None, exclude=True
    )  # Exclude from serialization
    project_path: Optional[str] = None
    git_branch: Optional[str] = None
    message_count: int = 0


class ClaudeProject(BaseModel):
    """Pydantic model representing a Claude project containing multiple sessions."""

    project_name: str
    project_path: str = Field(exclude=True)  # Exclude from serialization
    sessions: Dict[str, ClaudeSession] = Field(default_factory=dict)
    first_active_at: Optional[datetime] = Field(
        default=None, exclude=True
    )  # Exclude from serialization
    last_active_at: Optional[datetime] = Field(
        default=None, exclude=True
    )  # Exclude from serialization


class ClaudeProjectsScanner:
    """Main scanner class for Claude projects with all business logic."""

    def __init__(self, claude_projects_path: Optional[Path] = None):
        if claude_projects_path is None:
            # Default to $USER/.claude/projects
            home_dir = Path.home()
            claude_projects_path = home_dir / ".claude" / "projects"

        self.projects_path = claude_projects_path

    # Data loading and processing methods
    def load_session_data(self, session_file: Path) -> Optional[ClaudeSession]:
        """Load session data from JSONL file and return a populated ClaudeSession or None if error occurs."""
        session_id = session_file.stem
        is_agent_session = session_file.name.startswith("agent-")

        try:
            with open(session_file, "rb") as f:
                # Read entire file content for MD5 calculation
                content_bytes = f.read()
                file_hash = hashlib.md5()
                file_hash.update(content_bytes)
                file_md5 = file_hash.hexdigest()

                # Decode content for JSON parsing
                content = content_bytes.decode("utf-8")
                messages = []
                first_active_at = None
                last_active_at = None
                project_path = None
                git_branch = None

                for line in content.splitlines():
                    line = line.strip()
                    if line:
                        message_data = json.loads(line)
                        messages.append(message_data)

                        # Extract metadata from messages
                        if "timestamp" in message_data:
                            timestamp_str = message_data["timestamp"]
                            if timestamp_str.endswith("Z"):
                                timestamp_str = timestamp_str.replace("Z", "+00:00")
                            timestamp = datetime.fromisoformat(timestamp_str)

                            # Convert to naive datetime for consistent comparison
                            if timestamp.tzinfo is not None:
                                timestamp = timestamp.replace(tzinfo=None)

                            if first_active_at is None:
                                first_active_at = timestamp
                            last_active_at = max(last_active_at or timestamp, timestamp)

                        if "cwd" in message_data and not project_path:
                            project_path = message_data["cwd"]

                        if "gitBranch" in message_data and not git_branch:
                            git_branch = message_data["gitBranch"]

                message_count = len([msg for msg in messages if "message" in msg])

                # Create and return updated session with loaded data
                return ClaudeSession(
                    session_id=session_id,
                    session_file=str(session_file),
                    session_file_md5=file_md5,
                    is_agent_session=is_agent_session,
                    messages=messages,
                    first_active_at=first_active_at,
                    last_active_at=last_active_at,
                    project_path=project_path,
                    git_branch=git_branch,
                    message_count=message_count,
                )

        except (IOError, UnicodeDecodeError) as e:
            logger.error(f"Failed to read file {session_file}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {session_file}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading {session_file}: {e}")
            return None

    def scan_project_sessions(
        self, project_dir_name: str, project_path: Path
    ) -> Optional[ClaudeProject]:
        """Scan project directory for session files and return a populated ClaudeProject."""
        if not project_path.exists():
            return None

        sessions: Dict[str, ClaudeSession] = {}
        for session_file in project_path.glob("*.jsonl"):
            session = self.load_session_data(session_file)
            if session:  # Only add session if loading was successful
                sessions[session.session_id] = session

        # Extract real project name from session data
        project_name = project_dir_name  # fallback to directory name
        project_display_path = None

        if sessions:
            # Try to get the project path from the first session that has a project_path
            for session in sessions.values():
                if session.project_path:
                    # Extract the project directory name from the full path
                    path_parts = Path(session.project_path).parts
                    if path_parts:
                        project_name = path_parts[
                            -1
                        ]  # Use the last part (folder name) as project name
                        project_display_path = session.project_path
                        break

        # Calculate project's first_active_at and last_active_at from sessions
        project_first_active_at = None
        project_last_active_at = None

        if sessions:
            # Project first_active_at is the earliest session first_active_at
            session_first_active_ats = [
                s.first_active_at for s in sessions.values() if s.first_active_at
            ]
            if session_first_active_ats:
                project_first_active_at = min(session_first_active_ats)

            # Project last_active_at is the latest session last_active_at
            session_last_active_ats = [
                s.last_active_at for s in sessions.values() if s.last_active_at
            ]
            if session_last_active_ats:
                project_last_active_at = max(session_last_active_ats)

        return ClaudeProject(
            project_name=project_name,
            project_path=project_display_path or str(project_path),
            sessions=sessions,
            first_active_at=project_first_active_at,
            last_active_at=project_last_active_at,
        )

    def scan_all_projects(self) -> List[ClaudeProject]:
        """Scan all projects in the Claude projects directory and return a list of ClaudeProject objects."""
        if not self.projects_path.exists():
            logger.warning(
                f"Claude projects directory does not exist: {self.projects_path}"
            )
            return []

        projects = []
        # Look for project directories (they follow the pattern of encoded file paths)
        for project_dir in self.projects_path.iterdir():
            if project_dir.is_dir():
                project = self.scan_project_sessions(project_dir.name, project_dir)
                if project:
                    projects.append(project)

        return projects
