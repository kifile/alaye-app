/**
 * 内容项类型定义
 * 用于 Claude 消息中的不同内容类型
 */
export type ContentItemType =
  | 'text'
  | 'tool_use'
  | 'server_tool_use'
  | 'thinking'
  | 'interrupted'
  | 'command';

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
  // Command 类型专用字段
  command?: string; // command 名称，例如 /code-review:code-review
  args?: string; // command 参数，例如 http://localhost:3000/projects
}
