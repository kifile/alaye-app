'use client';

import React, { useState, memo } from 'react';
import { ChevronDown, ChevronRight, Sparkles } from 'lucide-react';
import type { ContentItem } from './ContentItem';
import { useTranslation } from 'react-i18next';

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
  const { t } = useTranslation('projects');
  const [expanded, setExpanded] = useState(false);
  const text = item.text || '';
  const isLongText = text.length > PREVIEW_LENGTH;

  // 显示的文字内容
  const displayText = expanded
    ? text
    : isLongText
      ? text.slice(0, PREVIEW_LENGTH) + '...'
      : text;

  // 只有文本长度超过预览长度时才显示折叠按钮
  const showCollapseButton = isLongText;

  return (
    <div className='my-3 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-lg'>
      {/* 标题行 - 使用 flex 布局，折叠按钮在右侧 */}
      <div
        className={`flex items-center gap-2 px-3 py-2 ${showCollapseButton ? 'cursor-pointer' : ''}`}
        onClick={() => showCollapseButton && setExpanded(!expanded)}
        role={showCollapseButton ? 'button' : undefined}
        tabIndex={showCollapseButton ? 0 : undefined}
        aria-expanded={showCollapseButton ? expanded : undefined}
        onKeyDown={e => {
          if (showCollapseButton && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            setExpanded(!expanded);
          }
        }}
      >
        <Sparkles className='h-4 w-4 text-emerald-700 dark:text-emerald-300 flex-shrink-0' />
        <span className='text-sm font-medium text-emerald-900 dark:text-emerald-100'>
          {t('session.thinkingBlock.title') || 'Thinking Process'}
        </span>

        {/* 折叠按钮 - 放在右侧 */}
        {showCollapseButton && (
          <div className='ml-auto text-gray-500'>
            {expanded ? (
              <ChevronDown className='h-4 w-4' />
            ) : (
              <ChevronRight className='h-4 w-4' />
            )}
          </div>
        )}
      </div>

      {/* 内容 */}
      {text && (
        <div className='px-3 pb-3 text-sm text-emerald-900 dark:text-emerald-100 whitespace-pre-wrap break-words'>
          {displayText}
          {isLongText && !expanded && (
            <button
              onClick={() => setExpanded(true)}
              className='ml-2 text-xs text-emerald-700 dark:text-emerald-300 underline hover:text-emerald-900 dark:hover:text-emerald-100'
            >
              {t('session.thinkingBlock.expandMore') || 'Show more'}
            </button>
          )}
        </div>
      )}
    </div>
  );
});

ThinkingBlock.displayName = 'ThinkingBlock';
