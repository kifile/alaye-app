'use client';

import { useState, useRef, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import log from '@/lib/log';
import { PreferenceWrapper } from './PreferenceWrapper';

interface SelectPreferenceProps {
  title: string;
  description?: string | React.ReactNode;
  value: string;
  settingKey: string;
  onSettingChange: (key: string, value: string) => Promise<boolean>;
  disabled?: boolean;
  placeholder?: string;
  options: Array<{
    value: string;
    label: string;
    description?: string;
  }>;
  allowEmpty?: boolean;
  emptyLabel?: string;
  infoLink?: string;
  prefix?: React.ReactNode;
  maxVisibleItems?: number; // 下拉框最大显示选项数量，超出则滚动
}

export function SelectPreference({
  title,
  description,
  value,
  settingKey,
  onSettingChange,
  disabled = false,
  placeholder = '请选择',
  options,
  allowEmpty = false,
  emptyLabel = '无',
  infoLink,
  prefix,
  maxVisibleItems = 10,
}: SelectPreferenceProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭下拉框
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isOpen]);

  // 选择选项并立即保存
  const selectOption = async (optionValue: string) => {
    if (isSaving || disabled) return;

    // 如果选择的值和当前值相同，只关闭下拉菜单
    if (optionValue === value) {
      setIsOpen(false);
      return;
    }

    try {
      setIsSaving(true);
      setSaveError(false);

      const success = await onSettingChange(settingKey, optionValue);

      if (!success) {
        setSaveError(true);
      }
    } catch (error) {
      setSaveError(true);
      log.error(`保存选择配置失败: ${error}`);
    } finally {
      setIsSaving(false);
      setIsOpen(false);
    }
  };

  // 获取当前选中项的显示文本
  const getCurrentDisplay = () => {
    if (!value && allowEmpty) {
      return emptyLabel;
    }

    const selectedOption = options.find(option => option.value === value);
    return selectedOption?.label || value || placeholder;
  };

  const selectorContent = (
    <div ref={containerRef} className='relative'>
      {/* 选择器按钮 */}
      <button
        type='button'
        onClick={() => !disabled && !isSaving && setIsOpen(!isOpen)}
        disabled={disabled || isSaving}
        className={`
          flex items-center justify-between gap-2 w-full
          rounded-[10px] bg-slate-100 px-4 py-3
          text-left font-normal
          ${saveError ? 'ring-2 ring-red-500' : ''}
          ${disabled || isSaving ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <div className='flex items-center gap-2'>
          {prefix && <span className='text-[18px]'>{prefix}</span>}
          <span className='text-[14px] font-medium text-slate-900 truncate'>
            {getCurrentDisplay()}
          </span>
        </div>
        {isSaving ? (
          <Loader2 className='h-4 w-4 animate-spin' />
        ) : (
          <span className='text-[10px] text-slate-500'>▼</span>
        )}
      </button>

      {/* 下拉选项 */}
      {isOpen && (
        <div
          className='absolute top-full left-0 right-0 z-50 mt-1 bg-popover border rounded-md shadow-lg overflow-auto'
          style={{
            maxHeight: `${Math.min(maxVisibleItems, options.length + (allowEmpty ? 1 : 0)) * 48 + 8}px`,
            maxWidth: '100%',
          }}
        >
          {allowEmpty && (
            <button
              type='button'
              onClick={() => selectOption('')}
              className='w-full text-left px-3 py-2 text-sm hover:bg-accent focus:bg-accent focus:outline-none'
            >
              <div>{emptyLabel}</div>
            </button>
          )}
          {options.map(option => (
            <button
              key={option.value}
              type='button'
              onClick={() => selectOption(option.value)}
              className={`w-full text-left px-3 py-2 text-sm hover:bg-accent focus:bg-accent focus:outline-none ${
                value === option.value ? 'bg-accent' : ''
              }`}
            >
              <div>{option.label}</div>
              {option.description && (
                <div className='text-xs text-muted-foreground'>
                  {option.description}
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <PreferenceWrapper
      title={title}
      description={description}
      infoLink={infoLink}
      disabled={disabled}
      saveError={saveError}
      isSaving={isSaving}
      prefix={prefix}
    >
      {selectorContent}
    </PreferenceWrapper>
  );
}
