import { AtSign } from 'lucide-react';
import { toast } from 'sonner';
import type { MessageTheme } from '../styles/markdown-styles';
import {
  getInlineCodeClass,
  getCodeBlockClass,
  getLinkClass,
  getListItemClass,
  getListMarkerClass,
  getMentionTagClass,
  getTableHeadClass,
  getTableBodyClass,
  getTableRowHoverClass,
  getTableCellTextClass,
  getTableCellHeaderClass,
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

    // 判断是否为内联代码
    // 如果有 language-xxx className，则一定是代码块
    // 否则，检查 code 内容是否包含换行符（代码块通常有多行）
    const hasLanguage = match !== null;
    const hasNewlines = code.includes('\n');
    // 有语言标识 或者 有换行符 = 代码块
    const isCodeBlock = hasLanguage || hasNewlines;
    const isInline = !isCodeBlock;

    const inlineCodeClass = getInlineCodeClass(theme);
    const finalClassName = className
      ? `${inlineCodeClass} ${className}`
      : inlineCodeClass;

    // 从 props 中移除 className 和 style，避免覆盖我们的自定义样式
    const { className: _, style: __, ...propsWithoutClassNameAndStyle } = props;

    // 统一使用 CodeBlock 组件渲染代码块，无论是否有语言标识
    return !isInline ? (
      <CodeBlock
        code={code}
        language={match ? match[1] : 'plaintext'}
        copiedId={copiedId}
        onCopy={onCopy}
        theme={theme}
      />
    ) : (
      // 内联代码 - 所有样式通过 Tailwind 类或全局 CSS
      <code
        {...propsWithoutClassNameAndStyle}
        className={finalClassName}
        style={{
          display: 'inline-block',
          overflowWrap: 'anywhere',
          wordBreak: 'break-word',
          whiteSpace: 'pre-wrap',
          lineHeight: '1.5',
        }}
      >
        {children}
      </code>
    );
  },

  pre({ children, ...props }: any) {
    return (
      <pre className={getCodeBlockClass(theme)} {...props}>
        {children}
      </pre>
    );
  },

  p({ children, ...props }: any) {
    return (
      <p className='mb-2 last:mb-0 leading-6' {...props}>
        {children}
      </p>
    );
  },

  ul({ children, ...props }: any) {
    return (
      <ul
        className={`list-disc pl-6 space-y-1.5 my-3 ${getListMarkerClass(theme)}`}
        {...props}
      >
        {children}
      </ul>
    );
  },

  ol({ children, ...props }: any) {
    return (
      <ol
        className={`list-decimal pl-6 space-y-1.5 my-3 ${getListMarkerClass(theme)}`}
        {...props}
      >
        {children}
      </ol>
    );
  },

  li({ children, ...props }: any) {
    return (
      <li className={getListItemClass(theme)} {...props}>
        {children}
      </li>
    );
  },

  strong({ children, ...props }: any) {
    return (
      <strong className='font-semibold' {...props}>
        {children}
      </strong>
    );
  },

  em({ children, ...props }: any) {
    return (
      <em className='italic' {...props}>
        {children}
      </em>
    );
  },

  del({ children, ...props }: any) {
    return (
      <del
        className={`line-through ${
          theme === 'user'
            ? 'text-white/70 dark:text-white/70'
            : 'text-gray-500 dark:text-gray-400'
        }`}
        {...props}
      >
        {children}
      </del>
    );
  },

  a({ children, href, ...props }: any) {
    return (
      <a
        href={href}
        target='_blank'
        rel='noopener noreferrer'
        className={getLinkClass(theme)}
        {...props}
      >
        {children}
      </a>
    );
  },

  table({ children, ...props }: any) {
    return (
      <div className='overflow-x-auto my-3'>
        <table
          className='min-w-full divide-y divide-gray-200 dark:divide-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden'
          {...props}
        >
          {children}
        </table>
      </div>
    );
  },

  thead({ children, ...props }: any) {
    return (
      <thead className={getTableHeadClass(theme)} {...props}>
        {children}
      </thead>
    );
  },

  tbody({ children, ...props }: any) {
    return (
      <tbody className={getTableBodyClass(theme)} {...props}>
        {children}
      </tbody>
    );
  },

  tr({ children, ...props }: any) {
    return (
      <tr className={getTableRowHoverClass(theme)} {...props}>
        {children}
      </tr>
    );
  },

  th({ children, ...props }: any) {
    return (
      <th
        className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${getTableCellHeaderClass(theme)}`}
        {...props}
      >
        {children}
      </th>
    );
  },

  td({ children, ...props }: any) {
    return (
      <td
        className={`px-4 py-3 whitespace-nowrap text-sm ${getTableCellTextClass(theme)}`}
        {...props}
      >
        {children}
      </td>
    );
  },

  blockquote({ children, ...props }: any) {
    return (
      <blockquote className={getBlockquoteClass(theme)} {...props}>
        {children}
      </blockquote>
    );
  },

  h1({ children, ...props }: any) {
    return (
      <h1 className={getHeadingClass(1, theme)} {...props}>
        {children}
      </h1>
    );
  },

  h2({ children, ...props }: any) {
    return (
      <h2 className={getHeadingClass(2, theme)} {...props}>
        {children}
      </h2>
    );
  },

  h3({ children, ...props }: any) {
    return (
      <h3 className={getHeadingClass(3, theme)} {...props}>
        {children}
      </h3>
    );
  },

  h4({ children, ...props }: any) {
    return (
      <h4 className={getHeadingClass(4, theme)} {...props}>
        {children}
      </h4>
    );
  },

  h5({ children, ...props }: any) {
    return (
      <h5 className={getHeadingClass(5, theme)} {...props}>
        {children}
      </h5>
    );
  },

  h6({ children, ...props }: any) {
    return (
      <h6 className={getHeadingClass(6, theme)} {...props}>
        {children}
      </h6>
    );
  },

  hr({ ...props }: any) {
    return <hr className={getHrClass(theme)} {...props} />;
  },

  img({ src, alt, ...props }: any) {
    return <img src={src} alt={alt} className={getImgClass(theme)} {...props} />;
  },

  // 自定义 span 渲染器，处理 @mentions 和路径引用
  span({ node, className, children, ...props }: any) {
    if (className === 'mention-tag') {
      const username = props['data-username'];
      const path = props['data-path'];
      const isPath = path && path.includes('/');
      const fullText = isPath ? `@${path}` : `@${username}`;

      // 对于路径，只显示最后20个字符（不包含 @ 符号，因为已经有 AtSign 图标了）
      let displayText: string;
      if (isPath) {
        const fullPath = path; // 不包含 @ 符号
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
          <AtSign className='h-3 w-3 shrink-0' />
          <span className='truncate'>{displayText}</span>
        </span>
      );
    }
    return <span className={className} {...props}>{children}</span>;
  },
});
