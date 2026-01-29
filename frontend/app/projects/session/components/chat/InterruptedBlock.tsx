'use client';

import React, { memo } from 'react';
import { Ban } from 'lucide-react';

interface InterruptedBlockProps {
  text: string;
}

/**
 * 用户打断消息块组件
 * 用于渲染被用户手动打断的消息
 * 使用警告色和打断图标来突出显示
 */
export const InterruptedBlock = memo(({ text }: InterruptedBlockProps) => {
  // 去除首尾的方括号
  const getDisplayText = (content: string) => {
    return content.replace(/^\[|\]$/g, '');
  };

  return (
    <div className='my-3 p-3 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 rounded-lg'>
      <div className='flex items-center gap-2'>
        <Ban className='h-4 w-4 text-rose-700 dark:text-rose-300 flex-shrink-0' />
        <span className='text-sm font-medium text-rose-900 dark:text-rose-100'>
          {getDisplayText(text)}
        </span>
      </div>
    </div>
  );
});

InterruptedBlock.displayName = 'InterruptedBlock';
