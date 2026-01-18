'use client';

import React, { memo, useState } from 'react';
import { Copy, Check, AtSign } from 'lucide-react';
import { toast } from 'sonner';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { visit } from 'unist-util-visit';
import type { Plugin } from 'unified';
import type { Root, Text, HTML, Link } from 'mdast';
import type { Root as HtmlRoot, Element as HtmlElement } from 'hast';

interface MarkdownRendererProps {
  text: string;
  isUserMessage?: boolean;
}

/**
 * 自定义 remark 插件，处理 @mentions 和路径引用
 */
const remarkMentions: Plugin<[], Root> = () => {
  return tree => {
    const mentionRegex = /(?<!\w)@([\w/][\w/.\-]*)/g;

    visit(tree, 'text', (node: Text, index, parent) => {
      if (!parent || index === undefined) return;

      const { value } = node;
      const matches = Array.from(value.matchAll(mentionRegex));

      if (matches.length === 0) return;

      const newNodes: Array<Text | HTML> = [];
      let lastIndex = 0;

      matches.forEach(match => {
        const fullMatch = match[0];
        const path = match[1];
        const matchIndex = match.index ?? 0;

        // 添加匹配前的文本
        if (matchIndex > lastIndex) {
          newNodes.push({
            type: 'text',
            value: value.slice(lastIndex, matchIndex),
          });
        }

        // 添加 mention HTML 节点
        const firstSegment = path.split('/')[0];
        newNodes.push({
          type: 'html',
          value: `<span class="mention-tag" data-username="${firstSegment}" data-path="${path}">${fullMatch}</span>`,
        });

        lastIndex = matchIndex + fullMatch.length;
      });

      // 添加剩余文本
      if (lastIndex < value.length) {
        newNodes.push({
          type: 'text',
          value: value.slice(lastIndex),
        });
      }

      // 替换原节点
      parent.children.splice(index, 1, ...newNodes);
    });
  };
};

/**
 * 自定义 rehype 插件，将未知的小写 HTML 标签转换为安全的元素
 * 这样可以避免 React 尝试将它们渲染为组件
 * 同时确保不会在 p 标签内嵌套 div 等块级元素
 */
const rehypeSanitizeCustomTags: Plugin<[], HtmlRoot> = () => {
  return tree => {
    // 允许的标准 HTML 标签列表
    const allowedTags = new Set([
      'div',
      'span',
      'p',
      'a',
      'strong',
      'em',
      'code',
      'pre',
      'ul',
      'ol',
      'li',
      'table',
      'thead',
      'tbody',
      'tr',
      'th',
      'td',
      'h1',
      'h2',
      'h3',
      'h4',
      'h5',
      'h6',
      'blockquote',
      'hr',
      'br',
      'img',
      'input',
      'button',
      'label',
      'select',
      'option',
    ]);

    // 不能作为 p 标签子元素的块级标签
    const blockLevelTags = new Set([
      'div',
      'p',
      'h1',
      'h2',
      'h3',
      'h4',
      'h5',
      'h6',
      'ul',
      'ol',
      'li',
      'table',
      'thead',
      'tbody',
      'tr',
      'th',
      'td',
      'blockquote',
      'pre',
      'hr',
      'img',
    ]);

    visit(tree, 'element', (node: HtmlElement, index, parent: any) => {
      if (!allowedTags.has(node.tagName)) {
        const originalTag = node.tagName;

        // 检查父元素是否为 p 标签
        const parentIsP = parent && parent.type === 'element' && parent.tagName === 'p';

        // 如果父元素是 p 标签，则必须使用 span（inline 元素）
        // 否则根据原始标签类型决定
        if (parentIsP) {
          node.tagName = 'span';
        } else if (blockLevelTags.has(originalTag)) {
          node.tagName = 'div';
        } else {
          node.tagName = 'span';
        }

        // 保留原始标签名作为 class
        node.properties = node.properties || {};
        const existingClass = node.properties.className || [];
        node.properties.className = Array.isArray(existingClass)
          ? [...existingClass, `original-tag-${originalTag}`]
          : [`original-tag-${originalTag}`];
      }
    });
  };
};

/**
 * 自定义 remark 插件，修复 remarkGfm 对 URL 的识别
 * remarkGfm 会将 "http://example.com，查看" 识别为完整链接
 * 这个插件会将链接末尾的中文标点符号和汉字从 URL 中移除，并放到链接后面
 * 应该在 remarkGfm 之后运行
 */
const remarkFixUrlBoundaries: Plugin<[], Root> = () => {
  return tree => {
    // 匹配末尾的中文标点符号和汉字（不包括英文字母、数字等 URL 字符）
    // 使用负向前瞻确保不匹配 URL 字符
    const trailingPunctuationRegex = /([^\w\-._~:/?#[\]@!$&'()*+,;=%\s]+)$/;

    visit(tree, 'link', (node: Link, index, parent: any) => {
      if (!parent || index === undefined) return;

      const url = node.url;
      const match = url.match(trailingPunctuationRegex);

      if (match) {
        const trailingText = match[1];
        const cleanedUrl = url.slice(0, -trailingText.length);

        // 只在有被移除的文本时才更新
        if (cleanedUrl !== url) {
          // 更新 URL
          node.url = cleanedUrl;

          // 从链接文本中移除末尾的中文部分
          if (node.children.length > 0) {
            const lastChild = node.children[node.children.length - 1];
            if (lastChild.type === 'text' && lastChild.value.endsWith(trailingText)) {
              lastChild.value = lastChild.value.slice(0, -trailingText.length);
            }
          }

          // 在链接后面添加文本节点，包含被移除的中文部分
          const textNode: Text = { type: 'text', value: trailingText };
          parent.children.splice(index + 1, 0, textNode);
        }
      }
    });
  };
};

/**
 * Markdown 渲染器组件
 * 使用 React.memo 优化性能，避免不必要的重新渲染
 * 代码块支持一键复制功能
 * 支持 @mentions 标签和 URL 自动链接识别
 */
export const MarkdownRenderer = memo(
  ({ text, isUserMessage }: MarkdownRendererProps) => {
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
          remarkPlugins={[remarkGfm, remarkFixUrlBoundaries, remarkMentions]}
          rehypePlugins={[rehypeRaw, rehypeSanitizeCustomTags]}
          components={{
            code({ node, inline, className, children, ...props }: any) {
              const match = /language-(\w+)/.exec(className || '');
              const code = String(children).replace(/\n$/, '');
              const codeId = `code-${Math.random().toString(36).substr(2, 9)}`;

              return !inline && match ? (
                <div className='relative group not-prose'>
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
                    codeTagProps={{
                      style: {
                        display: 'block',
                        overflowX: 'auto',
                        whiteSpace: 'pre',
                      },
                    }}
                    {...props}
                  >
                    {code}
                  </SyntaxHighlighter>
                </div>
              ) : !inline ? (
                // 代码块（没有语言标识）- 返回 code 元素，让 pre 组件处理背景
                <code
                  className={isUserMessage ? 'text-white font-mono' : 'font-mono'}
                  {...props}
                >
                  {children}
                </code>
              ) : (
                <code
                  className={
                    isUserMessage
                      ? 'px-1.5 py-0.5 rounded bg-slate-800/90 dark:bg-slate-700/90 text-white text-sm font-mono border border-slate-600/50'
                      : 'px-1.5 py-0.5 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm font-mono border border-gray-200 dark:border-gray-700'
                  }
                  {...props}
                >
                  {children}
                </code>
              );
            },
            pre({ children }) {
              return (
                <pre
                  className={
                    isUserMessage
                      ? 'bg-slate-600/70 dark:bg-slate-500/70 px-4 py-3 rounded-md overflow-x-auto text-sm not-prose text-white border border-slate-400/30 max-w-full'
                      : 'bg-gray-100 dark:bg-gray-800/80 px-4 py-3 rounded-md overflow-x-auto text-sm not-prose text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700 max-w-full'
                  }
                >
                  {children}
                </pre>
              );
            },
            p({ children }) {
              return <p className='mb-2 last:mb-0 leading-6'>{children}</p>;
            },
            ul({ children }) {
              return (
                <ul className='list-disc pl-6 space-y-1.5 my-3 marker:text-gray-500 dark:marker:text-gray-400'>
                  {children}
                </ul>
              );
            },
            ol({ children }) {
              return (
                <ol className='list-decimal pl-6 space-y-1.5 my-3 marker:text-gray-500 dark:marker:text-gray-400'>
                  {children}
                </ol>
              );
            },
            li({ children }) {
              return (
                <li className='text-gray-900 dark:text-gray-100 leading-relaxed'>
                  {children}
                </li>
              );
            },
            strong({ children }) {
              return <strong className='font-semibold'>{children}</strong>;
            },
            em({ children }) {
              return <em className='italic'>{children}</em>;
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
            table({ children }) {
              return (
                <div className='overflow-x-auto my-3'>
                  <table className='min-w-full divide-y divide-gray-200 dark:divide-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden'>
                    {children}
                  </table>
                </div>
              );
            },
            thead({ children }) {
              return (
                <thead className='bg-gray-50 dark:bg-gray-800/50'>{children}</thead>
              );
            },
            tbody({ children }) {
              return (
                <tbody className='bg-white dark:bg-gray-900/30 divide-y divide-gray-200 dark:divide-gray-700'>
                  {children}
                </tbody>
              );
            },
            tr({ children }) {
              return (
                <tr className='hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors'>
                  {children}
                </tr>
              );
            },
            th({ children }) {
              return (
                <th className='px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider'>
                  {children}
                </th>
              );
            },
            td({ children }) {
              return (
                <td className='px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100'>
                  {children}
                </td>
              );
            },
            // 自定义 span 渲染器，处理 @mentions 和路径引用
            span({ node, className, ...props }: any) {
              if (className === 'mention-tag') {
                const username = props['data-username'];
                const path = props['data-path'];
                const isPath = path && path.includes('/');
                const fullText = isPath ? `@${path}` : `@${username}`;

                // 对于路径，只显示最后20个字符（包括 @ 符号）
                let displayText: string;
                if (isPath) {
                  const fullPath = '@' + path; // 完整路径包含 @ 符号
                  if (fullPath.length > 20) {
                    displayText = '...' + fullPath.slice(-20);
                  } else {
                    displayText = fullPath;
                  }
                } else {
                  displayText = username;
                }

                return (
                  <span
                    className='inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors cursor-pointer group relative'
                    title={fullText}
                    onClick={() => {
                      navigator.clipboard.writeText(fullText);
                      toast.success(`Copied: ${fullText}`);
                    }}
                  >
                    <AtSign className='h-3 w-3 flex-shrink-0' />
                    <span className='truncate'>{displayText}</span>
                  </span>
                );
              }
              return <span className={className} {...props} />;
            },
          }}
        >
          {text}
        </ReactMarkdown>
      </div>
    );
  }
);

MarkdownRenderer.displayName = 'MarkdownRenderer';
