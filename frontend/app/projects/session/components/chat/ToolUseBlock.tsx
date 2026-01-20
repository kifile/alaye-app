'use client';

import React, { useState, memo } from 'react';
import { Bot, ChevronDown, ChevronRight, Settings, Server } from 'lucide-react';
import type { ContentItem } from './ContentItem';
import { useTranslation } from 'react-i18next';

interface ToolUseBlockProps {
  item: ContentItem;
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
 * 工具调用块组件
 * 默认只显示函数名和状态，点击后展开查看详细信息
 * 添加视觉指示器显示是否有参数和输出
 */
export const ToolUseBlock = memo(({ item }: ToolUseBlockProps) => {
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
            <Bot className='h-3 w-3 text-white' />
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
              <span
                className={`px-2 py-0.5 text-xs rounded font-mono font-medium ${
                  isComplete
                    ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
                    : 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                }`}
              >
                {item.name}
                {item.input?.subagent_type && (
                  <span className='ml-1 opacity-80'>
                    ({item.input.subagent_type as string})
                  </span>
                )}
              </span>
            )}
            {/* 如果是 Read/Edit/Write 工具，显示文件路径 */}
            {(item.name === 'Read' || item.name === 'Edit' || item.name === 'Write') &&
              item.input?.file_path && (
                <span
                  className={`px-2 py-0.5 text-xs rounded font-mono ${
                    isComplete
                      ? 'bg-green-50 dark:bg-green-900/50 text-green-600 dark:text-green-400'
                      : 'bg-blue-50 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400'
                  }`}
                  title={item.input.file_path}
                >
                  {(() => {
                    const filePath = item.input.file_path as string;
                    return filePath.length > 20
                      ? `...${filePath.slice(-20)}`
                      : filePath;
                  })()}
                </span>
              )}
            {/* 如果是 Bash 工具，显示 command */}
            {item.name === 'Bash' && item.input?.command && (
              <span
                className={`px-2 py-0.5 text-xs rounded font-mono ${
                  isComplete
                    ? 'bg-blue-50 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400'
                    : 'bg-amber-50 dark:bg-amber-900/50 text-amber-600 dark:text-amber-400'
                }`}
                title={item.input.command}
              >
                {(() => {
                  const command = item.input.command as string;
                  return command.length > 20 ? `${command.slice(0, 20)}...` : command;
                })()}
              </span>
            )}
            {/* 如果是 Grep/Glob 工具，显示 pattern */}
            {(item.name === 'Grep' || item.name === 'Glob') && item.input?.pattern && (
              <span
                className={`px-2 py-0.5 text-xs rounded font-mono ${
                  isComplete
                    ? 'bg-blue-50 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400'
                    : 'bg-amber-50 dark:bg-amber-900/50 text-amber-600 dark:text-amber-400'
                }`}
                title={item.input.pattern}
              >
                {(() => {
                  const pattern = item.input.pattern as string;
                  return pattern.length > 20 ? `...${pattern.slice(-20)}` : pattern;
                })()}
              </span>
            )}
            {/* 如果是 WebSearch 工具，显示 query */}
            {item.name === 'WebSearch' && item.input?.query && (
              <span
                className={`px-2 py-0.5 text-xs rounded font-mono ${
                  isComplete
                    ? 'bg-blue-50 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400'
                    : 'bg-amber-50 dark:bg-amber-900/50 text-amber-600 dark:text-amber-400'
                }`}
                title={item.input.query}
              >
                {(() => {
                  const query = item.input.query as string;
                  return query.length > 20 ? `${query.slice(0, 20)}...` : query;
                })()}
              </span>
            )}
            {/* 如果是 Skill 工具，显示 skill */}
            {item.name === 'Skill' && item.input?.skill && (
              <span
                className={`px-2 py-0.5 text-xs rounded font-mono ${
                  isComplete
                    ? 'bg-blue-50 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400'
                    : 'bg-amber-50 dark:bg-amber-900/50 text-amber-600 dark:text-amber-400'
                }`}
                title={item.input.skill as string}
              >
                {(() => {
                  const skill = item.input.skill as string;
                  return skill.length > 20 ? `${skill.slice(0, 20)}...` : skill;
                })()}
              </span>
            )}
            {/* 如果是 Task 工具，显示 description */}
            {item.name === 'Task' && item.input?.description && (
              <span
                className={`px-2 py-0.5 text-xs rounded font-mono ${
                  isComplete
                    ? 'bg-blue-50 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400'
                    : 'bg-amber-50 dark:bg-amber-900/50 text-amber-600 dark:text-amber-400'
                }`}
                title={item.input.description as string}
              >
                {(() => {
                  const description = item.input.description as string;
                  return description.length > 20
                    ? `${description.slice(0, 20)}...`
                    : description;
                })()}
              </span>
            )}
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
                  isComplete
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
                  isComplete
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
              <div
                className={`p-2 rounded border max-h-48 overflow-auto font-mono text-[10px] whitespace-pre-wrap break-all ${
                  isComplete
                    ? 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800'
                    : 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800'
                }`}
              >
                {item.extra}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

ToolUseBlock.displayName = 'ToolUseBlock';
