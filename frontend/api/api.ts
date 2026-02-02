/**
 * PyWebview API 统一接口层
 *
 * 该文件封装了所有与 pywebview 后端通信的逻辑，
 * 业务组件只需要调用这里的方法，不需要关心具体的实现细节
 */

import { log } from '@/lib/log';
import { is_pywebview, get_pywebview_api } from '@/lib/env';

// 导入所有类型定义
import type {
  LogLevel,
  TerminalSize,
  TerminalMetadata,
  AiToolType,
  LogRequest,
  NewTerminalRequest,
  CloseTerminalRequest,
  WriteToTerminalRequest,
  SetTerminalSizeRequest,
  LoadSettingsRequest,
  GetSettingRequest,
  UpdateSettingRequest,
  ScanClaudeSettingsRequest,
  UpdateClaudeSettingsValueRequest,
  UpdateClaudeSettingsScopeRequest,
  ShowFileDialogRequest,
  ListProjectsRequest,
  ScanAllProjectsRequest,
  ScanClaudeMemoryRequest,
  ScanClaudeAgentsRequest,
  ScanClaudeCommandsRequest,
  ScanClaudeSkillsRequest,
  LoadMarkdownContentRequest,
  UpdateMarkdownContentRequest,
  RenameMarkdownContentRequest,
  SaveMarkdownContentRequest,
  DeleteMarkdownContentRequest,
  ListSkillContentRequest,
  ReadSkillFileRequest,
  UpdateSkillFileRequest,
  DeleteSkillFileRequest,
  CreateSkillFileRequest,
  RenameSkillFileRequest,
  MoveSkillFileRequest,
  IDRequest,
  ScanMCPServersRequest,
  AddMCPServerRequest,
  UpdateMCPServerRequest,
  DeleteMCPServerRequest,
  RenameMCPServerRequest,
  EnableMCPServerRequest,
  DisableMCPServerRequest,
  UpdateEnableAllProjectMcpServersRequest,
  ScanLSPServersRequest,
  ScanClaudeHooksRequest,
  AddClaudeHookRequest,
  RemoveClaudeHookRequest,
  UpdateClaudeHookRequest,
  UpdateDisableAllHooksRequest,
  ScanClaudePluginMarketplacesRequest,
  InstallClaudePluginMarketplaceRequest,
  ScanClaudePluginsRequest,
  InstallClaudePluginRequest,
  UninstallClaudePluginRequest,
  EnableClaudePluginRequest,
  DisableClaudePluginRequest,
  MoveClaudePluginRequest,
  ReadPluginReadmeRequest,
  ScanSessionsRequest,
  ReadSessionContentsRequest,
  ClaudeSession,
  ClaudeSessionInfo,
  LogData,
  LoadSettingsData,
  ShowFileDialogData,
  MarkdownContentDTO,
  ClaudeSettingsInfoDTO,
  TerminalDTO,
  AIProjectInDB,
  ApiResponse,
  LogResponse,
  NewTerminalResponse,
  CloseTerminalResponse,
  WriteToTerminalResponse,
  SetTerminalSizeResponse,
  LoadSettingsResponse,
  GetSettingResponse,
  UpdateSettingResponse,
  LoadClaudeSettingsResponse,
  UpdateClaudeSettingsValueResponse,
  UpdateClaudeSettingsScopeResponse,
  ShowFileDialogResponse,
  ListProjectsResponse,
  ScanAllProjectsResponse,
  ScanClaudeMemoryResponse,
  ScanClaudeAgentsResponse,
  ScanClaudeCommandsResponse,
  ScanClaudeSkillsResponse,
  GetProjectResponse,
  LoadMarkdownContentResponse,
  UpdateMarkdownContentResponse,
  RenameMarkdownContentResponse,
  SaveMarkdownContentResponse,
  DeleteMarkdownContentResponse,
  ListSkillContentResponse,
  ReadSkillFileResponse,
  UpdateSkillFileResponse,
  DeleteSkillFileResponse,
  CreateSkillFileResponse,
  MoveSkillFileResponse,
  ScanMCPServersResponse,
  AddMCPServerResponse,
  UpdateMCPServerResponse,
  RenameMCPServerResponse,
  DeleteMCPServerResponse,
  EnableMCPServerResponse,
  DisableMCPServerResponse,
  UpdateEnableAllProjectMcpServersResponse,
  ScanLSPServersResponse,
  ScanClaudeHooksResponse,
  AddClaudeHookResponse,
  RemoveClaudeHookResponse,
  UpdateClaudeHookResponse,
  UpdateDisableAllHooksResponse,
  MCPInfo,
  ClaudeMemoryInfo,
  AgentInfo,
  CommandInfo,
  HooksInfo,
  SkillInfo,
  SkillFileTreeNode,
  LSPServerInfo,
  PluginMarketplaceInfo,
  PluginInfo,
  ProcessResult,
  ScanClaudePluginMarketplacesResponse,
  InstallClaudePluginMarketplaceResponse,
  ScanClaudePluginsResponse,
  InstallClaudePluginResponse,
  UninstallClaudePluginResponse,
  EnableClaudePluginResponse,
  DisableClaudePluginResponse,
  MoveClaudePluginResponse,
  ReadPluginReadmeResponse,
  ScanSessionsResponse,
  ReadSessionContentsResponse,
} from './types';

// 重新导出所有类型定义，供其他模块使用
export * from './types';

// ===== API 函数定义 =====

/**
 * 前端日志输出API
 * @param request 日志请求参数
 * @returns Promise<LogResponse>
 */
export const logToBackend = async (request: LogRequest): Promise<LogResponse> => {
  return await callAPI<LogData>('log', request);
};

/**
 * 创建新终端API
 * @param request 新终端请求参数
 * @returns Promise<NewTerminalResponse>
 */
export const createNewTerminal = async (
  request: NewTerminalRequest = {}
): Promise<NewTerminalResponse> => {
  return await callAPI<TerminalDTO>('new_terminal', request);
};

/**
 * 关闭终端API
 * @param request 关闭终端请求参数
 * @returns Promise<CloseTerminalResponse>
 */
export const closeTerminal = async (
  request: CloseTerminalRequest
): Promise<CloseTerminalResponse> => {
  return await callAPI<boolean>('close_terminal', request);
};

/**
 * 向终端写入数据API
 * @param request 写入终端请求参数
 * @returns Promise<WriteToTerminalResponse>
 */
export const writeToTerminal = async (
  request: WriteToTerminalRequest
): Promise<WriteToTerminalResponse> => {
  return await callAPI<boolean>('write_to_terminal', request);
};

/**
 * 设置终端大小API
 * @param request 设置终端大小请求参数
 * @returns Promise<SetTerminalSizeResponse>
 */
export const setTerminalSize = async (
  request: SetTerminalSizeRequest
): Promise<SetTerminalSizeResponse> => {
  return await callAPI<boolean>('set_terminal_size', request);
};

/**
 * 加载配置API
 * @param request 加载配置请求参数
 * @returns Promise<LoadSettingsResponse>
 */
export const loadSettings = async (
  request: LoadSettingsRequest = {}
): Promise<LoadSettingsResponse> => {
  return await callAPI<LoadSettingsData>('load_settings', request);
};

/**
 * 获取单个配置API
 * @param request 获取配置请求参数
 * @returns Promise<GetSettingResponse>
 */
export const getSetting = async (
  request: GetSettingRequest
): Promise<GetSettingResponse> => {
  return await callAPI<string>('get_setting', request);
};

/**
 * 更新配置API
 * @param request 更新配置请求参数
 * @returns Promise<UpdateSettingResponse>
 */
export const updateSetting = async (
  request: UpdateSettingRequest
): Promise<UpdateSettingResponse> => {
  return await callAPI<boolean>('update_setting', request);
};

/**
 * 加载指定项目的Claude设置API
 * @param request 扫描Claude设置请求参数
 * @returns Promise<LoadClaudeSettingsResponse>
 */
export const loadClaudeSettings = async (
  request: ScanClaudeSettingsRequest
): Promise<LoadClaudeSettingsResponse> => {
  return await callAPI<ClaudeSettingsInfoDTO>('scan_claude_settings', request);
};

/**
 * 更新指定项目的Claude设置值API
 * @param request 更新Claude设置值请求参数
 * @returns Promise<UpdateClaudeSettingsValueResponse>
 */
export const updateClaudeSettingsValue = async (
  request: UpdateClaudeSettingsValueRequest
): Promise<UpdateClaudeSettingsValueResponse> => {
  return await callAPI<boolean>('update_claude_settings_value', request);
};

/**
 * 更新指定项目的Claude设置作用域API
 * @param request 更新Claude设置作用域请求参数
 * @returns Promise<UpdateClaudeSettingsScopeResponse>
 */
export const updateClaudeSettingsScope = async (
  request: UpdateClaudeSettingsScopeRequest
): Promise<UpdateClaudeSettingsScopeResponse> => {
  return await callAPI<boolean>('update_claude_settings_scope', request);
};

/**
 * 显示文件选择对话框API
 * @param request 文件选择对话框请求参数
 * @returns Promise<ShowFileDialogResponse>
 */
export const showFileDialog = async (
  request: ShowFileDialogRequest
): Promise<ShowFileDialogResponse> => {
  return await callAPI<ShowFileDialogData>('show_file_dialog', request);
};

/**
 * 获取所有 Claude 项目列表API
 * @param request 获取项目列表请求参数
 * @returns Promise<ListProjectsResponse>
 */
export const listProjects = async (
  request: ListProjectsRequest = {}
): Promise<ListProjectsResponse> => {
  return await callAPI<AIProjectInDB[]>('list_projects', request);
};

/**
 * 扫描所有 Claude 项目API
 * @param request 扫描所有项目请求参数
 * @returns Promise<ScanAllProjectsResponse>
 */
export const scanAllProjects = async (
  request: ScanAllProjectsRequest = {}
): Promise<ScanAllProjectsResponse> => {
  return await callAPI<boolean>('scan_all_projects', request);
};

/**
 * 扫描指定项目的Claude Memory API
 * @param request 扫描Claude Memory请求参数
 * @returns Promise<ScanClaudeMemoryResponse>
 */
export const scanClaudeMemory = async (
  request: ScanClaudeMemoryRequest
): Promise<ScanClaudeMemoryResponse> => {
  return await callAPI<ClaudeMemoryInfo>('scan_claude_memory', request);
};

/**
 * 扫描指定项目的Claude Agents API
 * @param request 扫描Claude Agents请求参数
 * @returns Promise<ScanClaudeAgentsResponse>
 */
export const scanClaudeAgents = async (
  request: ScanClaudeAgentsRequest
): Promise<ScanClaudeAgentsResponse> => {
  return await callAPI<AgentInfo[]>('scan_claude_agents', request);
};

/**
 * 扫描指定项目的Claude Commands API
 * @param request 扫描Claude Commands请求参数
 * @returns Promise<ScanClaudeCommandsResponse>
 */
export const scanClaudeCommands = async (
  request: ScanClaudeCommandsRequest
): Promise<ScanClaudeCommandsResponse> => {
  return await callAPI<CommandInfo[]>('scan_claude_commands', request);
};

/**
 * 扫描指定项目的Claude Skills API
 * @param request 扫描Claude Skills请求参数
 * @returns Promise<ScanClaudeSkillsResponse>
 */
export const scanClaudeSkills = async (
  request: ScanClaudeSkillsRequest
): Promise<ScanClaudeSkillsResponse> => {
  return await callAPI<SkillInfo[]>('scan_claude_skills', request);
};

/**
 * 根据 ID 获取单个 Claude 项目API
 * @param request 获取项目请求参数
 * @returns Promise<GetProjectResponse>
 */
export const getProject = async (request: IDRequest): Promise<GetProjectResponse> => {
  return await callAPI<AIProjectInDB>('get_project', request);
};

/**
 * 收藏项目API
 * @param request 收藏项目请求参数
 * @returns Promise<ApiResponse<AIProjectInDB>>
 */
export const favoriteProject = async (
  request: IDRequest
): Promise<ApiResponse<AIProjectInDB>> => {
  return await callAPI<AIProjectInDB>('favorite_project', request);
};

/**
 * 取消收藏项目API
 * @param request 取消收藏项目请求参数
 * @returns Promise<ApiResponse<AIProjectInDB>>
 */
export const unfavoriteProject = async (
  request: IDRequest
): Promise<ApiResponse<AIProjectInDB>> => {
  return await callAPI<AIProjectInDB>('unfavorite_project', request);
};

/**
 * 永久删除项目API
 * @param request 删除项目请求参数
 * @returns Promise<ApiResponse<boolean>>
 */
export const deleteProject = async (
  request: IDRequest
): Promise<ApiResponse<boolean>> => {
  return await callAPI<boolean>('delete_project', request);
};

/**
 * 清理所有已移除项目API
 * @returns Promise<ApiResponse<boolean>>
 */
export const clearRemovedProjects = async (): Promise<ApiResponse<boolean>> => {
  return await callAPI<boolean>('clear_removed_projects', {});
};

/**
 * 加载指定项目Markdown内容API
 * @param request 加载Markdown内容请求参数
 * @returns Promise<LoadMarkdownContentResponse>
 */
export const loadClaudeMarkdownContent = async (
  request: LoadMarkdownContentRequest
): Promise<LoadMarkdownContentResponse> => {
  return await callAPI<MarkdownContentDTO>('load_claude_markdown_content', request);
};

/**
 * 更新指定项目Markdown内容API
 * @param request 更新Markdown内容请求参数
 * @returns Promise<UpdateMarkdownContentResponse>
 */
export const updateClaudeMarkdownContent = async (
  request: UpdateMarkdownContentRequest
): Promise<UpdateMarkdownContentResponse> => {
  return await callAPI<boolean>('update_claude_markdown_content', request);
};

/**
 * 重命名指定项目Markdown内容API
 * @param request 重命名Markdown内容请求参数
 * @returns Promise<RenameMarkdownContentResponse>
 */
export const renameClaudeMarkdownContent = async (
  request: RenameMarkdownContentRequest
): Promise<RenameMarkdownContentResponse> => {
  return await callAPI<boolean>('rename_claude_markdown_content', request);
};

/**
 * 保存（新增）指定项目Markdown内容API
 * @param request 保存Markdown内容请求参数
 * @returns Promise<SaveMarkdownContentResponse>
 */
export const saveClaudeMarkdownContent = async (
  request: SaveMarkdownContentRequest
): Promise<SaveMarkdownContentResponse> => {
  return await callAPI<MarkdownContentDTO>('save_claude_markdown_content', request);
};

/**
 * 删除指定项目Markdown内容API
 * @param request 删除Markdown内容请求参数
 * @returns Promise<DeleteMarkdownContentResponse>
 */
export const deleteClaudeMarkdownContent = async (
  request: DeleteMarkdownContentRequest
): Promise<DeleteMarkdownContentResponse> => {
  return await callAPI<boolean>('delete_claude_markdown_content', request);
};

// ===== Skill 文件管理 API =====

/**
 * 列出指定 Skill 的文件树结构API
 * @param request 列出 Skill 文件树请求参数
 * @returns Promise<ListSkillContentResponse>
 */
export const listSkillContent = async (
  request: ListSkillContentRequest
): Promise<ListSkillContentResponse> => {
  return await callAPI<SkillFileTreeNode[]>('list_skill_content', request);
};

/**
 * 读取指定 Skill 文件内容API
 * @param request 读取 Skill 文件内容请求参数
 * @returns Promise<ReadSkillFileResponse>
 */
export const readSkillFileContent = async (
  request: ReadSkillFileRequest
): Promise<ReadSkillFileResponse> => {
  return await callAPI<string>('read_skill_file_content', request);
};

/**
 * 更新指定 Skill 文件内容API
 * @param request 更新 Skill 文件内容请求参数
 * @returns Promise<UpdateSkillFileResponse>
 */
export const updateSkillFileContent = async (
  request: UpdateSkillFileRequest
): Promise<UpdateSkillFileResponse> => {
  return await callAPI<boolean>('update_skill_file_content', request);
};

/**
 * 删除指定 Skill 文件API
 * @param request 删除 Skill 文件请求参数
 * @returns Promise<DeleteSkillFileResponse>
 */
export const deleteSkillFile = async (
  request: DeleteSkillFileRequest
): Promise<DeleteSkillFileResponse> => {
  return await callAPI<boolean>('delete_skill_file', request);
};

/**
 * 创建 Skill 文件或文件夹API
 * @param request 创建 Skill 文件请求参数
 * @returns Promise<CreateSkillFileResponse>
 */
export const createSkillFile = async (
  request: CreateSkillFileRequest
): Promise<CreateSkillFileResponse> => {
  return await callAPI<boolean>('create_skill_file', request);
};

/**
 * 重命名 Skill 文件或文件夹API
 * @param request 重命名 Skill 文件请求参数
 * @returns Promise<RenameSkillFileResponse>
 */
export const renameSkillFile = async (
  request: RenameSkillFileRequest
): Promise<RenameSkillFileResponse> => {
  return await callAPI<boolean>('rename_skill_file', request);
};

/**
 * 移动 Skill 文件或文件夹API
 * @param request 移动 Skill 文件请求参数
 * @returns Promise<MoveSkillFileResponse>
 */
export const moveSkillFile = async (
  request: MoveSkillFileRequest
): Promise<MoveSkillFileResponse> => {
  return await callAPI<boolean>('move_skill_file', request);
};

// ===== MCP 服务器管理 API =====

/**
 * 扫描指定项目的MCP服务器配置API
 * @param request 扫描MCP服务器请求参数
 * @returns Promise<ScanMCPServersResponse>
 */
export const scanClaudeMCPServers = async (
  request: ScanMCPServersRequest
): Promise<ScanMCPServersResponse> => {
  return await callAPI<MCPInfo>('scan_claude_mcp_servers', request);
};

/**
 * 添加指定项目的MCP服务器API
 * @param request 添加MCP服务器请求参数
 * @returns Promise<AddMCPServerResponse>
 */
export const addClaudeMCPServer = async (
  request: AddMCPServerRequest
): Promise<AddMCPServerResponse> => {
  return await callAPI<boolean>('add_claude_mcp_server', request);
};

/**
 * 更新指定项目的MCP服务器API
 * @param request 更新MCP服务器请求参数
 * @returns Promise<UpdateMCPServerResponse>
 */
export const updateClaudeMCPServer = async (
  request: UpdateMCPServerRequest
): Promise<UpdateMCPServerResponse> => {
  return await callAPI<boolean>('update_claude_mcp_server', request);
};

/**
 * 删除指定项目的MCP服务器API
 * @param request 删除MCP服务器请求参数
 * @returns Promise<DeleteMCPServerResponse>
 */
export const deleteClaudeMCPServer = async (
  request: DeleteMCPServerRequest
): Promise<DeleteMCPServerResponse> => {
  return await callAPI<boolean>('delete_claude_mcp_server', request);
};

/**
 * 启用指定项目的MCP服务器API
 * @param request 启用MCP服务器请求参数
 * @returns Promise<EnableMCPServerResponse>
 */
export const enableClaudeMCPServer = async (
  request: EnableMCPServerRequest
): Promise<EnableMCPServerResponse> => {
  return await callAPI<boolean>('enable_claude_mcp_server', request);
};

/**
 * 禁用指定项目的MCP服务器API
 * @param request 禁用MCP服务器请求参数
 * @returns Promise<DisableMCPServerResponse>
 */
export const disableClaudeMCPServer = async (
  request: DisableMCPServerRequest
): Promise<DisableMCPServerResponse> => {
  return await callAPI<boolean>('disable_claude_mcp_server', request);
};

/**
 * 更新enableAllProjectMcpServers配置API
 * @param request 更新enableAllProjectMcpServers配置请求参数
 * @returns Promise<UpdateEnableAllProjectMcpServersResponse>
 */
export const updateEnableAllProjectMcpServers = async (
  request: UpdateEnableAllProjectMcpServersRequest
): Promise<UpdateEnableAllProjectMcpServersResponse> => {
  return await callAPI<boolean>('update_enable_all_project_mcp_servers', request);
};

/**
 * 重命名指定项目的MCP服务器API
 * @param request 重命名MCP服务器请求参数
 * @returns Promise<RenameMCPServerResponse>
 */
export const renameClaudeMCPServer = async (
  request: RenameMCPServerRequest
): Promise<RenameMCPServerResponse> => {
  return await callAPI<boolean>('rename_claude_mcp_server', request);
};

// ===== LSP 服务器管理 API =====

/**
 * 扫描指定项目的LSP服务器配置API
 * @param request 扫描LSP服务器请求参数
 * @returns Promise<ScanLSPServersResponse>
 */
export const scanClaudeLSPServers = async (
  request: ScanLSPServersRequest
): Promise<ScanLSPServersResponse> => {
  return await callAPI<LSPServerInfo[]>('scan_claude_lsp_servers', request);
};

// ===== Hooks 管理 API =====

/**
 * 扫描指定项目的Hooks配置API
 * @param request 扫描Hooks请求参数
 * @returns Promise<ScanClaudeHooksResponse>
 */
export const scanClaudeHooks = async (
  request: ScanClaudeHooksRequest
): Promise<ScanClaudeHooksResponse> => {
  return await callAPI<HooksInfo>('scan_claude_hooks', request);
};

/**
 * 添加指定项目的Hook API
 * @param request 添加Hook请求参数
 * @returns Promise<AddClaudeHookResponse>
 */
export const addClaudeHook = async (
  request: AddClaudeHookRequest
): Promise<AddClaudeHookResponse> => {
  return await callAPI<boolean>('add_claude_hook', request);
};

/**
 * 删除指定项目的Hook API
 * @param request 删除Hook请求参数
 * @returns Promise<RemoveClaudeHookResponse>
 */
export const removeClaudeHook = async (
  request: RemoveClaudeHookRequest
): Promise<RemoveClaudeHookResponse> => {
  return await callAPI<boolean>('remove_claude_hook', request);
};

/**
 * 更新指定项目的Hook API
 * @param request 更新Hook请求参数
 * @returns Promise<UpdateClaudeHookResponse>
 */
export const updateClaudeHook = async (
  request: UpdateClaudeHookRequest
): Promise<UpdateClaudeHookResponse> => {
  return await callAPI<boolean>('update_claude_hook', request);
};

/**
 * 更新disableAllHooks配置API
 * @param request 更新disableAllHooks配置请求参数
 * @returns Promise<UpdateDisableAllHooksResponse>
 */
export const updateDisableAllHooks = async (
  request: UpdateDisableAllHooksRequest
): Promise<UpdateDisableAllHooksResponse> => {
  return await callAPI<boolean>('update_disable_all_hooks', request);
};

// ===== Plugin Marketplace 管理 API =====

/**
 * 扫描Claude插件市场列表API
 * @param request 扫描Claude插件市场列表请求参数
 * @returns Promise<ScanClaudePluginMarketplacesResponse>
 */
export const scanClaudePluginMarketplaces = async (
  request: ScanClaudePluginMarketplacesRequest
): Promise<ScanClaudePluginMarketplacesResponse> => {
  return await callAPI<PluginMarketplaceInfo[]>(
    'scan_claude_plugin_marketplaces',
    request
  );
};

/**
 * 安装Claude插件市场API
 * @param request 安装Claude插件市场请求参数
 * @returns Promise<InstallClaudePluginMarketplaceResponse>
 */
export const installClaudePluginMarketplace = async (
  request: InstallClaudePluginMarketplaceRequest
): Promise<InstallClaudePluginMarketplaceResponse> => {
  return await callAPI<ProcessResult>('install_claude_plugin_marketplace', request);
};

/**
 * 扫描Claude插件列表API
 * @param request 扫描Claude插件列表请求参数
 * @returns Promise<ScanClaudePluginsResponse>
 */
export const scanClaudePlugins = async (
  request: ScanClaudePluginsRequest
): Promise<ScanClaudePluginsResponse> => {
  return await callAPI<PluginInfo[]>('scan_claude_plugins', request);
};

/**
 * 安装Claude插件API
 * @param request 安装插件请求参数
 * @returns Promise<InstallClaudePluginResponse>
 */
export const installClaudePlugin = async (
  request: InstallClaudePluginRequest
): Promise<InstallClaudePluginResponse> => {
  return await callAPI<ProcessResult>('install_claude_plugin', request);
};

/**
 * 卸载Claude插件API
 * @param request 卸载插件请求参数
 * @returns Promise<UninstallClaudePluginResponse>
 */
export const uninstallClaudePlugin = async (
  request: UninstallClaudePluginRequest
): Promise<UninstallClaudePluginResponse> => {
  return await callAPI<ProcessResult>('uninstall_claude_plugin', request);
};

/**
 * 启用Claude插件API
 * @param request 启用插件请求参数
 * @returns Promise<EnableClaudePluginResponse>
 */
export const enableClaudePlugin = async (
  request: EnableClaudePluginRequest
): Promise<EnableClaudePluginResponse> => {
  return await callAPI<boolean>('enable_claude_plugin', request);
};

/**
 * 禁用Claude插件API
 * @param request 禁用插件请求参数
 * @returns Promise<DisableClaudePluginResponse>
 */
export const disableClaudePlugin = async (
  request: DisableClaudePluginRequest
): Promise<DisableClaudePluginResponse> => {
  return await callAPI<boolean>('disable_claude_plugin', request);
};

/**
 * 移动Claude插件到新作用域API
 * @param request 移动插件请求参数
 * @returns Promise<MoveClaudePluginResponse>
 */
export const moveClaudePlugin = async (
  request: MoveClaudePluginRequest
): Promise<MoveClaudePluginResponse> => {
  return await callAPI<boolean>('move_claude_plugin', request);
};

/**
 * 读取指定插件README内容
 * @param request 请求参数
 * @returns Promise<ReadPluginReadmeResponse>
 */
export const readPluginReadme = async (
  request: ReadPluginReadmeRequest
): Promise<ReadPluginReadmeResponse> => {
  return await callAPI<string>('read_plugin_readme', request);
};

// ===== Session 管理 API =====

/**
 * 扫描指定项目的Sessions列表API
 * @param request 扫描Sessions列表请求参数
 * @returns Promise<ScanSessionsResponse>
 */
export const scanSessions = async (
  request: ScanSessionsRequest
): Promise<ScanSessionsResponse> => {
  return await callAPI<ClaudeSessionInfo[]>('scan_sessions', request);
};

/**
 * 读取指定Session的完整内容API
 * @param request 读取Session内容请求参数
 * @returns Promise<ReadSessionContentsResponse>
 */
export const readSessionContents = async (
  request: ReadSessionContentsRequest
): Promise<ReadSessionContentsResponse> => {
  return await callAPI<ClaudeSession>('read_session_contents', request);
};

// ===== 通用 API 调用方法 =====

/**
 * 通用 API 调用方法，自动选择 PyWebView 或 FastAPI 环境
 * @param endpointName API 端点名称（不包含 /api/ 前缀）
 * @param params 请求参数
 * @param dataType 响应数据类型
 * @returns Promise<ApiResponse<T>>
 */
const callAPI = async <T = any>(
  endpointName: string,
  params?: any
): Promise<ApiResponse<T>> => {
  if (is_pywebview()) {
    return await callPyWebviewAPI<T>(endpointName, params);
  } else {
    return await callFastAPI<T>(endpointName, params);
  }
};

/**
 * pywebview 环境专用 API 调用方法
 * 只处理 pywebview 环境下的逻辑，不包含开发环境的模拟逻辑
 * @param functionName API 函数名
 * @param params 参数对象
 * @returns Promise<ApiResponse<T>>
 */
export const callPyWebviewAPI = async <T = any>(
  functionName: string,
  params?: any
): Promise<ApiResponse<T>> => {
  try {
    const api = get_pywebview_api();

    // 等待 pywebview API 就绪
    await new Promise(resolve => setTimeout(resolve, 100));

    log.info(`Calling pywebview.api.${functionName}`, 'api');

    if (api && typeof api[functionName] === 'function') {
      const response = await api[functionName](params);
      log.debug(`API Response: ${JSON.stringify(response)}`, 'api');
      return response;
    } else {
      log.error(`${functionName} function not found in pywebview.api`, 'api');
      throw new Error(`${functionName} function not found in pywebview.api`);
    }
  } catch (error) {
    log.error(
      `API call error: ${error instanceof Error ? error.message : '未知错误'}`,
      'api'
    );
    return {
      code: 1,
      success: false,
      error: error instanceof Error ? error.message : '未知错误',
    };
  }
};

/**
 * FastAPI 环境专用 API 调用方法
 * 处理 FastAPI HTTP 请求
 * @param functionName API 函数名
 * @param params 参数对象
 * @returns Promise<ApiResponse<T>>
 */
export const callFastAPI = async <T = any>(
  functionName: string,
  params?: any
): Promise<ApiResponse<T>> => {
  try {
    const API_BASE_URL = 'http://127.0.0.1:8000';
    const endpoint = `/api/${functionName}`;
    const url = `${API_BASE_URL}${endpoint}`;

    log.info(`Calling FastAPI ${url} with params: ${JSON.stringify(params)}`, 'api');

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: params ? JSON.stringify(params) : '{}',
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result: ApiResponse<T> = await response.json();
    log.debug(`FastAPI Response: ${JSON.stringify(result)}`, 'api');
    return result;
  } catch (error) {
    log.error(
      `FastAPI call error: ${error instanceof Error ? error.message : '未知错误'}`,
      'api'
    );
    return {
      code: 1,
      success: false,
      error: error instanceof Error ? error.message : '未知错误',
    };
  }
};
