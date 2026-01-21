#!/usr/bin/env python3
"""
验证 Session 消息合并逻辑

遍历 $HOME/.claude/projects 下的所有 session 文件，
检查消息合并逻辑，识别可能丢失的消息，供人工检查。
"""

import sys
from pathlib import Path
from typing import Dict, List

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


def analyze_and_check_warnings(
    session_file: Path, session_ops: ClaudeSessionOperations
) -> tuple[Dict[str, int], List[str]]:
    """
    分析 session 文件并生成警告

    Args:
        session_file: session 文件路径
        session_ops: ClaudeSessionOperations 实例

    Returns:
        tuple[Dict, List[str]]: (分析结果, 警告列表)
    """
    # 使用 _load_session_data 方法获取详细统计（启用 debug 模式）
    _, analysis = session_ops._load_session_data(session_file, debug=True)

    # 生成警告
    warnings = []

    if analysis.get("error"):
        warnings.append(f"❌ 分析失败: {analysis['error']}")
        return analysis, warnings

    # 只在有非预期丢弃时才警告
    unexpected_dropped = 0
    for sample in analysis.get("dropped_samples", []):
        # 使用 _expected_drop 标记来判断是否为预期内的丢弃
        if sample.get("_expected_drop", False):
            # 预期内的丢弃，不产生警告
            continue
        else:
            # 其他原因的丢弃（如 empty_content）是非预期的
            unexpected_dropped += 1

    if unexpected_dropped > 0:
        total_dropped = analysis["dropped_messages"]
        expected = total_dropped - unexpected_dropped
        warnings.append(
            f"⚠️  非预期丢弃了 {unexpected_dropped} 条消息 "
            f"(预期内丢弃: {expected} 条)"
        )

    # 只显示非预期丢弃的样本（最多 2 条）
    unexpected_samples = []
    for sample in analysis.get("dropped_samples", []):
        # 使用 _expected_drop 标记来判断是否为预期内的丢弃
        if sample.get("_expected_drop", False):
            # 预期内丢弃，不显示
            continue
        else:
            # 非预期丢弃，显示
            unexpected_samples.append(sample)
            if len(unexpected_samples) >= 2:
                break

    # 更新样本，只显示非预期丢弃的
    analysis["dropped_samples_shown"] = unexpected_samples[:2]

    # 检查 tool_use 和 tool_result 的匹配
    if analysis["raw_tool_use"] > 0:
        if analysis["merged_tool_use"] < analysis["raw_tool_use"]:
            warnings.append(
                f"⚠️  tool_use 数量减少: {analysis['raw_tool_use']} → "
                f"{analysis['merged_tool_use']}"
            )

    if analysis["raw_tool_result"] > 0:
        if analysis["merged_tool_use_incomplete"] > 0:
            warnings.append(
                f"⚠️  存在未完成的 tool_use: {analysis['merged_tool_use_incomplete']} 个 "
                f"(可能有 {analysis['merged_tool_use_incomplete']} 个 tool_result 丢失)"
            )

    # 检查 thinking 消息
    if analysis["raw_thinking"] > 0 and analysis["merged_thinking"] == 0:
        warnings.append(
            f"⚠️  thinking 消息可能被转换为 text: {analysis['raw_thinking']} 个"
        )

    # 检查是否有 tool_result 但没有对应的 tool_use
    if analysis["raw_tool_result"] > analysis["raw_tool_use"]:
        warnings.append(
            f"⚠️  tool_result 数量多于 tool_use: "
            f"{analysis['raw_tool_result']} tool_result vs {analysis['raw_tool_use']} tool_use"
        )

    return analysis, warnings


def verify_all_session_merging():
    """
    验证所有 session 的消息合并逻辑
    """
    claude_path = find_claude_projects_path()
    print(f"📁 扫描目录: {claude_path}\n")

    # 收集所有 session 文件
    # Claude 的目录结构是: ~/.claude/projects/<project-name>/*.jsonl
    session_files = []
    project_dirs = []

    for project_dir in claude_path.iterdir():
        if not project_dir.is_dir():
            continue

        project_dirs.append(project_dir)

        # 每个项目目录下的所有 .jsonl 文件
        for session_file in project_dir.glob("*.jsonl"):
            session_files.append(session_file)

    if not session_files:
        print("❌ 未找到任何 session 文件")
        return

    print(
        f"📊 找到 {len(session_files)} 个 session 文件，来自 {len(project_dirs)} 个项目\n"
    )

    # 分析所有文件
    results = []
    warning_count = 0
    error_count = 0

    for i, session_file in enumerate(session_files, 1):
        relative_path = session_file.relative_to(claude_path)
        print(
            f"\r[{i}/{len(session_files)}] 分析中: {str(relative_path)[:60]}...",
            end="",
            flush=True,
        )

        # 创建 ClaudeSessionOperations 实例
        session_ops = ClaudeSessionOperations(session_file.parent)

        # 分析文件
        analysis, warnings = analyze_and_check_warnings(session_file, session_ops)

        result = {
            "file": session_file,
            "relative_path": relative_path,
            "session_id": session_file.stem,
            "analysis": analysis,
            "warnings": warnings,
        }

        results.append(result)

        if warnings:
            warning_count += 1
        if analysis.get("error"):
            error_count += 1

    print(f"\r{' ' * 100}", end="\r")

    # 输出结果
    print("=" * 100)
    print(f"✅ 分析完成: {len(results)} 个文件")
    print(f"   - 有警告: {warning_count} 个")
    print(f"   - 有错误: {error_count} 个")
    print(f"   - 正常: {len(results) - warning_count} 个\n")

    # 显示有问题的文件（最多显示 5 个）
    if warning_count > 0:
        print("-" * 100)
        print(f"⚠️  发现 {warning_count} 个文件可能有合并问题（显示前 5 个）:\n")

        shown_count = 0
        for result in results:
            if result["warnings"]:
                shown_count += 1
                if shown_count > 5:
                    continue

                print(f"📄 {result['relative_path']}")
                print(f"   Session ID: {result['session_id']}")

                # 显示原始消息统计
                analysis = result["analysis"]
                if not analysis.get("error"):
                    print(
                        f"   原始: {analysis['raw_total']} 行 "
                        f"(meta:{analysis['raw_meta']}, user:{analysis['raw_user']}, "
                        f"assistant:{analysis['raw_assistant']}, system:{analysis['raw_system']}, "
                        f"summary:{analysis['raw_summary']})"
                    )
                    print(
                        f"         有效消息: {analysis['raw_effective']} | "
                        f"tool_use:{analysis['raw_tool_use']}, "
                        f"tool_result:{analysis['raw_tool_result']}, "
                        f"thinking:{analysis['raw_thinking']}"
                    )

                # 显示合并后统计
                if not analysis.get("error"):
                    print(
                        f"   合并: {analysis['merged_total']} 条消息 "
                        f"(tool_use:{analysis['merged_tool_use']} | "
                        f"complete:{analysis['merged_tool_use_complete']}, "
                        f"incomplete:{analysis['merged_tool_use_incomplete']})"
                    )
                    print(
                        f"         text:{analysis['merged_text']}, "
                        f"thinking:{analysis['merged_thinking']}, "
                        f"system:{analysis['merged_system']}"
                    )
                    if analysis["dropped_messages"] > 0:
                        unexpected_dropped = analysis.get("dropped_samples_shown", [])
                        expected_dropped = analysis["dropped_messages"] - len(
                            unexpected_dropped
                        )
                        print(
                            f"         ⚠️  丢弃消息: {analysis['dropped_messages']} (预期内:{expected_dropped}, 非预期:{len(unexpected_dropped)})"
                        )
                        # 显示最多 2 条非预期丢弃消息的示例
                        if unexpected_dropped and len(unexpected_dropped) > 0:
                            print(f"         非预期丢弃消息示例:")
                            for i, sample in enumerate(unexpected_dropped, 1):
                                content_preview = sample.get("content_preview", "")
                                timestamp = sample.get("timestamp") or "N/A"
                                if timestamp != "N/A":
                                    timestamp = timestamp[:19]  # 只显示前19个字符
                                role = sample.get("role", "N/A")
                                msg_type = sample.get("type", "N/A")
                                subtype = sample.get("subtype", "N/A")
                                drop_reason = sample.get("drop_reason", "unknown")
                                print(
                                    f"           [{i}] type={msg_type}, subtype={subtype}, role={role}, reason={drop_reason}"
                                )
                                print(f"               timestamp={timestamp}")
                                print(f"               content={content_preview}")

                # 显示警告
                for warning in result["warnings"]:
                    print(f"   {warning}")

                print()

        if warning_count > 5:
            print(f"... 还有 {warning_count - 5} 个文件有类似问题（未显示）\n")

    # 显示统计信息
    print("-" * 100)
    print("📈 总体统计:")

    # 统计各类消息的数量
    total_raw = sum(
        r["analysis"].get("raw_total", 0)
        for r in results
        if not r["analysis"].get("error")
    )
    total_effective = sum(
        r["analysis"].get("raw_effective", 0)
        for r in results
        if not r["analysis"].get("error")
    )
    total_merged = sum(
        r["analysis"].get("merged_total", 0)
        for r in results
        if not r["analysis"].get("error")
    )
    total_summary = sum(
        r["analysis"].get("raw_summary", 0)
        for r in results
        if not r["analysis"].get("error")
    )
    total_system = sum(
        r["analysis"].get("raw_system", 0)
        for r in results
        if not r["analysis"].get("error")
    )
    total_tool_use = sum(
        r["analysis"].get("raw_tool_use", 0)
        for r in results
        if not r["analysis"].get("error")
    )
    total_tool_result = sum(
        r["analysis"].get("raw_tool_result", 0)
        for r in results
        if not r["analysis"].get("error")
    )
    total_tool_use_merged = sum(
        r["analysis"].get("merged_tool_use", 0)
        for r in results
        if not r["analysis"].get("error")
    )
    total_tool_use_complete = sum(
        r["analysis"].get("merged_tool_use_complete", 0)
        for r in results
        if not r["analysis"].get("error")
    )
    total_tool_use_incomplete = sum(
        r["analysis"].get("merged_tool_use_incomplete", 0)
        for r in results
        if not r["analysis"].get("error")
    )
    total_system_merged = sum(
        r["analysis"].get("merged_system", 0)
        for r in results
        if not r["analysis"].get("error")
    )
    total_dropped = sum(
        r["analysis"].get("dropped_messages", 0)
        for r in results
        if not r["analysis"].get("error")
    )

    print(f"  - 原始总行数: {total_raw}")
    print(f"  - 有效消息总数: {total_effective}")
    print(f"  - 合并后消息总数: {total_merged}")
    print(f"  - 丢弃消息总数: {total_dropped}")
    print(f"  - 原始 summary: {total_summary} 个")
    print(f"  - 原始 system: {total_system} 个（转换后）")
    print(f"  - 合并后 system: {total_system_merged} 个")
    print(f"  - 原始 tool_use: {total_tool_use} 个")
    print(f"  - 原始 tool_result: {total_tool_result} 个")
    print(f"  - 合并后 tool_use: {total_tool_use_merged} 个")
    print(f"    - 完成: {total_tool_use_complete} 个")
    print(f"    - 未完成: {total_tool_use_incomplete} 个")

    if total_tool_use_incomplete > 0:
        print(
            f"\n⚠️  存在 {total_tool_use_incomplete} 个未完成的 tool_use，可能需要人工检查"
        )

    if total_dropped > 0:
        print(f"\n⚠️  总共丢弃了 {total_dropped} 条消息，这可能是由合并逻辑导致的")

    print("\n" + "=" * 100)
    if warning_count > 0:
        print(
            f"🔍 建议：请人工检查上述 {warning_count} 个文件，确认消息合并是否符合预期"
        )
        print(f"\n可以使用以下命令查看具体文件内容：")
        print(f"  cat ~/.claude/projects/<project-path>/<session-id>.jsonl | jq")
        print(f"\n或使用 Python 分析工具：")
        print(
            f"  uv run python -c \"from pathlib import Path; import json; f = Path('~/.claude/projects/<file>').expanduser(); print('\\n'.join(json.loads(l) for l in f.open()))\""
        )
        sys.exit(1)
    else:
        print("✅ 所有文件的合并逻辑都正常！")


if __name__ == "__main__":
    verify_all_session_merging()
