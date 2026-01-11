import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { Terminal, Plus, ExternalLink } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useDetailHeader } from '../context/DetailHeaderContext';
import { EmptyView } from '@/components/EmptyView';
import { ClaudeToolSelectBar, ToolGroup } from './ClaudeToolSelectBar';
import { CommandContentView } from './CommandContentView';
import { NewCommandContentView } from './NewCommandContentView';
import { scanClaudeCommands } from '@/api/api';
import { ConfigScope, CommandInfo } from '@/api/types';
import { useTranslation } from 'react-i18next';

// 分组函数：按照 scope + pluginName 分组
function groupCommandsByScope(
  commands: CommandInfo[],
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

    const items = commands
      .filter(cmd => cmd.scope === scope)
      .map(cmd => ({
        name: cmd.name,
        scope: cmd.scope,
        description: cmd.description,
      }));

    if (items.length > 0) {
      groups.push({
        label: t(`toolSelectBar.groups.${scope}`),
        items,
      });
    }
  }

  // 插件 scope：按 pluginName 分组
  const pluginCommands = commands.filter(cmd => cmd.scope === ConfigScope.PLUGIN);
  const pluginsMap = new Map<string, CommandInfo[]>();

  pluginCommands.forEach(cmd => {
    const pluginName = cmd.plugin_name || 'Unknown';
    if (!pluginsMap.has(pluginName)) {
      pluginsMap.set(pluginName, []);
    }
    pluginsMap.get(pluginName)!.push(cmd);
  });

  // 按插件名称排序后添加分组
  Array.from(pluginsMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .forEach(([pluginName, cmds]) => {
      groups.push({
        label: t('toolSelectBar.groups.plugin', { name: pluginName }),
        items: cmds.map(cmd => ({
          name: cmd.name,
          scope: cmd.scope,
          description: cmd.description,
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

type ViewMode = 'select' | 'new' | 'edit';

interface CommandsDetailProps {
  projectId: number;
}

export function CommandsDetail({ projectId }: CommandsDetailProps) {
  const { t } = useTranslation('projects');
  const router = useRouter();
  const searchParams = useSearchParams();
  const { scopeSwitcher, setScopeSwitcher, clearScopeSwitcher } = useDetailHeader();

  // 视图模式
  const [viewMode, setViewMode] = useState<ViewMode>('select');

  // 选中的命令
  const [selectedCommand, setSelectedCommand] = useState<{
    name: string;
    scope?: ConfigScope;
  } | null>(null);

  // 列表状态
  const [commandsList, setCommandsList] = useState<CommandInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isInitialLoaded, setIsInitialLoaded] = useState(true);

  // 当前作用域
  const [currentScope, setCurrentScope] = useState<ConfigScope | 'mixed' | null>(
    'mixed'
  );

  // 获取当前选中的命令配置
  const currentCommand = useMemo(() => {
    if (!selectedCommand) return null;
    return commandsList.find(
      cmd =>
        cmd.name === selectedCommand.name &&
        (!selectedCommand.scope || cmd.scope === selectedCommand.scope)
    );
  }, [selectedCommand, commandsList]);

  // 分组后的命令列表
  const groupedCommands = useMemo(() => {
    return groupCommandsByScope(commandsList, t);
  }, [commandsList, t]);

  // 扫描命令列表
  const scanCommandsList = useCallback(
    async (keepSelection?: { name: string; scope?: ConfigScope }) => {
      if (!isInitialLoaded) {
        setIsLoading(true);
      }

      try {
        const scopeParam =
          currentScope === 'mixed' || currentScope === null ? undefined : currentScope;
        const response = await scanClaudeCommands({
          project_id: projectId,
          scope: scopeParam,
        });

        if (response.success && response.data) {
          setCommandsList(response.data);

          // 如果列表为空，切换到选择模式
          if (response.data.length === 0) {
            setSelectedCommand(null);
            setViewMode('select');
          } else {
            // 优先使用 keepSelection 参数（用于重命名场景）
            const targetCommand = keepSelection || selectedCommand;

            // 检查目标命令是否还在列表中
            const stillExists =
              targetCommand &&
              response.data.some(
                cmd =>
                  cmd.name === targetCommand.name && cmd.scope === targetCommand.scope
              );

            if (stillExists) {
              // 目标命令还在列表中，保持选中
              if (keepSelection) {
                setSelectedCommand(keepSelection);
              }
              setViewMode('edit');
            } else {
              // 目标命令不在列表中，选中第一个
              const firstCommand = response.data[0];
              setSelectedCommand({
                name: firstCommand.name,
                scope: firstCommand.scope,
              });
              setViewMode('edit');
            }
          }
        }
      } catch (error) {
        console.error(t('commands.scanFailed') + ':', error);
      } finally {
        setIsLoading(false);
        setIsInitialLoaded(true);
      }
    },
    [projectId, currentScope, t, selectedCommand, isInitialLoaded]
  );

  // 组件加载时获取数据
  useEffect(() => {
    if (projectId && !isInitialLoaded) {
      scanCommandsList();
    }
  }, [projectId, isInitialLoaded, scanCommandsList]);

  // 当 scope 变化时重新加载（不显示 loading）
  useEffect(() => {
    if (projectId && isInitialLoaded) {
      scanCommandsList();
    }
  }, [currentScope, projectId, isInitialLoaded, scanCommandsList]);

  // 配置 DetailHeader 的 scopeSwitcher
  useEffect(() => {
    setScopeSwitcher({
      enabled: true,
      supportedScopes: [
        'mixed',
        ConfigScope.USER,
        ConfigScope.PROJECT,
        ConfigScope.PLUGIN,
      ] as (ConfigScope | 'mixed')[],
      value: currentScope,
      onChange: setCurrentScope,
    });

    return () => {
      clearScopeSwitcher();
    };
  }, [setScopeSwitcher, clearScopeSwitcher, currentScope]);

  // 选择命令 - 切换到编辑模式
  const handleSelectCommand = useCallback((command: CommandInfo) => {
    setSelectedCommand({ name: command.name, scope: command.scope });
    setViewMode('edit');
  }, []);

  // 新建命令 - 切换到新建模式
  const handleNewCommand = useCallback(() => {
    setViewMode('new');
  }, []);

  // 命令保存完成 - 切换到编辑模式
  const handleCommandSaved = useCallback(
    (name: string, scope: ConfigScope) => {
      setSelectedCommand({ name, scope });
      setViewMode('edit');
      // 重新扫描列表
      scanCommandsList();
    },
    [scanCommandsList]
  );

  // 命令删除完成 - 切换到选择模式
  const handleCommandDeleted = useCallback(() => {
    setSelectedCommand(null);
    setViewMode('select');
    // 重新扫描列表
    scanCommandsList();
  }, [scanCommandsList]);

  // 命令重命名完成 - 更新选中的命令
  const handleCommandRenamed = useCallback(
    (newName: string, newScope?: ConfigScope) => {
      // 重新扫描列表，并保持选中重命名后的命令
      scanCommandsList({ name: newName, scope: newScope });
    },
    [scanCommandsList]
  );

  // 取消新建 - 返回选择模式
  const handleCancelNew = useCallback(() => {
    setViewMode(selectedCommand ? 'edit' : 'select');
  }, [selectedCommand]);

  // 跳转到插件页面
  const handleGoToPlugins = useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('section', 'plugins');
    router.push(`?${params.toString()}`);
  }, [router, searchParams]);

  // 根据视图模式渲染不同内容
  return (
    <div className='p-4 flex flex-col h-full'>
      {/* 加载状态 */}
      {isLoading && <LoadingState message={t('commands.loading')} />}

      {/* 视图内容 */}
      {!isLoading && (
        <>
          {viewMode === 'new' && (
            <>
              <div className='mb-4 flex-shrink-0'>
                <ClaudeToolSelectBar
                  groups={groupedCommands}
                  selectedItem={selectedCommand}
                  onSelectItem={handleSelectCommand}
                  onRefresh={() => selectedCommand && scanCommandsList(selectedCommand)}
                  onNew={handleNewCommand}
                />
              </div>
              <div className='flex-1 min-h-0'>
                <NewCommandContentView
                  projectId={projectId}
                  initialScope={ConfigScope.PROJECT}
                  onSaved={handleCommandSaved}
                  onCancelled={handleCancelNew}
                />
              </div>
            </>
          )}

          {viewMode === 'edit' && selectedCommand && currentCommand && (
            <>
              {/* 命令选择器 */}
              <div className='mb-4 flex-shrink-0'>
                <ClaudeToolSelectBar
                  groups={groupedCommands}
                  selectedItem={selectedCommand}
                  onSelectItem={handleSelectCommand}
                  onRefresh={() => selectedCommand && scanCommandsList(selectedCommand)}
                  onNew={handleNewCommand}
                />
              </div>

              {/* 编辑命令内容 */}
              <div className='flex-1 min-h-0'>
                <CommandContentView
                  projectId={projectId}
                  selectedCommand={selectedCommand}
                  currentCommand={currentCommand}
                  onDeleted={handleCommandDeleted}
                  onRenamed={handleCommandRenamed}
                />
              </div>
            </>
          )}

          {viewMode === 'select' && (
            <>
              {/* 命令选择器 */}
              <div className='mb-4'>
                <ClaudeToolSelectBar
                  groups={groupedCommands}
                  selectedItem={selectedCommand}
                  onSelectItem={handleSelectCommand}
                  onRefresh={() => selectedCommand && scanCommandsList(selectedCommand)}
                  onNew={handleNewCommand}
                />
              </div>

              {/* 提示用户选择命令 */}
              {currentScope === ConfigScope.PLUGIN ? (
                <EmptyView
                  icon={<Terminal />}
                  title={t('commands.pluginScopeTitle')}
                  description={t('commands.pluginScopeDesc')}
                  actionLabel={t('commands.goToPlugins')}
                  onAction={handleGoToPlugins}
                  actionIcon={<ExternalLink className='h-4 w-4' />}
                />
              ) : (
                <EmptyView
                  icon={<Terminal />}
                  title={t('commands.noSelection')}
                  description={t('commands.noSelectionDesc')}
                  actionLabel={t('commands.createNew')}
                  onAction={handleNewCommand}
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
