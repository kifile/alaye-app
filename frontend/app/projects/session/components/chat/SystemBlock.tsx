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
      <div className='w-auto max-w-full bg-gray-50 dark:bg-gray-900 text-gray-600 dark:text-gray-400 px-4 py-1.5 rounded-full shadow-sm border border-gray-200 dark:border-gray-800'>
        <div className='text-xs whitespace-pre-wrap break-words'>
          <MarkdownRenderer text={text} />
        </div>
      </div>
    </div>
  );
});

SystemBlock.displayName = 'SystemBlock';
