/**
 * Markdown 样式配置
 * 为不同的消息类型（user/assistant）提供不同的样式主题
 */

export type MessageTheme = 'user' | 'assistant';

/**
 * 获取内联代码样式
 */
export const getInlineCodeClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'px-1.5 py-0.5 rounded bg-slate-800/90 dark:bg-slate-700/90 text-white text-sm font-mono border border-slate-600/50';
  }
  // assistant - 使用更柔和的灰色
  return 'px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm font-mono border border-gray-300 dark:border-gray-600';
};

/**
 * 获取代码块容器样式
 */
export const getCodeBlockClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'bg-slate-600/70 dark:bg-slate-500/70 px-4 py-3 rounded-md overflow-x-auto text-sm not-prose text-white border border-slate-400/30 max-w-full';
  }
  // assistant
  return 'bg-gray-100 dark:bg-gray-800/80 px-4 py-3 rounded-md overflow-x-auto text-sm not-prose text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700 max-w-full';
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
    return 'bg-white/20 dark:bg-white/10';
  }
  return 'bg-gray-50 dark:bg-gray-800/50';
};

/**
 * 获取表格主体样式
 */
export const getTableBodyClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'bg-white/10 dark:bg-white/5 divide-y divide-white/20 dark:divide-white/10';
  }
  return 'bg-white dark:bg-gray-900/30 divide-y divide-gray-200 dark:divide-gray-700';
};

/**
 * 获取表格行 hover 样式
 */
export const getTableRowHoverClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'hover:bg-white/20 dark:hover:bg-white/10 transition-colors';
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
 * 获取引用块样式
 */
export const getBlockquoteClass = (theme: MessageTheme): string => {
  if (theme === 'user') {
    return 'border-l-4 border-white/40 dark:border-white/30 pl-4 py-1 my-4 italic text-white/90 dark:text-white/80 bg-white/10 dark:bg-white/5';
  }
  return 'border-l-4 border-gray-300 dark:border-gray-600 pl-4 py-1 my-4 italic text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800/50';
};

/**
 * 获取标题样式
 */
export const getHeadingClass = (level: number, theme: MessageTheme): string => {
  const baseSizes = [
    'text-2xl font-bold', // h1
    'text-xl font-bold', // h2
    'text-lg font-bold', // h3
    'text-base font-semibold', // h4
    'text-sm font-semibold', // h5
    'text-xs font-semibold', // h6
  ];

  if (theme === 'user') {
    return `${baseSizes[level - 1]} text-white dark:text-gray-100 mt-6 mb-3`;
  }
  return `${baseSizes[level - 1]} text-gray-900 dark:text-gray-100 mt-6 mb-3`;
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
