/**
 * Markdown 样式配置
 * 为不同的消息类型（user/assistant）提供不同的样式主题
 */

export type MessageTheme = 'user' | 'assistant';

/**
 * 获取内联代码样式
 * 使用 ! 前缀确保 prose 样式不会覆盖这些样式
 */
export const getInlineCodeClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return '!px-1.5 !py-0.5 !rounded !bg-slate-800/90 dark:!bg-slate-700/90 !text-white !text-sm !font-mono !border !border-slate-600/50';
  }
  // assistant - 使用更柔和的灰色
  return '!px-1.5 !py-0.5 !rounded !bg-gray-100 dark:!bg-gray-800 !text-gray-900 dark:!text-gray-100 !text-sm !font-mono !border !border-gray-300 dark:!border-gray-600';
};

/**
 * 获取代码块容器样式
 * 不设置 padding 和背景，这些由 CodeBlock 组件处理
 */
export const getCodeBlockClass = (theme: MessageTheme): string => {
  return '';
};

/**
 * 获取纯代码块（无语言标识）样式
 */
export const getPlainCodeClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'text-white font-mono';
  }
  return 'font-mono';
};

/**
 * 获取链接样式
 */
export const getLinkClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return '!text-white hover:!text-gray-100 underline font-medium';
  }
  // assistant
  return 'text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline';
};

/**
 * 获取列表项样式
 */
export const getListItemClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return '!text-white leading-relaxed';
  }
  return 'text-gray-900 dark:text-gray-100 leading-relaxed';
};

/**
 * 获取列表标记（数字/项目符号）样式
 */
export const getListMarkerClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'marker:text-white dark:marker:text-gray-200';
  }
  return 'marker:text-gray-500 dark:marker:text-gray-400';
};

/**
 * 获取 mentions 标签样式
 */
export const getMentionTagClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'inline-flex items-center gap-1 px-2 py-0.5 bg-white/20 dark:bg-white/10 text-white hover:bg-white/30 dark:hover:bg-white/20 rounded-full text-sm font-medium transition-colors cursor-pointer group relative focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2';
  }
  // assistant
  return 'inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors cursor-pointer group relative focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2';
};

/**
 * 获取表格头部样式
 */
export const getTableHeadClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'bg-gray-700/50 dark:bg-gray-800/50';
  }
  return 'bg-gray-50 dark:bg-gray-800/50';
};

/**
 * 获取表格主体样式
 */
export const getTableBodyClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'bg-gray-700/30 dark:bg-gray-800/30 divide-y divide-gray-600/30 dark:divide-gray-700/30';
  }
  return 'bg-white dark:bg-gray-900/30 divide-y divide-gray-200 dark:divide-gray-700';
};

/**
 * 获取表格行 hover 样式
 */
export const getTableRowHoverClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'hover:bg-gray-600/40 dark:hover:bg-gray-700/40 transition-colors';
  }
  return 'hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors';
};

/**
 * 获取表格单元格文字样式
 */
export const getTableCellTextClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'text-white dark:text-gray-100';
  }
  return 'text-gray-900 dark:text-gray-100';
};

/**
 * 获取表格表头单元格文字样式
 */
export const getTableCellHeaderClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'text-white dark:text-white';
  }
  return 'text-gray-500 dark:text-gray-400';
};

/**
 * 获取引用块样式
 */
export const getBlockquoteClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'border-l-4 border-gray-400 dark:border-gray-500 pl-4 py-1 my-4 italic text-white dark:text-white bg-gray-700/40 dark:bg-gray-800/40';
  }
  return 'border-l-4 border-gray-300 dark:border-gray-600 pl-4 py-1 my-4 italic text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800/50';
};

/**
 * 获取标题样式
 * 缩小标题字号，使其更适合聊天界面
 */
export const getHeadingClass = (level: number, theme: MessageTheme): string => {
  const baseSizes = [
    'text-lg font-bold', // h1 - 从 2xl 降到 lg
    'text-base font-bold', // h2 - 从 xl 降到 base
    'text-sm font-bold', // h3 - 从 lg 降到 sm
    'text-sm font-semibold', // h4 - 保持不变
    'text-xs font-semibold', // h5 - 保持不变
    'text-xs font-semibold', // h6 - 保持不变
  ];

  if (theme === 'user') {
    return `${baseSizes[level - 1]} text-white dark:text-gray-100 mt-4 mb-2`;
  }
  return `${baseSizes[level - 1]} text-gray-900 dark:text-gray-100 mt-4 mb-2`;
};

/**
 * 获取水平分割线样式
 */
export const getHrClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'my-6 border-blue-300/50 dark:border-blue-400/50';
  }
  return 'my-6 border-gray-300 dark:border-gray-700';
};

/**
 * 获取图片样式
 */
export const getImgClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'rounded-lg border border-white/30 dark:border-white/20 my-4';
  }
  return 'rounded-lg border border-gray-300 dark:border-gray-700 my-4';
};
