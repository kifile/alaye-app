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
    <div className='my-3 p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg'>
      <div className='flex items-center gap-2'>
        <Ban className='h-4 w-4 text-amber-700 dark:text-amber-300 flex-shrink-0' />
        <span className='text-sm font-medium text-amber-900 dark:text-amber-100'>
          {getDisplayText(text)}
        </span>
      </div>
    </div>
  );
});

InterruptedBlock.displayName = 'InterruptedBlock';
