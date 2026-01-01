/**
 * API 类型定义
 *
 * 该文件包含所有与后端 API 通信相关的 TypeScript 类型定义
 * 与 src/api/api_models.py 中的 Pydantic 模型保持一致
 */

// ===== 基础类型定义 =====

export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARN = 'warn',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

export enum EventType {
  USER_ACTION = 'user_action',
  SYSTEM_UPDATE = 'system_update',
  DATA_SYNC = 'data_sync',
  ERROR = 'error',
}

export enum ConfigScope {
  USER = 'user',
  PROJECT = 'project',
  LOCAL = 'local',
  PLUGIN = 'plugin',
}

export enum AiToolType {
  CLAUDE = 'claude',
}

// ===== 模型接口定义 =====

export interface TerminalSize {
  rows: number;
  cols: number;
}

export interface TerminalMetadata {
  user?: string;
  purpose?: string;
  description?: string;
  [key: string]: any;
}

// ===== 请求接口定义 =====

export interface LogRequest {
  level: LogLevel;
  message: string;
  category?: string;
}

export interface NewTerminalRequest {
  command?: string;
  args?: string[];
  work_dir?: string;
  env?: Record<string, string>;
  size?: TerminalSize;
  metadata?: Record<string, any>;
  terminal_id?: string;
}

export interface CloseTerminalRequest {
  instance_id: string;
}

export interface WriteToTerminalRequest {
  instance_id: string;
  data: string;
}

export interface SetTerminalSizeRequest {
  instance_id: string;
  rows: number;
  cols: number;
}

export interface LoadSettingsRequest {
  keys?: string[];
}

export interface GetSettingRequest {
  key: string;
}

export interface UpdateSettingRequest {
  key: string;
  value: string;
}

export interface ScanClaudeSettingsRequest {
  project_id: number;
  scope?: ConfigScope; // 可选，不传入时扫描所有作用域并合并
}

export interface UpdateClaudeSettingsValueRequest {
  project_id: number;
  scope: ConfigScope;
  key: string;
  value: string;
  value_type: 'string' | 'boolean' | 'integer' | 'array' | 'object' | 'dict';
}

export interface UpdateClaudeSettingsScopeRequest {
  project_id: number;
  old_scope: ConfigScope;
  new_scope: ConfigScope;
  key: string;
}

export interface FileDialogFilter {
  name: string;
  extensions: string[];
}

export interface ShowFileDialogRequest {
  title?: string;
  default_path?: string;
  multiple?: boolean;
  filters?: FileDialogFilter[];
}

export interface ListProjectsRequest {
  // 获取项目列表请求无需参数
}

export interface ScanAllProjectsRequest {
  force_refresh?: boolean;
}

export interface ScanSingleProjectRequest {
  project_id: string;
}

export interface ScanClaudeMemoryRequest {
  project_id: number;
}

export interface ScanClaudeAgentsRequest {
  project_id: number;
  scope?: ConfigScope;
}

export interface ScanClaudeCommandsRequest {
  project_id: number;
  scope?: ConfigScope;
}

export interface ScanClaudeSkillsRequest {
  project_id: number;
  scope?: ConfigScope;
}

export interface LoadMarkdownContentRequest {
  project_id: number;
  content_type: 'memory' | 'command' | 'agent' | 'hook' | 'skill';
  name?: string;
  scope?: ConfigScope;
}

export interface UpdateMarkdownContentRequest {
  project_id: number;
  content_type: 'memory' | 'command' | 'agent' | 'hook' | 'skill';
  name?: string;
  from_md5: string;
  content: string;
  scope?: ConfigScope;
}

export interface RenameMarkdownContentRequest {
  project_id: number;
  content_type: 'memory' | 'command' | 'agent' | 'hook' | 'skill';
  name: string;
  new_name: string;
  scope?: ConfigScope;
  new_scope?: ConfigScope;
}

export interface SaveMarkdownContentRequest {
  project_id: number;
  content_type: 'memory' | 'command' | 'agent' | 'hook' | 'skill';
  name: string;
  content: string;
  scope?: ConfigScope;
}

export interface DeleteMarkdownContentRequest {
  project_id: number;
  content_type: 'memory' | 'command' | 'agent' | 'hook' | 'skill';
  name: string;
  scope?: ConfigScope;
}

export interface MarkdownContentDTO {
  md5: string;
  content: string;
}

export interface IDRequest {
  id: string | number;
}

// ===== MCP 服务器管理相关类型 =====

export interface ScanMCPServersRequest {
  project_id: number;
  scope?: ConfigScope | null; // 可选的作用域过滤器
}

export interface MCPServer {
  type: string;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  cwd?: string;
  url?: string; // HTTP 类型的服务器 URL
  headers?: Record<string, string>; // HTTP 请求头
}

export interface MCPServerInfo {
  name: string;
  scope: ConfigScope;
  mcpServer: MCPServer;
  enabled?: boolean; // 服务器最终启用状态
  override: boolean; // 是否被同名的更高优先级服务器覆盖
}

export interface SettingsInfoWithValue {
  value?: boolean;
  scope?: ConfigScope;
}

export interface AddMCPServerRequest {
  project_id: number;
  name: string; // 服务器名称
  server: MCPServer;
  scope?: ConfigScope; // 配置作用域，默认为 project
}

export interface UpdateMCPServerRequest {
  project_id: number;
  name: string; // 原服务器名称
  server: MCPServer; // 新的MCP服务器配置
  scope?: ConfigScope; // 配置作用域，默认为 project
}

export interface RenameMCPServerRequest {
  project_id: number;
  old_name: string; // 原服务器名称
  new_name: string; // 新服务器名称
  old_scope?: ConfigScope; // 原配置作用域，默认为 project
  new_scope?: ConfigScope; // 新配置作用域，None表示保持不变
}

export interface DeleteMCPServerRequest {
  project_id: number;
  name: string; // 服务器名称
  scope?: ConfigScope; // 配置作用域，默认为 project
}

export interface EnableMCPServerRequest {
  project_id: number;
  name: string; // 服务器名称
}

export interface DisableMCPServerRequest {
  project_id: number;
  name: string; // 服务器名称
}

export interface UpdateEnableAllProjectMcpServersRequest {
  project_id: number;
  value: boolean; // enableAllProjectMcpServers的值
}

// ===== Hooks 管理相关类型 =====

export enum HookEvent {
  PreToolUse = 'PreToolUse',
  PermissionRequest = 'PermissionRequest',
  PostToolUse = 'PostToolUse',
  Notification = 'Notification',
  UserPromptSubmit = 'UserPromptSubmit',
  Stop = 'Stop',
  SubagentStop = 'SubagentStop',
  PreCompact = 'PreCompact',
  SessionStart = 'SessionStart',
  SessionEnd = 'SessionEnd',
}

export interface HookConfig {
  type: string; // "command" for bash commands or "prompt" for LLM-based evaluation
  command?: string; // (For type: "command") The bash command to execute
  prompt?: string; // (For type: "prompt") The prompt to send to the LLM
  timeout?: number; // (Optional) How long a hook should run, in seconds
}

export interface HookConfigInfo {
  id: string; // 格式: $type-$scope-$event-$matcher_md5-$content_md5
  scope: ConfigScope;
  event: HookEvent;
  matcher?: string;
  hook_config: HookConfig;
}

export interface HooksInfo {
  matchers: HookConfigInfo[];
  disable_all_hooks?: SettingsInfoWithValue;
}

export interface ScanClaudeHooksRequest {
  project_id: number;
  scope?: ConfigScope | null;
}

export interface AddClaudeHookRequest {
  project_id: number;
  event: HookEvent;
  hook: HookConfig;
  matcher?: string;
  scope?: ConfigScope;
}

export interface RemoveClaudeHookRequest {
  project_id: number;
  hook_id: string;
  scope?: ConfigScope;
}

export interface UpdateClaudeHookRequest {
  project_id: number;
  hook_id: string;
  hook: HookConfig;
  scope?: ConfigScope;
}

export interface UpdateDisableAllHooksRequest {
  project_id: number;
  value: boolean; // disableAllHooks的值
}

// ===== 响应接口定义 =====

export interface LogData {
  record_info: string;
}

export interface ShowFileDialogData {
  file_path?: string;
  file_paths: string[];
  message: string;
}

export interface LoadSettingsData {
  settings: Record<string, string>;
  count: number;
}

export interface TerminalDTO {
  instance_id: string;
  status: string;
}

export interface AIProjectInDB {
  id: number;
  project_name: string;
  project_path?: string;
  ai_tools: AiToolType[];
  first_active_at_str?: string; // Formatted datetime string
  last_active_at_str?: string; // Formatted datetime string
  created_at_str: string; // Formatted datetime string
  updated_at_str: string; // Formatted datetime string
}

// ===== Claude 配置相关类型 =====

export interface FileInfo {
  path: string;
  exists: boolean;
  size?: number;
  modified_str?: string; // Formatted datetime string
  readable?: boolean;
  error?: string;
}

export interface ClaudeMemoryInfo {
  project_claude_md: boolean;
  claude_dir_claude_md: boolean;
  local_claude_md: boolean;
  user_global_claude_md: boolean;
}

export interface MCPInfo {
  servers: MCPServerInfo[];
  enable_all_project_mcp_servers?: SettingsInfoWithValue;
}

export interface SettingsInfo {
  shared_settings?: FileInfo;
  local_settings?: FileInfo;
}

export interface CommandInfo {
  name: string;
  scope: ConfigScope;
  description?: string;
  last_modified_str?: string; // Formatted datetime string
}

export interface AgentInfo {
  name: string;
  scope: ConfigScope;
  description?: string;
  last_modified_str?: string; // Formatted datetime string
}

export interface HookInfo {
  name: string;
  last_modified_str?: string; // Formatted datetime string
}

export interface SkillInfo {
  name: string;
  scope: ConfigScope;
  description?: string;
  last_modified_str?: string; // Formatted datetime string
}

// Claude Settings DTO 类型
export interface ClaudeSettingsDTO {
  model?: string;
  alwaysThinkingEnabled?: boolean;
  env?: Record<string, string>;
  permissions?: ClaudePermissionsConfig;
  sandbox?: ClaudeSandboxConfig;
}

// Claude Settings Info DTO 类型（扁平化，包含作用域）
export interface ClaudeSettingsInfoDTO {
  settings: Record<string, [any, ConfigScope]>;
  env: [string, string, ConfigScope][]; // [(变量名, 值, 作用域)]
}

export interface ClaudePermissionsConfig {
  allow?: string[];
  ask?: string[];
  deny?: string[];
  additionalDirectories?: string[];
  defaultMode?: 'default' | 'acceptEdits' | 'plan' | 'bypassPermissions';
  disableBypassPermissionsMode?: 'disable';
}

export interface ClaudeSandboxConfig {
  enabled?: boolean;
  autoAllowBashIfSandboxed?: boolean;
  excludedCommands?: string[];
  allowUnsandboxedCommands?: boolean;
  enableWeakerNestedSandbox?: boolean;
  network?: ClaudeNetworkConfig;
}

export interface ClaudeNetworkConfig {
  allowUnixSockets?: string[];
  allowLocalBinding?: boolean;
  httpProxyPort?: number;
  socksProxyPort?: number;
}

// 通用 API 响应类型
export interface ApiResponse<T = any> {
  code: number;
  success: boolean;
  data?: T;
  error?: string;
}

// ===== 错误类型定义 =====

export class TerminalServiceError extends Error {
  constructor(
    message: string,
    public instanceId?: string
  ) {
    super(message);
    this.name = 'TerminalServiceError';
  }
}

// ===== API 响应类型别名 =====

export type LogResponse = ApiResponse<LogData>;
export type NewTerminalResponse = ApiResponse<TerminalDTO>;
export type CloseTerminalResponse = ApiResponse<boolean>;
export type WriteToTerminalResponse = ApiResponse<boolean>;
export type SetTerminalSizeResponse = ApiResponse<boolean>;
export type LoadSettingsResponse = ApiResponse<LoadSettingsData>;
export type GetSettingResponse = ApiResponse<string>;
export type UpdateSettingResponse = ApiResponse<boolean>;
export type LoadClaudeSettingsResponse = ApiResponse<ClaudeSettingsInfoDTO>;
export type UpdateClaudeSettingsValueResponse = ApiResponse<boolean>;
export type UpdateClaudeSettingsScopeResponse = ApiResponse<boolean>;
export type ShowFileDialogResponse = ApiResponse<ShowFileDialogData>;
export type ListProjectsResponse = ApiResponse<AIProjectInDB[]>;
export type ScanAllProjectsResponse = ApiResponse<boolean>;
export type ScanSingleProjectResponse = ApiResponse<boolean>;
export type ScanClaudeMemoryResponse = ApiResponse<ClaudeMemoryInfo>;
export type ScanClaudeAgentsResponse = ApiResponse<AgentInfo[]>;
export type ScanClaudeCommandsResponse = ApiResponse<CommandInfo[]>;
export type ScanClaudeSkillsResponse = ApiResponse<SkillInfo[]>;
export type GetProjectResponse = ApiResponse<AIProjectInDB>;
export type LoadMarkdownContentResponse = ApiResponse<MarkdownContentDTO>;
export type UpdateMarkdownContentResponse = ApiResponse<boolean>;
export type RenameMarkdownContentResponse = ApiResponse<boolean>;
export type SaveMarkdownContentResponse = ApiResponse<MarkdownContentDTO>;
export type DeleteMarkdownContentResponse = ApiResponse<boolean>;

// MCP 服务器管理响应类型
export type ScanMCPServersResponse = ApiResponse<MCPInfo>;
export type AddMCPServerResponse = ApiResponse<boolean>;
export type UpdateMCPServerResponse = ApiResponse<boolean>;
export type RenameMCPServerResponse = ApiResponse<boolean>;
export type DeleteMCPServerResponse = ApiResponse<boolean>;
export type EnableMCPServerResponse = ApiResponse<boolean>;
export type DisableMCPServerResponse = ApiResponse<boolean>;
export type UpdateEnableAllProjectMcpServersResponse = ApiResponse<boolean>;

// Hooks 管理响应类型
export type ScanClaudeHooksResponse = ApiResponse<HooksInfo>;
export type AddClaudeHookResponse = ApiResponse<boolean>;
export type RemoveClaudeHookResponse = ApiResponse<boolean>;
export type UpdateClaudeHookResponse = ApiResponse<boolean>;
export type UpdateDisableAllHooksResponse = ApiResponse<boolean>;

// Plugin Marketplace 相关类型
export interface PluginMarketplaceSource {
  source: string;
  repo?: string;
  url?: string;
}

export interface PluginMarketplaceInfo {
  name: string;
  source: PluginMarketplaceSource;
  installLocation: string;
  lastUpdated_str?: string; // Formatted datetime string
}

export interface PluginSource {
  source?: string;
  url?: string;
}

export interface PluginAuthor {
  name?: string;
  email?: string;
}

export interface PluginConfig {
  name: string;
  description?: string;
  version?: string;
  author?: PluginAuthor;
  source?: string | PluginSource;
  category?: string;
  homepage?: string;
  tags?: string[];
  strict?: boolean;
  lspServers?: Record<string, unknown>;
}

export interface PluginTools {
  commands?: CommandInfo[];
  skills?: SkillInfo[];
  agents?: AgentInfo[];
  mcp_servers?: MCPServerInfo[];
  hooks?: HookConfigInfo[];
}

export interface PluginInfo {
  config: PluginConfig;
  marketplace?: string;
  unique_installs?: number;
  installed?: boolean;
  enabled?: boolean;
  enabled_scope?: ConfigScope;
  tools?: PluginTools;
}

// Plugin Marketplace 管理请求类型
export interface ScanClaudePluginMarketplacesRequest {
  project_id: number;
}

export interface ScanClaudePluginsRequest {
  project_id: number;
  marketplace_names?: string[];
}

// Plugin Marketplace 操作请求类型
export interface InstallClaudePluginMarketplaceRequest {
  project_id: number;
  source: string;
}

// Plugin 操作请求类型
export interface InstallClaudePluginRequest {
  project_id: number;
  plugin_name: string;
  scope?: ConfigScope;
}

export interface UninstallClaudePluginRequest {
  project_id: number;
  plugin_name: string;
  scope?: ConfigScope;
}

export interface EnableClaudePluginRequest {
  project_id: number;
  plugin_name: string;
  scope?: ConfigScope;
}

export interface DisableClaudePluginRequest {
  project_id: number;
  plugin_name: string;
  scope?: ConfigScope;
}

export interface MoveClaudePluginRequest {
  project_id: number;
  plugin_name: string;
  old_scope: ConfigScope;
  new_scope: ConfigScope;
}

// ProcessResult 进程执行结果
export interface ProcessResult {
  success: boolean;
  return_code: number;
  stdout: string;
  stderr: string;
  error_message?: string;
}

// Plugin Marketplace 管理响应类型
export type ScanClaudePluginMarketplacesResponse = ApiResponse<PluginMarketplaceInfo[]>;
export type InstallClaudePluginMarketplaceResponse = ApiResponse<ProcessResult>;
export type ScanClaudePluginsResponse = ApiResponse<PluginInfo[]>;

// Plugin 操作响应类型
export type InstallClaudePluginResponse = ApiResponse<ProcessResult>;
export type UninstallClaudePluginResponse = ApiResponse<ProcessResult>;
export type EnableClaudePluginResponse = ApiResponse<boolean>;
export type DisableClaudePluginResponse = ApiResponse<boolean>;
export type MoveClaudePluginResponse = ApiResponse<boolean>;
