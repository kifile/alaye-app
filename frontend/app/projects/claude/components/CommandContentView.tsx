import React, { useState, useCallback, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Terminal, Trash2, Store } from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import {
  loadClaudeMarkdownContent,
  updateClaudeMarkdownContent,
  renameClaudeMarkdownContent,
  deleteClaudeMarkdownContent,
} from '@/api/api';
import type { ConfigScope, CommandInfo } from '@/api/types';
import { ConfigScope as ConfigScopeEnum } from '@/api/types';
import { MarkdownEditor } from '@/components/editor';
import { ClaudeEditorTitle } from './ClaudeEditorTitle';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

interface CommandContentViewProps {
  projectId: number;
  selectedCommand: { name: string; scope?: ConfigScope };
  currentCommand: CommandInfo | null;
  onDeleted: () => void;
  onRenamed?: (newName: string, newScope?: ConfigScope) => void;
}

export function CommandContentView({
  projectId,
  selectedCommand,
  currentCommand,
  onDeleted,
  onRenamed,
}: CommandContentViewProps) {
  const { t } = useTranslation('projects');
  const router = useRouter();
  const searchParams = useSearchParams();

  // 检查是否为只读模式（plugin 作用域）
  const isReadOnly = currentCommand?.scope === 'plugin';

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

  // 加载指定命令的内容
  const loadCommandContent = useCallback(async () => {
    if (!projectId || !selectedCommand) return;

    setIsLoading(true);
    try {
      const response = await loadClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'command',
        name: selectedCommand.name,
        scope: selectedCommand.scope,
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
      console.error('加载 Command 失败:', error);
      toast.error(t('commands.loadFailed'), {
        description: error instanceof Error ? error.message : t('unknownError'),
      });
      setOriginalContent('');
      setPendingContent('');
      setCurrentMd5('');
      setHasChanges(false);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, selectedCommand, t]);

  // 保存 Command 内容
  const saveCommandContent = useCallback(async () => {
    if (!projectId || !selectedCommand || !hasChanges) return;

    setIsSaving(true);
    try {
      const response = await updateClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'command',
        name: selectedCommand.name,
        from_md5: currentMd5,
        content: pendingContent, // 使用 pendingContent 而不是 commandContent
        scope: currentCommand?.scope,
      });

      if (response.success) {
        // 保存成功后，更新原始内容
        setOriginalContent(pendingContent);
        setPendingContent(pendingContent); // 保持同步
        setHasChanges(false);

        setShowSaveTooltip(true);
        setTimeout(() => setShowSaveTooltip(false), 2000);

        toast.success(t('commands.saveSuccess'), {
          description: t('commands.saveSuccessDesc', { name: selectedCommand.name }),
        });

        // 重新加载内容以获取新的 MD5
        await loadCommandContent();
      } else {
        toast.error(t('commands.saveFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error('保存 Command 失败:', error);
      toast.error(t('commands.saveFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    } finally {
      setIsSaving(false);
    }
  }, [
    projectId,
    selectedCommand,
    currentCommand,
    currentMd5,
    pendingContent,
    hasChanges,
    loadCommandContent,
    t,
  ]);

  // 刷新当前 Command 内容
  const refreshCommandContent = useCallback(() => {
    loadCommandContent();
  }, [loadCommandContent]);

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
      if (!projectId || !selectedCommand) {
        throw new Error('缺少必要参数');
      }

      const response = await renameClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'command',
        name: selectedCommand.name,
        new_name: newTitle,
        scope: currentCommand?.scope,
        new_scope: newScope,
      });

      if (!response.success) {
        throw new Error(response.error || t('commands.renameFailed'));
      }

      toast.success(t('commands.saveSuccess'));

      // 通知父组件重命名成功，传递新的 name 和 scope
      onRenamed?.(newTitle, newScope || currentCommand?.scope);
    },
    [projectId, selectedCommand, currentCommand, t, onRenamed]
  );

  // 删除命令
  const handleDeleteCommand = useCallback(async () => {
    if (!projectId || !selectedCommand) return;

    try {
      const response = await deleteClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'command',
        name: selectedCommand.name,
        scope: currentCommand?.scope,
      });

      if (response.success) {
        toast.success(t('commands.deleteSuccess'), {
          description: t('commands.deleteSuccessDesc', { name: selectedCommand.name }),
        });

        onDeleted();
      } else {
        toast.error(t('commands.deleteFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error('Delete command error:', error);
      toast.error(t('commands.deleteFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    }
  }, [projectId, selectedCommand, currentCommand, onDeleted, t]);

  // 跳转到插件页面
  const handleGoToPlugin = useCallback(() => {
    if (!currentCommand?.plugin_name) return;

    const params = new URLSearchParams(searchParams.toString());
    params.set('section', 'plugins');
    params.set('search', currentCommand.plugin_name);

    if (currentCommand.marketplace_name) {
      params.set('marketplaces', currentCommand.marketplace_name);
    }

    router.push(`?${params.toString()}`);
  }, [currentCommand, router, searchParams]);

  // 组件挂载时加载内容
  useEffect(() => {
    loadCommandContent();
  }, [loadCommandContent]);

  // 自定义标题 ReactNode
  const titleNode = (
    <ClaudeEditorTitle
      title={selectedCommand.name}
      scope={currentCommand?.scope}
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
        onSave={saveCommandContent}
        onRefresh={refreshCommandContent}
        isLoading={isLoading}
        isSaving={isSaving}
        hasChanges={hasChanges}
        showSaveTooltip={showSaveTooltip}
        toolbarActions={
          <>
            {/* Plugin scope 时显示跳转按钮 */}
            {isReadOnly && currentCommand?.plugin_name && (
              <Button
                variant='ghost'
                size='sm'
                onClick={handleGoToPlugin}
                className='text-blue-600 hover:text-blue-700 hover:bg-blue-50'
                title={t('commands.goToPlugin')}
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
                    title={t('commands.delete')}
                  >
                    <Trash2 className='h-4 w-4' />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className='w-80 p-4' align='end'>
                  <div className='space-y-4'>
                    <div>
                      <h4 className='font-medium'>{t('commands.deleteConfirm')}</h4>
                      <p className='text-sm text-muted-foreground mt-2'>
                        {t('commands.deleteConfirmMessage', {
                          name: selectedCommand.name,
                        })}
                        {currentCommand?.scope && (
                          <span className='ml-2'>
                            (
                            <span className='text-xs bg-gray-100 px-2 py-1 rounded'>
                              {currentCommand.scope.toUpperCase()}
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
                        {t('commands.cancel')}
                      </Button>
                      <Button
                        variant='destructive'
                        size='sm'
                        onClick={handleDeleteCommand}
                      >
                        {t('commands.delete')}
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
