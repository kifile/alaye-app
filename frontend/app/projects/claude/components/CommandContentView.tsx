import React, { useState, useCallback, useEffect } from 'react';
import { Terminal, Trash2 } from 'lucide-react';
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

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

  // 检查是否为只读模式（plugin 作用域）
  const isReadOnly = currentCommand?.scope === 'plugin';

  // 编辑器状态
  const [commandContent, setCommandContent] = useState<string>('');
  const [originalContent, setOriginalContent] = useState<string>('');
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
        setCommandContent(response.data.content);
        setOriginalContent(response.data.content);
        setCurrentMd5(response.data.md5);
        setHasChanges(false);
      } else {
        setCommandContent('');
        setOriginalContent('');
        setCurrentMd5('');
        setHasChanges(false);
      }
    } catch (error) {
      console.error('加载 Command 失败:', error);
      toast.error(t('commands.loadFailed'), {
        description: error instanceof Error ? error.message : t('unknownError'),
      });
      setCommandContent('');
      setOriginalContent('');
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
        content: commandContent,
        scope: currentCommand?.scope,
      });

      if (response.success) {
        setOriginalContent(commandContent);
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
    commandContent,
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
      setCommandContent(value);
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
        value={commandContent}
        onChange={handleEditorChange}
        onSave={saveCommandContent}
        onRefresh={refreshCommandContent}
        isLoading={isLoading}
        isSaving={isSaving}
        hasChanges={hasChanges}
        showSaveTooltip={showSaveTooltip}
        icon={<Terminal className='h-4 w-4 text-gray-500' />}
        headerInfo={
          currentCommand?.last_modified_str && (
            <span>
              {t('commands.lastModified')}: {currentCommand.last_modified_str}
            </span>
          )
        }
        toolbarActions={
          isReadOnly ? undefined : (
            <Button
              variant='ghost'
              size='sm'
              onClick={() => setShowDeleteDialog(true)}
              className='text-red-600 hover:text-red-700 hover:bg-red-50'
              title={t('commands.delete')}
            >
              <Trash2 className='h-4 w-4' />
            </Button>
          )
        }
        className='flex-1 flex flex-col'
        readonly={isReadOnly}
      />

      {/* 删除确认对话框 - 只在非只读模式下显示 */}
      {!isReadOnly && (
        <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{t('commands.deleteConfirm')}</AlertDialogTitle>
              <AlertDialogDescription>
                {t('commands.deleteConfirmMessage', { name: selectedCommand.name })}
                {currentCommand?.scope && (
                  <span className='ml-2'>
                    (
                    <span className='text-xs bg-gray-100 px-2 py-1 rounded'>
                      {currentCommand.scope.toUpperCase()}
                    </span>
                    )
                  </span>
                )}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{t('commands.cancel')}</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDeleteCommand}
                className='bg-red-600 hover:bg-red-700'
              >
                {t('commands.delete')}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  );
}
