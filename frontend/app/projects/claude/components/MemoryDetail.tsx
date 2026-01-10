import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { FileText } from 'lucide-react';
import {
  loadClaudeMarkdownContent,
  updateClaudeMarkdownContent,
  scanClaudeMemory,
} from '@/api/api';
import type { ClaudeMemoryInfo } from '@/api/types';
import { MarkdownEditor } from '@/components/editor';
import { ConfigScope } from '@/api/types';
import { useTranslation } from 'react-i18next';
import { useDetailHeader } from '../context/DetailHeaderContext';

type MemoryType =
  | 'project_claude_md'
  | 'claude_dir_claude_md'
  | 'local_claude_md'
  | 'user_global_claude_md';

interface MemoryFile {
  key: MemoryType;
  name: string;
  description: string;
  path: string;
}

interface MemoryDetailProps {
  projectId: number;
}

interface EditorState {
  originalContent: string;
  pendingContent: string;
  md5: string;
  hasChanges: boolean;
  showSaveTooltip: boolean;
}

interface LoadingState {
  isLoading: boolean;
  isSaving: boolean;
}

export function MemoryDetail({ projectId }: MemoryDetailProps) {
  const { t } = useTranslation('projects');
  const { setScopeSwitcher, clearScopeSwitcher } = useDetailHeader();

  // 合并相关状态
  const [editorState, setEditorState] = useState<EditorState>({
    originalContent: '',
    pendingContent: '',
    md5: '',
    hasChanges: false,
    showSaveTooltip: false,
  });

  const [loadingState, setLoadingState] = useState<LoadingState>({
    isLoading: false,
    isSaving: false,
  });

  const [memoryInfo, setMemoryInfo] = useState<ClaudeMemoryInfo | null>(null);
  const [currentScope, setCurrentScope] = useState<ConfigScope>(ConfigScope.PROJECT);

  // 使用 useMemo 缓存 memory files 配置
  const memoryFiles = useMemo<MemoryFile[]>(
    () => [
      {
        key: 'project_claude_md',
        name: t('memory.tabs.projectClaudeMd'),
        description: t('memory.descriptions.projectClaudeMd'),
        path: 'CLAUDE.md',
      },
      {
        key: 'claude_dir_claude_md',
        name: t('memory.tabs.claudeDirClaudeMd'),
        description: t('memory.descriptions.claudeDirClaudeMd'),
        path: '.claude/CLAUDE.md',
      },
      {
        key: 'local_claude_md',
        name: t('memory.tabs.localClaudeMd'),
        description: t('memory.descriptions.localClaudeMd'),
        path: 'CLAUDE.local.md',
      },
      {
        key: 'user_global_claude_md',
        name: t('memory.tabs.userGlobalClaudeMd'),
        description: t('memory.descriptions.userGlobalClaudeMd'),
        path: '~/.claude/CLAUDE.md',
      },
    ],
    [t]
  );

  // 根据 scope 获取对应的 MemoryType
  const getMemoryTypeByScope = useCallback(
    (scope: ConfigScope): MemoryType => {
      switch (scope) {
        case ConfigScope.USER:
          return 'user_global_claude_md';
        case ConfigScope.LOCAL:
          return 'local_claude_md';
        case ConfigScope.PROJECT:
          return memoryInfo?.claude_dir_claude_md
            ? 'claude_dir_claude_md'
            : 'project_claude_md';
        default:
          return 'project_claude_md';
      }
    },
    [memoryInfo]
  );

  // 获取当前 scope 对应的 MemoryFile
  const currentFile = useMemo<MemoryFile>(() => {
    const memoryType = getMemoryTypeByScope(currentScope);
    return memoryFiles.find(f => f.key === memoryType) || memoryFiles[0];
  }, [currentScope, getMemoryTypeByScope, memoryFiles]);

  // 加载当前 scope 的 Memory 内容
  const loadMemoryContent = useCallback(async () => {
    if (!projectId) return;

    setLoadingState(prev => ({ ...prev, isLoading: true }));
    try {
      const memoryType = getMemoryTypeByScope(currentScope);
      const response = await loadClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'memory',
        name: memoryType,
      });

      if (response.success && response.data) {
        setEditorState({
          originalContent: response.data.content,
          pendingContent: response.data.content,
          md5: response.data.md5,
          hasChanges: false,
          showSaveTooltip: false,
        });
      } else {
        // 文件不存在时显示空内容
        setEditorState(prev => ({
          ...prev,
          originalContent: '',
          pendingContent: '',
          md5: '',
          hasChanges: false,
        }));
      }
    } catch (error) {
      console.error('加载 Memory 失败:', error);
      setEditorState(prev => ({
        ...prev,
        originalContent: '',
        pendingContent: '',
        md5: '',
        hasChanges: false,
      }));
    } finally {
      setLoadingState(prev => ({ ...prev, isLoading: false }));
    }
  }, [projectId, currentScope, getMemoryTypeByScope]);

  // 扫描 Claude Memory 信息
  const scanMemoryInfo = useCallback(async () => {
    if (!projectId) return;

    try {
      const response = await scanClaudeMemory({
        project_id: projectId,
      });

      if (response.success && response.data) {
        setMemoryInfo(response.data);
      }
    } catch (error) {
      console.error('扫描 Claude Memory 失败:', error);
    }
  }, [projectId]);

  // 保存 Memory 内容
  const saveMemoryContent = useCallback(async () => {
    if (!projectId || !editorState.hasChanges) return;

    setLoadingState(prev => ({ ...prev, isSaving: true }));
    try {
      const memoryType = getMemoryTypeByScope(currentScope);
      const response = await updateClaudeMarkdownContent({
        project_id: projectId,
        content_type: 'memory',
        name: memoryType,
        from_md5: editorState.md5,
        content: editorState.pendingContent,
      });

      if (response.success) {
        setEditorState(prev => ({
          ...prev,
          originalContent: editorState.pendingContent,
          pendingContent: editorState.pendingContent,
          hasChanges: false,
          showSaveTooltip: true,
        }));

        // 2秒后隐藏保存成功提示
        setTimeout(() => {
          setEditorState(prev => ({ ...prev, showSaveTooltip: false }));
        }, 2000);

        // 并行执行刷新操作
        await Promise.all([loadMemoryContent(), scanMemoryInfo()]);
      }
    } catch (error) {
      console.error('保存 Memory 失败:', error);
    } finally {
      setLoadingState(prev => ({ ...prev, isSaving: false }));
    }
  }, [
    projectId,
    currentScope,
    editorState.pendingContent,
    editorState.md5,
    editorState.hasChanges,
    getMemoryTypeByScope,
    loadMemoryContent,
    scanMemoryInfo,
  ]);

  // 刷新当前 Memory 内容
  const refreshMemoryContent = useCallback(async () => {
    await Promise.all([loadMemoryContent(), scanMemoryInfo()]);
  }, [loadMemoryContent, scanMemoryInfo]);

  // 处理编辑器内容变化
  const handleEditorChange = useCallback((value: string) => {
    setEditorState(prev => ({
      ...prev,
      pendingContent: value,
      hasChanges: value !== prev.originalContent,
    }));
  }, []);

  // 初始化：扫描 Memory 信息并智能选择初始 scope
  useEffect(() => {
    const initialize = async () => {
      await scanMemoryInfo();

      // 智能选择初始 scope：优先级为 PROJECT > LOCAL > USER
      if (memoryInfo) {
        const firstAvailableScope = (
          [ConfigScope.PROJECT, ConfigScope.LOCAL, ConfigScope.USER] as const
        ).find(scope => {
          const memoryType = getMemoryTypeByScope(scope);
          return memoryInfo?.[memoryType];
        });

        if (firstAvailableScope) {
          setCurrentScope(firstAvailableScope);
        }
      }
    };

    initialize();
  }, []); // 只在组件挂载时执行一次

  // 处理 Scope 变化
  const handleScopeChange = useCallback(
    (scope: ConfigScope | 'mixed' | null) => {
      if (editorState.hasChanges) {
        const confirmed = window.confirm(t('memory.unsavedChanges'));
        if (!confirmed) return;
      }

      if (scope && scope !== 'mixed') {
        setCurrentScope(scope);
      }
    },
    [editorState.hasChanges, t]
  );

  // 设置 ScopeSwitcher 配置
  useEffect(() => {
    setScopeSwitcher({
      enabled: true,
      supportedScopes: [ConfigScope.USER, ConfigScope.PROJECT, ConfigScope.LOCAL],
      value: currentScope,
      onChange: handleScopeChange,
    });

    return () => {
      clearScopeSwitcher();
    };
  }, [setScopeSwitcher, clearScopeSwitcher, currentScope, handleScopeChange]);

  // 当 currentScope 变化时加载对应的内容
  useEffect(() => {
    loadMemoryContent();
  }, [currentScope, loadMemoryContent]);

  return (
    <div className='h-full flex flex-col p-4'>
      <MarkdownEditor
        title={currentFile.path}
        defaultValue={editorState.originalContent}
        onChange={handleEditorChange}
        onSave={saveMemoryContent}
        onRefresh={refreshMemoryContent}
        isLoading={loadingState.isLoading}
        isSaving={loadingState.isSaving}
        hasChanges={editorState.hasChanges}
        showSaveTooltip={editorState.showSaveTooltip}
        icon={<FileText className='h-4 w-4 text-gray-500' />}
        headerInfo={currentFile.description}
        className='flex-1 flex flex-col'
      />
    </div>
  );
}
