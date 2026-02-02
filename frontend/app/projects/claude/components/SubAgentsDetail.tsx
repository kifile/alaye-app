import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { Bot, Plus, ExternalLink } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useDetailHeader } from '../context/DetailHeaderContext';
import { EmptyView } from '@/components/EmptyView';
import { ClaudeToolSelectBar, ToolGroup } from './ClaudeToolSelectBar';
import { SubAgentContentView } from './SubAgentContentView';
import { scanClaudeAgents, saveClaudeMarkdownContent } from '@/api/api';
import { ConfigScope, AgentInfo } from '@/api/types';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';

// 分组函数：按照 scope + pluginName 分组
function groupAgentsByScope(
  agents: AgentInfo[],
  t: (key: string, params?: Record<string, string | number>) => string
): ToolGroup[] {
  const scopeOrder: ConfigScope[] = [
    ConfigScope.LOCAL,
    ConfigScope.PROJECT,
    ConfigScope.USER,
    ConfigScope.PLUGIN,
  ];
  const groups: ToolGroup[] = [];

  // 非插件 scope 的分组
  for (const scope of scopeOrder) {
    if (scope === ConfigScope.PLUGIN) continue; // 插件单独处理

    const items = agents
      .filter(agent => agent.scope === scope)
      .map(agent => ({
        name: agent.name,
        scope: agent.scope,
        description: agent.description,
      }));

    if (items.length > 0) {
      groups.push({
        label: t(`toolSelectBar.groups.${scope}`),
        items,
      });
    }
  }

  // 插件 scope：按 pluginName 分组
  const pluginAgents = agents.filter(agent => agent.scope === ConfigScope.PLUGIN);
  const pluginsMap = new Map<string, AgentInfo[]>();

  pluginAgents.forEach(agent => {
    const pluginName = agent.plugin_name || 'Unknown';
    if (!pluginsMap.has(pluginName)) {
      pluginsMap.set(pluginName, []);
    }
    pluginsMap.get(pluginName)!.push(agent);
  });

  // 按插件名称排序后添加分组
  Array.from(pluginsMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .forEach(([pluginName, agents]) => {
      groups.push({
        label: t('toolSelectBar.groups.plugin', { name: pluginName }),
        items: agents.map(agent => ({
          name: agent.name,
          scope: agent.scope,
          description: agent.description,
          pluginName,
        })),
      });
    });

  return groups;
}

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

type ViewMode = 'select' | 'edit';

interface SubAgentsDetailProps {
  projectId: number;
}

export function SubAgentsDetail({ projectId }: SubAgentsDetailProps) {
  const { t } = useTranslation('projects');
  const router = useRouter();
  const searchParams = useSearchParams();
  const { scopeSwitcher, setScopeSwitcher, clearScopeSwitcher } = useDetailHeader();

  // 视图模式
  const [viewMode, setViewMode] = useState<ViewMode>('select');

  // Popover 控制状态
  const [newPopoverOpen, setNewPopoverOpen] = useState<boolean>(false);

  // 选中的代理
  const [selectedAgent, setSelectedAgent] = useState<{
    name: string;
    scope?: ConfigScope;
  } | null>(null);

  // 列表状态
  const [agentsList, setAgentsList] = useState<AgentInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isInitialLoaded, setIsInitialLoaded] = useState(true);

  // 当前作用域
  const [currentScope, setCurrentScope] = useState<ConfigScope | 'mixed' | null>(null);

  // 获取当前选中的代理配置
  const currentAgent = useMemo(() => {
    if (!selectedAgent) return null;
    return agentsList.find(
      agent =>
        agent.name === selectedAgent.name &&
        (!selectedAgent.scope || agent.scope === selectedAgent.scope)
    );
  }, [selectedAgent, agentsList]);

  // 分组后的 agents 列表
  const groupedAgents = useMemo(() => {
    return groupAgentsByScope(agentsList, t);
  }, [agentsList, t]);

  // 扫描代理列表
  const scanAgentsList = useCallback(
    async (keepSelection?: { name: string; scope?: ConfigScope }) => {
      if (!isInitialLoaded) {
        setIsLoading(true);
      }

      try {
        const scopeParam =
          currentScope === 'mixed' || currentScope === null ? undefined : currentScope;
        const response = await scanClaudeAgents({
          project_id: projectId,
          scope: scopeParam,
        });

        if (response.success && response.data) {
          setAgentsList(response.data);

          // 如果列表为空，切换到选择模式
          if (response.data.length === 0) {
            setSelectedAgent(null);
            setViewMode('select');
          } else {
            // 优先使用 keepSelection 参数（用于重命名场景）
            const targetAgent = keepSelection || selectedAgent;

            // 检查目标代理是否还在列表中
            const stillExists =
              targetAgent &&
              response.data.some(
                agent =>
                  agent.name === targetAgent.name && agent.scope === targetAgent.scope
              );

            if (stillExists) {
              // 目标代理还在列表中，保持选中
              if (keepSelection) {
                setSelectedAgent(keepSelection);
              }
              setViewMode('edit');
            } else {
              // 目标代理不在列表中，选中第一个
              const firstAgent = response.data[0];
              setSelectedAgent({
                name: firstAgent.name,
                scope: firstAgent.scope,
              });
              setViewMode('edit');
            }
          }
        }
      } catch (error) {
        console.error(t('subAgents.scanFailed') + ':', error);
      } finally {
        setIsLoading(false);
        setIsInitialLoaded(true);
      }
    },
    [projectId, currentScope, t, selectedAgent, isInitialLoaded]
  );

  // 组件加载时获取数据
  useEffect(() => {
    if (projectId && !isInitialLoaded) {
      scanAgentsList();
    }
  }, [projectId, isInitialLoaded, scanAgentsList]);

  // 当 scope 变化时重新加载（不显示 loading）
  useEffect(() => {
    if (projectId && isInitialLoaded) {
      scanAgentsList();
    }
  }, [currentScope, projectId, isInitialLoaded, scanAgentsList]);

  // 配置 DetailHeader 的 scopeSwitcher
  useEffect(() => {
    setScopeSwitcher({
      enabled: true,
      supportedScopes: ['mixed', 'project', 'user', 'plugin'] as ConfigScope[],
      value: currentScope,
      onChange: setCurrentScope,
    });

    return () => {
      clearScopeSwitcher();
    };
  }, [setScopeSwitcher, clearScopeSwitcher, currentScope]);

  // 选择代理 - 切换到编辑模式
  const handleSelectAgent = useCallback((agent: AgentInfo) => {
    setSelectedAgent({ name: agent.name, scope: agent.scope });
    setViewMode('edit');
  }, []);

  // 新建 agent - 通过 Popover 创建空 agent
  const handleCreateAgent = useCallback(
    async (name: string, scope: ConfigScope) => {
      try {
        const response = await saveClaudeMarkdownContent({
          project_id: projectId,
          content_type: 'agent',
          name: name.trim(),
          content: '', // 内容为空
          scope,
        });

        if (response.success) {
          toast.success(t('subAgents.createSuccess'), {
            description: t('subAgents.createSuccessDesc', { name }),
          });
          // 关闭 Popover
          setNewPopoverOpen(false);
          // 选中新建的 agent 并切换到编辑模式
          setSelectedAgent({ name: name.trim(), scope });
          setViewMode('edit');
          // 重新扫描列表
          scanAgentsList({ name: name.trim(), scope });
        } else {
          toast.error(t('subAgents.createFailed'), {
            description: response.error || t('unknownError'),
          });
        }
      } catch (error) {
        console.error('Create agent error:', error);
        toast.error(t('subAgents.createFailed'), {
          description: error instanceof Error ? error.message : t('networkError'),
        });
      }
    },
    [projectId, t, scanAgentsList]
  );

  // 代理删除完成 - 切换到选择模式
  const handleAgentDeleted = useCallback(() => {
    setSelectedAgent(null);
    setViewMode('select');
    // 重新扫描列表
    scanAgentsList();
  }, [scanAgentsList]);

  // 代理重命名完成 - 更新选中的代理
  const handleAgentRenamed = useCallback(
    (newName: string, newScope?: ConfigScope) => {
      // 重新扫描列表，并保持选中重命名后的代理
      scanAgentsList({ name: newName, scope: newScope });
    },
    [scanAgentsList]
  );

  // 跳转到插件页面
  const handleGoToPlugins = useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('section', 'plugins');
    router.push(`?${params.toString()}`);
  }, [router, searchParams]);

  // 打开新建 Popover
  const handleOpenNewPopover = useCallback(() => {
    setNewPopoverOpen(true);
  }, []);

  // 处理 Popover 状态变化
  const handlePopoverOpenChange = useCallback((open: boolean) => {
    setNewPopoverOpen(open);
  }, []);

  // 根据视图模式渲染不同内容
  return (
    <div className='p-4 flex flex-col h-full'>
      {/* 加载状态 */}
      {isLoading && <LoadingState message={t('subAgents.loading')} />}

      {/* 视图内容 */}
      {!isLoading && (
        <>
          {viewMode === 'edit' && selectedAgent && currentAgent && (
            <>
              {/* 代理选择器 */}
              <div className='mb-4 flex-shrink-0'>
                <ClaudeToolSelectBar
                  groups={groupedAgents}
                  selectedItem={selectedAgent}
                  onSelectItem={handleSelectAgent}
                  onRefresh={() => selectedAgent && scanAgentsList(selectedAgent)}
                  onCreateItem={handleCreateAgent}
                  newPopoverOpen={newPopoverOpen}
                  onPopoverOpenChange={handlePopoverOpenChange}
                />
              </div>

              {/* 编辑代理内容 */}
              <div className='flex-1 min-h-0'>
                <SubAgentContentView
                  projectId={projectId}
                  selectedAgent={selectedAgent}
                  currentAgent={currentAgent}
                  onDeleted={handleAgentDeleted}
                  onRenamed={handleAgentRenamed}
                />
              </div>
            </>
          )}

          {viewMode === 'select' && (
            <>
              {/* 代理选择器 */}
              <div className='mb-4'>
                <ClaudeToolSelectBar
                  groups={groupedAgents}
                  selectedItem={selectedAgent}
                  onSelectItem={handleSelectAgent}
                  onRefresh={() => selectedAgent && scanAgentsList(selectedAgent)}
                  onCreateItem={handleCreateAgent}
                  newPopoverOpen={newPopoverOpen}
                  onPopoverOpenChange={handlePopoverOpenChange}
                />
              </div>

              {/* 提示用户选择代理 */}
              {currentScope === 'plugin' ? (
                <EmptyView
                  icon={<Bot />}
                  title={t('subAgents.pluginScopeTitle')}
                  description={t('subAgents.pluginScopeDesc')}
                  actionLabel={t('subAgents.goToPlugins')}
                  onAction={handleGoToPlugins}
                  actionIcon={<ExternalLink className='h-4 w-4' />}
                />
              ) : (
                <EmptyView
                  icon={<Bot />}
                  title={t('subAgents.noSelection')}
                  description={t('subAgents.noSelectionDesc')}
                  actionLabel={t('subAgents.createNew')}
                  onAction={handleOpenNewPopover}
                  actionIcon={<Plus className='h-4 w-4' />}
                />
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
