'use client';

import React, { useState, memo } from 'react';
import { ChevronDown, ChevronRight, Brain } from 'lucide-react';
import type { ContentItem } from './ContentItem';

interface ThinkingBlockProps {
  item: ContentItem;
}

const PREVIEW_LENGTH = 80; // 预览字符数

/**
 * 思考过程块组件
 * 每个块都有独立的展开/收起状态
 * 默认显示预览文字，点击后展开完整内容
 */
export const ThinkingBlock = memo(({ item }: ThinkingBlockProps) => {
  const [expanded, setExpanded] = useState(false);
  const text = item.text || '';
  const isLongText = text.length > PREVIEW_LENGTH;

  // 显示的文字内容
  const displayText = expanded
    ? text
    : isLongText
      ? text.slice(0, PREVIEW_LENGTH) + '...'
      : text;

  return (
    <div className='my-3 p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg'>
      <button
        onClick={() => setExpanded(!expanded)}
        className='flex items-center gap-2 w-full text-left'
      >
        {expanded || !isLongText ? (
          <ChevronDown className='h-4 w-4 text-amber-700 dark:text-amber-300 flex-shrink-0' />
        ) : (
          <ChevronRight className='h-4 w-4 text-amber-700 dark:text-amber-300 flex-shrink-0' />
        )}
        <Brain className='h-4 w-4 text-amber-700 dark:text-amber-300 flex-shrink-0' />
        <span className='text-sm font-medium text-amber-900 dark:text-amber-100'>
          Thinking Process
        </span>
      </button>
      {/* 始终显示预览文字 */}
      {text && (
        <div className='mt-2 pl-6 text-sm text-amber-900 dark:text-amber-100 whitespace-pre-wrap break-words'>
          {displayText}
          {isLongText && !expanded && (
            <button
              onClick={() => setExpanded(true)}
              className='ml-2 text-xs text-amber-700 dark:text-amber-300 underline hover:text-amber-900 dark:hover:text-amber-100'
            >
              展开更多
            </button>
          )}
        </div>
      )}
    </div>
  );
});

ThinkingBlock.displayName = 'ThinkingBlock';
