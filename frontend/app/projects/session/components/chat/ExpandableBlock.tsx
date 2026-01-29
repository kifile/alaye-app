'use client';

import React, { useState, memo } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface BlockConfig {
  icon: () => React.ComponentType<{ className?: string }>;
  titleKey: string;
  defaultTitle: string;
  bgColor: string;
  borderColor: string;
  textColor: string;
  iconColor: string;
  previewLength?: number;
}

const BLOCK_STYLES: Record<string, BlockConfig> = {
  thinking: {
    icon: () => {
      // 动态导入避免循环依赖
      const { Sparkles } = require('lucide-react');
      return Sparkles;
    },
    titleKey: 'session.thinkingBlock.title',
    defaultTitle: 'Thinking Process',
    bgColor: 'bg-slate-50 dark:bg-slate-950/30',
    borderColor: 'border-slate-200 dark:border-slate-800',
    textColor: 'text-slate-700 dark:text-slate-300',
    iconColor: 'text-slate-600 dark:text-slate-400',
    previewLength: 80,
  },
  suggestion: {
    icon: () => {
      const { Lightbulb } = require('lucide-react');
      return Lightbulb;
    },
    titleKey: 'session.suggestionBlock.title',
    defaultTitle: 'Suggestion',
    bgColor: 'bg-indigo-50 dark:bg-indigo-950/30',
    borderColor: 'border-indigo-200 dark:border-indigo-800',
    textColor: 'text-indigo-900 dark:text-indigo-100',
    iconColor: 'text-indigo-600 dark:text-indigo-400',
    previewLength: 80,
  },
  compact: {
    icon: () => {
      const { RotateCcw } = require('lucide-react');
      return RotateCcw;
    },
    titleKey: 'session.compactBlock.title',
    defaultTitle: 'Session Continued',
    bgColor: 'bg-cyan-50 dark:bg-cyan-950/30',
    borderColor: 'border-cyan-200 dark:border-cyan-800',
    textColor: 'text-cyan-900 dark:text-cyan-100',
    iconColor: 'text-cyan-600 dark:text-cyan-400',
    previewLength: 150,
  },
};

interface ExpandableBlockProps {
  type: 'thinking' | 'suggestion' | 'compact';
  text: string;
}

/**
 * 通用展开块组件
 * 支持多种可展开的消息类型（thinking、suggestion、compact）
 */
export const ExpandableBlock = memo(({ type, text }: ExpandableBlockProps) => {
  const { t } = useTranslation('projects');
  const [expanded, setExpanded] = useState(false);

  const config = BLOCK_STYLES[type];
  const IconComponent = config.icon();
  const previewLength = config.previewLength || 80;

  const isLongText = text.length > previewLength;
  const displayText = expanded
    ? text
    : isLongText
      ? text.slice(0, previewLength) + '...'
      : text;

  const showCollapseButton = isLongText;
  const title = t(config.titleKey) || config.defaultTitle;

  return (
    <div className={`my-3 ${config.bgColor} border ${config.borderColor} rounded-lg`}>
      {/* 标题行 */}
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
        <IconComponent className={`h-4 w-4 ${config.iconColor} flex-shrink-0`} />
        <span className={`text-sm font-medium ${config.textColor}`}>{title}</span>

        {/* 折叠按钮 */}
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
        <div
          className={`px-3 pb-3 text-sm ${config.textColor} whitespace-pre-wrap break-words`}
        >
          {displayText}
          {isLongText && !expanded && (
            <button
              onClick={() => setExpanded(true)}
              className={`ml-2 text-xs ${config.iconColor} underline hover:opacity-80`}
            >
              {t('session.thinkingBlock.expandMore') || 'Show more'}
            </button>
          )}
        </div>
      )}
    </div>
  );
});

ExpandableBlock.displayName = 'ExpandableBlock';
