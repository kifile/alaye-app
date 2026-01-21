'use client';

import React, { useState, memo } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Terminal,
  Command as CommandIcon,
} from 'lucide-react';
import { MarkdownRenderer } from './MarkdownRenderer';

interface CommandBlockProps {
  command: string;
  content?: string;
  args?: string;
}

/**
 * 截断文本辅助函数
 */
const truncateText = (
  text: string,
  maxLength: number,
  method: 'start' | 'end' = 'start'
) => {
  if (text.length <= maxLength) return text;
  return method === 'start'
    ? `${text.slice(0, maxLength)}...`
    : `...${text.slice(-maxLength)}`;
};

/**
 * Command 消息块组件
 * 用于渲染 Claude Code 的 slash command 消息
 * 默认只显示 command 名称和参数（如果有），点击后展开显示具体内容
 */
export const CommandBlock = memo(({ command, content, args }: CommandBlockProps) => {
  const [expanded, setExpanded] = useState(false);
  const hasContent = content && content.length > 0;
  const hasArgs = args && args.length > 0;

  return (
    <div className='my-3 rounded-lg border border-purple-300 dark:border-purple-700 bg-gradient-to-r from-purple-50 to-violet-50 dark:from-purple-950/40 dark:to-violet-950/40 shadow-sm'>
      <div
        className={`flex items-center gap-2 px-3 py-2.5 ${hasContent ? 'cursor-pointer hover:from-purple-100 dark:hover:from-purple-900/50' : ''}`}
        onClick={() => hasContent && setExpanded(!expanded)}
        role='button'
        tabIndex={hasContent ? 0 : undefined}
        aria-expanded={hasContent ? expanded : undefined}
        onKeyDown={e => {
          if (hasContent && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            setExpanded(!expanded);
          }
        }}
      >
        {/* 图标 */}
        <div className='p-1 rounded bg-purple-500 shadow-sm'>
          <CommandIcon className='h-3 w-3 text-white' />
        </div>

        {/* 命令名称 */}
        <div className='flex items-center gap-2 flex-1 min-w-0'>
          <span className='text-sm font-bold text-purple-900 dark:text-purple-100 flex-shrink-0'>
            {command}
          </span>
          {hasArgs && (
            <span
              className='text-xs text-purple-700 dark:text-purple-300 font-mono bg-white/80 dark:bg-purple-900/60 px-2.5 py-1 rounded-md border border-purple-200 dark:border-purple-700 truncate max-w-[300px]'
              title={args}
            >
              {truncateText(args, 40, 'start')}
            </span>
          )}
        </div>

        {/* 展开指示器 - 移到右边 */}
        {hasContent && (
          <div className='ml-auto text-purple-600 dark:text-purple-400 flex-shrink-0'>
            {expanded ? (
              <ChevronDown className='h-4 w-4' />
            ) : (
              <ChevronRight className='h-4 w-4' />
            )}
          </div>
        )}
      </div>

      {/* 展开后显示具体内容 */}
      {hasContent && expanded && (
        <div className='px-3 pb-3 pt-1 border-t border-purple-200 dark:border-purple-700'>
          <div className='pl-10 text-sm text-purple-900 dark:text-purple-100 max-h-96 overflow-y-auto'>
            <MarkdownRenderer text={content} />
          </div>
        </div>
      )}
    </div>
  );
});

CommandBlock.displayName = 'CommandBlock';
