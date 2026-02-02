import React, { useState, useCallback, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Bot, Trash2, Store } from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import {
  loadClaudeMarkdownContent,
  updateClaudeMarkdownContent,
  renameClaudeMarkdownContent,
  deleteClaudeMarkdownContent,
} from '@/api/api';
import type { ConfigScope, AgentInfo } from '@/api/types';
import { ConfigScope as ConfigScopeEnum } from '@/api/types';
import { MarkdownEditor } from '@/components/editor';
import { ClaudeEditorTitle } from './ClaudeEditorTitle';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

interface AgentContentViewProps {
  projectId: number;
  selectedAgent: { name: string; scope?: ConfigScope };
  currentAgent: AgentInfo | null;
  onDeleted: () => void;
  onRenamed?: (newName: string, newScope?: ConfigScope) => void;
}

export function AgentContentView({
  projectId,
  selectedAgent,
  currentAgent,
  onDeleted,
  onRenamed,
}: AgentContentViewProps) {
  const { t } = useTranslation('projects');
  const router = useRouter();
  const searchParams = useSearchParams();

  // 检查是否为只读模式（plugin 作用域）
  const isReadOnly = currentAgent?.scope === 'plugin';

  // 编辑器状态
  // originalContent: 从服务器加载的原始内容（用于 defaultValue）
  // pendingContent: 用户编辑的内容（用于保存，不传给编辑器）
  const [originalContent, setOriginalContent] = useState<string>('');
  const [pendingContent, setPendingContent] = useState<string>('');
  const [currentMd5, setCurrentMd5] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [hasChanges, setHasChanges] = useState<boolean>(false);
  const [showSaveTooltip, setShowSaveTooltip] = useState<boolean>(false);

  // 删除确认对话框
  const [showDeleteDialog, setShowDeleteDialog] = useState<boolean>(false);

  // 加载指定代理的内容
  const loadAgentContent = useCallback(async () => {
    if (!projectId || !selectedAgent) return;

    setIsLoading(true);
    try {
      const response = await loadClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'agent',
        name: selectedAgent.name,
        scope: selectedAgent.scope,
      });

      if (response.success && response.data) {
        // 同时更新原始内容和待保存内容
        const content = response.data.content;
        setOriginalContent(content);
        setPendingContent(content);
        setCurrentMd5(response.data.md5);
        setHasChanges(false);
      } else {
        setOriginalContent('');
        setPendingContent('');
        setCurrentMd5('');
        setHasChanges(false);
      }
    } catch (error) {
      console.error(t('agents.loadFailed') + ':', error);
      toast.error(t('agents.loadFailed'), {
        description: error instanceof Error ? error.message : t('unknownError'),
      });
      setOriginalContent('');
      setPendingContent('');
      setCurrentMd5('');
      setHasChanges(false);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, selectedAgent, t]);

  // 保存 Agent 内容
  const saveAgentContent = useCallback(async () => {
    if (!projectId || !selectedAgent || !hasChanges) return;

    setIsSaving(true);
    try {
      const response = await updateClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'agent',
        name: selectedAgent.name,
        from_md5: currentMd5,
        content: pendingContent, // 使用 pendingContent 而不是 agentContent
        scope: currentAgent?.scope,
      });

      if (response.success) {
        // 保存成功后，更新原始内容
        setOriginalContent(pendingContent);
        setPendingContent(pendingContent); // 保持同步
        setHasChanges(false);

        setShowSaveTooltip(true);
        setTimeout(() => setShowSaveTooltip(false), 2000);

        toast.success(t('agents.saveSuccess'), {
          description: t('agents.saveSuccessDesc', { name: selectedAgent.name }),
        });

        // 重新加载内容以获取新的 MD5
        await loadAgentContent();
      } else {
        toast.error(t('agents.saveFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error(t('agents.saveFailed') + ':', error);
      toast.error(t('agents.saveFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    } finally {
      setIsSaving(false);
    }
  }, [
    projectId,
    selectedAgent,
    currentAgent,
    currentMd5,
    pendingContent,
    hasChanges,
    loadAgentContent,
    t,
  ]);

  // 刷新当前 Agent 内容
  const refreshAgentContent = useCallback(() => {
    loadAgentContent();
  }, [loadAgentContent]);

  // 处理编辑器内容变化
  const handleEditorChange = useCallback(
    (value: string) => {
      // 只更新 pendingContent（用于保存），不更新 originalContent（避免触发编辑器重新初始化）
      setPendingContent(value);
      setHasChanges(value !== originalContent);
    },
    [originalContent]
  );

  // 处理标题变更
  const handleTitleChange = useCallback(
    async (newTitle: string, newScope?: ConfigScope) => {
      if (!projectId || !selectedAgent) {
        throw new Error(t('agents.missingParams'));
      }

      const response = await renameClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'agent',
        name: selectedAgent.name,
        new_name: newTitle,
        scope: currentAgent?.scope,
        new_scope: newScope,
      });

      if (!response.success) {
        throw new Error(response.error || t('agents.renameFailed'));
      }

      toast.success(t('agents.saveSuccess'));

      // 通知父组件重命名成功，传递新的 name 和 scope
      onRenamed?.(newTitle, newScope || currentAgent?.scope);
    },
    [projectId, selectedAgent, currentAgent, t, onRenamed]
  );

  // 删除代理
  const handleDeleteAgent = useCallback(async () => {
    if (!projectId || !selectedAgent) return;

    try {
      const response = await deleteClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'agent',
        name: selectedAgent.name,
        scope: currentAgent?.scope,
      });

      if (response.success) {
        toast.success(t('agents.deleteSuccess'), {
          description: t('agents.deleteSuccessDesc', { name: selectedAgent.name }),
        });

        onDeleted();
      } else {
        toast.error(t('agents.deleteFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error('Delete agent error:', error);
      toast.error(t('agents.deleteFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    }
  }, [projectId, selectedAgent, currentAgent, onDeleted, t]);

  // 跳转到插件页面
  const handleGoToPlugin = useCallback(() => {
    if (!currentAgent?.plugin_name) return;

    const params = new URLSearchParams(searchParams.toString());
    params.set('section', 'plugins');
    params.set('search', currentAgent.plugin_name);

    if (currentAgent.marketplace_name) {
      params.set('marketplaces', currentAgent.marketplace_name);
    }

    router.push(`?${params.toString()}`);
  }, [currentAgent, router, searchParams]);

  // 组件挂载时加载内容
  useEffect(() => {
    loadAgentContent();
  }, [loadAgentContent]);

  // 自定义标题 ReactNode
  const titleNode = (
    <ClaudeEditorTitle
      title={selectedAgent.name}
      scope={currentAgent?.scope}
      availableScopes={[ConfigScopeEnum.USER, ConfigScopeEnum.PROJECT]}
      onConfirm={handleTitleChange}
      readonly={isReadOnly}
    />
  );

  return (
    <div className='h-full flex flex-col'>
      <MarkdownEditor
        title={titleNode}
        defaultValue={originalContent}
        onChange={handleEditorChange}
        onSave={saveAgentContent}
        onRefresh={refreshAgentContent}
        isLoading={isLoading}
        isSaving={isSaving}
        hasChanges={hasChanges}
        showSaveTooltip={showSaveTooltip}
        toolbarActions={
          <>
            {/* Plugin scope 时显示跳转按钮 */}
            {isReadOnly && currentAgent?.plugin_name && (
              <Button
                variant='ghost'
                size='sm'
                onClick={handleGoToPlugin}
                className='text-blue-600 hover:text-blue-700 hover:bg-blue-50'
                title={t('agents.goToPlugin')}
              >
                <Store className='h-4 w-4' />
              </Button>
            )}
            {/* 非只读模式时显示删除按钮 */}
            {!isReadOnly && (
              <Popover open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
                <PopoverTrigger asChild>
                  <Button
                    variant='ghost'
                    size='sm'
                    className='text-red-600 hover:text-red-700 hover:bg-red-50'
                    title={t('agents.delete')}
                  >
                    <Trash2 className='h-4 w-4' />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className='w-80 p-4' align='end'>
                  <div className='space-y-4'>
                    <div>
                      <h4 className='font-medium'>{t('agents.deleteConfirm')}</h4>
                      <p className='text-sm text-muted-foreground mt-2'>
                        {t('agents.deleteConfirmMessage', { name: selectedAgent.name })}
                        {currentAgent?.scope && (
                          <span className='ml-2'>
                            (
                            <span className='text-xs bg-gray-100 px-2 py-1 rounded'>
                              {currentAgent.scope.toUpperCase()}
                            </span>
                            )
                          </span>
                        )}
                      </p>
                    </div>
                    <div className='flex justify-end gap-2'>
                      <Button
                        variant='outline'
                        size='sm'
                        onClick={() => setShowDeleteDialog(false)}
                      >
                        {t('agents.cancel')}
                      </Button>
                      <Button
                        variant='destructive'
                        size='sm'
                        onClick={handleDeleteAgent}
                      >
                        {t('agents.delete')}
                      </Button>
                    </div>
                  </div>
                </PopoverContent>
              </Popover>
            )}
          </>
        }
        className='flex-1 flex flex-col'
        readonly={isReadOnly}
      />
    </div>
  );
}
