import React, { useEffect, useCallback, useRef, useState } from 'react';
import { Save, RefreshCw, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Editor, { Monaco } from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import { useTranslation } from 'react-i18next';
import { loadComponentTranslations, getCurrentLanguage } from '@/lib/i18n';
import {
  isMonacoPreloaded,
  getPreloadPromise,
  preloadMonacoEditor,
} from '@/lib/monaco-preloader';

export interface MarkdownEditorProps {
  /** 编辑器标题（支持 string 或 ReactNode） */
  title?: React.ReactNode | string;
  /** 编辑器内容 */
  value: string;
  /** 内容变更回调（可选） */
  onChange?: (value: string) => void;
  /** 保存回调（可选） */
  onSave?: () => void | Promise<void>;
  /** 刷新回调 (当使用 customToolbar 时可选) */
  onRefresh?: () => void | Promise<void>;
  /** 是否正在加载 */
  isLoading?: boolean;
  /** 是否正在保存 */
  isSaving?: boolean;
  /** 是否有变更 */
  hasChanges?: boolean;
  /** 编辑器高度 */
  height?: string | number;
  /** 编辑器语言 */
  language?: string;
  /** 是否显示保存成功提示 */
  showSaveTooltip?: boolean;
  /** 额外的头部信息 */
  headerInfo?: React.ReactNode;
  /** 自定义图标 */
  icon?: React.ReactNode;
  /** 禁用快捷键 */
  disableShortcuts?: boolean;
  /** 工具栏右侧额外操作按钮 */
  toolbarActions?: React.ReactNode;
  /** 完全自定义工具栏（替换默认工具栏） */
  customToolbar?: React.ReactNode;
  /** 自定义容器类名 */
  className?: string;
  /** 是否为只读模式 */
  readonly?: boolean;
}

/**
 * 通用的 Markdown 编辑器组件
 *
 * 功能特性：
 * - Monaco 编辑器集成
 * - 工具栏（保存、刷新）
 * - 键盘快捷键（Ctrl+S 保存，Ctrl+R 刷新）
 * - 加载和保存状态显示
 * - 可配置的语言和高度
 */
export function MarkdownEditor({
  title,
  value,
  onChange,
  onSave,
  onRefresh,
  isLoading = false,
  isSaving = false,
  hasChanges = false,
  height = 500,
  language = 'markdown',
  showSaveTooltip = false,
  headerInfo,
  icon,
  disableShortcuts = false,
  toolbarActions,
  customToolbar,
  className = '',
  readonly = false,
}: MarkdownEditorProps) {
  // 加载组件翻译
  loadComponentTranslations('editor', getCurrentLanguage());

  const { t } = useTranslation('editor');
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const lastValueRef = useRef<string>(value);
  const [showCopyTooltip, setShowCopyTooltip] = useState(false);

  // Monaco 准备状态
  const [isMonacoReady, setIsMonacoReady] = useState(isMonacoPreloaded());

  // 等待 Monaco 预加载完成
  useEffect(() => {
    if (isMonacoReady) return;

    let mounted = true;
    const promise = getPreloadPromise() || preloadMonacoEditor();

    promise
      .then(() => {
        if (mounted) {
          setIsMonacoReady(true);
        }
      })
      .catch(err => {
        console.error('[MarkdownEditor] Failed to wait for preload:', err);
        // 即使预加载失败，也允许继续，让 Editor 组件自己初始化
        if (mounted) {
          setIsMonacoReady(true);
        }
      });

    return () => {
      mounted = false;
    };
  }, [isMonacoReady]);

  // 处理编辑器挂载
  const handleEditorMount = useCallback(
    (editor: editor.IStandaloneCodeEditor, monaco: Monaco) => {
      editorRef.current = editor;
      lastValueRef.current = value;
      console.log('[MarkdownEditor] Editor mounted successfully');
    },
    [value]
  );

  // 处理编辑器内容变化
  const handleEditorChange = useCallback(
    (newValue: string | undefined) => {
      if (!editorRef.current || readonly || !onChange) return;

      // 统一换行符为 \n，避免 Windows 上的 \r\n 导致保存后空行变多
      const content = (newValue || '').replace(/\r\n/g, '\n');
      lastValueRef.current = content;
      onChange(content);
    },
    [onChange, readonly]
  );

  // 处理拷贝功能
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(value);
      setShowCopyTooltip(true);
      setTimeout(() => setShowCopyTooltip(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  }, [value]);

  // 当外部值改变时更新编辑器
  useEffect(() => {
    if (editorRef.current && value !== lastValueRef.current) {
      const position = editorRef.current.getPosition();
      editorRef.current.setValue(value);
      lastValueRef.current = value;
      // 尝试恢复光标位置
      if (position) {
        editorRef.current.setPosition(position);
      }
    }
  }, [value]);

  // 键盘快捷键处理
  useEffect(() => {
    if (disableShortcuts) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // 检查是否按下了 Ctrl 或 Cmd
      if (event.ctrlKey || event.metaKey) {
        switch (event.key.toLowerCase()) {
          case 's':
            // Ctrl+S: 保存
            event.preventDefault();
            if (onSave && hasChanges && !isSaving && !isLoading) {
              onSave();
            }
            break;
          case 'r':
            // Ctrl+R: 刷新
            event.preventDefault();
            if (!isLoading && onRefresh) {
              onRefresh();
            }
            break;
        }
      }
    };

    // 添加键盘事件监听
    window.addEventListener('keydown', handleKeyDown);

    // 清理事件监听
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [disableShortcuts, hasChanges, isSaving, isLoading, onSave, onRefresh]);

  return (
    <div
      className={`bg-white border border-gray-200 rounded-xl overflow-hidden ${className}`}
    >
      {/* Editor Toolbar */}
      <div className='flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200'>
        <div className='flex items-center gap-2'>
          {icon && (
            <div className='flex items-center gap-2'>
              {icon}
              {title && (
                <span className='text-sm font-medium text-gray-700'>{title}</span>
              )}
            </div>
          )}
          {!icon && title && (
            <span className='text-sm font-medium text-gray-700'>{title}</span>
          )}
          {headerInfo && <div className='text-xs text-gray-500'>{headerInfo}</div>}
        </div>

        {customToolbar ? (
          <div>{customToolbar}</div>
        ) : (
          <div className='flex items-center gap-2'>
            {/* 保存成功提示 */}
            {showSaveTooltip && (
              <div className='text-xs py-1 mr-2 text-gray-600'>{t('saveSuccess')}</div>
            )}

            {/* 拷贝成功提示 */}
            {showCopyTooltip && (
              <div className='text-xs py-1 mr-2 text-gray-600'>{t('copySuccess')}</div>
            )}

            {/* 工具栏额外操作按钮 */}
            {toolbarActions}

            {/* 拷贝按钮 */}
            <Button
              variant='outline'
              size='icon'
              onClick={handleCopy}
              className='h-8 w-8'
              title={t('copyShortcut')}
            >
              <Copy className='h-4 w-4' />
            </Button>

            {onRefresh && (
              <Button
                variant='outline'
                size='icon'
                onClick={onRefresh}
                disabled={isLoading}
                className='h-8 w-8'
                title={t('refreshShortcut')}
              >
                <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              </Button>
            )}

            {/* 只读模式下不显示保存按钮 */}
            {!readonly && onSave && (
              <Button
                variant={hasChanges ? 'default' : 'outline'}
                size='icon'
                onClick={onSave}
                disabled={!hasChanges || isSaving || isLoading}
                className='h-8 w-8'
                title={isSaving ? t('savingShortcut') : t('saveShortcut')}
              >
                <Save className='h-4 w-4' />
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Monaco Editor */}
      <div
        className={className?.includes('flex-1') ? 'flex-1 flex flex-col' : ''}
        style={
          className?.includes('flex-1')
            ? undefined
            : { height: typeof height === 'number' ? `${height}px` : height }
        }
      >
        {!isMonacoReady ? (
          // Monaco 预加载中
          <div className='flex items-center justify-center h-full bg-gray-50'>
            <div className='text-center space-y-2'>
              <div className='w-8 h-8 mx-auto border-2 border-blue-600 border-t-transparent rounded-full animate-spin'></div>
              <p className='text-sm text-muted-foreground'>
                {t('loading') || 'Loading editor...'}
              </p>
            </div>
          </div>
        ) : (
          <Editor
            height='100%'
            defaultLanguage={language}
            value={value}
            onMount={handleEditorMount}
            onChange={readonly || !onChange ? undefined : handleEditorChange}
            loading={isLoading ? t('loading') : undefined}
            options={{
              minimap: { enabled: false },
              wordWrap: 'on',
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              fontSize: 14,
              fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
              theme: 'vs-light',
              automaticLayout: true,
              tabSize: 2,
              insertSpaces: true,
              readOnly: readonly,
            }}
          />
        )}
      </div>
    </div>
  );
}
