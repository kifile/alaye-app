'use client';

import React from 'react';
import Masonry from 'react-masonry-css';

interface MasonryGridProps {
  children: React.ReactNode;
  className?: string;
  breakpointColumnsObj?: {
    default: number;
    [key: number]: number;
  };
}

/**
 * 瀑布流网格组件
 *
 * 特性：
 * - 响应式列数配置
 * - 自动计算卡片高度，紧密排列
 * - 支持自定义间距
 *
 * 示例：
 * ```tsx
 * <MasonryGrid>
 *   {items.map(item => <Card key={item.id}>{item.content}</Card>)}
 * </MasonryGrid>
 * ```
 */
export function MasonryGrid({
  children,
  className = '',
  breakpointColumnsObj,
}: MasonryGridProps) {
  // 默认断点配置：根据 Tailwind 的断点
  // react-masonry-css 使用"最大宽度"逻辑
  // default: 默认值
  // {number}: 当容器宽度 ≤ 这个值时使用此列数
  const defaultBreakpointColumns = {
    default: 3, // 默认 3 列（当宽度 ≥ 最大断点时）
    1279: 2, // 宽度 ≤ 1279px 时 2 列（对应 md 到 xl 之前）
    767: 1, // 宽度 ≤ 767px 时 1 列（对应 md 之前）
  };

  const finalBreakpointColumns = breakpointColumnsObj || defaultBreakpointColumns;

  return (
    <Masonry
      breakpointCols={finalBreakpointColumns}
      className={`my-masonry-grid ${className}`}
      columnClassName='masonry-grid_column'
    >
      {children}
    </Masonry>
  );
}
