'use client';

import React, { memo, useState } from 'react';
import { Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

interface MarkdownRendererProps {
  text: string;
}

/**
 * Markdown 渲染器组件
 * 使用 React.memo 优化性能，避免不必要的重新渲染
 * 代码块支持一键复制功能
 */
export const MarkdownRenderer = memo(({ text }: MarkdownRendererProps) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const copyToClipboard = async (code: string, id: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className='prose prose-sm dark:prose-invert max-w-none'>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '');
            const code = String(children).replace(/\n$/, '');
            const codeId = `code-${Math.random().toString(36).substr(2, 9)}`;

            return !inline && match ? (
              <div className='relative group'>
                {/* 复制按钮 */}
                <button
                  onClick={() => copyToClipboard(code, codeId)}
                  className='absolute top-2 right-2 p-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10'
                  title='Copy code'
                >
                  {copiedId === codeId ? (
                    <Check className='h-4 w-4' />
                  ) : (
                    <Copy className='h-4 w-4' />
                  )}
                </button>

                {/* 语言标签 */}
                <div className='absolute top-2 left-2 px-2 py-0.5 bg-gray-700 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10'>
                  {match[1]}
                </div>

                <SyntaxHighlighter
                  style={oneDark}
                  language={match[1]}
                  PreTag='div'
                  className='rounded-md'
                  {...props}
                >
                  {code}
                </SyntaxHighlighter>
              </div>
            ) : (
              <code
                className='px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-sm font-mono'
                {...props}
              >
                {children}
              </code>
            );
          },
          p({ children }) {
            return <p className='mb-2 last:mb-0'>{children}</p>;
          },
          ul({ children }) {
            return <ul className='list-disc list-inside mb-2'>{children}</ul>;
          },
          ol({ children }) {
            return <ol className='list-decimal list-inside mb-2'>{children}</ol>;
          },
          li({ children }) {
            return <li className='mb-1'>{children}</li>;
          },
          a({ children, href }) {
            return (
              <a
                href={href}
                target='_blank'
                rel='noopener noreferrer'
                className='text-blue-600 hover:text-blue-800 underline'
              >
                {children}
              </a>
            );
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
});

MarkdownRenderer.displayName = 'MarkdownRenderer';
