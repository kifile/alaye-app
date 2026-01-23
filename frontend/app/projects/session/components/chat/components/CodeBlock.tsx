'use client';

import { memo } from 'react';
import { Copy, Check } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface CodeBlockProps {
  code: string;
  language: string;
  copiedId: string | null;
  onCopy: (code: string, id: string) => void;
  theme?: 'user' | 'assistant';
}

/**
 * 代码块组件
 * 支持语法高亮、一键复制、行号显示和自动换行功能
 * 使用 Figma 风格的简约设计
 */
export const CodeBlock = memo(
  ({ code, language, copiedId, onCopy, theme = 'assistant' }: CodeBlockProps) => {
    const codeId = `code-${Math.random().toString(36).substring(2, 11)}`;

    // Figma 风格的代码块容器样式
    const containerClass = theme === 'user'
      ? 'relative group not-prose rounded-lg bg-slate-50/90 border border-slate-200/50 dark:bg-slate-900/50 dark:border-slate-700/50 shadow-sm'
      : 'relative group not-prose rounded-lg bg-slate-50 border border-slate-200 dark:bg-slate-900/50 dark:border-slate-700/50 shadow-sm';

    // 按钮基础样式
    const iconButtonClass =
      'absolute top-2 p-1.5 bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300 rounded text-xs opacity-0 group-hover:opacity-100 transition-all duration-200 z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 shadow-sm border border-slate-200 dark:border-slate-600';

    // 语言标签样式
    const languageTagClass =
      'absolute top-2 left-2 px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-xs font-medium rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10 border border-slate-200 dark:border-slate-700';

    return (
      <div className={containerClass}>
        {/* 语言标签 */}
        <div className={languageTagClass}>{language}</div>

        {/* 复制按钮 */}
        <button
          onClick={() => onCopy(code, codeId)}
          className={`${iconButtonClass} right-2`}
          title='Copy code'
          aria-label='Copy code to clipboard'
        >
          {copiedId === codeId ? (
            <Check className='h-3.5 w-3.5' />
          ) : (
            <Copy className='h-3.5 w-3.5' />
          )}
        </button>

        {/* 代码高亮 */}
        <SyntaxHighlighter
          style={oneLight}
          language={language}
          PreTag='div'
          showLineNumbers={true}
          wrapLines={false}
          customStyle={{
            margin: 0,
            borderRadius: '0.5rem',
            background: 'transparent',
            fontSize: '0.875rem',
            paddingLeft: '0.75rem',
          }}
          codeTagProps={{
            style: {
              display: 'block',
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
