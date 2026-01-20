import React from 'react';
import { AtSign } from 'lucide-react';
import { toast } from 'sonner';
import type { MessageTheme } from '../styles/markdown-styles';
import {
  getInlineCodeClass,
  getCodeBlockClass,
  getPlainCodeClass,
  getLinkClass,
  getListItemClass,
  getListMarkerClass,
  getMentionTagClass,
  getTableHeadClass,
  getTableBodyClass,
  getTableRowHoverClass,
  getTableCellTextClass,
  getBlockquoteClass,
  getHeadingClass,
  getHrClass,
  getImgClass,
} from '../styles/markdown-styles';
import { CodeBlock } from '../components/CodeBlock';

interface RenderersProps {
  theme: MessageTheme;
  copiedId: string | null;
  onCopy: (code: string, id: string) => void;
}

/**
 * 创建自定义渲染器配置
 * 根据消息主题（user/assistant）返回不同的样式
 */
export const createRenderers = ({ theme, copiedId, onCopy }: RenderersProps) => ({
  code({ node, inline, className, children, ...props }: any) {
    const match = /language-(\w+)/.exec(className || '');
    const code = String(children).replace(/\n$/, '');

    return !inline && match ? (
      <CodeBlock code={code} language={match[1]} copiedId={copiedId} onCopy={onCopy} />
    ) : !inline ? (
      // 代码块（没有语言标识）
      <code className={getPlainCodeClass(theme)} {...props}>
        {children}
      </code>
    ) : (
      <code className={getInlineCodeClass(theme)} {...props}>
        {children}
      </code>
    );
  },

  pre({ children }) {
    return <pre className={getCodeBlockClass(theme)}>{children}</pre>;
  },

  p({ children }) {
    return <p className='mb-2 last:mb-0 leading-6'>{children}</p>;
  },

  ul({ children }) {
    return (
      <ul className={`list-disc pl-6 space-y-1.5 my-3 ${getListMarkerClass(theme)}`}>
        {children}
      </ul>
    );
  },

  ol({ children }) {
    return (
      <ol className={`list-decimal pl-6 space-y-1.5 my-3 ${getListMarkerClass(theme)}`}>
        {children}
      </ol>
    );
  },

  li({ children }) {
    return <li className={getListItemClass(theme)}>{children}</li>;
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
        className={getLinkClass(theme)}
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
    return <thead className={getTableHeadClass(theme)}>{children}</thead>;
  },

  tbody({ children }) {
    return <tbody className={getTableBodyClass(theme)}>{children}</tbody>;
  },

  tr({ children }) {
    return <tr className={getTableRowHoverClass(theme)}>{children}</tr>;
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
      <td
        className={`px-4 py-3 whitespace-nowrap text-sm ${getTableCellTextClass(theme)}`}
      >
        {children}
      </td>
    );
  },

  blockquote({ children }) {
    return <blockquote className={getBlockquoteClass(theme)}>{children}</blockquote>;
  },

  h1({ children }) {
    return <h1 className={getHeadingClass(1, theme)}>{children}</h1>;
  },

  h2({ children }) {
    return <h2 className={getHeadingClass(2, theme)}>{children}</h2>;
  },

  h3({ children }) {
    return <h3 className={getHeadingClass(3, theme)}>{children}</h3>;
  },

  h4({ children }) {
    return <h4 className={getHeadingClass(4, theme)}>{children}</h4>;
  },

  h5({ children }) {
    return <h5 className={getHeadingClass(5, theme)}>{children}</h5>;
  },

  h6({ children }) {
    return <h6 className={getHeadingClass(6, theme)}>{children}</h6>;
  },

  hr() {
    return <hr className={getHrClass(theme)} />;
  },

  img({ src, alt, ...props }) {
    return <img src={src} alt={alt} className={getImgClass(theme)} {...props} />;
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
          className={getMentionTagClass(theme)}
          title={fullText}
          role='button'
          tabIndex={0}
          aria-label={`Copy ${fullText} to clipboard`}
          onClick={() => {
            navigator.clipboard.writeText(fullText);
            toast.success(`Copied: ${fullText}`);
          }}
          onKeyDown={e => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              navigator.clipboard.writeText(fullText);
              toast.success(`Copied: ${fullText}`);
            }
          }}
        >
          <AtSign className='h-3 w-3 flex-shrink-0' />
          <span className='truncate'>{displayText}</span>
        </span>
      );
    }
    return <span className={className} {...props} />;
  },
});
