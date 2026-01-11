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
  /** 编辑器内容（受控模式，使用 value） */
  value?: string;
  /** 编辑器初始值（非受控模式，使用 defaultValue） */
  defaultValue?: string;
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
 * 架构说明：
 * - 支持受控和非受控两种模式
 * - 受控模式：使用 value prop，每次 value 变化时更新编辑器
 * - 非受控模式：使用 defaultValue prop，只在 defaultValue 变化时更新编辑器
 * - onChange 回调不会引起编辑器重新初始化，避免光标跳动问题
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
  defaultValue,
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
  // 记录上次处理的值，用于检测外部变化
  const lastProcessedValueRef = useRef<string>('');
  const [showCopyTooltip, setShowCopyTooltip] = useState(false);

  // Monaco 准备状态
  const [isMonacoReady, setIsMonacoReady] = useState(isMonacoPreloaded());

  // 确定当前应该使用的内容值
  // 受控模式：使用 value；非受控模式：使用 defaultValue（仅初始化）
  const currentValue = value !== undefined ? value : defaultValue || '';

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
      // 初始化 lastProcessedValueRef（使用编辑器当前值）
      lastProcessedValueRef.current = editor.getValue() || currentValue;
      console.log('[MarkdownEditor] Editor mounted successfully');
    },
    [currentValue]
  );

  // 处理编辑器内容变化
  const handleEditorChange = useCallback(
    (newValue: string | undefined) => {
      if (!editorRef.current || readonly) return;

      // 统一换行符为 \n，避免 Windows 上的 \r\n 导致保存后空行变多
      const content = (newValue || '').replace(/\r\n/g, '\n');

      // 更新 ref，避免被 useEffect 误认为是外部变化
      lastProcessedValueRef.current = content;

      // 通知外部组件（如果提供了 onChange）
      if (onChange) {
        onChange(content);
      }
    },
    [onChange, readonly]
  );

  // 处理拷贝功能
  const handleCopy = useCallback(async () => {
    try {
      // 从编辑器获取当前内容，而不是使用 props 中的 value
      const content = editorRef.current?.getValue() || currentValue;
      await navigator.clipboard.writeText(content);
      setShowCopyTooltip(true);
      setTimeout(() => setShowCopyTooltip(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  }, [currentValue]);

  // 当外部值改变时更新编辑器
  // 支持两种模式：
  // 1. 受控模式：value 变化时更新
  // 2. 非受控模式：defaultValue 变化时更新
  useEffect(() => {
    if (!editorRef.current) return;

    const editor = editorRef.current;

    // 判断是否需要更新
    let shouldUpdate = false;

    if (value !== undefined) {
      // 受控模式：value 变化时更新
      shouldUpdate =
        value !== lastProcessedValueRef.current && value !== editor.getValue();
    } else {
      // 非受控模式：defaultValue 变化时更新
      shouldUpdate =
        defaultValue !== undefined &&
        defaultValue !== lastProcessedValueRef.current &&
        defaultValue !== editor.getValue();
    }

    if (shouldUpdate) {
      const position = editor.getPosition();

      // 更新编辑器内容
      editor.setValue(currentValue);
      lastProcessedValueRef.current = currentValue;

      // 恢复光标位置
      if (position) {
        requestAnimationFrame(() => {
          if (editorRef.current) {
            editorRef.current.setPosition(position);
          }
        });
      }
    }
  }, [value, defaultValue, currentValue]);

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
            // 使用 defaultValue 实现非受控模式，避免频繁更新
            defaultValue={currentValue}
            value={undefined}
            onMount={handleEditorMount}
            onChange={readonly ? undefined : handleEditorChange}
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
