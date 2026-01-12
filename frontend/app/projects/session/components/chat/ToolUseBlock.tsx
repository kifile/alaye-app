'use client';

import React, { useState, memo } from 'react';
import { Bot, ChevronDown, ChevronRight, Settings } from 'lucide-react';
import type { ContentItem } from './ContentItem';

interface ToolUseBlockProps {
  item: ContentItem;
}

/**
 * 工具调用块组件
 * 默认只显示函数名和状态，点击后展开查看详细信息
 * 添加视觉指示器显示是否有参数和输出
 */
export const ToolUseBlock = memo(({ item }: ToolUseBlockProps) => {
  const [expanded, setExpanded] = useState(false);
  const status = item.status || (item.output ? 'complete' : 'incomplete');
  const isComplete = status === 'complete';

  const hasInput = item.input && Object.keys(item.input).length > 0;
  const hasOutput = !!item.output;
  const hasDetails = hasInput || hasOutput;

  return (
    <div
      className={`my-2 rounded-lg border transition-all duration-200 ${
        isComplete
          ? 'bg-blue-50/50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800 hover:bg-blue-50 dark:hover:bg-blue-950/30'
          : 'bg-amber-50/50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800 hover:bg-amber-50 dark:hover:bg-amber-950/30'
      } ${hasInput ? 'border-l-4 border-l-blue-400' : ''} ${hasOutput ? 'border-r-4 border-r-green-400' : ''}`}
    >
      {/* 默认显示的摘要行 */}
      <div
        className={`flex items-center gap-2 px-3 py-2 ${hasDetails ? 'cursor-pointer' : ''}`}
        onClick={() => hasDetails && setExpanded(!expanded)}
      >
        {/* 图标 */}
        <div className={`p-1 rounded ${isComplete ? 'bg-blue-500' : 'bg-amber-500'}`}>
          <Bot className='h-3 w-3 text-white' />
        </div>

        {/* 函数名称 */}
        {item.name && (
          <span
            className={`px-2 py-0.5 text-xs rounded font-mono font-medium ${
              isComplete
                ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                : 'bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300'
            }`}
          >
            {item.name}
          </span>
        )}

        {/* 参数指示器 */}
        {hasInput && (
          <div
            className='flex items-center gap-1 text-[10px] text-blue-600 dark:text-blue-400'
            title='Has parameters'
          >
            <Settings className='h-3 w-3' />
          </div>
        )}

        {/* 输出指示器 */}
        {hasOutput && (
          <div
            className='flex items-center gap-1 text-[10px] text-green-600 dark:text-green-400'
            title='Has output'
          >
            <svg
              className='h-3 w-3'
              fill='none'
              stroke='currentColor'
              viewBox='0 0 24 24'
            >
              <path
                strokeLinecap='round'
                strokeLinejoin='round'
                strokeWidth={2}
                d='M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.707.293H19a2 2 0 012 2z'
              />
            </svg>
          </div>
        )}

        {/* 状态标签 */}
        <span
          className={`ml-auto px-2 py-0.5 text-xs rounded-full font-medium ${
            isComplete
              ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
              : 'bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300'
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
                    ? 'text-blue-700 dark:text-blue-300'
                    : 'text-amber-700 dark:text-amber-300'
                }`}
              >
                Parameters:
              </div>
              <div
                className={`p-2 rounded border max-h-48 overflow-auto font-mono text-[10px] whitespace-pre-wrap break-all ${
                  isComplete
                    ? 'bg-white dark:bg-gray-900 border-blue-200 dark:border-blue-800'
                    : 'bg-white dark:bg-gray-900 border-amber-200 dark:border-amber-800'
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
                    ? 'text-blue-700 dark:text-blue-300'
                    : 'text-amber-700 dark:text-amber-300'
                }`}
              >
                Output:
              </div>
              <div
                className={`p-2 rounded border max-h-48 overflow-auto font-mono text-[10px] whitespace-pre-wrap break-all ${
                  isComplete
                    ? 'bg-white dark:bg-gray-900 border-blue-200 dark:border-blue-800'
                    : 'bg-white dark:bg-gray-900 border-amber-200 dark:border-amber-800'
                }`}
              >
                {typeof item.output === 'string'
                  ? item.output
                  : JSON.stringify(item.output, null, 2)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

ToolUseBlock.displayName = 'ToolUseBlock';
