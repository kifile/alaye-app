'use client';

import { useState, useEffect } from 'react';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Loader2, Check, X } from 'lucide-react';
import { toast } from 'sonner';
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
  size?: 'sm' | 'default' | 'lg';
  infoLink?: string;
  prefix?: React.ReactNode; // 新增：Label 前缀
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
  size = 'default',
  infoLink,
  prefix,
}: SelectPreferenceProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [selectedValue, setSelectedValue] = useState(value);
  const [originalValue, setOriginalValue] = useState(value);
  const [isOpen, setIsOpen] = useState(false);

  // 监听 value prop 的变化，更新内部状态
  useEffect(() => {
    setSelectedValue(value);
    setOriginalValue(value);
    if (!isEditing) {
      setSaveError(false);
    }
  }, [value, isEditing]);

  // 获取输入框尺寸
  const getInputSize = () => {
    switch (size) {
      case 'sm':
        return 'text-sm px-2 py-1 h-8';
      case 'lg':
        return 'text-lg px-4 py-3 h-12';
      default:
        return 'px-3 py-2 h-10';
    }
  };

  // 保存配置到后端
  const saveSetting = async (newValue: string) => {
    try {
      setIsSaving(true);
      setSaveError(false);

      // 调用父组件的回调
      const success = await onSettingChange(settingKey, newValue);

      if (success) {
        setSaveError(false);
        return true;
      } else {
        setSaveError(true);
        setSelectedValue(originalValue);
        return false;
      }
    } catch (error) {
      setSaveError(true);
      log.error(`保存选择配置失败: ${error}`);
      setSelectedValue(originalValue);
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  // 开始编辑
  const startEdit = () => {
    if (disabled || isSaving) return;
    setIsEditing(true);
    setOriginalValue(selectedValue);
    setIsOpen(true);
  };

  // 取消编辑
  const cancelEdit = () => {
    setSelectedValue(originalValue);
    setIsEditing(false);
    setIsOpen(false);
    setSaveError(false);
  };

  // 选择选项
  const selectOption = (optionValue: string) => {
    setSelectedValue(optionValue);
    setIsOpen(false);
  };

  // 保存编辑
  const saveEdit = async () => {
    if (!isEditing) return;

    const success = await saveSetting(selectedValue);
    if (success) {
      setIsEditing(false);
    }
  };

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isEditing) {
      if (e.key === 'Enter') {
        e.preventDefault();
        if (isOpen) {
          // 如果下拉菜单打开，选择当前高亮的选项
          setIsOpen(false);
        } else if (selectedValue !== originalValue) {
          // 只有在值发生变化时才保存
          saveEdit();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        if (isOpen) {
          setIsOpen(false);
        } else {
          // 如果值没有变化，直接退出编辑状态
          if (selectedValue === originalValue) {
            setIsEditing(false);
          } else {
            cancelEdit();
          }
        }
      } else if (e.key === 'Tab' && isOpen) {
        e.preventDefault();
        setIsOpen(false);
      }
    } else {
      if (e.key === 'Enter') {
        e.preventDefault();
        startEdit();
      }
    }
  };

  // 获取当前选中项的显示文本
  const getCurrentDisplay = () => {
    if (!selectedValue && allowEmpty) {
      return emptyLabel;
    }

    const selectedOption = options.find(option => option.value === selectedValue);
    return selectedOption?.label || selectedValue || placeholder;
  };

  // 获取当前选中项的描述
  const getCurrentDescription = () => {
    if (!selectedValue && allowEmpty) {
      return undefined;
    }

    const selectedOption = options.find(option => option.value === selectedValue);
    return selectedOption?.description;
  };

  const selectorContent = (
    <div className='relative'>
      {/* 选择器按钮 */}
      <Button
        type='button'
        onClick={isEditing ? () => setIsOpen(!isOpen) : startEdit}
        onKeyDown={handleKeyDown}
        disabled={disabled || isSaving}
        className={`w-full justify-between text-left font-normal ${getInputSize()} ${
          saveError ? 'border-red-500 focus:ring-red-500' : ''
        } ${!isEditing && !selectedValue ? 'text-muted-foreground' : ''}`}
        variant='outline'
      >
        <div className='flex flex-col items-start'>
          <span className='truncate'>{getCurrentDisplay()}</span>
          {getCurrentDescription() && (
            <span className='text-xs text-muted-foreground truncate'>
              {getCurrentDescription()}
            </span>
          )}
        </div>
        {isSaving ? (
          <Loader2 className='h-4 w-4 animate-spin' />
        ) : (
          <X className='h-4 w-4 opacity-50' />
        )}
      </Button>

      {/* 下拉选项 */}
      {isEditing && isOpen && (
        <div className='absolute top-full left-0 right-0 z-50 mt-1 bg-popover border rounded-md shadow-lg max-h-60 overflow-auto'>
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
                selectedValue === option.value ? 'bg-accent' : ''
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

      {/* 编辑状态按钮 - 仅在值发生变化时显示 */}
      {isEditing && !isOpen && selectedValue !== originalValue && (
        <div className='absolute right-2 top-1/2 transform -translate-y-1/2 flex items-center gap-1'>
          <Button
            onClick={saveEdit}
            disabled={disabled || isSaving}
            size='sm'
            variant='outline'
            className='h-7 px-2'
          >
            <Check className='w-3 h-3' />
          </Button>
          <Button
            onClick={cancelEdit}
            disabled={disabled || isSaving}
            size='sm'
            variant='outline'
            className='h-7 px-2'
          >
            <X className='w-3 h-3' />
          </Button>
        </div>
      )}
    </div>
  );

  return (
    <PreferenceWrapper
      title={title}
      description={!isEditing ? description : undefined}
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
