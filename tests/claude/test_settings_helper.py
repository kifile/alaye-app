"""
Settings Helper 模块的单元测试
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.claude.settings_helper import (
    convert_config_value,
    load_config,
    update_config,
    update_project_config,
)


class TestLoadConfig:
    """测试 load_config 函数"""

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件，应返回空字典"""
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent_file = Path(tmpdir) / "nonexistent.json"
            config = load_config(nonexistent_file)
            assert config == {}

    def test_load_simple_config(self):
        """测试加载简单配置文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            test_data = {"key1": "value1", "key2": "value2"}

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(test_data, f)

            config = load_config(config_file)
            assert config == test_data

    def test_load_with_key_path(self):
        """测试使用 key_path 加载子配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            test_data = {
                "projects": {
                    "/path/to/project1": {
                        "mcpServers": {"server1": {"command": "node"}}
                    },
                    "/path/to/project2": {
                        "mcpServers": {"server2": {"command": "python"}}
                    },
                }
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(test_data, f)

            # 加载特定项目的配置
            config = load_config(
                config_file, key_path=["projects", "/path/to/project1"]
            )
            assert config == {"mcpServers": {"server1": {"command": "node"}}}

    def test_load_with_nonexistent_key_path(self):
        """测试使用不存在的 key_path，应返回空字典"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            test_data = {"projects": {"/path/to/project1": {"mcpServers": {}}}}

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(test_data, f)

            # 尝试加载不存在的项目配置
            config = load_config(
                config_file, key_path=["projects", "/nonexistent/project"]
            )
            assert config == {}

    def test_load_with_key_path_pointing_to_non_dict(self):
        """测试 key_path 指向非字典类型时，应返回空字典"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            test_data = {"projects": "string_value"}

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(test_data, f)

            config = load_config(config_file, key_path=["projects"])
            assert config == {}

    def test_load_invalid_json(self):
        """测试加载无效的 JSON 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"

            with open(config_file, "w", encoding="utf-8") as f:
                f.write("{ invalid json }")

            with pytest.raises(ValueError, match="解析.*失败"):
                load_config(config_file)


class TestUpdateConfig:
    """测试 update_config 函数"""

    def test_update_nonexistent_file_creates_new(self):
        """测试更新不存在的文件，应创建新文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "new_config.json"

            # 文件不存在时创建新配置
            update_config(config_file, key_path=None, key="key1", value="value1")

            # 验证文件已创建
            assert config_file.exists()

            # 验证内容正确
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            assert config == {"key1": "value1"}

    def test_update_simple_key_value(self):
        """测试更新简单的键值对"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            initial_data = {"key1": "value1"}

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 添加新键
            update_config(config_file, key_path=None, key="key2", value="value2")

            # 验证
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            assert config == {"key1": "value1", "key2": "value2"}

    def test_update_nested_key_with_dots(self):
        """测试更新带点号的嵌套键"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"

            # 创建嵌套配置
            update_config(
                config_file,
                key_path=None,
                key="mcpServers.server1",
                value={"command": "node"},
            )

            # 验证
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            assert config == {"mcpServers": {"server1": {"command": "node"}}}

    def test_update_with_key_path(self):
        """测试使用 key_path 更新子配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "claude.json"
            initial_data = {
                "projects": {
                    "/path/to/project1": {"disabledMcpServers": ["server1"]},
                    "/path/to/project2": {"disabledMcpServers": ["server2"]},
                }
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 更新特定项目的配置
            update_config(
                config_file,
                key_path=["projects", "/path/to/project1"],
                key="disabledMcpServers",
                value=["server1", "server3"],
            )

            # 验证
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert config["projects"]["/path/to/project1"]["disabledMcpServers"] == [
                "server1",
                "server3",
            ]
            # 确保其他项目未被修改
            assert config["projects"]["/path/to/project2"]["disabledMcpServers"] == [
                "server2"
            ]

    def test_update_with_nonexistent_key_path_creates_path(self):
        """测试使用不存在的 key_path 时自动创建路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "claude.json"

            # 创建不存在的路径
            update_config(
                config_file,
                key_path=["projects", "/path/to/new_project"],
                key="mcpServers",
                value={"server1": {"command": "node"}},
            )

            # 验证
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert "projects" in config
            assert "/path/to/new_project" in config["projects"]
            assert config["projects"]["/path/to/new_project"]["mcpServers"] == {
                "server1": {"command": "node"}
            }

    def test_delete_key_with_none_value(self):
        """测试使用 None 值删除键"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            initial_data = {"key1": "value1", "key2": "value2"}

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 删除 key2
            update_config(config_file, key_path=None, key="key2", value=None)

            # 验证
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            assert config == {"key1": "value1"}
            assert "key2" not in config

    def test_delete_nested_key_with_none_value(self):
        """测试删除嵌套键"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            initial_data = {
                "mcpServers": {
                    "server1": {"command": "node"},
                    "server2": {"command": "python"},
                }
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 删除 server1
            update_config(
                config_file, key_path=None, key="mcpServers.server1", value=None
            )

            # 验证
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            assert config == {"mcpServers": {"server2": {"command": "python"}}}

    def test_delete_key_cleans_up_empty_objects(self):
        """测试删除键后自动清理空对象"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            initial_data = {
                "mcpServers": {
                    "server1": {"command": "node"},
                }
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 删除 server1，应该清理空的 mcpServers 对象
            update_config(
                config_file, key_path=None, key="mcpServers.server1", value=None
            )

            # 验证 mcpServers 也被删除了
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            assert config == {}

    def test_delete_with_key_path_cleans_up_empty_objects(self):
        """测试使用 key_path 删除后，清理空对象"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "claude.json"
            initial_data = {
                "projects": {
                    "/path/to/project1": {
                        "disabledMcpServers": ["server1"],
                        "mcpServers": {"server1": {"command": "node"}},
                    }
                }
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 删除 disabledMcpServers
            update_config(
                config_file,
                key_path=["projects", "/path/to/project1"],
                key="disabledMcpServers",
                value=None,
            )

            # 验证
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            # disabledMcpServers 被删除，但项目配置还在（因为还有 mcpServers）
            assert "disabledMcpServers" not in config["projects"]["/path/to/project1"]
            assert config["projects"]["/path/to/project1"]["mcpServers"] == {
                "server1": {"command": "node"}
            }

    def test_delete_nonexistent_key_does_nothing(self):
        """测试删除不存在的键，不应报错"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            initial_data = {"key1": "value1"}

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 尝试删除不存在的键
            update_config(config_file, key_path=None, key="nonexistent", value=None)

            # 验证配置未被修改
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            assert config == {"key1": "value1"}

    def test_update_non_dict_path_raises_error(self):
        """测试更新非字典类型的路径时应抛出异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            initial_data = {"key1": "string_value"}

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 尝试在字符串值上设置子键
            with pytest.raises(KeyError, match="不是字典类型"):
                update_config(
                    config_file, key_path=None, key="key1.subkey", value="value"
                )

    def test_update_with_key_path_non_dict_raises_error(self):
        """测试 key_path 包含非字典类型时应抛出异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            initial_data = {"projects": "string_value"}

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 尝试通过字符串类型的 projects 设置子键
            with pytest.raises(KeyError, match="不是字典类型"):
                update_config(
                    config_file,
                    key_path=["projects", "/some/path"],
                    key="key1",
                    value="value1",
                )


class TestConvertConfigValue:
    """测试 convert_config_value 函数"""

    def test_convert_string(self):
        """测试转换为字符串类型"""
        assert convert_config_value("hello", "string") == "hello"
        assert convert_config_value("123", "string") == "123"

    def test_convert_boolean_true(self):
        """测试转换为布尔类型（true）"""
        assert convert_config_value("true", "boolean") is True
        assert convert_config_value("True", "boolean") is True
        assert convert_config_value("TRUE", "boolean") is True
        assert convert_config_value("1", "boolean") is True
        assert convert_config_value("yes", "boolean") is True
        assert convert_config_value("on", "boolean") is True

    def test_convert_boolean_false(self):
        """测试转换为布尔类型（false）"""
        assert convert_config_value("false", "boolean") is False
        assert convert_config_value("False", "boolean") is False
        assert convert_config_value("FALSE", "boolean") is False
        assert convert_config_value("0", "boolean") is False
        assert convert_config_value("no", "boolean") is False
        assert convert_config_value("off", "boolean") is False

    def test_convert_boolean_invalid(self):
        """测试转换为无效的布尔类型"""
        with pytest.raises(ValueError, match="无法将.*转换为布尔类型"):
            convert_config_value("invalid", "boolean")

    def test_convert_integer(self):
        """测试转换为整数类型"""
        assert convert_config_value("42", "integer") == 42
        assert convert_config_value("-10", "integer") == -10
        assert convert_config_value("0", "integer") == 0

    def test_convert_integer_invalid(self):
        """测试转换为无效的整数类型"""
        with pytest.raises(ValueError, match="无法将.*转换为整数类型"):
            convert_config_value("not_a_number", "integer")

    def test_convert_array_json(self):
        """测试转换为数组类型（JSON 格式）"""
        result = convert_config_value('["a", "b", "c"]', "array")
        assert result == ["a", "b", "c"]

    def test_convert_array_comma_separated(self):
        """测试转换为数组类型（逗号分隔）"""
        result = convert_config_value("a,b,c", "array")
        assert result == ["a", "b", "c"]

        result = convert_config_value("x, y, z", "array")
        assert result == ["x", "y", "z"]

    def test_convert_array_empty(self):
        """测试转换为空数组"""
        result = convert_config_value("", "array")
        assert result == []

        result = convert_config_value("  ", "array")
        assert result == []

    def test_convert_object(self):
        """测试转换为对象类型"""
        result = convert_config_value('{"key": "value", "number": 42}', "object")
        assert result == {"key": "value", "number": 42}

    def test_convert_object_invalid(self):
        """测试转换为无效的对象类型"""
        with pytest.raises(ValueError, match="无法将.*转换为 JSON 对象"):
            convert_config_value("{invalid json}", "object")

    def test_convert_dict(self):
        """测试转换为字典类型"""
        result = convert_config_value('{"key": "value"}', "dict")
        assert result == {"key": "value"}

    def test_convert_dict_invalid_json(self):
        """测试转换为无效的字典类型（JSON 解析失败）"""
        with pytest.raises(ValueError, match="无法将.*转换为字典类型"):
            convert_config_value("{invalid}", "dict")

    def test_convert_dict_not_dict_type(self):
        """测试转换为字典类型（解析结果不是字典）"""
        with pytest.raises(ValueError, match="不是有效的字典格式"):
            convert_config_value('["array", "value"]', "dict")

    def test_convert_unsupported_type(self):
        """测试转换为不支持的类型"""
        with pytest.raises(ValueError, match="不支持的值类型"):
            convert_config_value("value", "unsupported_type")


class TestUpdateConfigWithSplitKey:
    """测试 update_config 函数的 split_key 参数"""

    def test_update_with_split_key_false(self):
        """测试 split_key=False 时，包含点号的键名不被分割"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"

            # 添加包含点号的键名
            update_config(
                config_file,
                key_path=["mcpServers"],
                key="my.server",
                value={"command": "node", "args": ["server.js"]},
                split_key=False,
            )

            # 验证配置结构
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert config == {
                "mcpServers": {"my.server": {"command": "node", "args": ["server.js"]}}
            }

    def test_update_with_split_key_false_multiple_dots(self):
        """测试 split_key=False 时，多个点号的键名不被分割"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"

            test_names = [
                "my.server",
                "server.v1.example",
                "com.example.mcp.server",
                "test..server",
                ".server",
            ]

            for name in test_names:
                update_config(
                    config_file,
                    key_path=["mcpServers"],
                    key=name,
                    value={"command": f"test_{name}"},
                    split_key=False,
                )

            # 验证所有键名都保持完整
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            for name in test_names:
                assert name in config["mcpServers"]
                assert config["mcpServers"][name]["command"] == f"test_{name}"

    def test_update_with_split_key_false_delete(self):
        """测试 split_key=False 时删除包含点号的键名"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            initial_data = {
                "mcpServers": {
                    "my.server": {"command": "node"},
                    "normal.server": {"command": "python"},
                }
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 删除包含点号的键
            update_config(
                config_file,
                key_path=["mcpServers"],
                key="my.server",
                value=None,
                split_key=False,
            )

            # 验证删除成功
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert "my.server" not in config["mcpServers"]
            assert "normal.server" in config["mcpServers"]

    def test_update_with_split_key_true_default(self):
        """测试 split_key=True（默认）时，点号分割的嵌套键正常工作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"

            # 默认行为：split_key=True，点号作为分隔符
            update_config(
                config_file,
                key_path=None,
                key="mcpServers.server1.env",
                value="development",
            )

            # 验证嵌套结构
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert config == {"mcpServers": {"server1": {"env": "development"}}}

    def test_update_with_split_key_and_key_path(self):
        """测试 split_key=False 与 key_path 组合使用"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            initial_data = {
                "projects": {"/path/to/project": {"disabledMcpServers": []}}
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 使用 key_path 和 split_key=False 添加包含点号的 MCP 服务器
            update_config(
                config_file,
                key_path=["projects", "/path/to/project", "mcpServers"],
                key="my.custom.server",
                value={"command": "node"},
                split_key=False,
            )

            # 验证配置结构
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert (
                "my.custom.server"
                in config["projects"]["/path/to/project"]["mcpServers"]
            )
            assert config["projects"]["/path/to/project"]["mcpServers"][
                "my.custom.server"
            ] == {"command": "node"}

    def test_update_with_split_key_false_preserves_empty_objects(self):
        """测试 split_key=False 删除后正确清理空对象"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            initial_data = {
                "mcpServers": {
                    "my.server": {"command": "node"},
                }
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 删除唯一的键，应该清理空的 mcpServers
            update_config(
                config_file,
                key_path=["mcpServers"],
                key="my.server",
                value=None,
                split_key=False,
            )

            # 验证 mcpServers 也被清理
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert config == {}


class TestUpdateProjectConfig:
    """测试 update_project_config 函数"""

    def test_update_project_config_basic(self):
        """测试基本的项目配置更新"""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_json = Path(tmpdir) / ".claude.json"
            initial_data = {
                "projects": {"/path/to/project": {"disabledMcpServers": []}}
            }

            with open(claude_json, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 更新项目配置（使用默认的 split_key=True）
            success = update_project_config(
                claude_json,
                Path("/path/to/project"),
                "disabledMcpServers",
                ["server1", "server2"],
            )

            assert success is True

            # 验证更新
            with open(claude_json, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert config["projects"]["/path/to/project"]["disabledMcpServers"] == [
                "server1",
                "server2",
            ]

    def test_update_project_config_with_key_path(self):
        """测试使用 key_path 参数更新项目配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_json = Path(tmpdir) / ".claude.json"
            initial_data = {
                "projects": {"/path/to/project": {"disabledMcpServers": []}}
            }

            with open(claude_json, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 使用 key_path 添加 MCP 服务器
            success = update_project_config(
                claude_json,
                Path("/path/to/project"),
                "myServer",
                {"command": "node"},
                key_path=["mcpServers"],
            )

            assert success is True

            # 验证配置结构
            with open(claude_json, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert "mcpServers" in config["projects"]["/path/to/project"]
            assert config["projects"]["/path/to/project"]["mcpServers"]["myServer"] == {
                "command": "node"
            }

    def test_update_project_config_with_split_key_false(self):
        """测试 split_key=False 与 key_path 组合使用"""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_json = Path(tmpdir) / ".claude.json"
            initial_data = {
                "projects": {"/path/to/project": {"disabledMcpServers": []}}
            }

            with open(claude_json, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 添加包含点号的 MCP 服务器
            success = update_project_config(
                claude_json,
                Path("/path/to/project"),
                "my.server",
                {"command": "node", "args": ["server.js"]},
                key_path=["mcpServers"],
                split_key=False,
            )

            assert success is True

            # 验证键名未被分割
            with open(claude_json, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert "my.server" in config["projects"]["/path/to/project"]["mcpServers"]
            assert config["projects"]["/path/to/project"]["mcpServers"][
                "my.server"
            ] == {"command": "node", "args": ["server.js"]}

    def test_update_project_config_nonexistent_project(self):
        """测试更新不存在的项目配置，应返回 False"""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_json = Path(tmpdir) / ".claude.json"
            initial_data = {"projects": {"/existing/project": {}}}

            with open(claude_json, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 尝试更新不存在的项目
            success = update_project_config(
                claude_json, Path("/nonexistent/project"), "key", "value"
            )

            assert success is False

    def test_update_project_config_delete(self):
        """测试删除项目配置中的键"""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_json = Path(tmpdir) / ".claude.json"
            initial_data = {
                "projects": {
                    "/path/to/project": {
                        "mcpServers": {"server1": {"command": "node"}},
                        "disabledMcpServers": ["server1"],
                    }
                }
            }

            with open(claude_json, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 删除 mcpServers 中的 server1
            success = update_project_config(
                claude_json,
                Path("/path/to/project"),
                "server1",
                None,
                key_path=["mcpServers"],
            )

            assert success is True

            # 验证删除成功（空对象被清理）
            with open(claude_json, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert "mcpServers" not in config["projects"]["/path/to/project"]
            assert config["projects"]["/path/to/project"]["disabledMcpServers"] == [
                "server1"
            ]

    def test_update_project_config_with_split_key_false_delete(self):
        """测试 split_key=False 删除包含点号的键"""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_json = Path(tmpdir) / ".claude.json"
            initial_data = {
                "projects": {
                    "/path/to/project": {
                        "mcpServers": {
                            "my.server": {"command": "node"},
                            "normal.server": {"command": "python"},
                        }
                    }
                }
            }

            with open(claude_json, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # 删除包含点号的键
            success = update_project_config(
                claude_json,
                Path("/path/to/project"),
                "my.server",
                None,
                key_path=["mcpServers"],
                split_key=False,
            )

            assert success is True

            # 验证删除成功
            with open(claude_json, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert (
                "my.server" not in config["projects"]["/path/to/project"]["mcpServers"]
            )
            assert (
                "normal.server" in config["projects"]["/path/to/project"]["mcpServers"]
            )
