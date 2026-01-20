import type { Plugin } from 'unified';
import type { Root, Text, Link } from 'mdast';
import { visit } from 'unist-util-visit';

/**
 * 自定义 remark 插件，修复 remarkGfm 对 URL 的识别
 * remarkGfm 会将 "http://example.com，查看" 识别为完整链接
 * 这个插件会将链接末尾的中文标点符号和汉字从 URL 中移除，并放到链接后面
 * 应该在 remarkGfm 之后运行
 */
export const remarkFixUrlBoundaries: Plugin<[], Root> = () => {
  return tree => {
    // 匹配末尾的中文标点符号和汉字（不包括英文字母、数字等 URL 字符）
    // 使用负向前瞻确保不匹配 URL 字符
    const trailingPunctuationRegex = /([^\w\-._~:/?#[\]@!$&'()*+,;=%\s]+)$/;

    visit(tree, 'link', (node: Link, index, parent) => {
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
