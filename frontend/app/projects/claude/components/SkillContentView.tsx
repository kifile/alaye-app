import React, { useState, useCallback, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { BookOpen, Trash2, Store } from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import {
  loadClaudeMarkdownContent,
  updateClaudeMarkdownContent,
  renameClaudeMarkdownContent,
  deleteClaudeMarkdownContent,
} from '@/api/api';
import type { ConfigScope, SkillInfo } from '@/api/types';
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

interface SkillContentViewProps {
  projectId: number;
  selectedSkill: { name: string; scope?: ConfigScope };
  currentSkill: SkillInfo | null;
  onDeleted: () => void;
  onRenamed?: (newName: string, newScope?: ConfigScope) => void;
}

export function SkillContentView({
  projectId,
  selectedSkill,
  currentSkill,
  onDeleted,
  onRenamed,
}: SkillContentViewProps) {
  const { t } = useTranslation('projects');
  const router = useRouter();
  const searchParams = useSearchParams();

  // 检查是否为只读模式（plugin 作用域）
  const isReadOnly = currentSkill?.scope === 'plugin';

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

  // 加载指定 skill 的内容
  const loadSkillContent = useCallback(async () => {
    if (!projectId || !selectedSkill) return;

    setIsLoading(true);
    try {
      const response = await loadClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'skill',
        name: selectedSkill.name,
        scope: selectedSkill.scope,
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
      console.error(t('skills.loadFailed') + ':', error);
      toast.error(t('skills.loadFailed'), {
        description: error instanceof Error ? error.message : t('unknownError'),
      });
      setOriginalContent('');
      setPendingContent('');
      setCurrentMd5('');
      setHasChanges(false);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, selectedSkill, t]);

  // 保存 Skill 内容
  const saveSkillContent = useCallback(async () => {
    if (!projectId || !selectedSkill || !hasChanges) return;

    setIsSaving(true);
    try {
      const response = await updateClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'skill',
        name: selectedSkill.name,
        from_md5: currentMd5,
        content: pendingContent, // 使用 pendingContent 而不是 skillContent
        scope: currentSkill?.scope,
      });

      if (response.success) {
        // 保存成功后，更新原始内容
        setOriginalContent(pendingContent);
        setPendingContent(pendingContent); // 保持同步
        setHasChanges(false);

        setShowSaveTooltip(true);
        setTimeout(() => setShowSaveTooltip(false), 2000);

        toast.success(t('skills.saveSuccess'), {
          description: t('skills.saveSuccessDesc', { name: selectedSkill.name }),
        });

        // 重新加载内容以获取新的 MD5
        await loadSkillContent();
      } else {
        toast.error(t('skills.saveFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error(t('skills.saveFailed') + ':', error);
      toast.error(t('skills.saveFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    } finally {
      setIsSaving(false);
    }
  }, [
    projectId,
    selectedSkill,
    currentSkill,
    currentMd5,
    pendingContent,
    hasChanges,
    loadSkillContent,
    t,
  ]);

  // 刷新当前 Skill 内容
  const refreshSkillContent = useCallback(() => {
    loadSkillContent();
  }, [loadSkillContent]);

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
      if (!projectId || !selectedSkill) {
        throw new Error(t('skills.missingParams'));
      }

      const response = await renameClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'skill',
        name: selectedSkill.name,
        new_name: newTitle,
        scope: currentSkill?.scope,
        new_scope: newScope,
      });

      if (!response.success) {
        throw new Error(response.error || t('skills.renameFailed'));
      }

      toast.success(t('skills.saveSuccess'));

      // 通知父组件重命名成功，传递新的 name 和 scope
      onRenamed?.(newTitle, newScope || currentSkill?.scope);
    },
    [projectId, selectedSkill, currentSkill, t, onRenamed]
  );

  // 删除 skill
  const handleDeleteSkill = useCallback(async () => {
    if (!projectId || !selectedSkill) return;

    try {
      const response = await deleteClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'skill',
        name: selectedSkill.name,
        scope: currentSkill?.scope,
      });

      if (response.success) {
        toast.success(t('skills.deleteSuccess'), {
          description: t('skills.deleteSuccessDesc', { name: selectedSkill.name }),
        });

        onDeleted();
      } else {
        toast.error(t('skills.deleteFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error('Delete skill error:', error);
      toast.error(t('skills.deleteFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    }
  }, [projectId, selectedSkill, currentSkill, onDeleted, t]);

  // 跳转到插件页面
  const handleGoToPlugin = useCallback(() => {
    if (!currentSkill?.plugin_name) return;

    const params = new URLSearchParams(searchParams.toString());
    params.set('section', 'plugins');
    params.set('search', currentSkill.plugin_name);

    if (currentSkill.marketplace_name) {
      params.set('marketplaces', currentSkill.marketplace_name);
    }

    router.push(`?${params.toString()}`);
  }, [currentSkill, router, searchParams]);

  // 组件挂载时加载内容
  useEffect(() => {
    loadSkillContent();
  }, [loadSkillContent]);

  // 自定义标题 ReactNode
  const titleNode = (
    <ClaudeEditorTitle
      title={selectedSkill.name}
      scope={currentSkill?.scope}
      availableScopes={[ConfigScopeEnum.PROJECT, ConfigScopeEnum.USER]}
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
        onSave={saveSkillContent}
        onRefresh={refreshSkillContent}
        isLoading={isLoading}
        isSaving={isSaving}
        hasChanges={hasChanges}
        showSaveTooltip={showSaveTooltip}
        icon={<BookOpen className='h-4 w-4 text-gray-500' />}
        headerInfo={
          currentSkill?.last_modified_str && (
            <span>
              {t('skills.lastModified')}: {currentSkill.last_modified_str}
            </span>
          )
        }
        toolbarActions={
          <>
            {/* Plugin scope 时显示跳转按钮 */}
            {isReadOnly && currentSkill?.plugin_name && (
              <Button
                variant='ghost'
                size='sm'
                onClick={handleGoToPlugin}
                className='text-blue-600 hover:text-blue-700 hover:bg-blue-50'
                title={t('skills.goToPlugin')}
              >
                <Store className='h-4 w-4' />
              </Button>
            )}
            {/* 非只读模式时显示删除按钮 */}
            {!isReadOnly && (
              <Button
                variant='ghost'
                size='sm'
                onClick={() => setShowDeleteDialog(true)}
                className='text-red-600 hover:text-red-700 hover:bg-red-50'
                title={t('skills.delete')}
              >
                <Trash2 className='h-4 w-4' />
              </Button>
            )}
          </>
        }
        className='flex-1 flex flex-col'
        readonly={isReadOnly}
      />

      {/* 删除确认对话框 - 只在非只读模式下显示 */}
      {!isReadOnly && (
        <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{t('skills.deleteConfirm')}</AlertDialogTitle>
              <AlertDialogDescription>
                {t('skills.deleteConfirmMessage', { name: selectedSkill.name })}
                {currentSkill?.scope && (
                  <span className='ml-2'>
                    (
                    <span className='text-xs bg-gray-100 px-2 py-1 rounded'>
                      {currentSkill.scope.toUpperCase()}
                    </span>
                    )
                  </span>
                )}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{t('skills.cancel')}</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDeleteSkill}
                className='bg-red-600 hover:bg-red-700'
              >
                {t('skills.delete')}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  );
}
