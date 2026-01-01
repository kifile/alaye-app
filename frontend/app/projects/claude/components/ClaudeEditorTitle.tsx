import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Edit, Check, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ConfigScope } from '@/api/types';
import { ScopeBadge } from './ScopeBadge';

export interface ClaudeEditorTitleProps {
  /** 标题文本 */
  title: string;
  /** 当前 Scope（可选） */
  scope?: ConfigScope;
  /** 可用的 Scope 选项（不传则默认所有） */
  availableScopes?: ConfigScope[];
  /** 确认修改回调，传入新的标题和新的 scope */
  onConfirm?: (newTitle: string, newScope?: ConfigScope) => void | Promise<void>;
  /** 标题样式类名 */
  className?: string;
  /** 是否默认处于编辑态（用于新建场景） */
  initialEditing?: boolean;
  /** 是否隐藏确认按钮（新建模式下通过外部保存按钮触发） */
  hideConfirmButton?: boolean;
  /** 取消回调（新建模式下用于返回选择界面） */
  onCancel?: () => void;
  /** 实时变更回调（新建模式下用于实时同步输入到父组件） */
  onChange?: (newTitle: string, newScope?: ConfigScope) => void;
  /** 是否为只读模式 */
  readonly?: boolean;
}

/**
 * Claude 编辑器标题组件
 *
 * 支持点击编辑图标进行标题编辑，同时支持编辑 Scope
 * 按 Enter 确认，按 Escape 取消
 */
export function ClaudeEditorTitle({
  title,
  scope,
  availableScopes,
  onConfirm,
  className = '',
  initialEditing = false,
  hideConfirmButton = false,
  onCancel,
  onChange,
  readonly = false,
}: ClaudeEditorTitleProps) {
  const { t } = useTranslation('projects');

  const [isEditing, setIsEditing] = useState(initialEditing);
  const [editingTitle, setEditingTitle] = useState(title);
  const [editingScope, setEditingScope] = useState<ConfigScope | undefined>(scope);

  // 默认所有 scope 都可用
  const scopes = availableScopes || [
    ConfigScope.USER,
    ConfigScope.PROJECT,
    ConfigScope.LOCAL,
  ];

  // 同步外部 title 和 scope 变化
  useEffect(() => {
    setEditingTitle(title);
  }, [title]);

  useEffect(() => {
    setEditingScope(scope);
  }, [scope]);

  // 开始编辑
  const startEditing = useCallback(() => {
    if (readonly) return;
    setIsEditing(true);
    setEditingTitle(title);
    setEditingScope(scope);
  }, [title, scope, readonly]);

  // 确认修改
  const confirmChange = useCallback(async () => {
    const titleChanged = editingTitle.trim() !== title;
    const scopeChanged = editingScope !== scope;

    if (!titleChanged && !scopeChanged) {
      setIsEditing(false);
      setEditingTitle(title);
      setEditingScope(scope);
      return;
    }

    try {
      if (onConfirm) {
        await onConfirm(editingTitle.trim(), editingScope);
      }
      setIsEditing(false);
    } catch (error) {
      // 恢复原始值
      setEditingTitle(title);
      setEditingScope(scope);
    }
  }, [editingTitle, editingScope, title, scope, onConfirm]);

  // 取消修改
  const cancelEdit = useCallback(() => {
    setIsEditing(false);
    setEditingTitle(title);
    setEditingScope(scope);
  }, [title, scope]);

  // 处理键盘事件
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLInputElement>) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        confirmChange();
      } else if (event.key === 'Escape') {
        event.preventDefault();
        cancelEdit();
      }
    },
    [confirmChange, cancelEdit]
  );

  const titleNode = useMemo(() => {
    if (isEditing) {
      return (
        <div className='flex items-center gap-2'>
          {scopes.length > 0 && (
            <Select
              value={editingScope}
              onValueChange={value => {
                const newScope = value as ConfigScope;
                setEditingScope(newScope);
                onChange?.(editingTitle, newScope);
              }}
            >
              <SelectTrigger className='h-7 w-28 text-xs'>
                <SelectValue placeholder={t('detail.editorTitle.scope')} />
              </SelectTrigger>
              <SelectContent>
                {scopes.map(s => (
                  <SelectItem key={s} value={s} className='text-xs'>
                    {t(`detail.editorTitle.scope_${s}`)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <input
            type='text'
            value={editingTitle}
            onChange={e => {
              const newTitle = e.target.value;
              setEditingTitle(newTitle);
              onChange?.(newTitle, editingScope);
            }}
            onKeyDown={handleKeyDown}
            className='px-2 py-1 text-sm font-medium text-gray-700 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500'
            autoFocus
            placeholder={t('detail.editorTitle.placeholder')}
          />
          {!hideConfirmButton && (
            <>
              <Button
                variant='ghost'
                size='icon'
                onClick={confirmChange}
                className='h-6 w-6 text-green-600 hover:text-green-700'
                title={t('detail.editorTitle.confirm')}
              >
                <Check className='h-4 w-4' />
              </Button>
              {onCancel ? (
                <Button
                  variant='ghost'
                  size='icon'
                  onClick={onCancel}
                  className='h-6 w-6 text-red-600 hover:text-red-700'
                  title={t('detail.editorTitle.cancel')}
                >
                  <X className='h-4 w-4' />
                </Button>
              ) : (
                <Button
                  variant='ghost'
                  size='icon'
                  onClick={cancelEdit}
                  className='h-6 w-6 text-red-600 hover:text-red-700'
                  title={t('detail.editorTitle.cancel')}
                >
                  <X className='h-4 w-4' />
                </Button>
              )}
            </>
          )}
        </div>
      );
    }

    return (
      <div className='flex items-center gap-2'>
        {scope && <ScopeBadge scope={scope} showLabel={true} className='text-xs' />}
        <span className={`text-sm font-medium text-gray-700 ${className}`}>
          {title}
        </span>
        {!readonly && (
          <Button
            variant='ghost'
            size='icon'
            onClick={startEditing}
            className='h-6 w-6 text-gray-500 hover:text-gray-700'
            title={t('detail.editorTitle.editTitle')}
          >
            <Edit className='h-4 w-4' />
          </Button>
        )}
      </div>
    );
  }, [
    isEditing,
    editingTitle,
    editingScope,
    title,
    scope,
    scopes,
    handleKeyDown,
    confirmChange,
    cancelEdit,
    startEditing,
    className,
    hideConfirmButton,
    onCancel,
    readonly,
    t,
  ]);

  return titleNode;
}
