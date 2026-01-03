import { useState, useMemo, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Terminal,
  Zap,
  Bot,
  Server,
  Workflow,
  Download,
  Trash2,
  Store,
  Tag,
  AlertCircle,
  Power,
  PowerOff,
  MoreVertical,
} from 'lucide-react';
import { ConfigScope } from '@/api/types';
import type { PluginInfo, ProcessResult } from '@/api/types';
import { PluginToolsDialog } from './PluginToolsDialog';
import { ScopeBadgeUpdater } from './ScopeBadgeUpdater';
import {
  installClaudePlugin,
  uninstallClaudePlugin,
  enableClaudePlugin,
  disableClaudePlugin,
  moveClaudePlugin,
} from '@/api/api';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { ScopeBadge } from './ScopeBadge';

interface ErrorPopoverProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  errorTitle: string;
  errorResult: ProcessResult | null;
  children: React.ReactNode;
}

// 错误提示 Popover 组件
function ErrorPopover({
  open,
  onOpenChange,
  errorTitle,
  errorResult,
  children,
}: ErrorPopoverProps) {
  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      {errorResult && (
        <PopoverContent className='w-auto max-w-md' side='top'>
          <div className='space-y-2'>
            <div className='flex items-center gap-2 text-sm font-medium text-red-600'>
              <AlertCircle className='w-4 h-4' />
              <span>{errorTitle}</span>
            </div>
            {errorResult.stdout && (
              <div className='text-xs text-gray-700 whitespace-pre-wrap bg-gray-50 p-2 rounded max-h-40 overflow-auto'>
                {errorResult.stdout}
              </div>
            )}
            {errorResult.error_message && (
              <div className='text-xs text-red-600 bg-red-50 p-2 rounded'>
                {errorResult.error_message}
              </div>
            )}
          </div>
        </PopoverContent>
      )}
    </Popover>
  );
}

interface PluginItemProps {
  plugin: PluginInfo;
  projectId: number;
  onPluginChange?: () => void;
}

export function PluginItem({ plugin, projectId, onPluginChange }: PluginItemProps) {
  const { t } = useTranslation('projects');
  const [toolsDialogOpen, setToolsDialogOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [errorResult, setErrorResult] = useState<ProcessResult | null>(null);

  // 缓存插件全名
  const pluginFullName = useMemo(
    () => `${plugin.config.name}@${plugin.marketplace || ''}`,
    [plugin.config.name, plugin.marketplace]
  );

  // 缓存工具数量计算
  const toolsCount = useMemo(() => {
    const commandsCount = plugin.tools?.commands?.length || 0;
    const skillsCount = plugin.tools?.skills?.length || 0;
    const agentsCount = plugin.tools?.agents?.length || 0;
    const mcpServersCount = plugin.tools?.mcp_servers?.length || 0;
    const hooksCount = plugin.tools?.hooks?.length || 0;
    return {
      commands: commandsCount,
      skills: skillsCount,
      agents: agentsCount,
      mcpServers: mcpServersCount,
      hooks: hooksCount,
      total: commandsCount + skillsCount + agentsCount + mcpServersCount + hooksCount,
    };
  }, [plugin.tools]);

  // 创建通用错误对象
  const createErrorResult = useCallback(
    (message: string): ProcessResult => ({
      success: false,
      return_code: -1,
      stdout: '',
      stderr: '',
      error_message: message || t('pluginItem.unknownError'),
    }),
    [t]
  );

  // 处理安装插件
  const handleInstall = async (scope: ConfigScope) => {
    setLoading(true);
    setErrorResult(null);
    try {
      const result = await installClaudePlugin({
        project_id: projectId,
        plugin_name: pluginFullName,
        scope,
      });

      if (result.success && result.data?.success) {
        onPluginChange?.();
      } else {
        setErrorResult(result.data || null);
      }
    } catch (error) {
      console.error('安装插件失败:', error);
      setErrorResult(createErrorResult(error instanceof Error ? error.message : ''));
    } finally {
      setLoading(false);
    }
  };

  // 处理卸载插件
  const handleUninstall = async () => {
    setLoading(true);
    setErrorResult(null);
    try {
      const scope = plugin.enabled_scope || ('local' as ConfigScope);
      const result = await uninstallClaudePlugin({
        project_id: projectId,
        plugin_name: pluginFullName,
        scope,
      });

      if (result.success && result.data?.success) {
        onPluginChange?.();
      } else {
        setErrorResult(result.data || null);
      }
    } catch (error) {
      console.error('卸载插件失败:', error);
      setErrorResult(createErrorResult(error instanceof Error ? error.message : ''));
    } finally {
      setLoading(false);
    }
  };

  // 处理切换插件启用状态
  const handleToggleEnabled = async (checked: boolean) => {
    setToggling(true);
    setErrorResult(null);
    try {
      const scope = plugin.enabled_scope || ('local' as ConfigScope);

      const result = checked
        ? await enableClaudePlugin({
            project_id: projectId,
            plugin_name: pluginFullName,
            scope,
          })
        : await disableClaudePlugin({
            project_id: projectId,
            plugin_name: pluginFullName,
            scope,
          });

      if (result.success) {
        onPluginChange?.();
      } else {
        setErrorResult({
          success: false,
          return_code: -1,
          stdout: '',
          stderr: '',
          error_message: result.error || t('pluginItem.toggleFailed'),
        });
      }
    } catch (error) {
      console.error('切换插件状态失败:', error);
      setErrorResult(createErrorResult(error instanceof Error ? error.message : ''));
    } finally {
      setToggling(false);
    }
  };

  // 处理切换插件作用域
  const handleScopeChange = async (oldScope: ConfigScope, newScope: ConfigScope) => {
    try {
      const result = await moveClaudePlugin({
        project_id: projectId,
        plugin_name: pluginFullName,
        old_scope: oldScope,
        new_scope: newScope,
      });

      if (result.success) {
        toast.success(t('pluginItem.scopeMoved', { scope: newScope }));
        onPluginChange?.();
      } else {
        toast.error(t('pluginItem.moveScopeFailed'), {
          description: result.error || t('pluginItem.unknownError'),
        });
      }
    } catch (error) {
      console.error('移动插件作用域失败:', error);
      toast.error(t('pluginItem.moveScopeFailed'), {
        description:
          error instanceof Error ? error.message : t('pluginItem.unknownError'),
      });
    }
  };

  return (
    <>
      <div className='border border-gray-200/60 rounded-lg p-4 hover:shadow-md transition-shadow bg-white relative'>
        <div className='space-y-3'>
          {/* 插件名称和状态标签 */}
          <div className='flex items-center gap-2 flex-wrap pr-16'>
            {/* Scope Badge Updater - 支持切换作用域 */}
            {plugin.enabled_scope && (
              <ScopeBadgeUpdater
                currentScope={plugin.enabled_scope}
                onScopeChange={handleScopeChange}
              />
            )}
            <h4 className='font-semibold text-gray-900'>{plugin.config.name}</h4>
            {/* 版本标签 */}
            {plugin.config.version && (
              <span className='text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full border border-blue-200'>
                {plugin.config.version}
              </span>
            )}
          </div>

          {/* 插件描述 */}
          {plugin.config.description && (
            <Tooltip delayDuration={400}>
              <TooltipTrigger asChild>
                <p className='text-sm text-gray-600 line-clamp-2 cursor-help'>
                  {plugin.config.description}
                </p>
              </TooltipTrigger>
              <TooltipContent>
                <p className='max-w-md'>{plugin.config.description}</p>
              </TooltipContent>
            </Tooltip>
          )}

          {/* 插件元数据 - 作者和安装量 */}
          <div className='flex items-center gap-3 text-xs text-gray-500 flex-wrap'>
            {plugin.config.author && (
              <div className='flex items-center gap-1'>
                <span className='font-medium'>{t('pluginItem.author')}</span>
                <span>
                  {plugin.config.author.name ||
                    plugin.config.author.email ||
                    t('pluginItem.unknown')}
                </span>
              </div>
            )}
            {plugin.unique_installs != null && (
              <div className='flex items-center gap-1'>
                <span className='font-medium'>{t('pluginItem.installs')}</span>
                <span>{plugin.unique_installs.toLocaleString()}</span>
              </div>
            )}
          </div>

          {/* Marketplace 和分类标签 - 同一行展示 */}
          <div className='flex items-center gap-1 flex-wrap'>
            {plugin.marketplace && (
              <span className='text-xs px-2 py-0.5 bg-purple-50 text-purple-700 rounded border border-purple-200 flex items-center gap-1'>
                <Store className='w-3 h-3' />
                {plugin.marketplace}
              </span>
            )}
            {plugin.config.category && (
              <span className='text-xs px-2 py-0.5 bg-orange-50 text-orange-700 rounded border border-orange-200 flex items-center gap-1'>
                <Tag className='w-3 h-3' />
                {plugin.config.category}
              </span>
            )}
          </div>

          {/* 操作按钮 */}
          <div className='space-y-2 pt-2'>
            {/* 启用/禁用按钮 - 仅在插件已安装时显示 */}
            {plugin.installed && (
              <ErrorPopover
                open={!!errorResult && errorResult.return_code === -1}
                onOpenChange={open => !open && setErrorResult(null)}
                errorTitle={t('pluginItem.operationFailed')}
                errorResult={
                  errorResult && errorResult.return_code === -1 ? errorResult : null
                }
              >
                <Button
                  variant={plugin.enabled ? 'outline' : 'default'}
                  size='sm'
                  className='w-full'
                  onClick={() => handleToggleEnabled(!plugin.enabled)}
                  disabled={toggling}
                >
                  {plugin.enabled ? (
                    <>
                      <PowerOff className='w-3.5 h-3.5 mr-1.5' />
                      {toggling
                        ? t('pluginItem.disabling')
                        : t('pluginItem.disablePlugin')}
                    </>
                  ) : (
                    <>
                      <Power className='w-3.5 h-3.5 mr-1.5' />
                      {toggling
                        ? t('pluginItem.enabling')
                        : t('pluginItem.enablePlugin')}
                    </>
                  )}
                </Button>
              </ErrorPopover>
            )}

            {/* 安装/卸载按钮 */}
            {plugin.installed ? (
              <ErrorPopover
                open={!!errorResult && errorResult.return_code !== -1}
                onOpenChange={open => !open && setErrorResult(null)}
                errorTitle={t('pluginItem.uninstallFailed')}
                errorResult={
                  errorResult && errorResult.return_code !== -1 ? errorResult : null
                }
              >
                <Button
                  variant='outline'
                  size='sm'
                  className='w-full'
                  onClick={handleUninstall}
                  disabled={loading}
                >
                  <Trash2 className='w-3.5 h-3.5 mr-1.5' />
                  {loading
                    ? t('pluginItem.uninstalling')
                    : t('pluginItem.uninstallPlugin')}
                </Button>
              </ErrorPopover>
            ) : (
              <div className='flex gap-0'>
                <ErrorPopover
                  open={!!errorResult}
                  onOpenChange={open => !open && setErrorResult(null)}
                  errorTitle={t('pluginItem.installFailed')}
                  errorResult={errorResult}
                >
                  <Button
                    variant='default'
                    size='sm'
                    className='flex-1 rounded-r-none'
                    onClick={() => handleInstall(ConfigScope.LOCAL)}
                    disabled={loading}
                  >
                    <Download className='w-3.5 h-3.5 mr-1.5' />
                    {loading ? (
                      t('pluginItem.installing')
                    ) : (
                      <span>
                        {t('pluginItem.installPlugin')} ({t('pluginItem.scope.local')})
                      </span>
                    )}
                  </Button>
                </ErrorPopover>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant='default'
                      size='sm'
                      className='px-2 rounded-l-none border-l-0'
                      disabled={loading}
                      title={t('pluginItem.selectInstallScope')}
                    >
                      <MoreVertical className='w-3.5 h-3.5' />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align='start' className='w-56'>
                    <div className='px-2 py-1.5 text-sm font-semibold text-gray-700 border-b'>
                      {t('pluginItem.selectInstallScope')}
                    </div>
                    <DropdownMenuItem
                      className='flex flex-col items-start py-2 cursor-pointer'
                      onClick={() => handleInstall(ConfigScope.LOCAL)}
                      disabled={loading}
                    >
                      <div className='flex items-center gap-2 w-full'>
                        <ScopeBadge scope={ConfigScope.LOCAL} showLabel={false} />
                        <span className='font-medium'>
                          {t('pluginItem.scope.local')}
                        </span>
                      </div>
                      <span className='text-xs text-gray-500 ml-6'>
                        {t('pluginItem.scope.localDesc')}
                      </span>
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className='flex flex-col items-start py-2 cursor-pointer'
                      onClick={() => handleInstall(ConfigScope.PROJECT)}
                      disabled={loading}
                    >
                      <div className='flex items-center gap-2 w-full'>
                        <ScopeBadge scope={ConfigScope.PROJECT} showLabel={false} />
                        <span className='font-medium'>
                          {t('pluginItem.scope.project')}
                        </span>
                      </div>
                      <span className='text-xs text-gray-500 ml-6'>
                        {t('pluginItem.scope.projectDesc')}
                      </span>
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className='flex flex-col items-start py-2 cursor-pointer'
                      onClick={() => handleInstall(ConfigScope.USER)}
                      disabled={loading}
                    >
                      <div className='flex items-center gap-2 w-full'>
                        <ScopeBadge scope={ConfigScope.USER} showLabel={false} />
                        <span className='font-medium'>
                          {t('pluginItem.scope.user')}
                        </span>
                      </div>
                      <span className='text-xs text-gray-500 ml-6'>
                        {t('pluginItem.scope.userDesc')}
                      </span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )}
          </div>
        </div>

        {/* Tools 状态栏 - 右上角绝对定位，显示数量 */}
        {toolsCount.total > 0 && (
          <div
            className='absolute top-3 right-3 flex items-center gap-1.5 text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded-lg cursor-pointer hover:bg-gray-200 transition-colors'
            onClick={() => setToolsDialogOpen(true)}
            title={t('pluginItem.viewToolsDetails')}
          >
            {toolsCount.commands > 0 && (
              <div className='flex items-center gap-0.5'>
                <Terminal className='w-3 h-3' />
                <span className='font-medium'>{toolsCount.commands}</span>
              </div>
            )}
            {toolsCount.skills > 0 && (
              <div className='flex items-center gap-0.5'>
                <Zap className='w-3 h-3' />
                <span className='font-medium'>{toolsCount.skills}</span>
              </div>
            )}
            {toolsCount.agents > 0 && (
              <div className='flex items-center gap-0.5'>
                <Bot className='w-3 h-3' />
                <span className='font-medium'>{toolsCount.agents}</span>
              </div>
            )}
            {toolsCount.mcpServers > 0 && (
              <div className='flex items-center gap-0.5'>
                <Server className='w-3 h-3' />
                <span className='font-medium'>{toolsCount.mcpServers}</span>
              </div>
            )}
            {toolsCount.hooks > 0 && (
              <div className='flex items-center gap-0.5'>
                <Workflow className='w-3 h-3' />
                <span className='font-medium'>{toolsCount.hooks}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Tools 对话框 */}
      <PluginToolsDialog
        open={toolsDialogOpen}
        onOpenChange={setToolsDialogOpen}
        plugin={plugin}
      />
    </>
  );
}
