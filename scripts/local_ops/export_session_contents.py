#!/usr/bin/env python3
"""
导出 session 内容到 JSON 文件

用于调试和查看 session 的解析结果，输出每个处理阶段的中间结果
"""

import argparse
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.claude.models import StandardMessage
from src.claude.parsers import DropRuleRegistry, MessageParser, MessageProcessor


def to_dict_safe(obj):
    """将对象转换为 dict，如果是 Pydantic 模型则调用 model_dump(mode='json')"""
    if hasattr(obj, "model_dump"):
        # 使用 Pydantic 的 model_dump 方法，mode='json' 确保返回可 JSON 序列化的数据
        return obj.model_dump(mode="json")
    elif isinstance(obj, list):
        return [to_dict_safe(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: to_dict_safe(v) for k, v in obj.items()}
    else:
        return obj


def save_json(data: dict, file_path: Path) -> None:
    """保存数据到 JSON 文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return file_path.stat().st_size


async def export_session(session_file: Path, output_dir: Path):
    """
    导出 session 内容到 JSON 文件

    输出以下环节的结果：
    1. parse 之后的数据情况
    2. 合并 tool_use 和 tool_result 后的结果
    3. 合并 subagent 消息（追加）后的结果
    4. 合并 subagent 到 tool_use 后的结果
    5. 最终的结果内容（合并连续 role 消息）

    Args:
        session_file: session 文件路径
        output_dir: 输出目录路径
    """
    print(f"解析 session 文件: {session_file}")

    # 1. Parse 阶段
    parser = MessageParser()
    parsed_messages, stats = await parser.parse_session_file_with_stats(
        str(session_file), collect_stats=True
    )

    print(f"  [阶段 1] Parse 完成: {len(parsed_messages)} 条消息")

    # 保存 parse 阶段结果（转换为 dict）
    parse_output = {
        "stage": "1. parsed_messages",
        "session_file": str(session_file),
        "stats": {
            "raw_total": stats.raw_total if stats else 0,
            "raw_effective": stats.raw_effective if stats else 0,
            "raw_user": stats.raw_user if stats else 0,
            "raw_assistant": stats.raw_assistant if stats else 0,
            "raw_tool_use": stats.raw_tool_use if stats else 0,
            "raw_tool_result": stats.raw_tool_result if stats else 0,
        },
        "messages": to_dict_safe(parsed_messages),
    }

    parse_file = output_dir / "1_parsed_messages.json"
    size = save_json(parse_output, parse_file)
    print(f"    -> 保存到: {parse_file} ({size / 1024:.2f} KB)")

    # 处理阶段（获取中间结果）
    drop_registry = DropRuleRegistry()
    processor = MessageProcessor(drop_registry)
    debug_info = processor.process_messages_with_debug(parsed_messages)

    # 2. 合并 tool_use 和 tool_result 后的结果
    after_merge_tool_result = debug_info["after_merge_tool_use_result"]
    print(
        f"  [阶段 2] 合并 tool_use 和 tool_result: {after_merge_tool_result['message_count']} 条消息"
    )

    merge_tool_result_output = {
        "stage": "2. after_merge_tool_use_and_result",
        "message_count": after_merge_tool_result["message_count"],
        "messages": to_dict_safe(after_merge_tool_result["messages"]),
    }

    merge_tool_result_file = output_dir / "2_after_merge_tool_result.json"
    size = save_json(merge_tool_result_output, merge_tool_result_file)
    print(f"    -> 保存到: {merge_tool_result_file} ({size / 1024:.2f} KB)")

    # 3. 合并 subagent 消息（追加）后的结果
    after_merge_subagent_inline = debug_info["after_merge_subagent_inline"]
    print(
        f"  [阶段 3] 合并 subagent 消息（追加）: {after_merge_subagent_inline['message_count']} 条消息"
    )

    merge_subagent_inline_output = {
        "stage": "3. after_merge_subagent_inline",
        "message_count": after_merge_subagent_inline["message_count"],
        "messages": to_dict_safe(after_merge_subagent_inline["messages"]),
    }

    merge_subagent_inline_file = output_dir / "3_after_merge_subagent_inline.json"
    size = save_json(merge_subagent_inline_output, merge_subagent_inline_file)
    print(f"    -> 保存到: {merge_subagent_inline_file} ({size / 1024:.2f} KB)")

    # 4. 合并 subagent 到 tool_use 后的结果
    after_merge_subagent = debug_info["after_merge_subagent"]
    print(
        f"  [阶段 4] 合并 subagent 到 tool_use: {after_merge_subagent['message_count']} 条消息"
    )

    merge_subagent_output = {
        "stage": "4. after_merge_subagent_to_tool_use",
        "message_count": after_merge_subagent["message_count"],
        "messages": to_dict_safe(after_merge_subagent["messages"]),
    }

    merge_subagent_file = output_dir / "4_after_merge_subagent_to_tool_use.json"
    size = save_json(merge_subagent_output, merge_subagent_file)
    print(f"    -> 保存到: {merge_subagent_file} ({size / 1024:.2f} KB)")

    # 5. 最终结果（合并连续 role 消息）
    final = debug_info["final"]
    print(f"  [阶段 5] 最终结果（合并连续 role）: {final['message_count']} 条消息")

    final_output = {
        "stage": "5. final_messages",
        "message_count": final["message_count"],
        "messages": to_dict_safe(final["messages"]),
        "dropped_messages": [
            {
                "type": msg.get("type"),
                "uuid": msg.get("uuid"),
                "uuids": msg.get("uuids"),
                "drop_reason": msg.get("_drop_reason"),
                "expected_drop": msg.get("_expected_drop"),
            }
            for msg in drop_registry.dropped_messages
        ],
    }

    final_file = output_dir / "5_final_messages.json"
    size = save_json(final_output, final_file)
    print(f"    -> 保存到: {final_file} ({size / 1024:.2f} KB)")

    # 6. 汇总报告
    summary = {
        "session_file": str(session_file),
        "stages": {
            "1_parsed": {
                "message_count": len(parsed_messages),
                "stats": parse_output["stats"],
            },
            "2_merged_tool_result": {
                "message_count": after_merge_tool_result["message_count"],
            },
            "3_merged_subagent_inline": {
                "message_count": after_merge_subagent_inline["message_count"],
            },
            "4_merged_subagent_to_tool_use": {
                "message_count": after_merge_subagent["message_count"],
            },
            "5_final": {
                "message_count": final["message_count"],
            },
        },
        "dropped_summary": {
            "total_dropped": len(drop_registry.dropped_messages),
            "by_reason": {},
        },
    }

    # 统计丢弃原因
    for msg in drop_registry.dropped_messages:
        reason = msg.get("_drop_reason", "unknown")
        if reason not in summary["dropped_summary"]["by_reason"]:
            summary["dropped_summary"]["by_reason"][reason] = 0
        summary["dropped_summary"]["by_reason"][reason] += 1

    summary_file = output_dir / "0_summary.json"
    size = save_json(summary, summary_file)
    print(f"\n  [汇总] 保存到: {summary_file} ({size / 1024:.2f} KB)")

    print(f"\n导出完成！所有文件保存在: {output_dir}")
    print(f"\n文件列表:")
    print(f"  - 0_summary.json: 汇总报告")
    print(f"  - 1_parsed_messages.json: Parse 阶段结果")
    print(f"  - 2_after_merge_tool_result.json: 合并 tool_use/tool_result 后")
    print(f"  - 3_after_merge_subagent_inline.json: 合并 subagent 消息（追加）后")
    print(f"  - 4_after_merge_subagent_to_tool_use.json: 合并 subagent 到 tool_use 后")
    print(f"  - 5_final_messages.json: 最终结果")


def main():
    parser = argparse.ArgumentParser(
        description="导出 session 内容到 JSON 文件（包含每个处理阶段的中间结果）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 导出到默认目录（当前目录的 session_export）
  python %(prog)s <session_file.jsonl>

  # 导出到指定目录
  python %(prog)s <session_file.jsonl> -o /path/to/output

输出文件:
  - 0_summary.json: 汇总报告
  - 1_parsed_messages.json: Parse 阶段结果
  - 2_after_merge_tool_result.json: 合并 tool_use/tool_result 后
  - 3_after_merge_subagent_inline.json: 合并 subagent 消息（追加）后
  - 4_after_merge_subagent_to_tool_use.json: 合并 subagent 到 tool_use 后
  - 5_final_messages.json: 最终结果
        """,
    )
    parser.add_argument(
        "session_file",
        type=Path,
        help="session 文件路径（.jsonl 文件）",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="输出目录路径（默认为 ./session_export）",
    )

    args = parser.parse_args()

    # 检查 session 文件是否存在
    if not args.session_file.exists():
        print(f"错误: session 文件不存在: {args.session_file}", file=sys.stderr)
        sys.exit(1)

    # 确定输出目录
    if args.output is None:
        output_dir = Path.cwd() / "session_export"
    else:
        output_dir = args.output

    # 运行导出
    import asyncio

    asyncio.run(export_session(args.session_file, output_dir))


if __name__ == "__main__":
    main()
