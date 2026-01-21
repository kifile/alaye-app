'use client';

import React, { memo } from 'react';
import { Copy, Check } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface CodeBlockProps {
  code: string;
  language: string;
  copiedId: string | null;
  onCopy: (code: string, id: string) => void;
  theme?: 'user' | 'assistant';
}

/**
 * 代码块组件
 * 支持语法高亮和一键复制功能
 */
export const CodeBlock = memo(
  ({ code, language, copiedId, onCopy, theme = 'assistant' }: CodeBlockProps) => {
    const codeId = `code-${Math.random().toString(36).substr(2, 9)}`;

    // 根据主题确定背景色
    const containerBgClass =
      theme === 'user'
        ? 'bg-slate-600/70 dark:bg-slate-500/70'
        : 'bg-gray-100 dark:bg-gray-800/80';

    return (
      <div className={`relative group not-prose rounded-md ${containerBgClass}`}>
        {/* 复制按钮 */}
        <button
          onClick={() => onCopy(code, codeId)}
          className='absolute top-2 right-2 p-2 bg-gray-700/90 hover:bg-gray-600 dark:bg-gray-600/90 dark:hover:bg-gray-500 text-white rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900 backdrop-blur-sm'
          title='Copy code'
          aria-label='Copy code to clipboard'
        >
          {copiedId === codeId ? (
            <Check className='h-4 w-4' />
          ) : (
            <Copy className='h-4 w-4' />
          )}
        </button>

        {/* 语言标签 */}
        <div className='absolute top-2 left-2 px-2 py-0.5 bg-gray-700/90 dark:bg-gray-600/90 text-white dark:text-gray-100 text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10 backdrop-blur-sm'>
          {language}
        </div>

        {/* 代码高亮 */}
        <SyntaxHighlighter
          style={oneDark}
          language={language}
          PreTag='div'
          codeTagProps={{
            style: {
              display: 'block',
              overflowX: 'auto',
              whiteSpace: 'pre',
            },
          }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    );
  }
);

CodeBlock.displayName = 'CodeBlock';
