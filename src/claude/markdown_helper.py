"""
Markdown 辅助工具模块
提供从 Markdown 文件中提取元数据的辅助函数
"""

import re
from pathlib import Path
from typing import Optional


def extract_frontmatter_label(content: str, label: str) -> Optional[str]:
    """
    从 Markdown 内容的 frontmatter 中提取指定标签的值

    Args:
        content: Markdown 文件内容
        label: 要提取的标签名称（例如: 'description'）

    Returns:
        Optional[str]: 如果找到标签则返回其值，否则返回 None

    Example:
        >>> content = '''
        ---\\ndescription: This is a test
        ---\\n# Title'''
        >>> extract_frontmatter_label(content, 'description')
        'This is a test'
    """
    # 匹配 YAML frontmatter (在文件开头的 --- ... --- 之间)
    frontmatter_pattern = r"^---\s*\n(.*?)\n---"
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if not match:
        return None

    frontmatter = match.group(1)

    # 尝试匹配 key: value 格式
    # 支持多种格式:
    # - description: value
    # - description: "value"
    # - description: 'value'
    pattern = rf"^{re.escape(label)}\s*:\s*(.+)$"

    for line in frontmatter.split("\n"):
        line = line.strip()
        match = re.match(pattern, line, re.MULTILINE)
        if match:
            value = match.group(1).strip()

            # 移除引号（如果有）
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]

            return value

    return None


def extract_description(file_path: Path, label: str = "description") -> Optional[str]:
    """
    从 Markdown 文件的 frontmatter 中提取描述信息

    Args:
        file_path: Markdown 文件路径
        label: 要提取的标签名称，默认为 'description'

    Returns:
        Optional[str]: 如果找到描述则返回其值，否则返回 None

    Example:
        >>> from pathlib import Path
        >>> file_path = Path('/path/to/command.md')
        >>> extract_description(file_path)
        'A sample command'
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            return extract_frontmatter_label(content, label)
    except Exception:
        # 文件读取失败，返回 None
        return None


def update_frontmatter_name(content: str, new_name: str) -> str:
    """
    更新 Markdown 内容 frontmatter 中的 name 字段

    Args:
        content: Markdown 文件内容
        new_name: 新的 name 值

    Returns:
        str: 更新后的 Markdown 内容

    Example:
        >>> content = '''---
        name: old-name
        description: Test
        ---
        # Content'''
        >>> update_frontmatter_name(content, 'new-name')
        '---\\nname: new-name\\ndescription: Test\\n---\\n# Content'
    """
    # 匹配 YAML frontmatter (在文件开头的 --- ... --- 之间)
    frontmatter_pattern = r"^---\s*\n(.*?)\n---"
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if not match:
        # 没有 frontmatter，直接返回原内容
        return content

    frontmatter = match.group(1)
    content_after_frontmatter = content[match.end() :]

    # 尝试匹配 name: value 格式
    # 支持多种格式:
    # - name: value
    # - name: "value"
    # - name: 'value'
    name_pattern = r"^name\s*:\s*(.+)$"

    # 在 frontmatter 中查找 name 字段
    frontmatter_lines = frontmatter.split("\n")
    updated = False

    for i, line in enumerate(frontmatter_lines):
        line_match = re.match(name_pattern, line, re.MULTILINE)
        if line_match:
            # 找到 name 字段，更新它
            frontmatter_lines[i] = f"name: {new_name}"
            updated = True
            break

    if not updated:
        # 没找到 name 字段，放弃更新，直接返回原内容
        return content

    # 重新组装内容
    new_frontmatter = "\n".join(frontmatter_lines)
    return f"---\n{new_frontmatter}\n---{content_after_frontmatter}"


def update_file_name_field(file_path: Path, new_name: str) -> bool:
    """
    更新 Markdown 文件 frontmatter 中的 name 字段

    Args:
        file_path: Markdown 文件路径
        new_name: 新的 name 值

    Returns:
        bool: 是否成功更新（如果文件不存在或读取失败返回 False）

    Example:
        >>> from pathlib import Path
        >>> file_path = Path('/path/to/command.md')
        >>> update_file_name_field(file_path, 'new-name')
        True
    """
    try:
        # 读取文件内容
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 更新 frontmatter 中的 name 字段
        updated_content = update_frontmatter_name(content, new_name)

        # 如果内容发生变化，写回文件
        if updated_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)
            return True

        return False
    except Exception:
        # 文件操作失败
        return False
