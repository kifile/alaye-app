import React, { useState, useCallback, useMemo } from 'react';
import { BookOpen, Save, X } from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { saveClaudeMarkdownContent } from '@/api/api';
import type { ConfigScope } from '@/api/types';
import { ConfigScope as ConfigScopeEnum } from '@/api/types';
import { MarkdownEditor } from '@/components/editor';
import { ClaudeEditorTitle } from './ClaudeEditorTitle';
import { Button } from '@/components/ui/button';

interface NewSkillContentViewProps {
  projectId: number;
  initialScope?: ConfigScope;
  onSaved: (name: string, scope: ConfigScope) => void;
  onCancelled: () => void;
}

export function NewSkillContentView({
  projectId,
  initialScope = ConfigScopeEnum.PROJECT,
  onSaved,
  onCancelled,
}: NewSkillContentViewProps) {
  const { t } = useTranslation('projects');

  const [skillName, setSkillName] = useState<string>('');
  const [skillScope, setSkillScope] = useState<ConfigScope>(initialScope);
  const [skillContent, setSkillContent] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);

  // 处理编辑器内容变化
  const handleEditorChange = useCallback((value: string) => {
    setSkillContent(value);
  }, []);

  // 处理标题变更
  const handleTitleChange = useCallback((newTitle: string, newScope?: ConfigScope) => {
    setSkillName(newTitle);
    if (newScope) {
      setSkillScope(newScope);
    }
  }, []);

  // 保存新 skill
  const handleSave = useCallback(async () => {
    if (!projectId) return;

    // 验证输入
    if (!skillName.trim()) {
      toast.error(t('skills.enterName'));
      return;
    }

    if (!skillContent.trim()) {
      toast.error(t('skills.enterContent'));
      return;
    }

    setIsSaving(true);
    try {
      const response = await saveClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'skill',
        name: skillName.trim(),
        content: skillContent,
        scope: skillScope,
      });

      if (response.success) {
        toast.success(t('skills.createSuccess'), {
          description: t('skills.createSuccessDesc', { name: skillName }),
        });
        onSaved(skillName.trim(), skillScope);
      } else {
        toast.error(t('skills.createFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error('Save skill error:', error);
      toast.error(t('skills.createFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    } finally {
      setIsSaving(false);
    }
  }, [projectId, skillName, skillContent, skillScope, onSaved, t]);

  // 自定义标题 ReactNode - 新建模式
  const titleNode = useMemo(() => {
    return (
      <ClaudeEditorTitle
        title={skillName || t('skills.newSkill')}
        scope={skillScope}
        availableScopes={[ConfigScopeEnum.PROJECT]}
        onConfirm={handleTitleChange}
        onChange={handleTitleChange}
        initialEditing={true}
        hideConfirmButton={true}
        onCancel={onCancelled}
      />
    );
  }, [skillName, skillScope, handleTitleChange, onCancelled, t]);

  // 自定义 toolbar - 只显示保存按钮和取消按钮
  const customToolbar = useMemo(() => {
    return (
      <div className='flex items-center gap-2'>
        <Button
          variant='ghost'
          size='sm'
          onClick={onCancelled}
          title={t('skills.cancel')}
        >
          <X className='h-4 w-4 mr-2' />
          {t('skills.cancel')}
        </Button>
        <Button
          variant='default'
          size='sm'
          onClick={handleSave}
          disabled={isSaving || !skillName.trim()}
          title={t('skills.save')}
        >
          <Save className='h-4 w-4 mr-2' />
          {isSaving ? t('skills.saving') : t('skills.save')}
        </Button>
      </div>
    );
  }, [handleSave, isSaving, skillName, onCancelled, t]);

  return (
    <div className='h-full flex flex-col'>
      <MarkdownEditor
        title={titleNode}
        value={skillContent}
        onChange={handleEditorChange}
        onSave={handleSave}
        isLoading={false}
        isSaving={isSaving}
        hasChanges={true}
        showSaveTooltip={false}
        icon={<BookOpen className='h-4 w-4 text-gray-500' />}
        customToolbar={customToolbar}
        className='flex-1 flex flex-col'
      />
    </div>
  );
}
