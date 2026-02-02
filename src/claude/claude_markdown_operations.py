"""
Markdown 通用操作模块
处理 Markdown 文件的读取、写入、重命名、删除等通用操作
"""

import hashlib
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .claude_plugin_operations import ClaudePluginOperations
from .markdown_helper import extract_description, update_file_name_field
from .models import (
    AgentInfo,
    ClaudeMemoryInfo,
    CommandInfo,
    ConfigScope,
    FileType,
    MarkdownContentDTO,
    SkillFileNotFoundError,
    SkillFileTreeNode,
    SkillInfo,
    SkillNotFoundError,
    SkillOperationError,
    SkillPathTraversalError,
)

# Configure logger
logger = logging.getLogger("claude")


class ClaudeMarkdownOperations:
    """Claude Markdown 通用操作类"""

    def __init__(
        self,
        project_path: Path,
        user_home: Path | None = None,
        plugin_ops: Optional[ClaudePluginOperations] = None,
    ):
        """
        初始化 Markdown 操作管理器

        Args:
            project_path: 项目路径
            user_home: 用户主目录路径，可空，默认为系统 User 路径（用于单元测试）
            plugin_ops: 可选的插件操作实例，用于扫描插件提供的资源
        """
        self.project_path = project_path
        self.user_home = user_home if user_home else Path.home()
        self.plugin_ops = plugin_ops

    def _validate_path_within_directory(
        self, target_path: Path, base_dir: Path, path_description: str = "路径"
    ) -> None:
        """
        验证目标路径是否在基础目录内（防止路径遍历攻击和符号链接绕过）

        使用 resolve() 解析所有符号链接，确保路径验证的安全性。

        Args:
            target_path: 需要验证的目标路径（可以是相对路径或绝对路径）
            base_dir: 基础目录路径
            path_description: 路径描述，用于错误消息

        Raises:
            SkillPathTraversalError: 当目标路径超出基础目录时抛出异常
        """
        try:
            # 解析完整路径（解析所有符号链接）
            # 先拼接 base_dir 和 target_path，确保 target_path 是相对于 base_dir 的
            full_path = (base_dir / target_path).resolve()
            base_resolved = base_dir.resolve()

            # 使用 relative_to 验证路径是否在基础目录内
            # 如果不在，会抛出 ValueError
            try:
                full_path.relative_to(base_resolved)
            except ValueError:
                raise SkillPathTraversalError(
                    f"{path_description} '{target_path}' 超出了 skill 目录范围"
                )
        except SkillPathTraversalError:
            raise
        except Exception as e:
            logger.error(f"路径验证失败: {e}")
            raise SkillPathTraversalError(
                f"{path_description} '{target_path}' 验证失败"
            )

    async def _get_markdown_file_path(
        self,
        content_type: str,
        name: str = None,
        scope: ConfigScope = ConfigScope.project,
    ) -> Path:
        """
        根据 content_type 和 name 获取文件路径

        Args:
            content_type: 内容类型，可选值: 'memory', 'command', 'agent', 'skill'
            name: 内容名称，对于 memory 类型，可以为 'project_claude_md', 'claude_dir_claude_md', 'local_claude_md'
            scope: 配置作用域，对于 agent 和 command 类型有效，默认为 project

        Returns:
            Path: 文件路径

        Raises:
            ValueError: 当 content_type 或 name 无效时抛出异常
        """
        # 如果是 plugin 作用域，从插件中获取路径
        if scope == ConfigScope.plugin:
            return await self._get_plugin_content_path(content_type, name)

        if content_type == "memory":
            if name == "project_claude_md":
                return self.project_path / "CLAUDE.md"
            elif name == "claude_dir_claude_md":
                return self.project_path / ".claude" / "CLAUDE.md"
            elif name == "local_claude_md":
                return self.project_path / "CLAUDE.local.md"
            elif name == "user_global_claude_md":
                return self.user_home / ".claude" / "CLAUDE.md"
            else:
                raise ValueError(f"不支持的 memory 类型: {name}")

        elif content_type == "command":
            if not name:
                raise ValueError("command 类型需要提供 name")
            # 将命令名称转换为文件路径，例如: features:value -> features/value.md
            path_parts = name.split(":")
            file_name = "/".join(path_parts) + ".md"
            if scope == ConfigScope.user:
                return self.user_home / ".claude" / "commands" / file_name
            else:
                return self.project_path / ".claude" / "commands" / file_name

        elif content_type == "agent":
            if not name:
                raise ValueError("agent 类型需要提供 name")
            if scope == ConfigScope.user:
                return self.user_home / ".claude" / "agents" / f"{name}.md"
            else:
                return self.project_path / ".claude" / "agents" / f"{name}.md"

        elif content_type == "skill":
            if not name:
                raise ValueError("skill 类型需要提供 name")
            if scope == ConfigScope.user:
                return self.user_home / ".claude" / "skills" / name / "SKILL.md"
            return self.project_path / ".claude" / "skills" / name / "SKILL.md"

        else:
            raise ValueError(f"不支持的 content_type: {content_type}")

    async def _get_plugin_content_path(self, content_type: str, name: str) -> Path:
        """
        获取插件内容的文件路径

        Args:
            content_type: 内容类型，可选值: 'command', 'agent', 'skill'
            name: 内容名称，格式为 <plugin_name>:<actual_name>

        Returns:
            Path: 插件内容的文件路径

        Raises:
            ValueError: 当 plugin_ops 未初始化、格式错误或未找到插件内容时抛出异常
        """
        if not self.plugin_ops:
            raise ValueError("plugin_ops 未初始化，无法加载插件内容")

        if not name:
            raise ValueError(f"{content_type} 类型需要提供 name")

        # 解析 name，提取插件名和实际名称
        # 格式: <plugin_name>:<actual_name>
        if ":" not in name:
            raise ValueError(
                f"插件 {content_type} 名称格式错误，应为 '<plugin_name>:<actual_name>'"
            )

        plugin_name, actual_name = name.split(":", 1)

        # 根据内容类型使用对应的 get_plugin_* 方法，避免全量扫描
        if content_type == "command":
            commands = await self.plugin_ops.get_plugin_commands(
                plugin_name_filter=plugin_name
            )
            for cmd in commands:
                if cmd.name == actual_name and cmd.file_path:
                    return Path(cmd.file_path)
            raise ValueError(
                f"未找到插件 command: '{plugin_name}:{actual_name}'。"
                f"请确认插件已安装且启用，command 名称正确。"
            )

        elif content_type == "agent":
            agents = await self.plugin_ops.get_plugin_agents(
                plugin_name_filter=plugin_name
            )
            for agent in agents:
                if agent.name == actual_name and agent.file_path:
                    return Path(agent.file_path)
            raise ValueError(
                f"未找到插件 agent: '{plugin_name}:{actual_name}'。"
                f"请确认插件已安装且启用，agent 名称正确。"
            )

        elif content_type == "skill":
            skills = await self.plugin_ops.get_plugin_skills(
                plugin_name_filter=plugin_name
            )
            for skill in skills:
                if skill.name == actual_name and skill.file_path:
                    # skill.file_path 是 skill 目录，需要定位到 SKILL.md
                    skill_path = Path(skill.file_path)
                    # 检查 file_path 是否已经是 SKILL.md 文件
                    if skill_path.name == "SKILL.md":
                        return skill_path
                    # 否则拼接 SKILL.md
                    return skill_path / "SKILL.md"
            raise ValueError(
                f"未找到插件 skill: '{plugin_name}:{actual_name}'。"
                f"请确认插件已安装且启用，skill 名称正确。"
            )

        else:
            raise ValueError(f"不支持的插件内容类型: {content_type}")

    async def load_markdown_content(
        self,
        content_type: str,
        name: str = None,
        scope: ConfigScope = ConfigScope.project,
    ) -> MarkdownContentDTO:
        """
        加载 Markdown 内容

        Args:
            content_type: 内容类型，可选值: 'memory', 'command', 'agent', 'skill'
            name: 内容名称
            scope: 配置作用域，对于 agent 和 command 类型有效，默认为 project

        Returns:
            MarkdownContentDTO: 包含 md5 和 content 的内容传输对象

        Raises:
            ValueError: 当 content_type 或 name 无效时抛出异常
        """
        file_path = await self._get_markdown_file_path(content_type, name, scope)

        # 读取文件内容
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = ""

        # 计算 MD5
        md5_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

        return MarkdownContentDTO(md5=md5_hash, content=content)

    async def update_markdown_content(
        self,
        content_type: str,
        name: str = None,
        from_md5: str = None,
        content: str = "",
        scope: ConfigScope = ConfigScope.project,
    ) -> None:
        """
        更新 Markdown 内容

        Args:
            content_type: 内容类型，可选值: 'memory', 'command', 'agent', 'skill'
            name: 内容名称
            from_md5: 期望的当前内容 MD5，用于并发控制
            content: 新的内容
            scope: 配置作用域，对于 agent 和 command 类型有效，默认为 project

        Raises:
            ValueError: 当 MD5 不匹配或 content_type/name 无效时抛出异常
                      当作用域为 plugin 时抛出异常（不允许修改插件内容）
        """
        # 不允许修改 plugin 作用域的内容
        if scope == ConfigScope.plugin:
            raise ValueError("不允许修改插件作用域的内容")

        content_md5 = hashlib.md5(content.encode("utf-8")).hexdigest()
        if content_md5 == from_md5:
            # 内容未发生变化
            return

        file_path = await self._get_markdown_file_path(content_type, name, scope)

        # 读取当前内容以检查 MD5
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                current_content = f.read()
        else:
            current_content = ""

        current_md5 = hashlib.md5(current_content.encode("utf-8")).hexdigest()

        # 如果提供了 from_md5 且不匹配，说明内容已被其他修改，抛出异常
        if from_md5 is not None and current_md5 != from_md5:
            raise ValueError(f"{content_type}文件已变化，请刷新后重新修改")

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入新内容
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    async def save_markdown_content(
        self,
        content_type: str,
        name: str,
        content: str = "",
        scope: ConfigScope = ConfigScope.project,
    ) -> MarkdownContentDTO:
        """
        保存（新增）Markdown 内容

        Args:
            content_type: 内容类型，可选值: 'memory', 'command', 'agent', 'skill'
            name: 内容名称
            content: 新的内容
            scope: 配置作用域，对于 agent 和 command 类型有效，默认为 project

        Returns:
            MarkdownContentDTO: 包含 md5 和 content 的内容传输对象

        Raises:
            ValueError: 当文件已存在或 content_type/name 无效时抛出异常
                      当作用域为 plugin 时抛出异常（不允许保存到插件作用域）
        """
        # 不允许保存到 plugin 作用域
        if scope == ConfigScope.plugin:
            raise ValueError("不允许保存到插件作用域")

        file_path = await self._get_markdown_file_path(content_type, name, scope)

        # 检查文件是否已存在
        if file_path.exists():
            raise ValueError(f"{content_type} '{name}' 已存在")

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入内容
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # 计算并返回 MD5
        md5_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        return MarkdownContentDTO(md5=md5_hash, content=content)

    async def rename_markdown_content(
        self,
        content_type: str,
        name: str,
        new_name: str,
        scope: ConfigScope = ConfigScope.project,
        new_scope: ConfigScope = None,
    ) -> None:
        """
        重命名 Markdown 内容（文件或文件夹）

        重命名时会同时更新 Markdown 文件 frontmatter 中的 name 字段。

        Args:
            content_type: 内容类型，可选值: 'memory', 'command', 'agent', 'skill'
            name: 当前内容名称
            new_name: 新的内容名称
            scope: 配置作用域，对于 agent 和 command 类型有效，默认为 project
            new_scope: 新的配置作用域，如果为 None 则使用 scope 的值

        Raises:
            ValueError: 当 name 不存在、new_name 已存在、或 content_type/name/new_name 无效时抛出异常
                      当涉及 plugin 作用域时抛出异常（不允许移动插件内容）
        """
        # 如果未指定 new_scope，使用 scope
        if new_scope is None:
            new_scope = scope

        # 不允许涉及 plugin 作用域的重命名操作
        if scope == ConfigScope.plugin or new_scope == ConfigScope.plugin:
            raise ValueError("不允许重命名或移动插件作用域的内容")

        # 获取源文件路径
        source_path = await self._get_markdown_file_path(content_type, name, scope)

        # 检查源文件是否存在
        if not source_path.exists():
            raise ValueError(f"{content_type} '{name}' 不存在")

        # 获取目标文件路径（先用 new_name 构造路径来检查是否已存在）
        # 对于 skill 类型，需要特殊处理文件夹
        if content_type == "skill":
            target_path = await self._get_markdown_file_path(
                content_type, new_name, new_scope
            )
            # 检查目标文件夹是否已存在
            target_dir = target_path.parent
            if target_dir.exists():
                raise ValueError(f"skill '{new_name}' 已存在")
        else:
            target_path = await self._get_markdown_file_path(
                content_type, new_name, new_scope
            )
            # 检查目标文件是否已存在
            if target_path.exists():
                raise ValueError(f"{content_type} '{new_name}' 已存在")

        # 先执行文件/文件夹移动
        if content_type == "skill":
            # Skill 类型需要移动整个文件夹
            source_dir = source_path.parent  # skill 文件夹路径
            target_dir = target_path.parent  # 新的 skill 文件夹路径
            target_dir.parent.mkdir(parents=True, exist_ok=True)

            # 移动文件夹
            shutil.move(str(source_dir), str(target_dir))
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            # 其他类型直接移动文件
            shutil.move(str(source_path), str(target_path))

        # 移动后更新内容中的 name 字段（仅在 name 发生变化时）
        if name != new_name:
            actual_name = new_name.split(":")[-1]

            # 使用 helper 函数更新文件中的 name 字段
            success = update_file_name_field(target_path, actual_name)
            if not success:
                logger.warning(
                    f"Failed to update name field for {content_type} '{new_name}'"
                )

    async def delete_markdown_content(
        self, content_type: str, name: str, scope: ConfigScope = ConfigScope.project
    ) -> None:
        """
        删除 Markdown 内容（文件或文件夹）

        Args:
            content_type: 内容类型，可选值: 'memory', 'command', 'agent', 'skill'
            name: 内容名称
            scope: 配置作用域，对于 agent 和 command 类型有效，默认为 project

        Raises:
            ValueError: 当 name 不存在、或 content_type/name 无效时抛出异常
                      当作用域为 plugin 时抛出异常（不允许删除插件内容）
        """
        # 不允许删除 plugin 作用域的内容
        if scope == ConfigScope.plugin:
            raise ValueError("不允许删除插件作用域的内容")

        # 获取文件路径
        file_path = await self._get_markdown_file_path(content_type, name, scope)

        # 检查文件是否存在
        if not file_path.exists():
            raise ValueError(f"{content_type} '{name}' 不存在")

        try:
            if content_type == "skill":
                # Skill 类型需要删除整个文件夹
                skill_dir = file_path.parent  # skill 文件夹路径
                shutil.rmtree(str(skill_dir))
            else:
                # 其他类型直接删除文件
                file_path.unlink()
        except Exception as e:
            raise ValueError(f"删除 {content_type} '{name}' 失败: {str(e)}")

    async def _markdown_content_exists(
        self,
        content_type: str,
        name: str = None,
        scope: ConfigScope = ConfigScope.project,
    ) -> bool:
        """
        检查 Markdown 内容是否存在

        Args:
            content_type: 内容类型，可选值: 'memory', 'command', 'agent', 'skill'
            name: 内容名称
            scope: 配置作用域，对于 agent 和 command 类型有效，默认为 project

        Returns:
            bool: 内容是否存在
        """
        try:
            file_path = await self._get_markdown_file_path(content_type, name, scope)
            return file_path.exists()
        except ValueError:
            return False

    async def scan_memory(self) -> ClaudeMemoryInfo:
        """
        扫描 CLAUDE.md 配置信息

        Returns:
            ClaudeMemoryInfo: CLAUDE.md 配置信息
        """
        return ClaudeMemoryInfo(
            project_claude_md=await self._markdown_content_exists(
                "memory", "project_claude_md"
            ),
            claude_dir_claude_md=await self._markdown_content_exists(
                "memory", "claude_dir_claude_md"
            ),
            local_claude_md=await self._markdown_content_exists(
                "memory", "local_claude_md"
            ),
            user_global_claude_md=await self._markdown_content_exists(
                "memory", "user_global_claude_md"
            ),
        )

    async def scan_agents(self, scope: ConfigScope | None = None) -> List[AgentInfo]:
        """
        扫描 Agents（包括用户全局和项目路径）

        Args:
            scope: 可选的作用域过滤器。如果指定，只返回该作用域的 Agents。
                   None 表示返回所有作用域的 Agents。

        Returns:
            List[AgentInfo]: Agent 信息列表
        """
        agents = []

        # 如果 scope 为 None 或为 project，扫描项目 agents
        if scope is None or scope == ConfigScope.project:
            project_agents_dir = self.project_path / ".claude" / "agents"
            if project_agents_dir.exists():
                for agent_file in project_agents_dir.rglob("*.md"):
                    try:
                        stat = agent_file.stat()
                        # 提取 description
                        description = extract_description(agent_file)
                        agents.append(
                            AgentInfo(
                                name=agent_file.stem,
                                scope=ConfigScope.project,
                                description=description,
                                last_modified=datetime.fromtimestamp(stat.st_mtime),
                                file_path=str(agent_file.absolute()),  # 添加文件路径
                            )
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to scan project Agent file {agent_file}: {e}"
                        )

        # 根据 scope 决定扫描哪些路径
        # 如果 scope 为 None 或为 user agents
        if scope is None or scope == ConfigScope.user:
            user_agents_dir = self.user_home / ".claude" / "agents"
            if user_agents_dir.exists():
                for agent_file in user_agents_dir.rglob("*.md"):
                    try:
                        stat = agent_file.stat()
                        # 提取 description
                        description = extract_description(agent_file)
                        agents.append(
                            AgentInfo(
                                name=agent_file.stem,
                                scope=ConfigScope.user,
                                description=description,
                                last_modified=datetime.fromtimestamp(stat.st_mtime),
                                file_path=str(agent_file.absolute()),  # 添加文件路径
                            )
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to scan user Agent file {agent_file}: {e}"
                        )

        # 如果 scope 为 None 或为 plugin，扫描已启用插件的 agents
        if (scope is None or scope == ConfigScope.plugin) and self.plugin_ops:
            try:
                # 使用新的 get_plugin_agents 方法获取插件 agents
                plugin_agents = await self.plugin_ops.get_plugin_agents()

                # 为插件 agents 添加前缀: <plugin_name>:
                for agent in plugin_agents:
                    # agent.plugin_name 和 agent.marketplace_name 已经由 get_plugin_agents 填充
                    plugin_name = agent.plugin_name or "unknown"
                    agents.append(
                        AgentInfo(
                            name=f"{plugin_name}:{agent.name}",
                            scope=ConfigScope.plugin,
                            description=agent.description,
                            last_modified=agent.last_modified,
                            plugin_name=agent.plugin_name,
                            marketplace_name=agent.marketplace_name,
                            file_path=agent.file_path,  # 保留插件文件的路径
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to scan plugin agents: {e}")

        return agents

    async def scan_commands(
        self, scope: ConfigScope | None = None
    ) -> List[CommandInfo]:
        """
        扫描 Slash Commands（包括用户全局和项目路径）

        Args:
            scope: 可选的作用域过滤器。如果指定，只返回该作用域的 Commands。
                   None 表示返回所有作用域的 Commands。

        Returns:
            List[CommandInfo]: 命令信息列表
        """
        commands = []

        # 根据 scope 决定扫描哪些路径
        # 如果 scope 为 None 或为 project，扫描项目 commands
        if scope is None or scope == ConfigScope.project:
            project_commands_dir = self.project_path / ".claude" / "commands"
            if project_commands_dir.exists():
                for cmd_file in project_commands_dir.rglob("*.md"):
                    try:
                        stat = cmd_file.stat()

                        # 计算相对于 commands 目录的相对路径
                        relative_path = cmd_file.relative_to(project_commands_dir)

                        # 将路径转换为命令名称，使用冒号分隔
                        # 例如: features/value.md -> features:value
                        path_parts = relative_path.with_suffix("").parts
                        command_name = ":".join(path_parts)

                        # 提取 description
                        description = extract_description(cmd_file)

                        commands.append(
                            CommandInfo(
                                name=command_name,
                                scope=ConfigScope.project,
                                description=description,
                                last_modified=datetime.fromtimestamp(stat.st_mtime),
                                file_path=str(cmd_file.absolute()),  # 添加文件路径
                            )
                        )
                    except Exception as e:
                        # 记录错误但继续扫描其他文件
                        logger.error(
                            f"Failed to scan project command file {cmd_file}: {e}"
                        )

        # 如果 scope 为 None 或为 user，扫描用户全局 commands
        if scope is None or scope == ConfigScope.user:
            user_commands_dir = self.user_home / ".claude" / "commands"
            if user_commands_dir.exists():
                for cmd_file in user_commands_dir.rglob("*.md"):
                    try:
                        stat = cmd_file.stat()

                        # 计算相对于 commands 目录的相对路径
                        relative_path = cmd_file.relative_to(user_commands_dir)

                        # 将路径转换为命令名称，使用冒号分隔
                        # 例如: features/value.md -> features:value
                        path_parts = relative_path.with_suffix("").parts
                        command_name = ":".join(path_parts)

                        # 提取 description
                        description = extract_description(cmd_file)

                        commands.append(
                            CommandInfo(
                                name=command_name,
                                scope=ConfigScope.user,
                                description=description,
                                last_modified=datetime.fromtimestamp(stat.st_mtime),
                                file_path=str(cmd_file.absolute()),  # 添加文件路径
                            )
                        )
                    except Exception as e:
                        # 记录错误但继续扫描其他文件
                        logger.error(
                            f"Failed to scan user command file {cmd_file}: {e}"
                        )

        # 如果 scope 为 None 或为 plugin，扫描已启用插件的 commands
        if (scope is None or scope == ConfigScope.plugin) and self.plugin_ops:
            try:
                # 使用新的 get_plugin_commands 方法获取插件 commands
                plugin_commands = await self.plugin_ops.get_plugin_commands()

                # 为插件命令添加前缀: <plugin_name>:
                for cmd in plugin_commands:
                    # cmd.plugin_name 和 cmd.marketplace_name 已经由 get_plugin_commands 填充
                    plugin_name = cmd.plugin_name or "unknown"
                    commands.append(
                        CommandInfo(
                            name=f"{plugin_name}:{cmd.name}",
                            scope=ConfigScope.plugin,
                            description=cmd.description,
                            last_modified=cmd.last_modified,
                            plugin_name=cmd.plugin_name,
                            marketplace_name=cmd.marketplace_name,
                            file_path=cmd.file_path,  # 保留插件文件的路径
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to scan plugin commands: {e}")

        return commands

    async def scan_skills(self, scope: ConfigScope | None = None) -> List[SkillInfo]:
        """
        扫描 Skills（包括用户全局和项目路径）

        Args:
            scope: 可选的作用域过滤器。如果指定，只返回该作用域的 Skills。
                   None 表示返回所有作用域的 Skills。

        Returns:
            List[SkillInfo]: Skill 信息列表
        """
        skills = []

        # 根据 scope 决定扫描哪些路径
        # 如果 scope 为 None 或为 project，扫描项目 skills
        if scope is None or scope == ConfigScope.project:
            project_skills_dir = self.project_path / ".claude" / "skills"
            if project_skills_dir.exists():
                for skill_dir in project_skills_dir.iterdir():
                    if skill_dir.is_dir():
                        try:
                            skill_file = skill_dir / "SKILL.md"
                            if skill_file.exists():
                                stat = skill_file.stat()
                                # 提取 description
                                description = extract_description(skill_file)
                                skills.append(
                                    SkillInfo(
                                        name=skill_dir.name,
                                        scope=ConfigScope.project,
                                        description=description,
                                        last_modified=datetime.fromtimestamp(
                                            stat.st_mtime
                                        ),
                                        file_path=str(
                                            skill_dir.absolute()
                                        ),  # 记录 skill 目录路径
                                    )
                                )
                        except Exception as e:
                            logger.error(
                                f"Failed to scan project Skill directory {skill_dir}: {e}"
                            )

        # 如果 scope 为 None 或为 user，扫描用户全局 skills
        if scope is None or scope == ConfigScope.user:
            user_skills_dir = self.user_home / ".claude" / "skills"
            if user_skills_dir.exists():
                for skill_dir in user_skills_dir.iterdir():
                    if skill_dir.is_dir():
                        try:
                            skill_file = skill_dir / "SKILL.md"
                            if skill_file.exists():
                                stat = skill_file.stat()
                                # 提取 description
                                description = extract_description(skill_file)
                                skills.append(
                                    SkillInfo(
                                        name=skill_dir.name,
                                        scope=ConfigScope.user,
                                        description=description,
                                        last_modified=datetime.fromtimestamp(
                                            stat.st_mtime
                                        ),
                                        file_path=str(
                                            skill_dir.absolute()
                                        ),  # 记录 skill 目录路径
                                    )
                                )
                        except Exception as e:
                            logger.error(
                                f"Failed to scan user Skill directory {skill_dir}: {e}"
                            )

        # 如果 scope 为 None 或为 plugin，扫描已启用插件的 skills
        if (scope is None or scope == ConfigScope.plugin) and self.plugin_ops:
            try:
                # 使用新的 get_plugin_skills 方法获取插件 skills
                plugin_skills = await self.plugin_ops.get_plugin_skills()

                # 为插件 skills 添加前缀: <plugin_name>:
                for skill in plugin_skills:
                    # skill.plugin_name 和 skill.marketplace_name 已经由 get_plugin_skills 填充
                    plugin_name = skill.plugin_name or "unknown"
                    skills.append(
                        SkillInfo(
                            name=f"{plugin_name}:{skill.name}",
                            scope=ConfigScope.plugin,
                            description=skill.description,
                            last_modified=skill.last_modified,
                            plugin_name=skill.plugin_name,
                            marketplace_name=skill.marketplace_name,
                            file_path=skill.file_path,  # 保留插件 skill 目录的路径
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to scan plugin skills: {e}")

        return skills

    async def list_skill_content(
        self,
        name: str,
        scope: ConfigScope = ConfigScope.project,
    ) -> List[SkillFileTreeNode]:
        """
        列出 skill 目录的文件树结构

        Args:
            name: skill 名称
            scope: 配置作用域，默认为 project

        Returns:
            List[SkillFileTreeNode]: skill 目录的文件树结构（按名称排序）

        Raises:
            SkillNotFoundError: 当 skill 不存在时抛出异常
        """
        logger.info(f"列出 skill 文件树: skill_name={name}")

        # 获取 skill 目录路径
        skill_file_path = await self._get_markdown_file_path("skill", name, scope)
        skill_dir = skill_file_path.parent

        # 检查 skill 目录是否存在
        if not skill_dir.exists():
            logger.error(f"skill 目录不存在: {skill_dir}")
            raise SkillNotFoundError(f"skill '{name}' 不存在")

        # 递归构建文件树
        file_tree = self._build_file_tree(skill_dir, skill_dir)
        logger.info(
            f"成功列出 skill 文件树: skill_name={name}, 节点数={len(file_tree)}"
        )
        return file_tree

    def _build_file_tree(
        self, current_dir: Path, root_dir: Path
    ) -> List[SkillFileTreeNode]:
        """
        递归构建文件树

        Args:
            current_dir: 当前遍历的目录
            root_dir: 根目录（用于计算相对路径）

        Returns:
            List[SkillFileTreeNode]: 文件树节点列表（目录优先，然后按名称排序）
        """
        nodes = []

        # 遍历当前目录的所有条目
        try:
            entries = sorted(current_dir.iterdir(), key=lambda x: x.name)

            # 先处理目录，再处理文件
            # 过滤条件：以 . 开头的隐藏文件/目录、__pycache__ 目录
            def should_ignore(name: str) -> bool:
                """判断是否应该忽略该文件或目录"""
                if name.startswith("."):
                    return True
                if name == "__pycache__":
                    return True
                return False

            directories = [
                e for e in entries if e.is_dir() and not should_ignore(e.name)
            ]
            files = [e for e in entries if e.is_file() and not should_ignore(e.name)]

            for entry in directories + files:
                stat = entry.stat()
                relative_path = entry.relative_to(root_dir)
                path_str = str(relative_path).replace("\\", "/")

                if entry.is_dir():
                    # 递归构建子目录的文件树
                    children = self._build_file_tree(entry, root_dir)
                    nodes.append(
                        SkillFileTreeNode(
                            name=entry.name,
                            type=FileType.DIRECTORY,
                            path=path_str,
                            children=children if children else None,
                            modified=datetime.fromtimestamp(stat.st_mtime),
                        )
                    )
                elif entry.is_file():
                    nodes.append(
                        SkillFileTreeNode(
                            name=entry.name,
                            type=FileType.FILE,
                            path=path_str,
                            size=stat.st_size,
                            modified=datetime.fromtimestamp(stat.st_mtime),
                        )
                    )
        except Exception as e:
            logger.error(f"构建文件树失败: {current_dir}, 错误: {e}")

        return nodes

    async def read_skill_file_content(
        self,
        skill_name: str,
        file_path: str,
        scope: ConfigScope = ConfigScope.project,
    ) -> str:
        """
        读取 skill 目录中特定文件的内容

        Args:
            skill_name: skill 名称
            file_path: 相对于 skill 目录的文件路径
            scope: 配置作用域，默认为 project（支持 plugin 作用域）

        Returns:
            str: 文件内容

        Raises:
            SkillNotFoundError: 当 skill 不存在时抛出异常
            SkillFileNotFoundError: 当文件不存在时抛出异常
            SkillPathTraversalError: 当文件路径超出 skill 目录时抛出异常
            SkillOperationError: 当读取文件失败时抛出异常
        """
        logger.info(f"读取 skill 文件: skill_name={skill_name}, file_path={file_path}")

        # 获取 SKILL.md 文件路径
        skill_md_path = await self._get_markdown_file_path("skill", skill_name, scope)

        # 获取 skill 目录路径
        skill_dir = skill_md_path.parent

        # 检查 skill 目录是否存在
        if not skill_dir.exists():
            logger.error(f"skill 目录不存在: {skill_dir}")
            raise SkillNotFoundError(f"skill '{skill_name}' 不存在")

        # 构建完整文件路径
        full_path = skill_dir / file_path

        # 验证路径在 skill 目录内（安全检查）
        self._validate_path_within_directory(
            full_path, skill_dir, f"文件路径 '{file_path}'"
        )

        # 检查文件是否存在
        if not full_path.exists():
            logger.error(f"文件不存在: {full_path}")
            raise SkillFileNotFoundError(f"文件 '{file_path}' 不存在")

        # 读取文件内容
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info(f"成功读取文件: {file_path}, 大小: {len(content)} 字节")
            return content
        except Exception as e:
            logger.error(f"读取文件失败: {file_path}, 错误: {e}")
            raise SkillOperationError(f"读取文件 '{file_path}' 失败: {str(e)}")

    async def update_skill_file_content(
        self,
        skill_name: str,
        file_path: str,
        content: str,
        scope: ConfigScope = ConfigScope.project,
    ) -> None:
        """
        更新 skill 目录中特定文件的内容

        Args:
            skill_name: skill 名称
            file_path: 相对于 skill 目录的文件路径
            content: 新的文件内容
            scope: 配置作用域，默认为 project

        Raises:
            SkillOperationError: 当 skill 不存在、作用域为 plugin 或文件操作失败时抛出异常
            SkillPathTraversalError: 当文件路径超出 skill 目录时抛出异常
        """
        logger.info(
            f"更新 skill 文件: skill_name={skill_name}, file_path={file_path}, 大小={len(content)} 字节"
        )

        # 不允许修改 plugin 作用域的内容
        if scope == ConfigScope.plugin:
            logger.error(f"不允许修改 plugin 作用域的内容: {skill_name}")
            raise SkillOperationError("不允许修改插件作用域的内容")

        # 获取 skill 目录路径
        skill_file_path = await self._get_markdown_file_path("skill", skill_name, scope)
        skill_dir = skill_file_path.parent

        # 检查 skill 目录是否存在
        if not skill_dir.exists():
            logger.error(f"skill 目录不存在: {skill_dir}")
            raise SkillOperationError(f"skill '{skill_name}' 不存在")

        # 构建完整文件路径
        full_path = skill_dir / file_path

        # 验证路径在 skill 目录内（安全检查）
        self._validate_path_within_directory(
            full_path, skill_dir, f"文件路径 '{file_path}'"
        )

        # 确保父目录存在
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件内容
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"成功更新文件: {file_path}")
        except Exception as e:
            logger.error(f"更新文件失败: {file_path}, 错误: {e}")
            raise SkillOperationError(f"更新文件 '{file_path}' 失败: {str(e)}")

    async def delete_skill_file(
        self,
        skill_name: str,
        file_path: str,
        scope: ConfigScope = ConfigScope.project,
    ) -> None:
        """
        删除 skill 目录中的特定文件或文件夹

        Args:
            skill_name: skill 名称
            file_path: 相对于 skill 目录的文件或文件夹路径
            scope: 配置作用域，默认为 project

        Raises:
            SkillOperationError: 当 skill 不存在、作用域为 plugin 或删除失败时抛出异常
            SkillFileNotFoundError: 当文件不存在时抛出异常
            SkillPathTraversalError: 当文件路径超出 skill 目录时抛出异常
        """
        logger.info(f"删除 skill 文件: skill_name={skill_name}, file_path={file_path}")

        # 不允许删除 plugin 作用域的内容
        if scope == ConfigScope.plugin:
            logger.error(f"不允许删除 plugin 作用域的内容: {skill_name}")
            raise SkillOperationError("不允许删除插件作用域的内容")

        # 获取 skill 目录路径
        skill_file_path = await self._get_markdown_file_path("skill", skill_name, scope)
        skill_dir = skill_file_path.parent

        # 检查 skill 目录是否存在
        if not skill_dir.exists():
            logger.error(f"skill 目录不存在: {skill_dir}")
            raise SkillOperationError(f"skill '{skill_name}' 不存在")

        # 构建完整文件路径
        full_path = skill_dir / file_path

        # 验证路径在 skill 目录内（安全检查）
        self._validate_path_within_directory(
            full_path, skill_dir, f"文件路径 '{file_path}'"
        )

        # 检查文件或文件夹是否存在
        if not full_path.exists():
            logger.error(f"文件或文件夹不存在: {full_path}")
            raise SkillFileNotFoundError(f"文件或文件夹 '{file_path}' 不存在")

        # 删除文件或文件夹
        try:
            if full_path.is_dir():
                logger.warning(f"删除目录: {file_path}")
                shutil.rmtree(str(full_path))
            else:
                logger.info(f"删除文件: {file_path}")
                full_path.unlink()
            logger.info(f"成功删除: {file_path}")
        except Exception as e:
            logger.error(f"删除失败: {file_path}, 错误: {e}")
            raise SkillOperationError(f"删除 '{file_path}' 失败: {str(e)}")

    async def create_skill_file(
        self,
        skill_name: str,
        parent_path: str,
        name: str,
        file_type: FileType,
        scope: ConfigScope = ConfigScope.project,
    ) -> None:
        """
        在 skill 目录中创建新文件或文件夹

        Args:
            skill_name: skill 名称
            parent_path: 父目录路径（相对于 skill 目录）
            name: 新文件或文件夹的名称
            file_type: 文件类型枚举 (FileType.FILE 或 FileType.DIRECTORY)
            scope: 配置作用域，默认为 project

        Raises:
            SkillOperationError: 当 skill 不存在、父路径不存在、名称已存在、作用域为 plugin 或创建失败时抛出异常
            SkillPathTraversalError: 当父路径超出 skill 目录时抛出异常
        """
        logger.info(
            f"创建 skill 文件: skill_name={skill_name}, parent_path={parent_path}, name={name}, type={file_type.value}"
        )

        # 不允许在 plugin 作用域创建内容
        if scope == ConfigScope.plugin:
            logger.error(f"不允许在 plugin 作用域创建内容: {skill_name}")
            raise SkillOperationError("不允许在插件作用域创建内容")

        # 获取 skill 目录路径
        skill_file_path = await self._get_markdown_file_path("skill", skill_name, scope)
        skill_dir = skill_file_path.parent

        # 检查 skill 目录是否存在
        if not skill_dir.exists():
            logger.error(f"skill 目录不存在: {skill_dir}")
            raise SkillOperationError(f"skill '{skill_name}' 不存在")

        # 构建父目录路径
        parent_dir = skill_dir / parent_path if parent_path else skill_dir

        # 验证父目录在 skill 目录内（安全检查）
        self._validate_path_within_directory(
            parent_dir, skill_dir, f"父目录路径 '{parent_path}'"
        )

        # 检查父目录是否存在
        if not parent_dir.exists():
            logger.error(f"父目录不存在: {parent_dir}")
            raise SkillOperationError(f"父目录 '{parent_path}' 不存在")

        # 构建新文件/文件夹路径
        new_path = parent_dir / name

        # 检查是否已存在
        if new_path.exists():
            logger.error(f"文件或文件夹已存在: {new_path}")
            raise SkillOperationError(f"文件或文件夹 '{name}' 已存在")

        # 创建文件或文件夹
        try:
            if file_type == FileType.DIRECTORY:
                new_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"成功创建目录: {name}")
            else:
                # 确保父目录存在
                new_path.parent.mkdir(parents=True, exist_ok=True)
                # 创建空文件
                new_path.touch()
                logger.info(f"成功创建文件: {name}")
        except Exception as e:
            logger.error(f"创建失败: {name}, 错误: {e}")
            raise SkillOperationError(f"创建 '{name}' 失败: {str(e)}")

    async def rename_skill_file(
        self,
        skill_name: str,
        file_path: str,
        new_file_path: str,
        scope: ConfigScope = ConfigScope.project,
    ) -> None:
        """
        重命名/移动 skill 目录中的文件或文件夹

        支持路径分隔符，可以将文件移动到不同目录，只要目标路径仍在 skill 目录内。

        Args:
            skill_name: skill 名称
            file_path: 相对于 skill 目录的文件或文件夹路径
            new_file_path: 新的文件或文件夹路径（支持路径分隔符，可包含目录）
            scope: 配置作用域，默认为 project

        Raises:
            SkillOperationError: 当 skill 不存在、作用域为 plugin 或操作失败时抛出异常
            SkillFileNotFoundError: 当文件不存在时抛出异常
            SkillPathTraversalError: 当路径超出 skill 目录时抛出异常
        """
        logger.info(
            f"重命名/移动 skill 文件: skill_name={skill_name}, file_path={file_path}, new_file_path={new_file_path}"
        )

        # 不允许重命名 plugin 作用域的内容
        if scope == ConfigScope.plugin:
            logger.error(f"不允许重命名 plugin 作用域的内容: {skill_name}")
            raise SkillOperationError("不允许重命名插件作用域的内容")

        # 获取 skill 目录路径
        skill_file_path = await self._get_markdown_file_path("skill", skill_name, scope)
        skill_dir = skill_file_path.parent

        # 检查 skill 目录是否存在
        if not skill_dir.exists():
            logger.error(f"skill 目录不存在: {skill_dir}")
            raise SkillOperationError(f"skill '{skill_name}' 不存在")

        # 构建源路径
        source_full_path = skill_dir / file_path

        # 验证源路径在 skill 目录内（安全检查）
        self._validate_path_within_directory(
            source_full_path, skill_dir, f"文件路径 '{file_path}'"
        )

        # 检查源是否存在
        if not source_full_path.exists():
            logger.error(f"源文件或文件夹不存在: {source_full_path}")
            raise SkillFileNotFoundError(f"文件或文件夹 '{file_path}' 不存在")

        # 检查是否为 SKILL.md 主文件
        if source_full_path.name == "SKILL.md":
            logger.error(f"不允许重命名 SKILL.md 主文件")
            raise SkillOperationError("不允许重命名 SKILL.md 主文件")

        # 构建目标路径（相对于 skill 目录）
        target_full_path = skill_dir / new_file_path

        # 验证目标路径在 skill 目录内（安全检查）
        self._validate_path_within_directory(
            target_full_path, skill_dir, f"目标路径 '{new_file_path}'"
        )

        # 检查目标是否已存在
        if target_full_path.exists():
            logger.error(f"目标位置已存在同名文件或文件夹: {target_full_path}")
            raise SkillOperationError("目标位置已存在同名的文件或文件夹")

        # 确保目标目录存在，如果不存在则创建
        target_parent = target_full_path.parent
        if target_parent != skill_dir and not target_parent.exists():
            logger.info(f"创建目标目录: {target_parent}")
            target_parent.mkdir(parents=True, exist_ok=True)

        # 重命名/移动文件或文件夹
        try:
            source_full_path.rename(target_full_path)
            logger.info(f"成功重命名/移动: {file_path} -> {new_file_path}")
        except Exception as e:
            logger.error(f"重命名/移动失败: {file_path} -> {new_file_path}, 错误: {e}")
            raise SkillOperationError(f"重命名/移动 '{file_path}' 失败: {str(e)}")

    async def move_skill_file(
        self,
        skill_name: str,
        source_path: str,
        target_path: str,
        scope: ConfigScope = ConfigScope.project,
    ) -> None:
        """
        在 skill 目录中移动文件或文件夹

        Args:
            skill_name: skill 名称
            source_path: 源文件或文件夹路径（相对于 skill 目录）
            target_path: 目标文件夹路径（相对于 skill 目录）
            scope: 配置作用域，默认为 project

        Raises:
            SkillOperationError: 当 skill 不存在、源不存在、目标不存在、作用域为 plugin 或移动失败时抛出异常
            SkillPathTraversalError: 当路径超出 skill 目录时抛出异常
            SkillFileNotFoundError: 当源不存在时抛出异常
        """
        logger.info(
            f"移动 skill 文件: skill_name={skill_name}, source={source_path}, target={target_path}"
        )

        # 不允许移动 plugin 作用域的内容
        if scope == ConfigScope.plugin:
            logger.error(f"不允许移动 plugin 作用域的内容: {skill_name}")
            raise SkillOperationError("不允许移动插件作用域的内容")

        # 获取 skill 目录路径
        skill_file_path = await self._get_markdown_file_path("skill", skill_name, scope)
        skill_dir = skill_file_path.parent

        # 检查 skill 目录是否存在
        if not skill_dir.exists():
            logger.error(f"skill 目录不存在: {skill_dir}")
            raise SkillOperationError(f"skill '{skill_name}' 不存在")

        # 构建源路径
        source_full_path = skill_dir / source_path

        # 验证源路径在 skill 目录内（安全检查）
        self._validate_path_within_directory(
            source_full_path, skill_dir, f"源路径 '{source_path}'"
        )

        # 检查源是否存在
        if not source_full_path.exists():
            logger.error(f"源文件或文件夹不存在: {source_full_path}")
            raise SkillFileNotFoundError(f"源文件或文件夹 '{source_path}' 不存在")

        # 检查是否为 SKILL.md 主文件，不允许移动
        if source_full_path.name == "SKILL.md":
            logger.error(f"不允许移动 SKILL.md 主文件")
            raise SkillOperationError("不允许移动 SKILL.md 主文件")

        # 构建目标路径
        target_full_path = skill_dir / target_path

        # 验证目标路径在 skill 目录内（安全检查）
        self._validate_path_within_directory(
            target_full_path, skill_dir, f"目标路径 '{target_path}'"
        )

        # 检查目标是否存在且是目录
        if not target_full_path.exists():
            logger.error(f"目标文件夹不存在: {target_full_path}")
            raise SkillOperationError(f"目标文件夹 '{target_path}' 不存在")
        if not target_full_path.is_dir():
            logger.error(f"目标不是文件夹: {target_full_path}")
            raise SkillOperationError(f"目标 '{target_path}' 不是文件夹")

        # 检查是否将项目移动到其子目录中
        try:
            target_full_path.absolute().relative_to(source_full_path.absolute())
            logger.error(
                f"不能将文件移动到其子目录中: source={source_path}, target={target_path}"
            )
            raise SkillOperationError("不能将文件或文件夹移动到其子目录中")
        except ValueError:
            # 这是预期的，说明目标不在源目录内
            pass

        # 构建最终目标路径
        final_target = target_full_path / source_full_path.name

        # 检查最终目标是否已存在
        if final_target.exists():
            logger.error(f"目标位置已存在同名文件或文件夹: {final_target}")
            raise SkillOperationError("目标位置已存在同名的文件或文件夹")

        # 移动文件或文件夹
        try:
            shutil.move(str(source_full_path), str(final_target))
            logger.info(f"成功移动: {source_path} -> {target_path}")
        except Exception as e:
            logger.error(f"移动失败: {source_path} -> {target_path}, 错误: {e}")
            raise SkillOperationError(
                f"移动 '{source_path}' 到 '{target_path}' 失败: {str(e)}"
            )
