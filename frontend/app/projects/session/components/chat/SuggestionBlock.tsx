'use client';

import React, { memo } from 'react';
import type { ContentItem } from './ContentItem';
import { ExpandableBlock } from './ExpandableBlock';

interface SuggestionBlockProps {
  item: ContentItem;
}

/**
 * 建议消息块组件
 * 使用通用 ExpandableBlock 组件
 */
export const SuggestionBlock = memo(({ item }: SuggestionBlockProps) => {
  const text = item.text || '';
  return <ExpandableBlock type='suggestion' text={text} />;
});

SuggestionBlock.displayName = 'SuggestionBlock';
