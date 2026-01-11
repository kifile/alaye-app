import React, { useState, useCallback, useMemo } from 'react';
import { Terminal, Save, X } from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { saveClaudeMarkdownContent } from '@/api/api';
import type { ConfigScope } from '@/api/types';
import { ConfigScope as ConfigScopeEnum } from '@/api/types';
import { MarkdownEditor } from '@/components/editor';
import { ClaudeEditorTitle } from './ClaudeEditorTitle';
import { Button } from '@/components/ui/button';

interface NewCommandContentViewProps {
  projectId: number;
  initialScope?: ConfigScope;
  onSaved: (name: string, scope: ConfigScope) => void;
  onCancelled: () => void;
}

export function NewCommandContentView({
  projectId,
  initialScope = ConfigScopeEnum.PROJECT,
  onSaved,
  onCancelled,
}: NewCommandContentViewProps) {
  const { t } = useTranslation('projects');
  const [commandName, setCommandName] = useState<string>('');
  const [commandScope, setCommandScope] = useState<ConfigScope>(initialScope);
  // originalContent 始终为空（新建模式）
  // pendingContent 跟踪用户编辑的内容
  const [pendingContent, setPendingContent] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);

  // 处理编辑器内容变化
  const handleEditorChange = useCallback((value: string) => {
    setPendingContent(value);
  }, []);

  // 处理标题变更
  const handleTitleChange = useCallback((newTitle: string, newScope?: ConfigScope) => {
    setCommandName(newTitle);
    if (newScope) {
      setCommandScope(newScope);
    }
  }, []);

  // 保存新命令
  const handleSave = useCallback(async () => {
    if (!projectId) return;

    // 验证输入
    if (!commandName.trim()) {
      toast.error(t('commands.enterName'));
      return;
    }

    if (!pendingContent.trim()) {
      toast.error(t('commands.enterContent'));
      return;
    }

    setIsSaving(true);
    try {
      const response = await saveClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'command',
        name: commandName.trim(),
        content: pendingContent,
        scope: commandScope,
      });

      if (response.success) {
        toast.success(t('commands.createSuccess'), {
          description: t('commands.createSuccessDesc', { name: commandName }),
        });
        onSaved(commandName.trim(), commandScope);
      } else {
        toast.error(t('commands.createFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error('Save command error:', error);
      toast.error(t('commands.createFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    } finally {
      setIsSaving(false);
    }
  }, [projectId, commandName, pendingContent, commandScope, onSaved, t]);

  // 自定义标题 ReactNode - 新建模式
  const titleNode = useMemo(() => {
    return (
      <ClaudeEditorTitle
        title={commandName || t('commands.newCommand')}
        scope={commandScope}
        availableScopes={[ConfigScopeEnum.USER, ConfigScopeEnum.PROJECT]}
        onConfirm={handleTitleChange}
        onChange={handleTitleChange}
        initialEditing={true}
        hideConfirmButton={true}
        onCancel={onCancelled}
      />
    );
  }, [commandName, commandScope, handleTitleChange, onCancelled, t]);

  // 自定义 toolbar - 只显示保存按钮和取消按钮
  const customToolbar = useMemo(() => {
    return (
      <div className='flex items-center gap-2'>
        <Button
          variant='ghost'
          size='sm'
          onClick={onCancelled}
          title={t('commands.cancel')}
        >
          <X className='h-4 w-4 mr-2' />
          {t('commands.cancel')}
        </Button>
        <Button
          variant='default'
          size='sm'
          onClick={handleSave}
          disabled={isSaving || !commandName.trim()}
          title={t('commands.save')}
        >
          <Save className='h-4 w-4 mr-2' />
          {isSaving ? t('commands.saving') : t('commands.save')}
        </Button>
      </div>
    );
  }, [handleSave, isSaving, commandName, onCancelled, t]);

  return (
    <div className='h-full flex flex-col'>
      <MarkdownEditor
        title={titleNode}
        defaultValue=''
        onChange={handleEditorChange}
        onSave={handleSave}
        isLoading={false}
        isSaving={isSaving}
        hasChanges={true}
        showSaveTooltip={false}
        icon={<Terminal className='h-4 w-4 text-gray-500' />}
        customToolbar={customToolbar}
        className='flex-1 flex flex-col'
      />
    </div>
  );
}
