'use client';

import React, { memo } from 'react';
import type { ContentItem } from './ContentItem';
import { MarkdownRenderer } from './MarkdownRenderer';

interface SystemBlockProps {
  item: ContentItem;
}

/**
 * 系统消息块组件
 * 用于渲染 role=system 的消息内容
 * 简洁展示，不折叠，不显示标题
 */
export const SystemBlock = memo(({ item }: SystemBlockProps) => {
  const text = item.text || '';

  if (!text) return null;

  return (
    <div className='w-full my-3 flex justify-center'>
      <div className='w-auto max-w-full bg-zinc-50 dark:bg-zinc-950/30 text-zinc-600 dark:text-zinc-400 px-4 py-1.5 rounded-full shadow-sm border border-zinc-200 dark:border-zinc-800'>
        <div className='text-xs whitespace-pre-wrap break-words'>
          <MarkdownRenderer text={text} />
        </div>
      </div>
    </div>
  );
});

SystemBlock.displayName = 'SystemBlock';
