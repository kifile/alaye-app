import type { Plugin } from 'unified';
import type { Root, Text, HTML } from 'mdast';
import { visit } from 'unist-util-visit';

/**
 * 自定义 remark 插件，处理 @mentions 和路径引用
 * 支持格式：
 * - @username
 * - @path/to/file
 * - @"prompt-engineer (agent)" - 带引号，可包含空格和括号
 * - @prompt-engineer - 不带引号，但不包含空格
 */
export const remarkMentions: Plugin<[], Root> = () => {
  return tree => {
    // 匹配 @mentions，支持带引号和不带引号两种格式
    const mentionRegex = /(?<!\w)@(?:"([^"]+)"|([\w/][\w/.\-]*))/g;

    visit(tree, 'text', (node: Text, index, parent) => {
      if (!parent || index === undefined) return;

      const { value } = node;
      const matches = Array.from(value.matchAll(mentionRegex));

      if (matches.length === 0) return;

      const newNodes: Array<Text | HTML> = [];
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
