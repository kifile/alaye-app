import { useState, useEffect, useMemo, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { McpServerItem } from './McpServerItem';
import { McpServerDialog } from './McpServerDialog';
import { Plus, Search } from 'lucide-react';
import { useDetailHeader } from '../context/DetailHeaderContext';
import {
  addClaudeMCPServer,
  updateClaudeMCPServer,
  deleteClaudeMCPServer,
  renameClaudeMCPServer,
  scanClaudeMCPServers,
  enableClaudeMCPServer,
  disableClaudeMCPServer,
  updateEnableAllProjectMcpServers,
} from '@/api/api';
import { MCPServerInfo, MCPServer, ConfigScope } from '@/api/types';
import { ConfigScope as ConfigScopeEnum } from '@/api/types';
import { EmptyView } from '@/components/EmptyView';
import { useTranslation } from 'react-i18next';

// 加载状态组件
function LoadingState({ message }: { message: string }) {
  return (
    <div className='flex items-center justify-center py-16'>
      <div className='text-center space-y-4'>
        <div className='w-8 h-8 mx-auto border-2 border-blue-600 border-t-transparent rounded-full animate-spin'></div>
        <p className='text-muted-foreground'>{message}</p>
      </div>
    </div>
  );
}

// 过滤栏组件
function FilterBar({
  searchQuery,
  onSearchChange,
  enableAll,
  onToggleEnableAll,
  onAdd,
  isProcessing,
  isLoading,
}: {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  enableAll: boolean | undefined;
  onToggleEnableAll: (checked: boolean) => void;
  onAdd: () => void;
  isProcessing: boolean;
  isLoading: boolean;
}) {
  const { t } = useTranslation('projects');

  return (
    <div className='flex items-center gap-3 flex-wrap'>
      {/* 搜索框 */}
      <div className='flex-1 min-w-[200px] relative'>
        <Search className='w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none' />
        <Input
          placeholder={t('mcpServers.filter.searchPlaceholder')}
          value={searchQuery}
          onChange={e => onSearchChange(e.target.value)}
          className='max-w-md pl-9'
        />
      </div>

      {/* 启用所有项目 MCP 服务器开关 */}
      <div className='flex items-center gap-2'>
        <span className='text-sm text-muted-foreground'>
          {t('mcpServers.enableAllLabel')}
        </span>
        <Switch
          checked={enableAll ?? false}
          onCheckedChange={onToggleEnableAll}
          disabled={isProcessing || isLoading}
        />
      </div>

      {/* 添加新服务器按钮 */}
      <Button onClick={onAdd} disabled={isProcessing} variant='outline'>
        <Plus className='w-4 h-4 mr-2' />
        {t('mcpServers.addServer')}
      </Button>
    </div>
  );
}

interface McpServersDetailProps {
  projectId: number;
}

export function McpServersDetail({ projectId }: McpServersDetailProps) {
  const { t } = useTranslation('projects');
  const { scopeSwitcher, setScopeSwitcher, clearScopeSwitcher } = useDetailHeader();

  const [isProcessing, setIsProcessing] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingServer, setEditingServer] = useState<MCPServerInfo | null>(null);
  const [servers, setServers] = useState<MCPServerInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isInitialLoaded, setIsInitialLoaded] = useState(false);
  const [enableAllProjectMcpServers, setEnableAllProjectMcpServers] = useState<
    boolean | undefined
  >(undefined);
  const [currentScope, setCurrentScope] = useState<ConfigScope | 'mixed' | null>(
    'mixed'
  );
  const [searchQuery, setSearchQuery] = useState('');

  // 加载 MCP 服务器配置
  const loadMcpServers = useCallback(
    async (scope?: ConfigScope | 'mixed' | null, showLoading = false) => {
      if (showLoading) {
        setIsLoading(true);
      }
      try {
        const scopeParam = scope === 'mixed' || scope === null ? null : scope;
        const response = await scanClaudeMCPServers({
          project_id: projectId,
          scope: scopeParam,
        });

        if (response.success && response.data) {
          setServers(response.data.servers || []);
          if (response.data.enable_all_project_mcp_servers?.value !== undefined) {
            setEnableAllProjectMcpServers(
              response.data.enable_all_project_mcp_servers.value
            );
          }
        } else {
          console.warn('加载 MCP 服务器配置失败或无数据:', response.error);
          setServers([]);
        }
      } catch (error) {
        console.error('加载 MCP 服务器配置失败:', error);
        toast.error(t('mcpServers.loadConfigFailed'));
        setServers([]);
      } finally {
        setIsLoading(false);
        setIsInitialLoaded(true);
      }
    },
    [projectId, t]
  );

  // 组件加载时获取数据
  useEffect(() => {
    if (projectId && !isInitialLoaded) {
      loadMcpServers(currentScope, true);
    }
  }, [projectId, isInitialLoaded, currentScope, loadMcpServers]);

  // 当 scope 变化时重新加载（不显示 loading）
  useEffect(() => {
    if (projectId && isInitialLoaded) {
      loadMcpServers(currentScope, false);
    }
  }, [currentScope, projectId, isInitialLoaded, loadMcpServers]);

  // 配置 DetailHeader 的 scopeSwitcher
  useEffect(() => {
    setScopeSwitcher({
      enabled: true,
      supportedScopes: [
        'mixed',
        ConfigScope.USER,
        ConfigScope.PROJECT,
        ConfigScope.LOCAL,
        ConfigScope.PLUGIN,
      ],
      value: currentScope,
      onChange: setCurrentScope,
    });

    return () => {
      clearScopeSwitcher();
    };
  }, [setScopeSwitcher, clearScopeSwitcher, currentScope]);

  // 提取错误处理逻辑
  const handleError = useCallback((error: any, defaultErrorMessage: string) => {
    console.error(defaultErrorMessage, error);
    const errorMessage = error?.error || error?.message || defaultErrorMessage;
    toast.error(errorMessage);
  }, []);

  // 添加服务器
  const handleAddServer = useCallback(
    async (serverData: { name: string; server: MCPServer; scope?: ConfigScope }) => {
      setIsProcessing(true);
      try {
        await addClaudeMCPServer({
          project_id: projectId,
          name: serverData.name,
          server: serverData.server,
          scope: serverData.scope || ConfigScopeEnum.PROJECT,
        });

        toast.success(t('mcpServers.addSuccess'));
        await loadMcpServers(currentScope, false);
      } catch (error: any) {
        const errorMessage =
          error?.error || error?.message || t('mcpServers.addFailed');
        if (errorMessage.includes('已存在')) {
          toast.error(t('mcpServers.alreadyExists', { name: serverData.name }));
        } else {
          handleError(error, t('mcpServers.addFailed'));
        }
      } finally {
        setIsProcessing(false);
      }
    },
    [projectId, currentScope, loadMcpServers, t, handleError]
  );

  // 更新服务器
  const handleUpdateServer = useCallback(
    async (serverData: { name: string; server: MCPServer; scope?: ConfigScope }) => {
      if (!editingServer) return;

      setIsProcessing(true);
      try {
        await updateClaudeMCPServer({
          project_id: projectId,
          name: editingServer.name,
          server: serverData.server,
          scope: editingServer.scope,
        });

        toast.success(t('mcpServers.updateSuccess'));
        await loadMcpServers(currentScope, false);
      } catch (error: any) {
        handleError(error, t('mcpServers.updateFailed'));
      } finally {
        setIsProcessing(false);
      }
    },
    [editingServer, projectId, currentScope, loadMcpServers, t, handleError]
  );

  // 删除服务器
  const handleDeleteServer = useCallback(
    async (serverName: string, scope: ConfigScope) => {
      setIsProcessing(true);
      try {
        await deleteClaudeMCPServer({
          project_id: projectId,
          name: serverName,
          scope,
        });

        toast.success(t('mcpServers.deleteSuccess'));
        await loadMcpServers(currentScope, false);
      } catch (error: any) {
        handleError(error, t('mcpServers.deleteFailed'));
      } finally {
        setIsProcessing(false);
      }
    },
    [projectId, currentScope, loadMcpServers, t, handleError]
  );

  // 编辑服务器
  const handleEditServer = useCallback((serverInfo: MCPServerInfo) => {
    setEditingServer(serverInfo);
    setDialogOpen(true);
  }, []);

  // 添加新服务器
  const handleAddNew = useCallback(() => {
    setEditingServer(null);
    setDialogOpen(true);
  }, []);

  // 切换服务器启用状态
  const handleToggleServerEnable = useCallback(
    async (serverName: string, scope: ConfigScope, enabled: boolean) => {
      const serverInfo = servers.find(s => s.name === serverName && s.scope === scope);
      if (!serverInfo) return;

      setIsProcessing(true);
      try {
        if (enabled) {
          await enableClaudeMCPServer({ project_id: projectId, name: serverName });
          toast.success(t('mcpServers.enabled', { name: serverName }));
        } else {
          await disableClaudeMCPServer({ project_id: projectId, name: serverName });
          toast.success(t('mcpServers.disabled', { name: serverName }));
        }

        await loadMcpServers(currentScope, false);
      } catch (error: any) {
        handleError(error, t('mcpServers.toggleFailed'));
      } finally {
        setIsProcessing(false);
      }
    },
    [servers, projectId, currentScope, loadMcpServers, t, handleError]
  );

  // 切换所有项目 MCP 服务器启用状态
  const handleToggleEnableAll = useCallback(
    async (checked: boolean) => {
      setIsProcessing(true);
      try {
        await updateEnableAllProjectMcpServers({
          project_id: projectId,
          value: checked,
        });

        toast.success(
          checked ? t('mcpServers.enableAllSuccess') : t('mcpServers.disableAllSuccess')
        );

        setEnableAllProjectMcpServers(checked);
        await loadMcpServers(currentScope, false);
      } catch (error: any) {
        handleError(error, t('mcpServers.toggleAllFailed'));
        setEnableAllProjectMcpServers(!checked);
      } finally {
        setIsProcessing(false);
      }
    },
    [projectId, currentScope, loadMcpServers, t, handleError]
  );

  // 处理 MCP 服务器作用域变更
  const handleScopeChange = useCallback(
    async (oldScope: string, newScope: string) => {
      const serverInfo = servers.find(s => s.scope === oldScope);
      if (!serverInfo) return;

      setIsProcessing(true);
      try {
        await renameClaudeMCPServer({
          project_id: projectId,
          old_name: serverInfo.name,
          new_name: serverInfo.name,
          old_scope: oldScope as ConfigScope,
          new_scope: newScope as ConfigScope,
        });

        toast.success(t('mcpServers.scopeChangeSuccess'));
        await loadMcpServers(currentScope, false);
      } catch (error: any) {
        handleError(error, t('mcpServers.scopeChangeFailed'));
      } finally {
        setIsProcessing(false);
      }
    },
    [servers, projectId, currentScope, loadMcpServers, t, handleError]
  );

  // 过滤服务器列表
  const filteredServers = useMemo(() => {
    if (!searchQuery) return servers;

    const query = searchQuery.toLowerCase();
    return servers.filter(server => server.name.toLowerCase().includes(query));
  }, [servers, searchQuery]);

  return (
    <div className='p-4'>
      <div className='space-y-4'>
        {/* 加载状态 */}
        {isLoading ? (
          <LoadingState message={t('mcpServers.loading')} />
        ) : (
          <>
            {/* Filter 区域 */}
            <FilterBar
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              enableAll={enableAllProjectMcpServers}
              onToggleEnableAll={handleToggleEnableAll}
              onAdd={handleAddNew}
              isProcessing={isProcessing}
              isLoading={isLoading}
            />

            {/* 服务器列表 */}
            {filteredServers.length > 0 ? (
              filteredServers.map(serverInfo => (
                <McpServerItem
                  key={`${serverInfo.scope}-${serverInfo.name}`}
                  serverInfo={serverInfo}
                  onEdit={() => handleEditServer(serverInfo)}
                  onDelete={() => handleDeleteServer(serverInfo.name, serverInfo.scope)}
                  onToggleEnable={enabled =>
                    handleToggleServerEnable(serverInfo.name, serverInfo.scope, enabled)
                  }
                  onScopeChange={handleScopeChange}
                  isProcessing={isProcessing}
                />
              ))
            ) : (
              <EmptyView
                icon={<Plus />}
                title={t('mcpServers.noServers')}
                description={t('mcpServers.noServersDesc')}
                actionLabel={t('mcpServers.addFirstServer')}
                onAction={handleAddNew}
                actionDisabled={isProcessing}
                actionIcon={<Plus className='w-5 h-5 mr-2' />}
              />
            )}
          </>
        )}
      </div>

      {/* 编辑对话框 */}
      <McpServerDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        serverInfo={editingServer}
        onSave={editingServer ? handleUpdateServer : handleAddServer}
        isProcessing={isProcessing}
        currentScope={currentScope}
      />
    </div>
  );
}
