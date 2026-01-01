import { useState, useEffect, useMemo, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { HookItem } from './HookItem';
import { HookDialog } from './HookDialog';
import { Plus, Search } from 'lucide-react';
import { useDetailHeader } from '../context/DetailHeaderContext';
import {
  scanClaudeHooks,
  addClaudeHook,
  updateClaudeHook,
  removeClaudeHook,
  updateDisableAllHooks,
} from '@/api/api';
import type { HookConfigInfo, HookEvent, HookConfig, ConfigScope } from '@/api/types';
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
  disableAll,
  onToggleDisableAll,
  onAdd,
  isProcessing,
  isLoading,
}: {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  disableAll: boolean | undefined;
  onToggleDisableAll: (checked: boolean) => void;
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
          placeholder={t('hooks.filter.searchPlaceholder')}
          value={searchQuery}
          onChange={e => onSearchChange(e.target.value)}
          className='max-w-md pl-9'
        />
      </div>

      {/* 禁用所有 Hooks 开关 */}
      <div className='flex items-center gap-2'>
        <span className='text-sm text-muted-foreground'>
          {t('hooks.disableAllLabel')}
        </span>
        <Switch
          checked={disableAll ?? false}
          onCheckedChange={onToggleDisableAll}
          disabled={isProcessing || isLoading}
        />
      </div>

      {/* 添加新 Hook 按钮 */}
      <Button onClick={onAdd} disabled={isProcessing} variant='outline'>
        <Plus className='w-4 h-4 mr-2' />
        {t('hooks.addHook')}
      </Button>
    </div>
  );
}

interface HooksDetailProps {
  projectId: number;
}

export function HooksDetail({ projectId }: HooksDetailProps) {
  const { t } = useTranslation('projects');
  const { scopeSwitcher, setScopeSwitcher, clearScopeSwitcher } = useDetailHeader();

  const [isProcessing, setIsProcessing] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingHook, setEditingHook] = useState<HookConfigInfo | null>(null);
  const [hooks, setHooks] = useState<HookConfigInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isInitialLoaded, setIsInitialLoaded] = useState(false);
  const [disableAllHooks, setDisableAllHooks] = useState<boolean | undefined>(
    undefined
  );
  const [currentScope, setCurrentScope] = useState<ConfigScope | 'mixed' | null>(
    'mixed'
  );
  const [searchQuery, setSearchQuery] = useState('');

  // 加载 Hooks 配置
  const loadHooks = useCallback(
    async (scope?: ConfigScope | 'mixed' | null, showLoading = false) => {
      if (showLoading) {
        setIsLoading(true);
      }
      try {
        const scopeParam = scope === 'mixed' || scope === null ? null : scope;
        const response = await scanClaudeHooks({
          project_id: projectId,
          scope: scopeParam,
        });

        if (response.success && response.data) {
          setHooks(response.data.matchers || []);
          // 获取 disable_all_hooks 的值
          if (response.data.disable_all_hooks?.value !== undefined) {
            setDisableAllHooks(response.data.disable_all_hooks.value);
          }
        } else {
          console.warn('加载 Hooks 配置失败或无数据:', response.error);
          setHooks([]);
        }
      } catch (error) {
        console.error('加载 Hooks 配置失败:', error);
        toast.error(t('hooks.loadConfigFailed'));
        setHooks([]);
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
      loadHooks(currentScope, true);
    }
  }, [projectId, isInitialLoaded, currentScope, loadHooks]);

  // 当 scope 变化时重新加载（不显示 loading）
  useEffect(() => {
    if (projectId && isInitialLoaded) {
      loadHooks(currentScope, false);
    }
  }, [currentScope, projectId, isInitialLoaded, loadHooks]);

  // 配置 DetailHeader 的 scopeSwitcher
  useEffect(() => {
    setScopeSwitcher({
      enabled: true,
      supportedScopes: [
        'mixed',
        ConfigScopeEnum.USER,
        ConfigScopeEnum.PROJECT,
        ConfigScopeEnum.LOCAL,
        ConfigScopeEnum.PLUGIN,
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

  const handleAddHook = useCallback(
    async (hookData: {
      event: HookEvent;
      hook: HookConfig;
      matcher?: string;
      scope?: ConfigScope;
    }) => {
      setIsProcessing(true);
      try {
        await addClaudeHook({
          project_id: projectId,
          event: hookData.event,
          hook: hookData.hook,
          matcher: hookData.matcher,
          scope: hookData.scope || ConfigScopeEnum.PROJECT,
        });

        toast.success(t('hooks.addSuccess'));
        await loadHooks(currentScope, false);
      } catch (error: any) {
        handleError(error, t('hooks.addFailed'));
      } finally {
        setIsProcessing(false);
      }
    },
    [projectId, currentScope, loadHooks, t, handleError]
  );

  const handleUpdateHook = useCallback(
    async (hookData: {
      event: HookEvent;
      hook: HookConfig;
      matcher?: string;
      scope?: ConfigScope;
    }) => {
      if (!editingHook) return;

      setIsProcessing(true);
      try {
        await updateClaudeHook({
          project_id: projectId,
          hook_id: editingHook.id,
          hook: hookData.hook,
          scope: editingHook.scope,
        });

        toast.success(t('hooks.updateSuccess'));
        await loadHooks(currentScope, false);
      } catch (error: any) {
        handleError(error, t('hooks.updateFailed'));
      } finally {
        setIsProcessing(false);
      }
    },
    [editingHook, projectId, currentScope, loadHooks, t, handleError]
  );

  const handleDeleteHook = useCallback(
    async (hookInfo: HookConfigInfo) => {
      setIsProcessing(true);
      try {
        await removeClaudeHook({
          project_id: projectId,
          hook_id: hookInfo.id,
          scope: hookInfo.scope,
        });

        toast.success(t('hooks.deleteSuccess'));
        await loadHooks(currentScope, false);
      } catch (error: any) {
        handleError(error, t('hooks.deleteFailed'));
      } finally {
        setIsProcessing(false);
      }
    },
    [projectId, currentScope, loadHooks, t, handleError]
  );

  const handleEditHook = useCallback((hookInfo: HookConfigInfo) => {
    setEditingHook(hookInfo);
    setDialogOpen(true);
  }, []);

  const handleAddNew = useCallback(() => {
    setEditingHook(null);
    setDialogOpen(true);
  }, []);

  // 处理禁用所有 Hooks 的切换
  const handleToggleDisableAll = useCallback(
    async (checked: boolean) => {
      setIsProcessing(true);
      try {
        await updateDisableAllHooks({
          project_id: projectId,
          value: checked,
        });

        toast.success(
          checked ? t('hooks.disableAllSuccess') : t('hooks.enableAllSuccess')
        );

        setDisableAllHooks(checked);
        await loadHooks(currentScope, false);
      } catch (error: any) {
        handleError(error, t('hooks.toggleAllFailed'));
        setDisableAllHooks(!checked);
      } finally {
        setIsProcessing(false);
      }
    },
    [projectId, currentScope, loadHooks, t, handleError]
  );

  // 过滤 Hooks 列表
  const filteredHooks = useMemo(() => {
    if (!searchQuery) return hooks;

    const query = searchQuery.toLowerCase();
    return hooks.filter(
      hook =>
        hook.id.toLowerCase().includes(query) ||
        hook.event.toLowerCase().includes(query)
    );
  }, [hooks, searchQuery]);

  return (
    <div className='p-4'>
      <div className='space-y-4'>
        {/* 加载状态 */}
        {isLoading ? (
          <LoadingState message={t('hooks.loading')} />
        ) : (
          <>
            {/* Filter 区域 */}
            <FilterBar
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              disableAll={disableAllHooks}
              onToggleDisableAll={handleToggleDisableAll}
              onAdd={handleAddNew}
              isProcessing={isProcessing}
              isLoading={isLoading}
            />

            {/* Hooks 列表 */}
            {filteredHooks.length > 0 ? (
              filteredHooks.map(hookInfo => (
                <HookItem
                  key={hookInfo.id}
                  hookInfo={hookInfo}
                  onEdit={() => handleEditHook(hookInfo)}
                  onDelete={() => handleDeleteHook(hookInfo)}
                  isProcessing={isProcessing}
                />
              ))
            ) : (
              <EmptyView
                icon={<Plus />}
                title={t('hooks.noHooks')}
                description={t('hooks.noHooksDesc')}
                actionLabel={t('hooks.addFirstHook')}
                onAction={handleAddNew}
                actionDisabled={isProcessing}
                actionIcon={<Plus className='w-5 h-5 mr-2' />}
              />
            )}
          </>
        )}
      </div>

      {/* 编辑对话框 */}
      <HookDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        hookInfo={editingHook}
        onSave={editingHook ? handleUpdateHook : handleAddHook}
        isProcessing={isProcessing}
        currentScope={currentScope}
      />
    </div>
  );
}
