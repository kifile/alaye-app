"""
Settings 文件操作辅助模块
提供统一的 JSON 配置文件读写接口，支持嵌套路径操作和增量更新
"""

import json
from pathlib import Path
from typing import Any


def load_config(config_path: Path, key_path: list[str] | None = None) -> dict:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径
        key_path: 可选的嵌套路径，用于定位配置中的特定子节点
                 例如 ["projects", "/path/to/project"] 用于 ~/.claude.json 中的项目配置

    Returns:
        dict: 配置字典。如果指定了 key_path，返回对应的子配置；否则返回完整配置。
             如果文件不存在或为空，返回空字典。

    Raises:
        ValueError: 当文件解析失败时抛出异常

    Example:
        # 读取 ~/.claude/settings.json
        config = load_config(Path.home() / ".claude" / "settings.json")

        # 读取 ~/.claude.json 中特定项目的配置
        config = load_config(
            Path.home() / ".claude.json",
            key_path=["projects", "/path/to/project"]
        )
    """
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            full_config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"解析 {config_path} 失败: {e}")
    except Exception as e:
        raise ValueError(f"读取 {config_path} 失败: {e}")

    # 如果没有 key_path，直接返回完整配置
    if not key_path:
        return full_config

    # 根据 key_path 导航到子配置
    current = full_config
    for key in key_path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            # 路径不存在，返回空字典
            return {}

    # 确保返回的是字典
    if not isinstance(current, dict):
        return {}

    return current


def update_config(
    config_path: Path,
    key_path: list[str] | None,
    key: str,
    value: Any,
    split_key: bool = True,
) -> None:
    """
    增量更新配置文件

    支持点号分隔的嵌套键。如果 value 为 None，则删除该键。

    Args:
        config_path: 配置文件路径
        key_path: 可选的嵌套路径，用于定位配置中的特定子节点
                 例如 ["projects", "/path/to/project"] 用于 ~/.claude.json 中的项目配置
        key: 配置项的键，支持点号分隔的嵌套键，如 'mcpServers.server1' 或 'env.HTTP_PROXY'
             当 split_key=False 时，key 将作为完整的键名，不进行点号分割
        value: 配置项的值。如果为 None，则删除该键
        split_key: 是否对 key 进行点号分割，默认为 True。设置为 False 时，key 不会被分割，
                   用于处理键名中包含点号的情况（如 MCP 服务器名称 "my.server"）

    Raises:
        ValueError: 当保存配置失败时抛出异常
        KeyError: 当无法定位到键路径时抛出异常

    Example:
        # 更新 settings.json 中的值（默认 split_key=True）
        update_config(
            Path.home() / ".claude" / "settings.json",
            key_path=None,
            key="mcpServers.server1",
            value={"command": "node", "args": ["server.js"]}
        )

        # 更新 ~/.claude.json 中特定项目的配置
        update_config(
            Path.home() / ".claude.json",
            key_path=["projects", "/path/to/project"],
            key="disabledMcpServers",
            value=["server1"]
        )

        # 删除配置项
        update_config(
            Path.home() / ".claude" / "settings.json",
            key_path=None,
            key="mcpServers.oldServer",
            value=None  # 删除
        )

        # 当键名包含点号时，使用 split_key=False
        update_config(
            Path.home() / ".claude" / "settings.json",
            key_path=["mcpServers"],
            key="my.server",
            value={"command": "node", "args": ["server.js"]},
            split_key=False
        )
    """
    # 读取完整配置
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"解析 {config_path} 失败: {e}")
        except Exception as e:
            raise ValueError(f"读取 {config_path} 失败: {e}")
    else:
        config = {}

    # 1. 先根据 key_path 定位到根对象
    root_obj = config
    if key_path:
        for k in key_path:
            if k not in root_obj:
                root_obj[k] = {}
            if not isinstance(root_obj[k], dict):
                raise KeyError(f"路径 '{k}' 不是字典类型，无法设置子键")
            root_obj = root_obj[k]

    # 2. 在根对象上对 key 进行 split 和更新
    if split_key:
        # 默认行为：支持点号分隔的嵌套键
        if "." in key:
            keys = key.split(".")
        else:
            keys = [key]
    else:
        # split_key=False：将 key 作为完整的键名，不进行分割
        keys = [key]

    # 3. 导航到最后一级的父对象
    current = root_obj
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        if not isinstance(current[k], dict):
            raise KeyError(f"路径 '{k}' 不是字典类型，无法设置子键")
        current = current[k]

    # 4. 设置或删除最终键
    final_key = keys[-1]

    if value is None:
        # 删除操作
        if final_key in current:
            del current[final_key]

            # 检查是否需要清理空的父对象
            # 先清理 key 对应的空对象
            _cleanup_empty_objects(root_obj, keys[:-1])

            # 如果 key_path 存在，再清理 key_path 对应的空对象
            if key_path:
                _cleanup_empty_objects(config, key_path)
        else:
            # key 不存在，但仍需检查 key_path 对应的空对象
            if key_path:
                _cleanup_empty_objects(config, key_path)
    else:
        # 设置值
        current[final_key] = value

    # 确保目录存在
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # 保存配置
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise ValueError(f"保存 {config_path} 失败: {e}")


def convert_config_value(value: str, value_type: str) -> Any:
    """
    根据指定的值类型转换值的数据类型

    Args:
        value: 字符串值
        value_type: 值类型，可选值: 'string', 'boolean', 'integer', 'array', 'object', 'dict'

    Returns:
        转换后适当类型的值

    Raises:
        ValueError: 当类型转换失败时抛出异常

    Example:
        # 转换为布尔值
        bool_val = convert_config_value("true", "boolean")  # True

        # 转换为整数
        int_val = convert_config_value("42", "integer")  # 42

        # 转换为数组
        arr_val = convert_config_value("a,b,c", "array")  # ["a", "b", "c"]

        # 转换为 JSON 对象
        obj_val = convert_config_value('{"key": "value"}', "object")  # {"key": "value"}
    """
    if value_type == "string":
        return value

    elif value_type == "boolean":
        lower_value = value.lower().strip()
        if lower_value in ("true", "1", "yes", "on"):
            return True
        elif lower_value in ("false", "0", "no", "off"):
            return False
        else:
            raise ValueError(f"无法将 '{value}' 转换为布尔类型")

    elif value_type == "integer":
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"无法将 '{value}' 转换为整数类型")

    elif value_type == "array":
        # 尝试解析为 JSON 数组
        if value.strip().startswith("[") and value.strip().endswith("]"):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # JSON 解析失败，继续尝试其他方式
                pass

        # 按逗号分隔
        items = [item.strip() for item in value.split(",") if item.strip()]
        return items

    elif value_type == "object":
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise ValueError(f"无法将 '{value}' 转换为 JSON 对象")

    elif value_type == "dict":
        # 尝试解析为 JSON 对象
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
            else:
                raise ValueError(f"'{value}' 不是有效的字典格式")
        except json.JSONDecodeError:
            raise ValueError(f"无法将 '{value}' 转换为字典类型")

    else:
        raise ValueError(
            f"不支持的值类型: {value_type}，支持的类型: string, boolean, integer, array, object, dict"
        )


def save_config(config_path: Path, config: dict) -> None:
    """
    保存整个配置字典到文件

    Args:
        config_path: 配置文件路径
        config: 要保存的完整配置字典

    Raises:
        ValueError: 当保存配置失败时抛出异常

    Example:
        # 保存整个配置
        config = {"mcpServers": {"server1": {"command": "node"}}}
        save_config(Path.home() / ".claude" / "settings.json", config)
    """
    # 确保目录存在
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # 保存配置
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise ValueError(f"保存 {config_path} 失败: {e}")


def load_project_config(claude_json_path: Path, project_path: Path) -> dict:
    """
    从 ~/.claude.json 加载特定项目的配置

    Args:
        claude_json_path: ~/.claude.json 文件路径
        project_path: 项目路径

    Returns:
        dict: 项目配置字典。如果未找到项目配置，返回空字典。

    Example:
        # 加载项目配置
        project_config = load_project_config(
            Path.home() / ".claude.json",
            Path("/path/to/project")
        )
        # 如果项目存在，返回如 {"mcpServers": {}, "disabledMcpServers": []}
        # 如果项目不存在，返回 {}
    """
    # 加载完整配置
    config = load_config(claude_json_path)

    # 查找当前项目的配置
    for proj_path in config.get("projects", {}).keys():
        try:
            if Path(proj_path).resolve() == project_path.resolve():
                return config.get("projects", {}).get(proj_path, {})
        except Exception:
            continue

    # 未找到项目配置
    return {}


def update_project_config(
    claude_json_path: Path,
    project_path: Path,
    key: str,
    value: Any,
    key_path: list[str] | None = None,
    split_key: bool = True,
) -> bool:
    """
    更新 ~/.claude.json 中特定项目的配置

    Args:
        claude_json_path: ~/.claude.json 文件路径
        project_path: 项目路径
        key: 配置项的键，支持点号分隔的嵌套键
             当 split_key=False 时，key 将作为完整的键名，不进行点号分割
        value: 配置项的值
        key_path: 可选的嵌套路径，用于定位项目配置中的特定子节点
                 如果提供，将在 ["projects", project_key] 之后追加该路径
        split_key: 是否对 key 进行点号分割，默认为 True。设置为 False 时，key 不会被分割

    Returns:
        bool: 是否成功更新（找到项目配置并更新）

    Raises:
        ValueError: 当保存配置失败时抛出异常

    Example:
        # 更新项目的 MCP 服务器配置（默认 split_key=True）
        success = update_project_config(
            Path.home() / ".claude.json",
            Path("/path/to/project"),
            "server1",
            {"command": "node", "args": ["server.js"]},
            key_path=["mcpServers"]
        )

        # 当 MCP 服务器名称包含点号时，使用 split_key=False
        success = update_project_config(
            Path.home() / ".claude.json",
            Path("/path/to/project"),
            "my.server",
            {"command": "node", "args": ["server.js"]},
            key_path=["mcpServers"],
            split_key=False
        )
    """
    # 加载完整配置
    config = load_config(claude_json_path)

    # 查找当前项目的配置路径
    proj_key = None
    for proj_path in config.get("projects", {}).keys():
        try:
            if Path(proj_path).resolve() == project_path.resolve():
                proj_key = proj_path
                break
        except Exception:
            continue

    if not proj_key:
        # 未找到项目配置，返回 False
        return False

    # 构建完整的 key_path：["projects", proj_key] + (key_path or [])
    full_key_path = ["projects", proj_key]
    if key_path:
        full_key_path.extend(key_path)

    # 更新配置
    update_config(
        claude_json_path,
        key_path=full_key_path,
        key=key,
        value=value,
        split_key=split_key,
    )

    return True


def save_project_config(
    claude_json_path: Path, project_path: Path, project_config: dict
) -> bool:
    """
    保存 ~/.claude.json 中特定项目的完整配置

    Args:
        claude_json_path: ~/.claude.json 文件路径
        project_path: 项目路径
        project_config: 要保存的项目配置字典

    Returns:
        bool: 是否成功保存

    Raises:
        ValueError: 当保存配置失败时抛出异常

    Example:
        # 保存项目的完整配置
        success = save_project_config(
            Path.home() / ".claude.json",
            Path("/path/to/project"),
            {"mcpServers": {"server1": {"command": "node"}}, "disabledMcpServers": []}
        )
    """
    # 加载完整配置
    full_config = load_config(claude_json_path)

    # 查找当前项目的配置路径
    proj_key = None
    for proj_path in full_config.get("projects", {}).keys():
        try:
            if Path(proj_path).resolve() == project_path.resolve():
                proj_key = proj_path
                break
        except Exception:
            continue

    if not proj_key:
        # 未找到项目配置，创建新的
        proj_key = str(project_path)

    # 更新项目配置
    if "projects" not in full_config:
        full_config["projects"] = {}
    full_config["projects"][proj_key] = project_config

    # 保存完整配置
    save_config(claude_json_path, full_config)

    return True


def add_to_config(
    config_path: Path,
    key_path: list[str] | None,
    key: str,
    value: str,
) -> None:
    """
    向配置中的列表添加元素

    如果列表不存在，则创建新列表。如果元素已存在，则不重复添加。

    Args:
        config_path: 配置文件路径
        key_path: 可选的嵌套路径，用于定位配置中的特定子节点
        key: 配置项的键，其值应该是一个列表
        value: 要添加到列表的元素

    Raises:
        ValueError: 当保存配置失败时抛出异常
        KeyError: 当键路径指向非字典类型时抛出异常

    Example:
        # 向列表添加元素
        add_to_config(
            Path.home() / ".claude" / "settings.json",
            key_path=None,
            key="disabledMcpjsonServers",
            value="server1"
        )

        # 向嵌套列表添加元素
        add_to_config(
            Path.home() / ".claude.json",
            key_path=["projects", "/path/to/project"],
            key="disabledMcpServers",
            value="server1"
        )
    """
    # 加载完整配置
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"解析 {config_path} 失败: {e}")
        except Exception as e:
            raise ValueError(f"读取 {config_path} 失败: {e}")
    else:
        config = {}

    # 1. 先根据 key_path 定位到根对象
    root_obj = config
    if key_path:
        for k in key_path:
            if k not in root_obj:
                root_obj[k] = {}
            if not isinstance(root_obj[k], dict):
                raise KeyError(f"路径 '{k}' 不是字典类型，无法设置子键")
            root_obj = root_obj[k]

    # 2. 在根对象上对 key 进行操作
    if "." in key:
        keys = key.split(".")
    else:
        keys = [key]

    # 3. 导航到最后一级的父对象
    current = root_obj
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        if not isinstance(current[k], dict):
            raise KeyError(f"路径 '{k}' 不是字典类型，无法设置子键")
        current = current[k]

    # 4. 获取或创建列表
    final_key = keys[-1]
    if final_key not in current:
        current[final_key] = []
    elif not isinstance(current[final_key], list):
        current[final_key] = []

    # 5. 添加元素（如果不存在）
    if value not in current[final_key]:
        current[final_key].append(value)

    # 确保目录存在并保存配置
    config_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise ValueError(f"保存 {config_path} 失败: {e}")


def remove_from_config(
    config_path: Path,
    key_path: list[str] | None,
    key: str,
    value: str,
) -> None:
    """
    从配置中的列表移除元素

    如果列表为空或元素不存在，则不做任何操作。

    Args:
        config_path: 配置文件路径
        key_path: 可选的嵌套路径，用于定位配置中的特定子节点
        key: 配置项的键，其值应该是一个列表
        value: 要从列表中移除的元素

    Raises:
        ValueError: 当保存配置失败时抛出异常
        KeyError: 当键路径指向非字典类型时抛出异常

    Example:
        # 从列表移除元素
        remove_from_config(
            Path.home() / ".claude" / "settings.json",
            key_path=None,
            key="disabledMcpjsonServers",
            value="server1"
        )

        # 从嵌套列表移除元素
        remove_from_config(
            Path.home() / ".claude.json",
            key_path=["projects", "/path/to/project"],
            key="disabledMcpServers",
            value="server1"
        )
    """
    # 加载完整配置
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"解析 {config_path} 失败: {e}")
        except Exception as e:
            raise ValueError(f"读取 {config_path} 失败: {e}")
    else:
        config = {}

    # 1. 先根据 key_path 定位到根对象
    root_obj = config
    if key_path:
        for k in key_path:
            if k not in root_obj:
                # 路径不存在，不需要移除
                return
            if not isinstance(root_obj[k], dict):
                raise KeyError(f"路径 '{k}' 不是字典类型，无法导航")
            root_obj = root_obj[k]

    # 2. 在根对象上对 key 进行操作
    if "." in key:
        keys = key.split(".")
    else:
        keys = [key]

    # 3. 导航到最后一级的父对象
    current = root_obj
    for k in keys[:-1]:
        if k not in current:
            # 路径不存在，不需要移除
            return
        if not isinstance(current[k], dict):
            raise KeyError(f"路径 '{k}' 不是字典类型，无法导航")
        current = current[k]

    # 4. 获取列表并移除元素
    final_key = keys[-1]
    if final_key not in current:
        # 键不存在，不需要移除
        return

    if not isinstance(current[final_key], list):
        # 不是列表，无法移除
        return

    # 5. 移除元素（如果存在）
    if value in current[final_key]:
        current[final_key].remove(value)

        # 如果列表为空，可以保留空列表或删除键
        # 这里选择保留空列表，以便后续添加

    # 确保目录存在并保存配置
    config_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise ValueError(f"保存 {config_path} 失败: {e}")


def add_to_project_config(
    claude_json_path: Path,
    project_path: Path,
    key: str,
    value: str,
) -> bool:
    """
    向 ~/.claude.json 中项目配置的列表添加元素

    如果列表不存在，则创建新列表。如果元素已存在，则不重复添加。

    Args:
        claude_json_path: ~/.claude.json 文件路径
        project_path: 项目路径
        key: 配置项的键，其值应该是一个列表
        value: 要添加到列表的元素

    Returns:
        bool: 是否成功添加（找到项目配置并添加）

    Raises:
        ValueError: 当保存配置失败时抛出异常
        KeyError: 当键路径指向非字典类型时抛出异常

    Example:
        # 向项目的 disabledMcpServers 列表添加元素
        add_to_project_config(
            Path.home() / ".claude.json",
            Path("/path/to/project"),
            "disabledMcpServers",
            "server1"
        )
    """
    # 加载完整配置
    config = load_config(claude_json_path)

    # 查找当前项目的配置路径
    proj_key = None
    for proj_path in config.get("projects", {}).keys():
        try:
            if Path(proj_path).resolve() == project_path.resolve():
                proj_key = proj_path
                break
        except Exception:
            continue

    if not proj_key:
        # 未找到项目配置，返回 False
        return False

    # 使用 add_to_config 添加元素
    add_to_config(
        claude_json_path, key_path=["projects", proj_key], key=key, value=value
    )
    return True


def remove_from_project_config(
    claude_json_path: Path,
    project_path: Path,
    key: str,
    value: str,
) -> bool:
    """
    从 ~/.claude.json 中项目配置的列表移除元素

    如果列表为空或元素不存在，则不做任何操作。

    Args:
        claude_json_path: ~/.claude.json 文件路径
        project_path: 项目路径
        key: 配置项的键，其值应该是一个列表
        value: 要从列表中移除的元素

    Returns:
        bool: 是否成功移除（找到项目配置并移除）

    Raises:
        ValueError: 当保存配置失败时抛出异常
        KeyError: 当键路径指向非字典类型时抛出异常

    Example:
        # 从项目的 disabledMcpServers 列表移除元素
        remove_from_project_config(
            Path.home() / ".claude.json",
            Path("/path/to/project"),
            "disabledMcpServers",
            "server1"
        )
    """
    # 加载完整配置
    config = load_config(claude_json_path)

    # 查找当前项目的配置路径
    proj_key = None
    for proj_path in config.get("projects", {}).keys():
        try:
            if Path(proj_path).resolve() == project_path.resolve():
                proj_key = proj_path
                break
        except Exception:
            continue

    if not proj_key:
        # 未找到项目配置，返回 False
        return False

    # 使用 remove_from_config 移除元素
    remove_from_config(
        claude_json_path, key_path=["projects", proj_key], key=key, value=value
    )
    return True


def _cleanup_empty_objects(config: dict, key_path: list[str]) -> None:
    """
    递归清理空的嵌套对象（内部辅助函数）

    Args:
        config: 配置字典
        key_path: 从根到被删除键的路径（不包含被删除的键）
    """
    if not key_path:
        return

    # 从最深层的父对象开始检查
    for i in range(len(key_path) - 1, -1, -1):
        current_path = key_path[: i + 1]
        current_obj = config

        # 导航到当前检查的对象
        for k in current_path[:-1]:
            if k not in current_obj or not isinstance(current_obj[k], dict):
                break
            current_obj = current_obj[k]

        # 获取要检查的键
        check_key = current_path[-1]
        if (
            check_key in current_obj
            and isinstance(current_obj[check_key], dict)
            and not current_obj[check_key]
        ):
            # 如果对象为空，则删除它
            del current_obj[check_key]
        else:
            # 如果对象不为空或不存在，停止清理
            break
