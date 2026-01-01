import React, { useState, useCallback, useEffect } from 'react';
import { Bot, Trash2 } from 'lucide-react';
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

interface SubAgentContentViewProps {
  projectId: number;
  selectedAgent: { name: string; scope?: ConfigScope };
  currentAgent: AgentInfo | null;
  onDeleted: () => void;
  onRenamed?: (newName: string, newScope?: ConfigScope) => void;
}

export function SubAgentContentView({
  projectId,
  selectedAgent,
  currentAgent,
  onDeleted,
  onRenamed,
}: SubAgentContentViewProps) {
  const { t } = useTranslation('projects');

  // 检查是否为只读模式（plugin 作用域）
  const isReadOnly = currentAgent?.scope === 'plugin';

  // 编辑器状态
  const [agentContent, setAgentContent] = useState<string>('');
  const [originalContent, setOriginalContent] = useState<string>('');
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
        setAgentContent(response.data.content);
        setOriginalContent(response.data.content);
        setCurrentMd5(response.data.md5);
        setHasChanges(false);
      } else {
        setAgentContent('');
        setOriginalContent('');
        setCurrentMd5('');
        setHasChanges(false);
      }
    } catch (error) {
      console.error(t('subAgents.loadFailed') + ':', error);
      toast.error(t('subAgents.loadFailed'), {
        description: error instanceof Error ? error.message : t('unknownError'),
      });
      setAgentContent('');
      setOriginalContent('');
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
        content: agentContent,
        scope: currentAgent?.scope,
      });

      if (response.success) {
        setOriginalContent(agentContent);
        setHasChanges(false);

        setShowSaveTooltip(true);
        setTimeout(() => setShowSaveTooltip(false), 2000);

        toast.success(t('subAgents.saveSuccess'), {
          description: t('subAgents.saveSuccessDesc', { name: selectedAgent.name }),
        });

        // 重新加载内容以获取新的 MD5
        await loadAgentContent();
      } else {
        toast.error(t('subAgents.saveFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error(t('subAgents.saveFailed') + ':', error);
      toast.error(t('subAgents.saveFailed'), {
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
    agentContent,
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
      setAgentContent(value);
      setHasChanges(value !== originalContent);
    },
    [originalContent]
  );

  // 处理标题变更
  const handleTitleChange = useCallback(
    async (newTitle: string, newScope?: ConfigScope) => {
      if (!projectId || !selectedAgent) {
        throw new Error(t('subAgents.missingParams'));
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
        throw new Error(response.error || t('subAgents.renameFailed'));
      }

      toast.success(t('subAgents.saveSuccess'));

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
        toast.success(t('subAgents.deleteSuccess'), {
          description: t('subAgents.deleteSuccessDesc', { name: selectedAgent.name }),
        });

        onDeleted();
      } else {
        toast.error(t('subAgents.deleteFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error('Delete agent error:', error);
      toast.error(t('subAgents.deleteFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    }
  }, [projectId, selectedAgent, currentAgent, onDeleted, t]);

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
        value={agentContent}
        onChange={handleEditorChange}
        onSave={saveAgentContent}
        onRefresh={refreshAgentContent}
        isLoading={isLoading}
        isSaving={isSaving}
        hasChanges={hasChanges}
        showSaveTooltip={showSaveTooltip}
        icon={<Bot className='h-4 w-4 text-gray-500' />}
        headerInfo={
          currentAgent?.last_modified_str && (
            <span>
              {t('subAgents.lastModified')}: {currentAgent.last_modified_str}
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
              title={t('subAgents.delete')}
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
              <AlertDialogTitle>{t('subAgents.deleteConfirm')}</AlertDialogTitle>
              <AlertDialogDescription>
                {t('subAgents.deleteConfirmMessage', { name: selectedAgent.name })}
                {currentAgent?.scope && (
                  <span className='ml-2'>
                    (
                    <span className='text-xs bg-gray-100 px-2 py-1 rounded'>
                      {currentAgent.scope.toUpperCase()}
                    </span>
                    )
                  </span>
                )}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{t('subAgents.cancel')}</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDeleteAgent}
                className='bg-red-600 hover:bg-red-700'
              >
                {t('subAgents.delete')}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  );
}
