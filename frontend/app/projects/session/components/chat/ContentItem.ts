/**
 * 内容项类型定义
 * 用于 Claude 消息中的不同内容类型
 */
export type ContentItemType = 'text' | 'tool_use' | 'thinking';

export interface ContentItem {
  type: ContentItemType;
  text?: string;
  name?: string;
  input?: Record<string, any>;
  output?: any; // 合并后的 tool_use 包含 output
  status?: 'complete' | 'incomplete'; // tool_use 状态
  tool_use_id?: string;
  id?: string;
  content?: string | Array<any>;
  is_continuation?: boolean;
}
