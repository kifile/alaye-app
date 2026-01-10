import React, { useState, useCallback, useMemo } from 'react';
import { Terminal, Save, X } from 'lucide-react';
import { toast } from 'sonner';
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
      toast.error('请输入命令名称');
      return;
    }

    if (!pendingContent.trim()) {
      toast.error('请输入命令内容');
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
        toast.success('创建成功', {
          description: `Command "${commandName}" 已创建`,
        });
        onSaved(commandName.trim(), commandScope);
      } else {
        toast.error('创建失败', {
          description: response.error || '未知错误',
        });
      }
    } catch (error) {
      console.error('Save command error:', error);
      toast.error('创建失败', {
        description: error instanceof Error ? error.message : '网络错误',
      });
    } finally {
      setIsSaving(false);
    }
  }, [projectId, commandName, pendingContent, commandScope, onSaved]);

  // 自定义标题 ReactNode - 新建模式
  const titleNode = useMemo(() => {
    return (
      <ClaudeEditorTitle
        title={commandName || 'New Command'}
        scope={commandScope}
        availableScopes={[ConfigScopeEnum.USER, ConfigScopeEnum.PROJECT]}
        onConfirm={handleTitleChange}
        onChange={handleTitleChange}
        initialEditing={true}
        hideConfirmButton={true}
        onCancel={onCancelled}
      />
    );
  }, [commandName, commandScope, handleTitleChange, onCancelled]);

  // 自定义 toolbar - 只显示保存按钮和取消按钮
  const customToolbar = useMemo(() => {
    return (
      <div className='flex items-center gap-2'>
        <Button variant='ghost' size='sm' onClick={onCancelled} title='取消'>
          <X className='h-4 w-4 mr-2' />
          取消
        </Button>
        <Button
          variant='default'
          size='sm'
          onClick={handleSave}
          disabled={isSaving || !commandName.trim()}
          title='保存'
        >
          <Save className='h-4 w-4 mr-2' />
          {isSaving ? '保存中...' : '保存'}
        </Button>
      </div>
    );
  }, [handleSave, isSaving, commandName, onCancelled]);

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
