'use client';

import React, { memo, useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { MessageTheme } from './styles/markdown-styles';
import { remarkFixUrlBoundaries } from './plugins/remarkFixUrlBoundaries';
import { rehypeMention } from './plugins/rehypeMention';
import { createRenderers } from './renderers/markdown-renderers';

interface MarkdownRendererProps {
  text: string;
  isUserMessage?: boolean;
}

/**
 * Markdown 渲染器组件
 * 使用 React.memo 优化性能，避免不必要的重新渲染
 * 代码块支持一键复制功能
 * 支持 @mentions 标签和 URL 自动链接识别
 * 根据消息类型（user/assistant）自动应用不同的样式主题
 */
export const MarkdownRenderer = memo(
  ({ text, isUserMessage = false }: MarkdownRendererProps) => {
    const [copiedId, setCopiedId] = useState<string | null>(null);

    // 根据消息类型确定主题
    const theme: MessageTheme = useMemo(
      () => (isUserMessage ? 'user' : 'assistant'),
      [isUserMessage]
    );

    // 复制到剪贴板
    const copyToClipboard = async (code: string, id: string) => {
      try {
        await navigator.clipboard.writeText(code);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
      } catch (err) {
        console.error('Failed to copy:', err);
      }
    };

    // 创建自定义渲染器
    const renderers = useMemo(
      () => createRenderers({ theme, copiedId, onCopy: copyToClipboard }),
      [theme, copiedId]
    );

    return (
      <div className='prose prose-sm dark:prose-invert max-w-none'>
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkFixUrlBoundaries]}
          rehypePlugins={[rehypeMention]}
          components={renderers}
        >
          {text}
        </ReactMarkdown>
      </div>
    );
  }
);

MarkdownRenderer.displayName = 'MarkdownRenderer';
