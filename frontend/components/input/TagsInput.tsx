'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export interface TagsInputProps {
  value: string[];
  onChange?: (tags: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  allowEmptyValues?: boolean;
  maxItems?: number;
  validator?: (value: string) => string | null;
  delimiter?: string | RegExp; // 自定义分隔符（仅用于粘贴操作），支持逗号、空格等
  allowDuplicates?: boolean; // 是否允许重复标签
  className?: string;
  onValidationError?: (error: string) => void;
  saving?: boolean; // 保存中状态
  maxItemsError?: string; // 最大数量错误提示
  duplicateError?: string; // 重复标签错误提示
}

export function TagsInput({
  value = [],
  onChange,
  placeholder = '输入内容后按回车添加',
  disabled = false,
  allowEmptyValues = false,
  maxItems,
  validator,
  delimiter,
  allowDuplicates = false,
  className = '',
  onValidationError,
  saving = false,
  maxItemsError,
  duplicateError,
}: TagsInputProps) {
  const { t } = useTranslation('preference');
  const [tags, setTags] = useState<string[]>(value);
  const [inputValue, setInputValue] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // 统一的错误显示函数
  const showError = useCallback(
    (error: string) => {
      setValidationError(error);
      if (onValidationError) {
        onValidationError(error);
      }
    },
    [onValidationError]
  );

  // 同步外部 value 变化
  useEffect(() => {
    setTags(value);
  }, [value]);

  // 通知父组件标签变化
  const notifyChange = useCallback(
    (newTags: string[]) => {
      setTags(newTags);
      if (onChange) {
        onChange(newTags);
      }
    },
    [onChange]
  );

  // 添加标签
  const addTag = useCallback(
    (tagToAdd: string) => {
      const trimmedTag = tagToAdd.trim();

      // 检查是否为空
      if (!trimmedTag && !allowEmptyValues) {
        return;
      }

      // 验证标签
      if (validator) {
        const error = validator(trimmedTag);
        if (error) {
          showError(error);
          return;
        }
      }

      // 检查最大数量
      if (maxItems && tags.length >= maxItems) {
        showError(maxItemsError || t('tagsInput.maxItemsError', { max: maxItems }));
        return;
      }

      // 检查重复
      if (!allowDuplicates && tags.includes(trimmedTag)) {
        showError(duplicateError || t('tagsInput.duplicateError'));
        return;
      }

      // 添加标签
      const newTags = [...tags, trimmedTag];
      notifyChange(newTags);
      setValidationError(null);
    },
    [
      tags,
      allowEmptyValues,
      validator,
      maxItems,
      allowDuplicates,
      notifyChange,
      showError,
      maxItemsError,
      duplicateError,
    ]
  );

  // 删除标签
  const removeTag = useCallback(
    (tagToRemove: string) => {
      const newTags = tags.filter(tag => tag !== tagToRemove);
      notifyChange(newTags);
    },
    [tags, notifyChange]
  );

  // 处理输入变化
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
    setValidationError(null);
  };

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (inputValue) {
        addTag(inputValue);
        setInputValue('');
      }
    } else if (e.key === 'Backspace' && !inputValue && tags.length > 0) {
      // 当输入框为空且按下删除键时，删除最后一个标签
      removeTag(tags[tags.length - 1]);
    } else if (e.key === 'Escape') {
      setInputValue('');
      setValidationError(null);
    }
  };

  // 处理失焦
  const handleBlur = () => {
    if (inputValue.trim() && allowEmptyValues) {
      addTag(inputValue);
      setInputValue('');
    } else {
      setValidationError(null);
    }
  };

  // 处理粘贴事件（支持从剪贴板粘贴多个标签）
  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedText = e.clipboardData.getData('text');

    if (delimiter) {
      // 使用分隔符分割
      const splitTags = pastedText
        .split(delimiter)
        .map(tag => tag.trim())
        .filter(Boolean);
      splitTags.forEach(tag => addTag(tag));
    } else {
      // 直接添加
      addTag(pastedText);
    }
    setInputValue('');
  };

  const isMaxItemsReached = maxItems && tags.length >= maxItems;
  const isInteractive = !disabled && !saving && !isMaxItemsReached;

  return (
    <div
      className={`
        min-h-[44px] rounded-[8px] bg-slate-100 px-3 py-2
        flex flex-wrap items-center gap-2
        ${isInteractive ? 'cursor-text' : ''}
        ${saving ? 'animate-pulse border-0.5 border-blue-400' : ''}
        ${className}
      `}
      onClick={() => {
        if (isInteractive) {
          inputRef.current?.focus();
        }
      }}
    >
      {/* 渲染标签 */}
      {tags.map((tag, index) => (
        <span
          key={index}
          className='inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-white text-slate-900 rounded-md border border-slate-200'
        >
          <span className='max-w-[200px] truncate'>{tag}</span>
          {!disabled && !saving && (
            <button
              type='button'
              onClick={e => {
                e.stopPropagation();
                removeTag(tag);
              }}
              className='text-slate-400 hover:text-red-600 hover:bg-red-50 rounded p-0.5 transition-colors'
              title='删除'
            >
              <X className='w-3 h-3' />
            </button>
          )}
        </span>
      ))}

      {/* 输入框 */}
      {isInteractive && (
        <input
          ref={inputRef}
          type='text'
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          onPaste={handlePaste}
          placeholder={tags.length === 0 ? placeholder : ''}
          className='flex-1 min-w-[60px] bg-transparent text-sm text-slate-900 outline-none placeholder:text-muted-foreground'
        />
      )}

      {/* 禁用或达到最大数量的提示 */}
      {disabled || isMaxItemsReached ? (
        <div className='text-xs text-muted-foreground'>
          {disabled
            ? t('tagsInput.disabled')
            : t('tagsInput.maxItemsReached', { max: maxItems })}
        </div>
      ) : null}

      {/* 验证错误提示 */}
      {validationError && (
        <div className='w-full'>
          <p className='text-xs text-red-500'>{validationError}</p>
        </div>
      )}
    </div>
  );
}
