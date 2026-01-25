import type { Plugin } from 'unified';
import type { Root, Element, Text } from 'hast';
import { visit } from 'unist-util-visit';

/**
 * 自定义 rehype 插件，处理 @mentions 并转换为 HTML span 元素
 *
 * 该插件在 remark 之后运行，查找文本中的 @mentions 模式
 * 然后将它们转换为带有特定样式的 span 元素
 *
 * 支持格式：
 * - @username
 * - @path/to/file
 * - @"prompt-engineer (agent)" - 带引号，可包含空格和括号
 * - @prompt-engineer - 不带引号，但不包含空格
 */

// 将正则表达式提取为常量，避免每次调用都重新创建
const MENTION_REGEX = /(?<!\w)@(?:\"([^\"]+)\"|([\w/][\w/.\-]*))/g;

export const rehypeMention: Plugin<[], Root> = () => {
  return tree => {
    visit(tree, 'text', (node: Text, index, parent: any) => {
      if (!parent || index === undefined || typeof index !== 'number') return;

      const { value } = node;
      const matches = Array.from(value.matchAll(MENTION_REGEX));

      if (matches.length === 0) return;

      const newNodes: Array<Element | Text> = [];
      let lastIndex = 0;

      matches.forEach(match => {
        // match[1] 是带引号的内容（如 "prompt-engineer (agent)"）
        // match[2] 是不带引号的内容（如 username 或 path/to/file）
        const quotedContent = match[1];
        const unquotedContent = match[2];
        const path = quotedContent || unquotedContent;
        const fullMatch = match[0];
        const matchIndex = match.index ?? 0;

        // 添加匹配前的文本
        if (matchIndex > lastIndex) {
          newNodes.push({
            type: 'text',
            value: value.slice(lastIndex, matchIndex),
          });
        }

        // 添加 mention span 元素（不包含原始文本，避免重复的 @ 符号）
        const firstSegment = path.split('/')[0];
        newNodes.push({
          type: 'element',
          tagName: 'span',
          properties: {
            className: ['mention-tag'],
            'data-username': firstSegment,
            'data-path': path,
          },
          children: [], // 空数组，让渲染器完全控制显示
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
