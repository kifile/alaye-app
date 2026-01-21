import type { Plugin } from 'unified';
import type { Root as HtmlRoot, Element as HtmlElement } from 'hast';
import { visit } from 'unist-util-visit';

/**
 * 自定义 rehype 插件，将未知的小写 HTML 标签转换为安全的元素
 * 这样可以避免 React 尝试将它们渲染为组件
 * 同时确保不会在 p 标签内嵌套 div 等块级元素
 */
export const rehypeSanitizeCustomTags: Plugin<[], HtmlRoot> = () => {
  return tree => {
    // 允许的标准 HTML 标签列表
    const allowedTags = new Set([
      'div',
      'span',
      'p',
      'a',
      'strong',
      'em',
      'del',
      's',
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

    visit(tree, 'element', (node: HtmlElement, parent: any) => {
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
