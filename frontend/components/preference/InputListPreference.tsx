'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Loader2, X } from 'lucide-react';
import { toast } from 'sonner';
import log from '@/lib/log';
import { PreferenceWrapper } from './PreferenceWrapper';

interface InputListPreferenceProps {
  title: string;
  description?: string | React.ReactNode;
  value: string[];
  settingKey: string;
  onSettingChange: (key: string, value: string) => Promise<boolean>;
  disabled?: boolean;
  placeholder?: string;
  allowEmptyValues?: boolean;
  maxItems?: number;
  validator?: (value: string) => string | null; // 验证每个值的函数
  infoLink?: string;
  prefix?: React.ReactNode; // 新增：Label 前缀
}

export function InputListPreference({
  title,
  description,
  value,
  settingKey,
  onSettingChange,
  disabled = false,
  placeholder = '输入内容后按回车添加',
  allowEmptyValues = false,
  maxItems,
  validator,
  infoLink,
  prefix,
}: InputListPreferenceProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [items, setItems] = useState<string[]>(value || []);
  const [inputValue, setInputValue] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // 监听 value prop 的变化，更新内部状态
  useEffect(() => {
    setItems(value || []);
  }, [value]);

  // 将当前状态转换为 JSON 字符串
  const convertToString = useCallback(
    (list: string[]) => {
      const filteredList = list.filter(item => allowEmptyValues || item.trim());
      return JSON.stringify(filteredList);
    },
    [allowEmptyValues]
  );

  // 保存配置到后端
  const saveSetting = async (newItems: string[]) => {
    try {
      setIsSaving(true);
      setSaveError(false);

      const success = await onSettingChange(settingKey, convertToString(newItems));

      if (success) {
        setSaveError(false);
        setItems(newItems);
        return true;
      } else {
        setSaveError(true);
        return false;
      }
    } catch (error) {
      setSaveError(true);
      log.error(`保存列表配置失败: ${error}`);
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  // 添加新项目
  const addItem = async () => {
    if (!inputValue.trim() && !allowEmptyValues) {
      return;
    }

    // 验证输入值
    if (validator) {
      const error = validator(inputValue);
      if (error) {
        setValidationError(error);
        return;
      }
    }

    if (maxItems && items.length >= maxItems) {
      toast.error(`最多支持 ${maxItems} 个配置项`);
      return;
    }

    // 检查重复
    if (items.includes(inputValue)) {
      setValidationError('该项目已存在');
      return;
    }

    const newItems = [...items, inputValue];
    const success = await saveSetting(newItems);

    if (success) {
      setInputValue('');
      setValidationError(null);
    }
  };

  // 删除项目
  const removeItem = async (itemToRemove: string) => {
    const newItems = items.filter(item => item !== itemToRemove);
    await saveSetting(newItems);
  };

  // 处理输入变化
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
    setValidationError(null);
  };

  // 处理按键事件
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addItem();
    } else if (e.key === 'Escape') {
      setInputValue('');
      setValidationError(null);
    }
  };

  // 处理输入框失焦
  const handleInputBlur = () => {
    if (inputValue.trim() && allowEmptyValues) {
      addItem();
    } else {
      setValidationError(null);
    }
  };

  const rightElement = maxItems ? (
    <span className='text-xs text-muted-foreground'>
      {items.length}
      {maxItems && ` / ${maxItems}`}
    </span>
  ) : undefined;

  const tagsContent = (
    <div
      className={`min-h-[32px] p-2 border rounded-md bg-background hover:border-input focus-within:border-ring focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 transition-colors ${
        !disabled && (!maxItems || items.length < maxItems) ? 'cursor-text' : ''
      }`}
      onClick={() => {
        if (!disabled && (!maxItems || items.length < maxItems)) {
          inputRef.current?.focus();
        }
      }}
    >
      {/* 现有项目标签 */}
      {items.map((item, index) => (
        <span
          key={index}
          className='inline-flex items-center gap-1 px-2 py-1 m-1 text-sm bg-primary/10 text-primary rounded-md border border-primary/20 group'
        >
          <span className='max-w-[200px] truncate'>{item}</span>
          {!disabled && !isSaving && (
            <button
              type='button'
              onClick={e => {
                e.stopPropagation();
                removeItem(item);
              }}
              className='ml-1 text-primary/60 hover:text-primary hover:bg-primary/20 rounded p-0.5 transition-colors'
              title='删除'
            >
              <X className='w-3 h-3' />
            </button>
          )}
        </span>
      ))}

      {/* 输入框或空状态 */}
      {!disabled && (!maxItems || items.length < maxItems) && (
        <input
          ref={inputRef}
          type='text'
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onBlur={handleInputBlur}
          placeholder={items.length === 0 ? placeholder : ''}
          disabled={isSaving}
          className={`${
            items.length === 0 && !inputValue
              ? 'w-full'
              : 'inline-block w-32 min-w-[60px]'
          } px-2 py-1 text-sm bg-transparent outline-none placeholder:text-muted-foreground/50`}
        />
      )}

      {/* 空状态提示（当没有输入框时显示） */}
      {disabled || (maxItems && items.length >= maxItems) ? (
        <div className='text-center py-4 text-muted-foreground/60 text-xs'>
          {disabled
            ? '已禁用编辑'
            : maxItems && items.length >= maxItems
              ? `已达到最大数量限制 (${maxItems})`
              : ''}
        </div>
      ) : null}
    </div>
  );

  const extraInfo = (
    <>{validationError && <p className='text-xs text-red-500'>{validationError}</p>}</>
  );

  return (
    <PreferenceWrapper
      title={title}
      description={description}
      infoLink={infoLink}
      disabled={disabled}
      saveError={saveError}
      isSaving={isSaving}
      rightElement={rightElement}
      extraInfo={extraInfo}
      className='space-y-3'
      prefix={prefix}
    >
      {tagsContent}
    </PreferenceWrapper>
  );
}
