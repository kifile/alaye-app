"""
Hooks 配置操作模块
处理 Hooks 的扫描和配置管理操作
"""

import hashlib
from pathlib import Path
from typing import Optional

from .claude_plugin_operations import ClaudePluginOperations
from .models import (
    ConfigScope,
    HookConfig,
    HookConfigInfo,
    HookEvent,
    HooksInfo,
    HooksSettings,
    SettingsInfoWithValue,
)
from .settings_helper import (
    load_config,
    save_config,
    update_config,
)


class ClaudeHooksOperations:
    """Claude Hooks 操作类"""

    def __init__(
        self,
        project_path: Path,
        user_home: Path | None = None,
        plugin_ops: Optional[ClaudePluginOperations] = None,
    ):
        """
        初始化 Hooks 操作管理器

        Args:
            project_path: 项目路径
            user_home: 用户主目录路径，可空，默认为系统 User 路径（用于单元测试）
            plugin_ops: 可选的插件操作实例，用于扫描插件提供的 Hooks
        """
        self.project_path = project_path
        self.user_home = user_home if user_home else Path.home()
        self.plugin_ops = plugin_ops

    def scan_hooks_info(self, scope: ConfigScope | None = None) -> HooksInfo:
        """
        扫描并合并所有 Hooks 配置

        扫描以下位置的 Hooks 配置：
        1. ~/.claude/settings.json - user 配置（用户全局配置）
        2. $PROJECT/.claude/settings.json - project 配置
        3. $PROJECT/.claude/settings.local.json - 优先级最高的 local 配置

        Args:
            scope: 可选的作用域过滤器。如果指定，只返回该作用域的 Hooks。
                   None 表示返回所有作用域的 Hooks。

        Returns:
            HooksInfo: 合并后的 Hooks 配置信息
        """
        # 根据 scope 决定扫描哪些配置源
        user_settings = None
        project_settings = None
        project_local_settings = None

        if scope is None or scope == ConfigScope.user:
            user_settings = self._scan_user_settings_config()

        if scope is None or scope == ConfigScope.project:
            project_settings = self._scan_project_settings_config()

        if scope is None or scope == ConfigScope.local:
            project_local_settings = self._scan_project_local_settings_config()

        hooks_info = self._combine_hooks_configs(
            user_settings, project_settings, project_local_settings
        )

        # 如果 scope 为 None 或为 plugin，扫描已启用插件的 hooks
        if (scope is None or scope == ConfigScope.plugin) and self.plugin_ops:
            try:
                # 获取已安装的插件列表
                plugins = self.plugin_ops.scan_plugins()

                # 筛选出已启用的插件
                enabled_plugins = [
                    p for p in plugins if p.installed and p.enabled and p.tools
                ]

                # 从已启用插件中提取 hooks
                for plugin in enabled_plugins:
                    if plugin.tools and plugin.tools.hooks:
                        hooks_info.matchers.extend(plugin.tools.hooks)
            except Exception as e:
                print(f"扫描插件 hooks 失败: {e}")

        return hooks_info

    def _scan_user_settings_config(self) -> HooksSettings:
        """
        扫描 User Settings 配置 (~/.claude/settings.json)

        Returns:
            HooksSettingsDTO: User Hooks 配置
        """
        settings_file = self.user_home / ".claude" / "settings.json"

        # 使用 settings_helper 加载配置
        settings = load_config(settings_file)

        return HooksSettings.model_validate(settings)

    def _scan_project_settings_config(self) -> HooksSettings:
        """
        扫描 Project Settings 配置 ($PROJECT/.claude/settings.json)

        Returns:
            HooksSettingsDTO: Project Hooks 配置
        """
        settings_file = self.project_path / ".claude" / "settings.json"

        # 使用 settings_helper 加载配置
        settings = load_config(settings_file)

        return HooksSettings.model_validate(settings)

    def _scan_project_local_settings_config(self) -> HooksSettings:
        """
        扫描 Project Local Settings 配置 ($PROJECT/.claude/settings.local.json)

        Returns:
            HooksSettingsDTO: Project Local Hooks 配置
        """
        settings_file = self.project_path / ".claude" / "settings.local.json"

        # 使用 settings_helper 加载配置
        settings = load_config(settings_file)

        return HooksSettings.model_validate(settings)

    def _combine_hooks_configs(
        self,
        user_settings: HooksSettings | None,
        project_settings: HooksSettings | None,
        project_local_settings: HooksSettings | None,
    ) -> HooksInfo:
        """
        合并所有 Hooks 配置

        优先级逻辑：local > project > user (高优先级会覆盖低优先级)
        返回结果按优先级排序：local > project > user

        Args:
            user_settings: User Hooks 配置 (~/.claude/settings.json)
            project_settings: Project Hooks 配置 ($PROJECT/.claude/settings.json)
            project_local_settings: Project Local Hooks 配置 ($PROJECT/.claude/settings.local.json)

        Returns:
            HooksInfo: 合并后的 Hooks 配置信息
        """
        hook_configs = []

        # 1. 确定 disableAllHooks 的最终值和作用域
        disable_all_info = self._determine_disable_all_hooks(
            user_settings, project_settings, project_local_settings
        )

        # 2. 按 local > project > user 的顺序遍历（优先级高的在前）
        # 这样最终的列表就是按优先级排序的

        # 2.1 处理 local 配置（最高优先级）
        if project_local_settings and project_local_settings.hooks:
            for event, matcher_list in project_local_settings.hooks.items():
                for matcher in matcher_list:
                    for hook_config in matcher.hooks:
                        hook_configs.append(
                            HookConfigInfo(
                                id=self._generate_hook_id(
                                    hook_config,
                                    ConfigScope.local,
                                    event,
                                    matcher.matcher,
                                ),
                                scope=ConfigScope.local,
                                event=event,
                                matcher=matcher.matcher,
                                hook_config=hook_config,
                            )
                        )

        # 2.2 处理 project 配置（中等优先级）
        if project_settings and project_settings.hooks:
            for event, matcher_list in project_settings.hooks.items():
                for matcher in matcher_list:
                    for hook_config in matcher.hooks:
                        hook_configs.append(
                            HookConfigInfo(
                                id=self._generate_hook_id(
                                    hook_config,
                                    ConfigScope.project,
                                    event,
                                    matcher.matcher,
                                ),
                                scope=ConfigScope.project,
                                event=event,
                                matcher=matcher.matcher,
                                hook_config=hook_config,
                            )
                        )

        # 2.3 处理 user 配置（最低优先级）
        if user_settings and user_settings.hooks:
            for event, matcher_list in user_settings.hooks.items():
                for matcher in matcher_list:
                    for hook_config in matcher.hooks:
                        hook_configs.append(
                            HookConfigInfo(
                                id=self._generate_hook_id(
                                    hook_config,
                                    ConfigScope.user,
                                    event,
                                    matcher.matcher,
                                ),
                                scope=ConfigScope.user,
                                event=event,
                                matcher=matcher.matcher,
                                hook_config=hook_config,
                            )
                        )

        return HooksInfo(matchers=hook_configs, disable_all_hooks=disable_all_info)

    def _generate_hook_id(
        self,
        hook_config: HookConfig,
        scope: ConfigScope,
        event: HookEvent,
        matcher: Optional[str],
    ) -> str:
        """
        生成 Hook 配置的唯一标识

        格式: $type-$scope-$event-$matcher_md5-$content_md5

        Args:
            hook_config: Hook 配置
            scope: 配置作用域
            event: Hook 事件
            matcher: 匹配器模式

        Returns:
            str: Hook ID
        """
        # 生成 matcher 的 hash（空字符串也参与 hash）
        matcher_hash = hashlib.md5((matcher or "").encode()).hexdigest()

        # 获取用于生成 hash 的内容（command 或 prompt）
        content = hook_config.command or hook_config.prompt or ""
        content_hash = hashlib.md5(content.encode()).hexdigest()

        return f"${hook_config.type}-{scope.value}-{event.value}-{matcher_hash}-{content_hash}"

    def _determine_disable_all_hooks(
        self,
        user_settings: HooksSettings | None,
        project_settings: HooksSettings | None,
        project_local_settings: HooksSettings | None,
    ) -> SettingsInfoWithValue:
        """
        确定 disableAllHooks 的最终值和作用域

        优先级: local > project > user

        Args:
            user_settings: User Hooks 配置
            project_settings: Project Hooks 配置
            project_local_settings: Project Local Hooks 配置

        Returns:
            SettingsInfoWithValue: 包含值和作用域的设置信息
        """
        # settings.local.json 优先级最高
        if (
            project_local_settings
            and project_local_settings.disableAllHooks is not None
        ):
            return SettingsInfoWithValue(
                value=project_local_settings.disableAllHooks,
                scope=ConfigScope.local,
            )

        # .claude/settings.json 次之
        if project_settings and project_settings.disableAllHooks is not None:
            return SettingsInfoWithValue(
                value=project_settings.disableAllHooks,
                scope=ConfigScope.project,
            )

        # ~/.claude/settings.json 最低
        if user_settings and user_settings.disableAllHooks is not None:
            return SettingsInfoWithValue(
                value=user_settings.disableAllHooks,
                scope=ConfigScope.user,
            )

        # 都未设置，返回 None
        return SettingsInfoWithValue(value=None, scope=None)

    def add_hook(
        self,
        event: HookEvent,
        hook: HookConfig,
        matcher: Optional[str] = None,
        scope: ConfigScope = ConfigScope.project,
    ) -> None:
        """
        添加 Hook 配置

        Args:
            event: Hook 事件枚举
            hook: Hook 配置
            matcher: 可选的匹配器模式
            scope: 配置作用域，默认为 project

        Raises:
            ValueError: 当事件名称无效时抛出异常
        """
        config = self._load_settings_config_by_scope(scope)

        if "hooks" not in config:
            config["hooks"] = {}

        event_name = event.value
        if event_name not in config["hooks"]:
            config["hooks"][event_name] = []

        # 查找或创建匹配器
        event_hooks = config["hooks"][event_name]
        target_matcher = None

        for matcher_config in event_hooks:
            if matcher_config.get("matcher") == matcher:
                target_matcher = matcher_config
                break

        if target_matcher is None:
            # 创建新的匹配器（matcher 为空时不包含 matcher 键）
            target_matcher = (
                {"hooks": []} if matcher is None else {"matcher": matcher, "hooks": []}
            )
            event_hooks.append(target_matcher)

        # 添加 hook 配置
        hook_dict = hook.model_dump(exclude_none=True)
        target_matcher["hooks"].append(hook_dict)

        self._save_settings_config_by_scope(config, scope)

    def remove_hook(
        self,
        hook_id: str,
        scope: ConfigScope = ConfigScope.project,
    ) -> bool:
        """
        删除 Hook 配置

        Args:
            hook_id: Hook ID (格式: $type-$scope-$event-$matcher_md5-$content_md5)
            scope: 配置作用域，默认为 project

        Returns:
            bool: 是否成功删除
        """
        config = self._load_settings_config_by_scope(scope)

        if "hooks" not in config:
            return False

        # 解析 hook_id
        if not hook_id.startswith("$"):
            return False

        parts = hook_id.split("-")
        if len(parts) < 5:
            return False

        hook_type = parts[0][1:]  # 去掉 $ 前缀
        scope_value = parts[1]
        event_value = parts[2]
        matcher_hash = parts[3]

        # 验证 scope 匹配
        if scope_value != scope.value:
            return False

        # 查找对应的事件
        if event_value not in config["hooks"]:
            return False

        event_hooks = config["hooks"][event_value]

        # 查找匹配的 matcher 和 hook
        for matcher_config in event_hooks:
            current_matcher = matcher_config.get("matcher") or ""
            current_matcher_hash = hashlib.md5(current_matcher.encode()).hexdigest()

            if current_matcher_hash == matcher_hash:
                if "hooks" in matcher_config:
                    for i, hook_dict in enumerate(matcher_config["hooks"]):
                        if hook_dict.get("type") == hook_type:
                            # 生成完整的 id 来验证
                            temp_config = HookConfig(**hook_dict)
                            temp_id = self._generate_hook_id(
                                temp_config,
                                scope,
                                HookEvent(event_value),
                                current_matcher,
                            )
                            if temp_id == hook_id:
                                # 找到了，删除
                                matcher_config["hooks"].pop(i)

                                # 如果匹配器的 hooks 列表为空，删除匹配器
                                if not matcher_config["hooks"]:
                                    event_hooks.remove(matcher_config)

                                # 如果事件的 hooks 列表为空，删除事件
                                if not event_hooks:
                                    del config["hooks"][event_value]

                                self._save_settings_config_by_scope(config, scope)
                                return True

        return False

    def update_hook(
        self,
        hook_id: str,
        hook: HookConfig,
        scope: ConfigScope = ConfigScope.project,
    ) -> bool:
        """
        更新 Hook 配置

        Args:
            hook_id: Hook ID (格式: $type-$scope-$event-$matcher_md5-$content_md5)
            hook: 新的 Hook 配置
            scope: 配置作用域，默认为 project

        Returns:
            bool: 是否成功更新
        """
        config = self._load_settings_config_by_scope(scope)

        if "hooks" not in config:
            return False

        # 解析 hook_id
        if not hook_id.startswith("$"):
            return False

        parts = hook_id.split("-")
        if len(parts) < 5:
            return False

        hook_type = parts[0][1:]  # 去掉 $ 前缀
        scope_value = parts[1]
        event_value = parts[2]
        matcher_hash = parts[3]

        # 验证 scope 匹配
        if scope_value != scope.value:
            return False

        # 查找对应的事件
        if event_value not in config["hooks"]:
            return False

        event_hooks = config["hooks"][event_value]

        # 查找匹配的 matcher 和 hook
        for matcher_config in event_hooks:
            current_matcher = matcher_config.get("matcher") or ""
            current_matcher_hash = hashlib.md5(current_matcher.encode()).hexdigest()

            if current_matcher_hash == matcher_hash:
                if "hooks" in matcher_config:
                    for i, hook_dict in enumerate(matcher_config["hooks"]):
                        if hook_dict.get("type") == hook_type:
                            # 生成完整的 id 来验证
                            temp_config = HookConfig(**hook_dict)
                            temp_id = self._generate_hook_id(
                                temp_config,
                                scope,
                                HookEvent(event_value),
                                current_matcher,
                            )
                            if temp_id == hook_id:
                                # 找到了，更新
                                hook_dict_new = hook.model_dump(exclude_none=True)
                                matcher_config["hooks"][i] = hook_dict_new

                                self._save_settings_config_by_scope(config, scope)
                                return True

        return False

    def update_disable_all_hooks(self, value: bool) -> None:
        """
        更新 disableAllHooks 配置

        直接操作 settings.local.json 文件中的 disableAllHooks 值。

        Args:
            value: disableAllHooks 的布尔值

        Raises:
            ValueError: 当保存配置失败时抛出异常
        """
        settings_file = self.project_path / ".claude" / "settings.local.json"
        # 使用 settings_helper 进行增量更新
        update_config(settings_file, key_path=None, key="disableAllHooks", value=value)

    def _load_settings_config_by_scope(self, scope: ConfigScope) -> dict:
        """
        根据作用域加载 settings 配置

        Args:
            scope: 配置作用域

        Returns:
            dict: 配置字典
        """
        if scope == ConfigScope.user:
            settings_file = self.user_home / ".claude" / "settings.json"
        elif scope == ConfigScope.project:
            settings_file = self.project_path / ".claude" / "settings.json"
        elif scope == ConfigScope.local:
            settings_file = self.project_path / ".claude" / "settings.local.json"
        else:
            raise ValueError(f"Hooks 不支持作用域: {scope}")

        # 使用 settings_helper 加载配置
        return load_config(settings_file)

    def _save_settings_config_by_scope(self, config: dict, scope: ConfigScope) -> None:
        """
        根据作用域保存 settings 配置

        Args:
            config: 配置字典
            scope: 配置作用域
        """
        if scope == ConfigScope.user:
            settings_file = self.user_home / ".claude" / "settings.json"
        elif scope == ConfigScope.project:
            settings_file = self.project_path / ".claude" / "settings.json"
        elif scope == ConfigScope.local:
            settings_file = self.project_path / ".claude" / "settings.local.json"
        else:
            raise ValueError(f"Hooks 不支持作用域: {scope}")

        # 使用 settings_helper 保存配置
        save_config(settings_file, config)
