import { useState, useCallback, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { BookOpen, Trash2, Store } from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import {
  listSkillContent,
  readSkillFileContent,
  updateSkillFileContent,
  deleteSkillFile,
  renameClaudeMarkdownContent,
  deleteClaudeMarkdownContent,
  createSkillFile,
  moveSkillFile,
  renameSkillFile,
} from '@/api/api';
import type { ConfigScope, FileType, SkillInfo } from '@/api/types';
import { ConfigScope as ConfigScopeEnum } from '@/api/types';
import { MarkdownEditor } from '@/components/editor';
import { ClaudeEditorTitle } from './ClaudeEditorTitle';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { type FileTreeNode } from '@/components/editor/EditorFileTree';

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
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [hasChanges, setHasChanges] = useState<boolean>(false);
  const [showSaveTooltip, setShowSaveTooltip] = useState<boolean>(false);

  // 删除确认对话框
  const [showDeleteDialog, setShowDeleteDialog] = useState<boolean>(false);

  // 文件树状态
  const [fileTree, setFileTree] = useState<FileTreeNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>('');

  // 加载文件树
  const loadFileTree = useCallback(async () => {
    if (!projectId || !selectedSkill) return;

    try {
      const response = await listSkillContent({
        project_id: projectId,
        name: selectedSkill.name,
        scope: selectedSkill.scope,
      });

      if (response.success && response.data) {
        setFileTree(response.data);
        // 默认选中 SKILL.md 主文件
        const mainFile = response.data.find(f => f.name === 'SKILL.md');
        if (mainFile) {
          setSelectedFile(mainFile.path);
        } else if (response.data.length > 0 && response.data[0].type === 'file') {
          setSelectedFile(response.data[0].path);
        }
      }
    } catch (error) {
      console.error('Failed to load file tree:', error);
    }
  }, [projectId, selectedSkill]);

  // 加载指定 skill 的内容
  const loadSkillContent = useCallback(async () => {
    if (!projectId || !selectedSkill || !selectedFile) return;

    setIsLoading(true);
    try {
      const response = await readSkillFileContent({
        project_id: projectId,
        name: selectedSkill.name,
        scope: selectedSkill.scope,
        file_path: selectedFile,
      });

      if (response.success && response.data !== undefined) {
        // 同时更新原始内容和待保存内容
        const content = response.data;
        setOriginalContent(content);
        setPendingContent(content);
        setHasChanges(false);
      } else {
        // API 返回错误
        toast.error(t('skills.loadFailed'), {
          description: response.error || t('unknownError'),
        });
        setOriginalContent('');
        setPendingContent('');
        setHasChanges(false);
      }
    } catch (error) {
      console.error(t('skills.loadFailed') + ':', error);
      toast.error(t('skills.loadFailed'), {
        description: error instanceof Error ? error.message : t('unknownError'),
      });
      setOriginalContent('');
      setPendingContent('');
      setHasChanges(false);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, selectedSkill, selectedFile, t]);

  // 保存 Skill 内容
  const saveSkillContent = useCallback(async () => {
    if (!projectId || !selectedSkill || !hasChanges || !selectedFile) return;

    setIsSaving(true);
    try {
      const response = await updateSkillFileContent({
        project_id: projectId,
        name: selectedSkill.name,
        scope: selectedSkill.scope,
        file_path: selectedFile,
        content: pendingContent,
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

        // 重新加载内容
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
    selectedFile,
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

  // 删除整个 skill
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

        // 通知父组件 skill 已删除
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
  }, [projectId, selectedSkill, currentSkill, t, onDeleted]);

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

  // 处理文件树选择
  const handleFileTreeSelect = useCallback(
    (file: FileTreeNode) => {
      if (file.type === 'file') {
        // 检查是否有未保存的更改
        if (hasChanges) {
          const confirm = window.confirm(t('skills.unsavedChanges'));
          if (!confirm) return;
        }
        setSelectedFile(file.path);
      }
    },
    [hasChanges, t]
  );

  // 处理文件创建
  const handleFileCreate = useCallback(
    async (parentPath: string, name: string, type: 'file' | 'directory') => {
      if (!projectId || !selectedSkill) return;

      try {
        const response = await createSkillFile({
          project_id: projectId,
          name: selectedSkill.name,
          parent_path: parentPath,
          new_name: name,
          file_type: type as FileType,
          scope: selectedSkill.scope,
        });

        if (response.success) {
          toast.success(`Successfully created ${type} '${name}'`);
          // 重新加载文件树
          await loadFileTree();
        } else {
          toast.error('Failed to create file', {
            description: response.error || 'Unknown error',
          });
        }
      } catch (error) {
        console.error('Failed to create file:', error);
        toast.error('Failed to create file', {
          description: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    },
    [projectId, selectedSkill, loadFileTree]
  );

  // 处理文件删除
  const handleFileDelete = useCallback(
    async (path: string) => {
      if (!projectId || !selectedSkill) return;

      try {
        const response = await deleteSkillFile({
          project_id: projectId,
          name: selectedSkill.name,
          file_path: path,
          scope: selectedSkill.scope,
        });

        if (response.success) {
          toast.success(`Successfully deleted '${path}'`);
          // 重新加载文件树
          await loadFileTree();

          // 如果删除的是当前选中的文件，清空选中状态
          if (selectedFile === path) {
            setSelectedFile('');
          }
        } else {
          toast.error('Failed to delete file', {
            description: response.error || 'Unknown error',
          });
        }
      } catch (error) {
        console.error('Failed to delete file:', error);
        toast.error('Failed to delete file', {
          description: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    },
    [projectId, selectedSkill, selectedFile, loadFileTree]
  );

  // 处理文件移动
  const handleFileMove = useCallback(
    async (sourcePath: string, targetPath: string) => {
      if (!projectId || !selectedSkill) return;

      try {
        const response = await moveSkillFile({
          project_id: projectId,
          name: selectedSkill.name,
          source_path: sourcePath,
          target_path: targetPath,
          scope: selectedSkill.scope,
        });

        if (response.success) {
          toast.success(`Successfully moved '${sourcePath}' to '${targetPath}'`);
          // 重新加载文件树
          await loadFileTree();
        } else {
          toast.error('Failed to move file', {
            description: response.error || 'Unknown error',
          });
        }
      } catch (error) {
        console.error('Failed to move file:', error);
        toast.error('Failed to move file', {
          description: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    },
    [projectId, selectedSkill, loadFileTree]
  );

  // 处理文件重命名
  const handleFileRename = useCallback(
    async (path: string, newFilePath: string) => {
      if (!projectId || !selectedSkill) return;

      try {
        const response = await renameSkillFile({
          project_id: projectId,
          name: selectedSkill.name,
          file_path: path,
          new_file_path: newFilePath,
          scope: selectedSkill.scope,
        });

        if (response.success) {
          toast.success(`Successfully renamed to '${newFilePath}'`);
          // 重新加载文件树
          await loadFileTree();

          // 如果重命名的是当前选中的文件，更新选中路径
          if (selectedFile === path) {
            // 构建新的路径
            const pathParts = path.split('/');
            pathParts[pathParts.length - 1] = newFilePath;
            const newPath = pathParts.join('/');
            setSelectedFile(newPath);
          }
        } else {
          toast.error('Failed to rename file', {
            description: response.error || 'Unknown error',
          });
        }
      } catch (error) {
        console.error('Failed to rename file:', error);
        toast.error('Failed to rename file', {
          description: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    },
    [projectId, selectedSkill, selectedFile, loadFileTree]
  );

  // 组件挂载时加载内容
  useEffect(() => {
    loadFileTree();
  }, [loadFileTree]);

  // 当选中文件变化时，加载文件内容
  useEffect(() => {
    if (selectedFile) {
      loadSkillContent();
    }
  }, [selectedFile, loadSkillContent]);

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
        headerInfo={
          selectedFile && (
            <span className='text-sm text-muted-foreground'>{selectedFile}</span>
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
              <Popover open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
                <PopoverTrigger asChild>
                  <Button
                    variant='ghost'
                    size='sm'
                    className='text-red-600 hover:text-red-700 hover:bg-red-50'
                    title={t('skills.delete')}
                  >
                    <Trash2 className='h-4 w-4' />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className='w-80 p-4' align='end'>
                  <div className='space-y-4'>
                    <div>
                      <h4 className='font-medium'>{t('skills.deleteConfirm')}</h4>
                      <p className='text-sm text-muted-foreground mt-2'>
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
                      </p>
                    </div>
                    <div className='flex justify-end gap-2'>
                      <Button
                        variant='outline'
                        size='sm'
                        onClick={() => setShowDeleteDialog(false)}
                      >
                        {t('skills.cancel')}
                      </Button>
                      <Button
                        variant='destructive'
                        size='sm'
                        onClick={handleDeleteSkill}
                      >
                        {t('skills.delete')}
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
        files={fileTree}
        selectedFile={selectedFile}
        onFileSelect={handleFileTreeSelect}
        onFileCreate={handleFileCreate}
        onFileDelete={handleFileDelete}
        onFileRename={handleFileRename}
        onFileMove={handleFileMove}
      />
    </div>
  );
}
