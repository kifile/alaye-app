'use client';

import React, { memo } from 'react';
import type { ContentItem } from './ContentItem';
import { ExpandableBlock } from './ExpandableBlock';

interface CompactBlockProps {
  item: ContentItem;
}

/**
 * 会话继续块组件
 * 使用通用 ExpandableBlock 组件
 */
export const CompactBlock = memo(({ item }: CompactBlockProps) => {
  const text = item.text || '';
  return <ExpandableBlock type='compact' text={text} />;
});

CompactBlock.displayName = 'CompactBlock';
