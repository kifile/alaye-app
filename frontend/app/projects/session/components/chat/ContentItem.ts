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
  | 'command'
  | 'subagent'
  | 'suggestion'
  | 'compact';

export interface ContentItem {
  type: ContentItemType;
  text?: string;
  name?: string;
  thinking?: string;
  input?: Record<string, any>;
  output?: any; // 合并后的 tool_use 包含 output
  status?: 'complete' | 'incomplete'; // tool_use 状态
  tool_use_id?: string;
  id?: string;
  content?: string | Array<any>;
  is_continuation?: boolean;
  extra?: string; // isMeta 消息提取的 text 内容
  // Command 类型专用字段
  command?: string; // command 名称，例如 /code-review:code-review
  args?: string; // command 参数，例如 http://localhost:3000/projects
  // Subagent 类型专用字段
  agent_type?: string; // agent 类型，例如 uiux_reviewer
  description?: string; // agent 描述
  session?: any; // subagent 的 ClaudeSession 对象
}
