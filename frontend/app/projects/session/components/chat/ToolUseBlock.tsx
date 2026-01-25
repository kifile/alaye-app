'use client';

import React, { useState, memo } from 'react';
import { ChevronDown, ChevronRight, Server, Wrench } from 'lucide-react';
import type { ContentItem } from './ContentItem';
import { useTranslation } from 'react-i18next';
import { MarkdownRenderer } from './MarkdownRenderer';

interface ToolUseBlockProps {
  item: ContentItem;
  isUserMessage?: boolean;
}

/**
 * 解析 MCP 工具名称
 * mcp__serverName__methodName -> { isMCP: true, serverName, methodName }
 */
const parseMcpToolName = (name: string) => {
  if (!name.startsWith('mcp__')) {
    return { isMCP: false };
  }

  const parts = name.split('__');
  if (parts.length >= 3) {
    return {
      isMCP: true,
      serverName: parts[1],
      methodName: parts.slice(2).join('__'), // 处理方法名中可能包含 __ 的情况
    };
  }

  return { isMCP: false };
};

/**
 * 获取工具参数徽章样式
 */
const getToolBadgeClass = (status: 'complete' | 'incomplete', isPrimary = false) => {
  const baseClass = 'px-2 py-0.5 text-xs rounded font-mono';
  if (isPrimary) {
    return status === 'complete'
      ? `${baseClass} bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 font-medium`
      : `${baseClass} bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 font-medium`;
  }
  return status === 'complete'
    ? `${baseClass} bg-green-50 dark:bg-green-900/50 text-green-600 dark:text-green-400`
    : `${baseClass} bg-amber-50 dark:bg-amber-900/50 text-amber-600 dark:text-amber-400`;
};

/**
 * 工具参数配置
 */
interface ToolParamConfig {
  key: string;
  truncate: number;
  method: 'start' | 'end';
}

const TOOL_PARAM_CONFIGS: Record<string, ToolParamConfig> = {
  Read: { key: 'file_path', truncate: 20, method: 'end' },
  Edit: { key: 'file_path', truncate: 20, method: 'end' },
  Write: { key: 'file_path', truncate: 20, method: 'end' },
  Bash: { key: 'command', truncate: 20, method: 'start' },
  Grep: { key: 'pattern', truncate: 20, method: 'end' },
  Glob: { key: 'pattern', truncate: 20, method: 'end' },
  WebSearch: { key: 'query', truncate: 20, method: 'start' },
  Skill: { key: 'skill', truncate: 20, method: 'start' },
  TaskCreate: { key: 'subject', truncate: 30, method: 'start' },
};

/**
 * 渲染工具参数徽章
 */
const renderToolParameter = (
  toolName: string,
  input: Record<string, any> | undefined,
  status: 'complete' | 'incomplete'
) => {
  const config = TOOL_PARAM_CONFIGS[toolName];
  if (!config || !input?.[config.key]) return null;

  const value = input[config.key] as string;
  const displayValue =
    config.method === 'start'
      ? value.length > config.truncate
        ? `${value.slice(0, config.truncate)}...`
        : value
      : value.length > config.truncate
        ? `...${value.slice(-config.truncate)}`
        : value;

  return (
    <span className={getToolBadgeClass(status, false)} title={value}>
      {displayValue}
    </span>
  );
};

/**
 * 检查 extra 是否是可渲染的文本格式
 * 如果是数组且只有一条记录，且包含 text 字段，则返回该文本
 */
const extractTextFromExtra = (extra: any): string | null => {
  if (Array.isArray(extra) && extra.length === 1) {
    const firstItem = extra[0];
    if (
      firstItem &&
      typeof firstItem === 'object' &&
      typeof firstItem.text === 'string'
    ) {
      return firstItem.text;
    }
  }
  return null;
};

/**
 * 工具调用块组件
 * 默认只显示函数名和状态，点击后展开查看详细信息
 * 添加视觉指示器显示是否有参数和输出
 */
export const ToolUseBlock = memo(
  ({ item, isUserMessage = false }: ToolUseBlockProps) => {
    const { t } = useTranslation('projects');
    const [expanded, setExpanded] = useState(false);
    const status = item.status || (item.output ? 'complete' : 'incomplete');
    const isComplete = status === 'complete';

    const hasInput = item.input && Object.keys(item.input).length > 0;
    const hasOutput = !!item.output;
    const hasExtra = !!item.extra;
    const hasDetails = hasInput || hasOutput || hasExtra;

    // 解析 MCP 工具
    const mcpInfo = item.name ? parseMcpToolName(item.name) : { isMCP: false };
    const isMCP = mcpInfo.isMCP;

    return (
      <div
        className={`my-2 rounded-lg border transition-all duration-200 ${
          isComplete
            ? 'bg-green-50/50 dark:bg-green-950/20 border-green-200 dark:border-green-800 hover:bg-green-50 dark:hover:bg-green-950/30'
            : 'bg-blue-50/50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800 hover:bg-blue-50 dark:hover:bg-blue-950/30'
        }`}
      >
        {/* 默认显示的摘要行 */}
        <div
          className={`flex items-center gap-2 px-3 py-2 ${hasDetails ? 'cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2' : ''}`}
          onClick={() => hasDetails && setExpanded(!expanded)}
          role='button'
          tabIndex={hasDetails ? 0 : undefined}
          aria-expanded={hasDetails ? expanded : undefined}
          onKeyDown={e => {
            if (hasDetails && (e.key === 'Enter' || e.key === ' ')) {
              e.preventDefault();
              setExpanded(!expanded);
            }
          }}
        >
          {/* 图标 */}
          <div className={`p-1 rounded ${isComplete ? 'bg-green-500' : 'bg-blue-500'}`}>
            {isMCP ? (
              <Server className='h-3 w-3 text-white' />
            ) : (
              <Wrench className='h-3 w-3 text-white' />
            )}
          </div>

          {/* 函数名称 */}
          {item.name && (
            <div className='flex items-center gap-0.5'>
              {isMCP ? (
                // MCP 工具显示格式：(MCP) serverName / methodName
                <>
                  <span
                    className={`px-2 py-0.5 text-xs rounded font-mono font-medium ${
                      isComplete
                        ? 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300'
                        : 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300'
                    }`}
                  >
                    (MCP) {mcpInfo.serverName}
                  </span>
                  <span className='text-gray-400 text-xs'>/</span>
                  <span
                    className={`px-2 py-0.5 text-xs rounded font-mono ${
                      isComplete
                        ? 'bg-purple-50 dark:bg-purple-900/50 text-purple-600 dark:text-purple-400'
                        : 'bg-purple-50 dark:bg-purple-900/50 text-purple-600 dark:text-purple-400'
                    }`}
                  >
                    {mcpInfo.methodName}
                  </span>
                </>
              ) : (
                // 普通工具显示
                <span className={getToolBadgeClass(status, true)}>
                  {item.name}
                  {item.input?.subagent_type && (
                    <span className='ml-1 opacity-80'>
                      ({item.input.subagent_type as string})
                    </span>
                  )}
                </span>
              )}
              {/* 渲染工具参数 */}
              {renderToolParameter(item.name, item.input, status)}
            </div>
          )}

          {/* 状态标签 */}
          <span
            className={`ml-auto px-2 py-0.5 text-xs rounded-full font-medium ${
              isComplete
                ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
                : 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
            }`}
          >
            {isComplete ? '✓ Done' : '⏳ Pending'}
          </span>

          {/* 展开指示器 */}
          {hasDetails && (
            <div className='ml-1 text-gray-500'>
              {expanded ? (
                <ChevronDown className='h-4 w-4' />
              ) : (
                <ChevronRight className='h-4 w-4' />
              )}
            </div>
          )}
        </div>

        {/* 展开的详细信息 */}
        {expanded && hasDetails && (
          <div className='px-3 pb-3 space-y-2'>
            {hasInput && (
              <div className='text-xs'>
                <div
                  className={`mb-1 font-medium ${
                    isComplete
                      ? 'text-green-700 dark:text-green-300'
                      : 'text-blue-700 dark:text-blue-300'
                  }`}
                >
                  Parameters:
                </div>
                <div
                  className={`p-2 rounded border max-h-48 overflow-auto font-mono text-[10px] whitespace-pre-wrap break-all ${
                    isUserMessage
                      ? 'bg-gray-100 dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100'
                      : isComplete
                        ? 'bg-white dark:bg-gray-900 border-green-200 dark:border-green-800'
                        : 'bg-white dark:bg-gray-900 border-blue-200 dark:border-blue-800'
                  }`}
                >
                  {JSON.stringify(item.input, null, 2)}
                </div>
              </div>
            )}

            {hasOutput && (
              <div className='text-xs'>
                <div
                  className={`mb-1 font-medium ${
                    isComplete
                      ? 'text-green-700 dark:text-green-300'
                      : 'text-blue-700 dark:text-blue-300'
                  }`}
                >
                  Output:
                </div>
                <div
                  className={`p-2 rounded border max-h-48 overflow-auto font-mono text-[10px] whitespace-pre-wrap break-all ${
                    isUserMessage
                      ? 'bg-gray-100 dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100'
                      : isComplete
                        ? 'bg-white dark:bg-gray-900 border-green-200 dark:border-green-800'
                        : 'bg-white dark:bg-gray-900 border-blue-200 dark:border-blue-800'
                  }`}
                >
                  {typeof item.output === 'string'
                    ? item.output
                    : JSON.stringify(item.output, null, 2)}
                </div>
              </div>
            )}

            {hasExtra && (
              <div className='text-xs'>
                <div
                  className={`mb-1 font-medium ${
                    isComplete
                      ? 'text-green-700 dark:text-green-300'
                      : 'text-blue-700 dark:text-blue-300'
                  }`}
                >
                  Extra:
                </div>
                {(() => {
                  const textFromExtra = extractTextFromExtra(item.extra);
                  if (textFromExtra) {
                    // 使用 MarkdownRenderer 渲染文本
                    return (
                      <div
                        className={`p-2 rounded border max-h-48 overflow-auto text-[10px] ${
                          isUserMessage
                            ? 'bg-gray-100 dark:bg-gray-900 border-gray-300 dark:border-gray-700'
                            : isComplete
                              ? 'bg-white dark:bg-gray-900 border-green-200 dark:border-green-800'
                              : 'bg-white dark:bg-gray-900 border-blue-200 dark:border-blue-800'
                        }`}
                      >
                        <MarkdownRenderer
                          text={textFromExtra}
                          isUserMessage={isUserMessage}
                        />
                      </div>
                    );
                  }
                  // 否则渲染 JSON
                  return (
                    <div
                      className={`p-2 rounded border max-h-48 overflow-auto font-mono text-[10px] whitespace-pre-wrap break-all ${
                        isUserMessage
                          ? 'bg-gray-100 dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100'
                          : isComplete
                            ? 'bg-white dark:bg-gray-900 border-green-200 dark:border-green-800'
                            : 'bg-white dark:bg-gray-900 border-blue-200 dark:border-blue-800'
                      }`}
                    >
                      {typeof item.extra === 'string'
                        ? item.extra
                        : JSON.stringify(item.extra, null, 2)}
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }
);

ToolUseBlock.displayName = 'ToolUseBlock';
