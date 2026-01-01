import React, { useState, useCallback, useMemo } from 'react';
import { Bot, Save, X } from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { saveClaudeMarkdownContent } from '@/api/api';
import type { ConfigScope } from '@/api/types';
import { ConfigScope as ConfigScopeEnum } from '@/api/types';
import { MarkdownEditor } from '@/components/editor';
import { ClaudeEditorTitle } from './ClaudeEditorTitle';
import { Button } from '@/components/ui/button';

interface NewSubAgentContentViewProps {
  projectId: number;
  initialScope?: ConfigScope;
  onSaved: (name: string, scope: ConfigScope) => void;
  onCancelled: () => void;
}

export function NewSubAgentContentView({
  projectId,
  initialScope = ConfigScopeEnum.PROJECT,
  onSaved,
  onCancelled,
}: NewSubAgentContentViewProps) {
  const { t } = useTranslation('projects');

  const [agentName, setAgentName] = useState<string>('');
  const [agentScope, setAgentScope] = useState<ConfigScope>(initialScope);
  const [agentContent, setAgentContent] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);

  // 处理编辑器内容变化
  const handleEditorChange = useCallback((value: string) => {
    setAgentContent(value);
  }, []);

  // 处理标题变更
  const handleTitleChange = useCallback((newTitle: string, newScope?: ConfigScope) => {
    setAgentName(newTitle);
    if (newScope) {
      setAgentScope(newScope);
    }
  }, []);

  // 保存新代理
  const handleSave = useCallback(async () => {
    if (!projectId) return;

    // 验证输入
    if (!agentName.trim()) {
      toast.error(t('subAgents.enterName'));
      return;
    }

    if (!agentContent.trim()) {
      toast.error(t('subAgents.enterContent'));
      return;
    }

    setIsSaving(true);
    try {
      const response = await saveClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'agent',
        name: agentName.trim(),
        content: agentContent,
        scope: agentScope,
      });

      if (response.success) {
        toast.success(t('subAgents.createSuccess'), {
          description: t('subAgents.createSuccessDesc', { name: agentName }),
        });
        onSaved(agentName.trim(), agentScope);
      } else {
        toast.error(t('subAgents.createFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error('Save agent error:', error);
      toast.error(t('subAgents.createFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    } finally {
      setIsSaving(false);
    }
  }, [projectId, agentName, agentContent, agentScope, onSaved, t]);

  // 自定义标题 ReactNode - 新建模式
  const titleNode = useMemo(() => {
    return (
      <ClaudeEditorTitle
        title={agentName || t('subAgents.newAgent')}
        scope={agentScope}
        availableScopes={[ConfigScopeEnum.USER, ConfigScopeEnum.PROJECT]}
        onConfirm={handleTitleChange}
        onChange={handleTitleChange}
        initialEditing={true}
        hideConfirmButton={true}
        onCancel={onCancelled}
      />
    );
  }, [agentName, agentScope, handleTitleChange, onCancelled, t]);

  // 自定义 toolbar - 只显示保存按钮和取消按钮
  const customToolbar = useMemo(() => {
    return (
      <div className='flex items-center gap-2'>
        <Button
          variant='ghost'
          size='sm'
          onClick={onCancelled}
          title={t('subAgents.cancel')}
        >
          <X className='h-4 w-4 mr-2' />
          {t('subAgents.cancel')}
        </Button>
        <Button
          variant='default'
          size='sm'
          onClick={handleSave}
          disabled={isSaving || !agentName.trim()}
          title={t('subAgents.save')}
        >
          <Save className='h-4 w-4 mr-2' />
          {isSaving ? t('subAgents.saving') : t('subAgents.save')}
        </Button>
      </div>
    );
  }, [handleSave, isSaving, agentName, onCancelled, t]);

  return (
    <div className='h-full flex flex-col'>
      <MarkdownEditor
        title={titleNode}
        value={agentContent}
        onChange={handleEditorChange}
        onSave={handleSave}
        isLoading={false}
        isSaving={isSaving}
        hasChanges={true}
        showSaveTooltip={false}
        icon={<Bot className='h-4 w-4 text-gray-500' />}
        customToolbar={customToolbar}
        className='flex-1 flex flex-col'
      />
    </div>
  );
}
