'use client';

import React, { useState, memo } from 'react';
import { ChevronDown, ChevronRight, Terminal } from 'lucide-react';
import { MarkdownRenderer } from './MarkdownRenderer';

interface CommandBlockProps {
  command: string;
  content?: string;
}

/**
 * Command 消息块组件
 * 用于渲染 Claude Code 的 slash command 消息
 * 默认只显示 command 名称，点击后展开显示具体内容
 */
export const CommandBlock = memo(({ command, content }: CommandBlockProps) => {
  const [expanded, setExpanded] = useState(false);
  const hasContent = content && content.length > 0;

  return (
    <div className='my-3 p-3 bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-800 rounded-lg'>
      <button
        onClick={() => hasContent && setExpanded(!expanded)}
        className={`flex items-center gap-2 w-full text-left ${
          !hasContent ? 'cursor-default' : ''
        }`}
        disabled={!hasContent}
      >
        {hasContent &&
          (expanded ? (
            <ChevronDown className='h-4 w-4 text-purple-700 dark:text-purple-300 flex-shrink-0' />
          ) : (
            <ChevronRight className='h-4 w-4 text-purple-700 dark:text-purple-300 flex-shrink-0' />
          ))}
        <Terminal className='h-4 w-4 text-purple-700 dark:text-purple-300 flex-shrink-0' />
        <span className='text-sm font-medium text-purple-900 dark:text-purple-100'>
          {command}
        </span>
      </button>
      {/* 展开后显示具体内容 */}
      {hasContent && expanded && (
        <div className='mt-3 pl-6 text-sm text-purple-900 dark:text-purple-100 max-h-96 overflow-y-auto'>
          <MarkdownRenderer text={content} />
        </div>
      )}
    </div>
  );
});

CommandBlock.displayName = 'CommandBlock';
