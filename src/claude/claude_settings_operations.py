"""
Settings 配置操作模块
处理 Settings 的加载和更新操作
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    ClaudeSettingsDTO,
    ClaudeSettingsInfoDTO,
    ConfigScope,
)
from .settings_helper import (
    convert_config_value,
    load_config,
    update_config,
)


class ClaudeSettingsOperations:
    """Claude Settings 操作类"""

    def __init__(self, project_path: Path, user_home: Optional[Path] = None):
        """
        初始化 Settings 操作管理器

        Args:
            project_path: 项目路径
            user_home: 用户主目录路径，可空，默认为系统 User 路径（用于单元测试）
        """
        self.project_path = project_path
        self.user_home = user_home if user_home else Path.home()

    def scan_settings(
        self, scope: Optional[ConfigScope] = None
    ) -> ClaudeSettingsInfoDTO:
        """
        扫描设置配置

        Args:
            scope: 配置作用域，可选值: user, project, local
                   为 None 时扫描所有作用域并合并（优先级: local > project > user

        Returns:
            ClaudeSettingsInfoDTO: 设置配置信息（包含作用域）
        """
        if scope is None:
            # 扫描所有作用域并合并
            user_settings, user_env = self._scan_and_flatten(ConfigScope.user)
            project_settings, project_env = self._scan_and_flatten(ConfigScope.project)
            local_settings, local_env = self._scan_and_flatten(ConfigScope.local)

            merged_settings = self._merge_with_scope(
                user_settings, project_settings, local_settings
            )
            merged_env = self._merge_env_with_scope(user_env, project_env, local_env)

            return ClaudeSettingsInfoDTO(settings=merged_settings, env=merged_env)
        else:
            # 只扫描指定作用域
            settings_dict, env_dict = self._scan_and_flatten(scope)
            # 添加作用域信息
            with_scope = {key: (value, scope) for key, value in settings_dict.items()}
            with_env_scope = [(key, value, scope) for key, value in env_dict.items()]
            return ClaudeSettingsInfoDTO(settings=with_scope, env=with_env_scope)

    def _scan_and_flatten(
        self, scope: ConfigScope
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        扫描指定作用域的配置并展平为字典

        Args:
            scope: 配置作用域

        Returns:
            (扁平化的配置字典, 环境变量字典)
            如: ({"model": "claude-3", "permissions.allow": ["*"]}, {"HTTP_PROXY": "http://..."})
        """
        settings_file = self._get_settings_file_by_scope(scope)
        settings_data = load_config(settings_file)
        settings_dto = ClaudeSettingsDTO.model_validate(
            settings_data,
            strict=False,
            from_attributes=True,
            context={"allow_extra": True},
        )
        # 转换为字典并展平
        data_dict = settings_dto.model_dump(exclude_none=True)

        # 提取 env 字段
        env_dict = data_dict.pop("env", {}) or {}

        # 展平剩余字段
        flattened = self._flatten_dict(data_dict)

        return flattened, env_dict

    def _flatten_dict(
        self, data: Dict[str, Any], parent_key: str = ""
    ) -> Dict[str, Any]:
        """
        将嵌套字典展平为单层字典

        Args:
            data: 输入字典
            parent_key: 父键前缀

        Returns:
            展平后的字典，如: {"permissions.allow": ["*"]}
        """
        items: Dict[str, Any] = {}
        for key, value in data.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, dict):
                # 递归展平嵌套字典
                items.update(self._flatten_dict(value, new_key))
            else:
                # 处理枚举类型
                if hasattr(value, "value"):
                    value = value.value
                items[new_key] = value
        return items

    def _merge_with_scope(
        self,
        user: Dict[str, Any],
        project: Dict[str, Any],
        local: Dict[str, Any],
    ) -> Dict[str, Tuple[Any, ConfigScope]]:
        """
        合并三个作用域的配置，优先级: local > project > user

        Args:
            user: user 配置字典
            project: project 配置字典
            local: local 配置字典

        Returns:
            合并后的配置，格式: {路径: (值, 作用域)}
        """
        result: Dict[str, Tuple[Any, ConfigScope]] = {}
        all_keys = set(user) | set(project) | set(local)

        for key in all_keys:
            # 按优先级选择值和作用域
            if key in local:
                result[key] = (local[key], ConfigScope.local)
            elif key in project:
                result[key] = (project[key], ConfigScope.project)
            else:
                result[key] = (user[key], ConfigScope.user)

        return result

    def _merge_env_with_scope(
        self,
        user: Dict[str, str],
        project: Dict[str, str],
        local: Dict[str, str],
    ) -> List[Tuple[str, str, ConfigScope]]:
        """
        合并三个作用域的环境变量，保留所有作用域的配置

        Args:
            user: user 环境变量字典
            project: project 环境变量字典
            local: local 环境变量字典

        Returns:
            环境变量列表，格式: [(变量名, 值, 作用域)]
        """
        result: List[Tuple[str, str, ConfigScope]] = []

        # 添加 user 环境变量
        for key, value in user.items():
            result.append((key, value, ConfigScope.user))

        # 添加 project 环境变量
        for key, value in project.items():
            result.append((key, value, ConfigScope.project))

        # 添加 local 环境变量
        for key, value in local.items():
            result.append((key, value, ConfigScope.local))

        return result

    def update_settings_values(
        self, scope: ConfigScope, key: str, value: str, value_type: str
    ) -> None:
        """
        更新设置配置中的键值对

        Args:
            scope: 配置作用域，可选值: user, project, local
            key: 配置项的键，支持点号分隔的嵌套键，如 'env.HTTP_PROXY'
            value: 配置项的值（字符串格式）
            value_type: 值类型，可选值: 'string', 'boolean', 'integer', 'array', 'object', 'dict'

        Raises:
            ValueError: 当 scope 或 key 无效时抛出异常
        """
        settings_file = self._get_settings_file_by_scope(scope)

        # 如果值为空字符串，执行移除操作
        if value == "":
            # 使用 settings_helper 删除键（value=None 表示删除）
            update_config(settings_file, key_path=None, key=key, value=None)
        else:
            # 转换值类型并更新
            converted_value = convert_config_value(value, value_type)
            update_config(settings_file, key_path=None, key=key, value=converted_value)

    def update_settings_scope(
        self,
        old_scope: ConfigScope,
        new_scope: ConfigScope,
        key: str,
    ) -> None:
        """
        更新设置配置项的作用域：从旧作用域移除，在新作用域添加

        Args:
            old_scope: 原配置作用域，可选值: user, project, local
            new_scope: 新配置作用域，可选值: user, project, local
            key: 配置项的键，支持点号分隔的嵌套键，如 'model' 或 'env.HTTP_PROXY'

        Raises:
            ValueError: 当 scope 或 key 无效时抛出异常
        """
        if old_scope == new_scope:
            return
        # 1. 获取旧作用域的完整配置
        old_settings_file = self._get_settings_file_by_scope(old_scope)
        old_settings_data = load_config(old_settings_file)
        old_settings_dto = ClaudeSettingsDTO.model_validate(
            old_settings_data,
            strict=False,
            from_attributes=True,
            context={"allow_extra": True},
        )

        # 2. 提取配置项的值（复用 _flatten_dict）
        data_dict = old_settings_dto.model_dump(exclude_none=True)
        flattened = self._flatten_dict(data_dict)

        # 如果值不存在，直接返回
        if key not in flattened:
            return

        value = flattened[key]

        # 3. 从旧作用域中删除配置项
        update_config(old_settings_file, key_path=None, key=key, value=None)

        # 4. 在新作用域中添加配置项
        new_settings_file = self._get_settings_file_by_scope(new_scope)
        # 使用 settings_helper 的 update_config 添加配置
        # 注意：这里需要传递原始值，而不是字符串
        update_config(new_settings_file, key_path=None, key=key, value=value)

    def _get_settings_file_by_scope(self, scope: ConfigScope) -> Path:
        """
        根据作用域获取 settings 文件路径

        Args:
            scope: 配置作用域

        Returns:
            Path: settings 文件路径

        Raises:
            ValueError: 当 scope 无效时抛出异常
        """
        if scope == ConfigScope.user:
            return self.user_home / ".claude" / "settings.json"
        elif scope == ConfigScope.project:
            return self.project_path / ".claude" / "settings.json"
        elif scope == ConfigScope.local:
            return self.project_path / ".claude" / "settings.local.json"
        else:
            raise ValueError(f"Settings 不支持作用域: {scope}")
