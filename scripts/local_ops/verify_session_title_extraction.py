#!/usr/bin/env python3
"""
验证 Session 标题提取功能

遍历 $HOME/.claude/projects 下的所有 session 文件，
提取标题并验证是否从第一行有效消息获取（跳过 file_history_snapshot 和 Warmup）。
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Tuple

# 添加项目路径到 Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.claude.claude_session_operations import ClaudeSessionOperations


def find_claude_projects_path() -> Path:
    """
    查找 Claude projects 目录

    Returns:
        Path: Claude projects 目录路径
    """
    claude_path = Path.home() / ".claude" / "projects"

    if not claude_path.exists():
        print(f"❌ Claude projects 目录不存在: {claude_path}")
        print("提示：请确保 Claude Code 已安装并至少创建过一个项目")
        sys.exit(1)

    return claude_path


async def verify_single_file_title(
    session_file: Path, session_ops: ClaudeSessionOperations
) -> Tuple[str, str, int]:
    """
    验证单个 session 文件的标题提取

    Args:
        session_file: session 文件路径
        session_ops: ClaudeSessionOperations 实例

    Returns:
        Tuple[str, str, int]: (标题, session_id, 提取行号)
    """
    session_id = session_file.stem

    # 使用 _read_session_title 方法提取标题（现在返回标题和行号）
    title, line_number = await session_ops._read_session_title(session_file)

    return title or "无标题", session_id, line_number


async def verify_all_session_titles():
    """
    验证所有 session 文件的标题提取
    """
    claude_path = find_claude_projects_path()
    print(f"📁 扫描目录: {claude_path}\n")

    # 收集所有 session 文件
    # Claude 的目录结构是: ~/.claude/projects/<project-name>/*.jsonl
    session_files = []
    for project_dir in claude_path.iterdir():
        if not project_dir.is_dir():
            continue

        # 每个项目目录下的所有 .jsonl 文件
        for session_file in project_dir.glob("*.jsonl"):
            session_files.append(session_file)

    if not session_files:
        print("❌ 未找到任何 session 文件")
        return

    print(f"📊 找到 {len(session_files)} 个 session 文件\n")

    # 验证所有文件
    results = []
    warning_count = 0
    no_title_count = 0

    for session_file in session_files:
        # 为每个文件创建对应的 session_ops（使用其所在目录）
        session_ops = ClaudeSessionOperations(session_file.parent)

        title, session_id, line_number = await verify_single_file_title(
            session_file, session_ops
        )

        result = {
            "file": session_file,
            "session_id": session_id,
            "title": title,
            "line_number": line_number,
        }

        results.append(result)

        # 统计无标题的文件
        if title == "无标题" or line_number == 0:
            no_title_count += 1
        # 只能从第一行获取（跳过 file_history_snapshot 和 Warmup 后）
        elif line_number > 1:
            warning_count += 1

    # 输出结果
    print("=" * 100)
    print(f"✅ 验证完成: {len(results)} 个文件\n")

    # 显示无标题的文件
    if no_title_count > 0:
        print("⚠️  以下文件未能提取到标题:\n")
        print("-" * 100)

        for result in results:
            if result["line_number"] == 0 or result["title"] == "无标题":
                print(f"📄 {result['file']}")
                print(f"   Session ID: {result['session_id']}")
                print(f"   状态: 无标题")
                print()

    # 显示有问题的文件
    if warning_count > 0:
        print("⚠️  以下文件的标题不是从第一行获取:\n")
        print("-" * 100)

        for result in results:
            if result["line_number"] > 1:
                print(f"📄 {result['file']}")
                print(f"   Session ID: {result['session_id']}")
                print(f"   提取的标题: {result['title']}")
                print(f"   提取行号: {result['line_number']} ⚠️ (应该是第 1 行)")
                print()

    # 显示部分正常文件（最多10个）
    print("-" * 100)
    normal_count = sum(1 for r in results if r["line_number"] == 1)
    print(f"✓ 正常文件数量: {normal_count}\n")

    if normal_count > 0:
        print("部分正常文件示例（前10个）:")
        count = 0
        for result in results:
            if result["line_number"] == 1:
                print(f"  ✓ {result['file']}: {result['title']}")
                count += 1
                if count >= 10:
                    break

    print("\n" + "=" * 100)
    print(f"📈 统计:")
    print(f"  - 总文件数: {len(results)}")
    print(f"  - 正常文件 (标题在第1行): {normal_count}")
    print(f"  - 需要检查 (标题不在第1行): {warning_count}")
    print(f"  - 无标题: {no_title_count}")
    print(f"  - 合计: {normal_count + warning_count + no_title_count}")

    if no_title_count > 0:
        print(f"\n⚠️  发现 {no_title_count} 个文件无标题，可能文件格式有问题或为空")

    if warning_count > 0:
        print(f"\n⚠️  建议：请人工检查上述 {warning_count} 个文件，确认标题提取是否正确")
        print(f"  注意：file-history-snapshot 和 Warmup 消息已被自动跳过")
        print(f"\n可以使用以下命令查看具体文件内容：")
        print(
            f"  cat ~/.claude/projects/<project-path>/<session-id>.jsonl | head -n 10 | jq"
        )
        sys.exit(1)
    else:
        print(f"\n✅ 所有文件的标题提取都正常！")


if __name__ == "__main__":
    asyncio.run(verify_all_session_titles())
