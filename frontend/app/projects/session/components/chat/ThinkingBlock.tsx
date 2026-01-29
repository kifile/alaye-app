'use client';

import React, { memo } from 'react';
import type { ContentItem } from './ContentItem';
import { ExpandableBlock } from './ExpandableBlock';

interface ThinkingBlockProps {
  item: ContentItem;
}

/**
 * 思考过程块组件
 * 使用通用 ExpandableBlock 组件
 */
export const ThinkingBlock = memo(({ item }: ThinkingBlockProps) => {
  const text = item.thinking || '';
  return <ExpandableBlock type='thinking' text={text} />;
});

ThinkingBlock.displayName = 'ThinkingBlock';
