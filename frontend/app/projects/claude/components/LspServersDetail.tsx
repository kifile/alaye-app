import { useState, useEffect, useCallback, useMemo } from 'react';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { LspServerItem } from './LspServerItem';
import { Search } from 'lucide-react';
import { useDetailHeader } from '../context/DetailHeaderContext';
import { scanClaudeLSPServers } from '@/api/api';
import { LSPServerInfo, ConfigScope } from '@/api/types';
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
}: {
  searchQuery: string;
  onSearchChange: (value: string) => void;
}) {
  const { t } = useTranslation('projects');

  return (
    <div className='flex items-center gap-3 flex-wrap'>
      {/* 搜索框 */}
      <div className='flex-1 min-w-[200px] relative'>
        <Search className='w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none' />
        <Input
          placeholder={t('lspServers.filter.searchPlaceholder')}
          value={searchQuery}
          onChange={e => onSearchChange(e.target.value)}
          className='max-w-md pl-9'
        />
      </div>
    </div>
  );
}

interface LspServersDetailProps {
  projectId: number;
}

export function LspServersDetail({ projectId }: LspServersDetailProps) {
  const { t } = useTranslation('projects');
  const { setScopeSwitcher, clearScopeSwitcher } = useDetailHeader();

  const [servers, setServers] = useState<LSPServerInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isInitialLoaded, setIsInitialLoaded] = useState(false);
  const [currentScope, setCurrentScope] = useState<ConfigScope | 'mixed' | null>(
    ConfigScope.PLUGIN
  );
  const [searchQuery, setSearchQuery] = useState('');

  // 加载 LSP 服务器配置
  const loadLspServers = useCallback(
    async (scope?: ConfigScope | null, showLoading = false) => {
      if (showLoading) {
        setIsLoading(true);
      }
      try {
        const scopeParam = scope === null ? undefined : scope;
        const response = await scanClaudeLSPServers({
          project_id: projectId,
          scope: scopeParam,
        });

        if (response.success && response.data) {
          setServers(response.data || []);
        } else {
          console.warn('加载 LSP 服务器配置失败或无数据:', response.error);
          setServers([]);
        }
      } catch (error) {
        console.error('加载 LSP 服务器配置失败:', error);
        toast.error(t('lspServers.loadConfigFailed'));
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
      // LSP 只支持 PLUGIN 作用域，忽略 'mixed' 和 null
      const scope =
        currentScope === 'mixed' || currentScope === null
          ? ConfigScope.PLUGIN
          : currentScope;
      loadLspServers(scope, true);
    }
  }, [projectId, isInitialLoaded, currentScope, loadLspServers]);

  // 配置 DetailHeader 的 scopeSwitcher - LSP 只支持 plugin 作用域
  useEffect(() => {
    setScopeSwitcher({
      enabled: false,
      supportedScopes: [ConfigScope.PLUGIN],
      value: currentScope,
      onChange: setCurrentScope,
    });

    return () => {
      clearScopeSwitcher();
    };
  }, [setScopeSwitcher, clearScopeSwitcher, currentScope]);

  // 过滤服务器列表
  const filteredServers = useMemo(() => {
    if (!searchQuery) return servers;

    const query = searchQuery.toLowerCase();
    return servers.filter(server => {
      const nameMatch = server.name.toLowerCase().includes(query);
      const pluginMatch = server.plugin_name?.toLowerCase().includes(query);
      const marketplaceMatch = server.marketplace_name?.toLowerCase().includes(query);
      const commandMatch = server.lspServer.command.toLowerCase().includes(query);

      return nameMatch || pluginMatch || marketplaceMatch || commandMatch;
    });
  }, [servers, searchQuery]);

  return (
    <div className='p-4'>
      <div className='space-y-4'>
        {/* 加载状态 */}
        {isLoading ? (
          <LoadingState message={t('lspServers.loading')} />
        ) : (
          <>
            {/* Filter 区域 */}
            <FilterBar searchQuery={searchQuery} onSearchChange={setSearchQuery} />

            {/* 服务器列表 */}
            {filteredServers.length > 0 ? (
              filteredServers.map(serverInfo => (
                <LspServerItem
                  key={`${serverInfo.scope}-${serverInfo.name}`}
                  serverInfo={serverInfo}
                />
              ))
            ) : (
              <EmptyView
                icon={<Search className='w-12 h-12' />}
                title={t('lspServers.noServers')}
                description={
                  searchQuery
                    ? t('lspServers.noSearchResults')
                    : t('lspServers.noServersDesc')
                }
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
