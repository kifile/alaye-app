'use client';

import React, { useState, memo } from 'react';
import { Bot, ChevronDown, ChevronRight } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import type { ClaudeMessage } from '@/api/types';

interface AgentBlockProps {
  item: {
    type: 'subagent';
    id: string;
    name: string;
    input: {
      subagent_type: string;
      description: string;
      [key: string]: unknown;
    };
    output?: string | Record<string, unknown>;
    status?: 'complete' | 'pending' | 'error';
    agent_type: string;
    description: string;
    session: {
      session_id: string;
      title: string;
      message_count: number;
      messages: ClaudeMessage[];
    };
  };
}

const RESULT_PREVIEW_LENGTH = 120; // Result 预览字符数
const DESCRIPTION_MAX_LENGTH = 40; // Description 最大显示长度

/**
 * 检测是否是纯 agentId 消息（没有实际内容）
 * 匹配格式：agentId: xxx (for resuming to continue this agent's work if needed)
 */
const isPureAgentIdMessage = (text: string): boolean => {
  const trimmed = text.trim();
  // 匹配 agentId: xxx (for resuming...) 模式
  const agentIdPattern =
    /^agentId:\s*[a-f0-9]+\s*\(for resuming to continue this agent['']s work if needed\)\.?$/i;
  return agentIdPattern.test(trimmed);
};

/**
 * 过滤 output 内容，移除纯 agentId 消息
 */
const filterOutput = (outputStr: string): string => {
  // 如果是数组格式的 JSON，尝试解析并过滤
  try {
    const parsed = JSON.parse(outputStr) as unknown;
    if (Array.isArray(parsed)) {
      // 过滤掉纯 agentId 消息
      const filtered = parsed.filter((item: unknown) => {
        if (typeof item === 'string') {
          return !isPureAgentIdMessage(item);
        }
        if (
          typeof item === 'object' &&
          item !== null &&
          'type' in item &&
          item.type === 'text' &&
          'text' in item
        ) {
          return !isPureAgentIdMessage(String(item.text));
        }
        return true;
      });

      // 如果过滤后是空数组，返回空字符串
      if (filtered.length === 0) {
        return '';
      }

      // 如果过滤后只剩一条消息，直接返回其文本内容
      if (filtered.length === 1) {
        const item = filtered[0];
        if (typeof item === 'string') {
          return item;
        }
        if (
          typeof item === 'object' &&
          item !== null &&
          'type' in item &&
          item.type === 'text' &&
          'text' in item
        ) {
          return String(item.text) || '';
        }
      }

      // 多条消息，重新序列化
      return JSON.stringify(filtered, null, 2);
    }
  } catch {
    // JSON 解析失败，直接返回原字符串
  }

  // 对于普通字符串，检查是否是纯 agentId 消息
  if (isPureAgentIdMessage(outputStr)) {
    return '';
  }

  return outputStr;
};

/**
 * SubAgent 调用块组件
 *
 * 设计理念：
 * - Header：与 ToolUseBlock 统一样式
 * - Input 区域：任务描述
 * - 中部：可展开的对话历史
 * - Output 区域：支持折叠的执行结果
 *
 * 视觉风格：
 * - 干净简约，无渐变
 * - 与 ToolUseBlock 保持一致的设计语言
 */
export const AgentBlock = memo(({ item }: AgentBlockProps) => {
  const [expanded, setExpanded] = useState(false);
  const [resultExpanded, setResultExpanded] = useState(false);

  // 获取友好的 agent 类型名称
  const getAgentDisplayName = (agentType: string): string => {
    const agentNames: Record<string, string> = {
      uiux_reviewer: 'UI/UX Reviewer',
      general_purpose: 'General Purpose',
      explore: 'Explorer',
      feature_dev_code_architect: 'Code Architect',
      statusline_setup: 'Statusline Setup',
      claude_code_guide: 'Claude Code Guide',
      rust_minimal_developer: 'Rust Developer',
    };
    return (
      agentNames[agentType] ||
      agentType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    );
  };

  // 安全地将值转换为字符串
  const safeToString = (value: unknown): string => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value;
    if (typeof value === 'object') {
      try {
        return JSON.stringify(value, null, 2);
      } catch {
        return String(value);
      }
    }
    return String(value);
  };

  // 截断描述文本
  const truncateDescription = (text: string): string => {
    if (!text) return '';
    return text.length > DESCRIPTION_MAX_LENGTH
      ? `${text.slice(0, DESCRIPTION_MAX_LENGTH)}...`
      : text;
  };

  const { session, input, output, status } = item;
  const messageCount = session.message_count || 0;
  const agentDisplayName = getAgentDisplayName(item.agent_type);

  // 判断状态
  const isComplete = status === 'complete';
  const statusColor = isComplete
    ? 'bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-300'
    : 'bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300';

  // 获取显示的描述
  const displayDescription = truncateDescription(
    input.description || item.description || ''
  );

  // 处理 output
  const rawOutputStr = safeToString(output);
  const filteredOutputStr = filterOutput(rawOutputStr);
  const hasOutput = filteredOutputStr !== '';
  const isLongOutput = hasOutput && filteredOutputStr.length > RESULT_PREVIEW_LENGTH;

  // 判断是否应该折叠（多条消息时才折叠）
  const shouldCollapseResult = () => {
    try {
      const parsed = JSON.parse(rawOutputStr);
      if (Array.isArray(parsed)) {
        // 如果原始输出是多条消息，过滤后也是多条，则需要折叠
        return parsed.length > 1;
      }
    } catch {
      // JSON 解析失败，根据文本长度判断
    }
    // 单条消息或纯文本，根据长度判断
    return isLongOutput;
  };

  return (
    <div
      className={`my-2 rounded-lg border transition-all duration-200 ${
        isComplete
          ? 'bg-orange-50/50 dark:bg-orange-950/20 border-orange-200 dark:border-orange-800 hover:bg-orange-50 dark:hover:bg-orange-950/30'
          : 'bg-amber-50/50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800 hover:bg-amber-50 dark:hover:bg-amber-950/30'
      }`}
    >
      {/* Header - 与 ToolUseBlock 统一样式 */}
      <div
        className={`flex items-center gap-2 px-3 py-2 ${messageCount > 0 || hasOutput ? 'cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2' : ''}`}
        onClick={() => (messageCount > 0 || hasOutput) && setExpanded(!expanded)}
        role='button'
        tabIndex={messageCount > 0 || hasOutput ? 0 : undefined}
        aria-expanded={messageCount > 0 || hasOutput ? expanded : undefined}
        onKeyDown={e => {
          if ((messageCount > 0 || hasOutput) && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            setExpanded(!expanded);
          }
        }}
      >
        {/* 图标 - 使用橙色调 */}
        <div className={`p-1 rounded ${isComplete ? 'bg-orange-500' : 'bg-amber-500'}`}>
          <Bot className='h-3 w-3 text-white' />
        </div>

        {/* Agent 名称和描述 */}
        <div className='flex items-center gap-0.5'>
          <span
            className={`px-2 py-0.5 text-xs rounded font-mono font-medium ${
              isComplete
                ? 'bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-300'
                : 'bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300'
            }`}
          >
            {agentDisplayName}
          </span>
          {/* 描述放到括号里 */}
          {displayDescription && (
            <span className='text-xs text-gray-600 dark:text-gray-400'>
              ({displayDescription})
            </span>
          )}
        </div>

        {/* 状态标签 - 与 ToolUseBlock 位置一致 */}
        <span
          className={`ml-auto px-2 py-0.5 text-xs rounded-full font-medium ${statusColor}`}
        >
          {isComplete ? '✓ Done' : '⏳ Pending'}
        </span>

        {/* 展开指示器 */}
        {(messageCount > 0 || hasOutput) && (
          <div className='ml-1 text-gray-500'>
            {expanded ? (
              <ChevronDown className='h-4 w-4' />
            ) : (
              <ChevronRight className='h-4 w-4' />
            )}
          </div>
        )}
      </div>

      {/* 展开的详细内容 */}
      {expanded && (
        <div className='px-3 pb-3 space-y-2'>
          {/* Input 区域 - 任务描述 */}
          <div className='text-xs'>
            <div
              className={`mb-1 font-medium ${
                isComplete
                  ? 'text-orange-700 dark:text-orange-300'
                  : 'text-amber-700 dark:text-amber-300'
              }`}
            >
              Task:
            </div>
            <div
              className={`p-2 rounded border max-h-32 overflow-auto font-mono text-[10px] whitespace-pre-wrap break-all ${
                isComplete
                  ? 'bg-white dark:bg-gray-900 border-orange-200 dark:border-orange-800'
                  : 'bg-white dark:bg-gray-900 border-amber-200 dark:border-amber-800'
              }`}
            >
              {safeToString(input.description || item.description) || 'No description'}
            </div>
            {/* 额外的 input 参数（如果有） */}
            {Object.keys(input).some(
              key => !['subagent_type', 'description'].includes(key)
            ) && (
              <details className='mt-2'>
                <summary className='text-xs text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300'>
                  Parameters
                </summary>
                <div className='mt-1.5 space-y-1'>
                  {Object.entries(input).map(([key, value]) => {
                    if (['subagent_type', 'description'].includes(key)) return null;
                    return (
                      <div key={key} className='text-xs'>
                        <span className='font-mono text-purple-600 dark:text-purple-400'>
                          {key}:
                        </span>{' '}
                        <span className='text-gray-600 dark:text-gray-400 font-mono'>
                          {safeToString(value)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </details>
            )}
          </div>

          {/* 对话历史 */}
          {messageCount > 0 && (
            <div className='text-xs'>
              <div
                className={`mb-1 font-medium ${
                  isComplete
                    ? 'text-orange-700 dark:text-orange-300'
                    : 'text-amber-700 dark:text-amber-300'
                }`}
              >
                Conversation:
              </div>
              <div
                className={`max-h-96 overflow-auto rounded border bg-white dark:bg-gray-900 ${
                  isComplete
                    ? 'border-orange-200 dark:border-orange-800'
                    : 'border-amber-200 dark:border-amber-800'
                }`}
              >
                <div className='divide-y divide-gray-100 dark:divide-gray-800/50'>
                  {session.messages.map((msg, index) => (
                    <div key={msg.timestamp || index} className='px-3 py-2'>
                      <ChatMessage message={msg} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Output 区域 - 支持折叠 */}
          {hasOutput && (
            <div
              className={`rounded-lg border transition-all ${
                isComplete
                  ? 'border-orange-200 dark:border-orange-800'
                  : 'border-amber-200 dark:border-amber-800'
              }`}
            >
              {/* 标题栏 - 包含折叠按钮 */}
              <div
                className={`flex items-center gap-2 px-3 py-2 ${
                  shouldCollapseResult() ? 'cursor-pointer' : ''
                }`}
                onClick={() =>
                  shouldCollapseResult() && setResultExpanded(!resultExpanded)
                }
                role={shouldCollapseResult() ? 'button' : undefined}
                tabIndex={shouldCollapseResult() ? 0 : undefined}
                aria-expanded={shouldCollapseResult() ? resultExpanded : undefined}
                onKeyDown={e => {
                  if (shouldCollapseResult() && (e.key === 'Enter' || e.key === ' ')) {
                    e.preventDefault();
                    setResultExpanded(!resultExpanded);
                  }
                }}
              >
                <div
                  className={`text-xs font-medium ${
                    isComplete
                      ? 'text-orange-700 dark:text-orange-300'
                      : 'text-amber-700 dark:text-amber-300'
                  }`}
                >
                  Result:
                </div>

                {/* 右侧：折叠按钮 */}
                {shouldCollapseResult() && (
                  <div className='ml-auto text-gray-500'>
                    {resultExpanded ? (
                      <ChevronDown className='h-4 w-4' />
                    ) : (
                      <ChevronRight className='h-4 w-4' />
                    )}
                  </div>
                )}
              </div>

              {/* 内容区域 */}
              <div
                className={`px-3 pb-3 ${
                  isComplete
                    ? 'bg-orange-50/50 dark:bg-orange-950/20'
                    : 'bg-amber-50/50 dark:bg-amber-950/20'
                }`}
              >
                <div
                  className={`p-2 rounded border max-h-48 overflow-auto font-mono text-[10px] whitespace-pre-wrap break-word ${
                    isComplete
                      ? 'bg-white dark:bg-gray-900 border-orange-200 dark:border-orange-800'
                      : 'bg-white dark:bg-gray-900 border-amber-200 dark:border-amber-800'
                  }`}
                >
                  {resultExpanded ? (
                    filteredOutputStr
                  ) : (
                    <>
                      {filteredOutputStr.slice(0, RESULT_PREVIEW_LENGTH)}...
                      {shouldCollapseResult() && (
                        <button
                          onClick={e => {
                            e.stopPropagation();
                            setResultExpanded(true);
                          }}
                          className='ml-2 text-xs underline text-orange-700 dark:text-orange-300 hover:text-orange-900 dark:hover:text-orange-100'
                        >
                          Show more
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

AgentBlock.displayName = 'AgentBlock';
