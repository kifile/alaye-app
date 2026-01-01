"""
Markdown 通用操作模块
处理 Markdown 文件的读取、写入、重命名、删除等通用操作
"""

import hashlib
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
    MarkdownContentDTO,
    SkillInfo,
)


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

    def _get_markdown_file_path(
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
            return self._get_plugin_content_path(content_type, name)

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

    def _get_plugin_content_path(self, content_type: str, name: str) -> Path:
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
            commands = self.plugin_ops.get_plugin_commands(
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
            agents = self.plugin_ops.get_plugin_agents(plugin_name_filter=plugin_name)
            for agent in agents:
                if agent.name == actual_name and agent.file_path:
                    return Path(agent.file_path)
            raise ValueError(
                f"未找到插件 agent: '{plugin_name}:{actual_name}'。"
                f"请确认插件已安装且启用，agent 名称正确。"
            )

        elif content_type == "skill":
            skills = self.plugin_ops.get_plugin_skills(plugin_name_filter=plugin_name)
            for skill in skills:
                if skill.name == actual_name and skill.file_path:
                    # skill.file_path 是 skill 目录，需要定位到 SKILL.md
                    return Path(skill.file_path) / "SKILL.md"
            raise ValueError(
                f"未找到插件 skill: '{plugin_name}:{actual_name}'。"
                f"请确认插件已安装且启用，skill 名称正确。"
            )

        else:
            raise ValueError(f"不支持的插件内容类型: {content_type}")

    def load_markdown_content(
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
        file_path = self._get_markdown_file_path(content_type, name, scope)

        # 读取文件内容
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = ""

        # 计算 MD5
        md5_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

        return MarkdownContentDTO(md5=md5_hash, content=content)

    def update_markdown_content(
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

        file_path = self._get_markdown_file_path(content_type, name, scope)

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

    def save_markdown_content(
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

        file_path = self._get_markdown_file_path(content_type, name, scope)

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

    def rename_markdown_content(
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
        source_path = self._get_markdown_file_path(content_type, name, scope)

        # 检查源文件是否存在
        if not source_path.exists():
            raise ValueError(f"{content_type} '{name}' 不存在")

        # 获取目标文件路径（先用 new_name 构造路径来检查是否已存在）
        # 对于 skill 类型，需要特殊处理文件夹
        if content_type == "skill":
            target_path = self._get_markdown_file_path(
                content_type, new_name, new_scope
            )
            # 检查目标文件夹是否已存在
            target_dir = target_path.parent
            if target_dir.exists():
                raise ValueError(f"skill '{new_name}' 已存在")
        else:
            target_path = self._get_markdown_file_path(
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
                print(f"更新 {content_type} '{new_name}' 的 name 字段失败")

    def delete_markdown_content(
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
        file_path = self._get_markdown_file_path(content_type, name, scope)

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

    def _markdown_content_exists(
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
            file_path = self._get_markdown_file_path(content_type, name, scope)
            return file_path.exists()
        except ValueError:
            return False

    def scan_memory(self) -> ClaudeMemoryInfo:
        """
        扫描 CLAUDE.md 配置信息

        Returns:
            ClaudeMemoryInfo: CLAUDE.md 配置信息
        """
        return ClaudeMemoryInfo(
            project_claude_md=self._markdown_content_exists(
                "memory", "project_claude_md"
            ),
            claude_dir_claude_md=self._markdown_content_exists(
                "memory", "claude_dir_claude_md"
            ),
            local_claude_md=self._markdown_content_exists("memory", "local_claude_md"),
            user_global_claude_md=self._markdown_content_exists(
                "memory", "user_global_claude_md"
            ),
        )

    def scan_agents(self, scope: ConfigScope | None = None) -> List[AgentInfo]:
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
                        print(f"扫描项目 Agent 文件失败 {agent_file}: {e}")

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
                        print(f"扫描用户全局 Agent 文件失败 {agent_file}: {e}")

        # 如果 scope 为 None 或为 plugin，扫描已启用插件的 agents
        if (scope is None or scope == ConfigScope.plugin) and self.plugin_ops:
            try:
                # 使用新的 get_plugin_agents 方法获取插件 agents
                plugin_agents = self.plugin_ops.get_plugin_agents()

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
                print(f"扫描插件 agents 失败: {e}")

        return agents

    def scan_commands(self, scope: ConfigScope | None = None) -> List[CommandInfo]:
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
                        print(f"扫描项目命令文件失败 {cmd_file}: {e}")

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
                        print(f"扫描用户全局命令文件失败 {cmd_file}: {e}")

        # 如果 scope 为 None 或为 plugin，扫描已启用插件的 commands
        if (scope is None or scope == ConfigScope.plugin) and self.plugin_ops:
            try:
                # 使用新的 get_plugin_commands 方法获取插件 commands
                plugin_commands = self.plugin_ops.get_plugin_commands()

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
                print(f"扫描插件命令失败: {e}")

        return commands

    def scan_skills(self, scope: ConfigScope | None = None) -> List[SkillInfo]:
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
                            print(f"扫描项目 Skill 目录失败 {skill_dir}: {e}")

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
                            print(f"扫描用户全局 Skill 目录失败 {skill_dir}: {e}")

        # 如果 scope 为 None 或为 plugin，扫描已启用插件的 skills
        if (scope is None or scope == ConfigScope.plugin) and self.plugin_ops:
            try:
                # 使用新的 get_plugin_skills 方法获取插件 skills
                plugin_skills = self.plugin_ops.get_plugin_skills()

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
                print(f"扫描插件 skills 失败: {e}")

        return skills
