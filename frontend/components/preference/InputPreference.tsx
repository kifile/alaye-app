'use client';

import { useState, useEffect } from 'react';
import { Loader2, Eye, EyeOff } from 'lucide-react';
import log from '@/lib/log';
import { PreferenceWrapper } from './PreferenceWrapper';

interface InputPreferenceProps {
  title: string;
  description?: string | React.ReactNode;
  value: string;
  settingKey: string;
  onSettingChange: (key: string, value: string) => Promise<boolean>;
  placeholder?: string;
  disabled?: boolean;
  type?: 'text' | 'password' | 'email' | 'url' | 'number' | 'textarea';
  rows?: number;
  maxLength?: number;
  showCharacterCount?: boolean;
  validate?: (value: string) => string | null;
  infoLink?: string;
  prefix?: React.ReactNode;
  leftIcon?: React.ReactNode;
}

export function InputPreference({
  title,
  description,
  value,
  settingKey,
  onSettingChange,
  placeholder = '',
  disabled = false,
  type = 'text',
  rows = 3,
  maxLength,
  showCharacterCount = false,
  validate,
  infoLink,
  prefix,
  leftIcon,
}: InputPreferenceProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [localValue, setLocalValue] = useState(value);
  const [showPassword, setShowPassword] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // 同步外部value变化
  useEffect(() => {
    setLocalValue(value);
    setValidationError(null);
    setSaveError(false);
  }, [value]);

  // 保存配置到后端
  const saveSetting = async (newValue: string) => {
    // 如果值没有变化，不保存
    if (newValue === value) return;

    try {
      setIsSaving(true);
      setSaveError(false);

      // 验证输入
      if (validate) {
        const error = validate(newValue);
        if (error) {
          setValidationError(error);
          return;
        }
      }
      setValidationError(null);

      const success = await onSettingChange(settingKey, newValue);

      if (!success) {
        setSaveError(true);
        setLocalValue(value); // 恢复原值
      }
    } catch (error) {
      setSaveError(true);
      log.error(`保存输入配置失败: ${error}`);
      setLocalValue(value); // 恢复原值
    } finally {
      setIsSaving(false);
    }
  };

  // 处理输入变化
  const handleInputChange = (newValue: string) => {
    setLocalValue(newValue);
    setValidationError(null);
  };

  // 处理失焦保存
  const handleBlur = () => {
    if (!validationError) {
      saveSetting(localValue);
    }
  };

  // 处理按键事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && type !== 'textarea') {
      e.preventDefault();
      (e.target as HTMLElement).blur();
    }
  };

  const inputContent = (
    <div className='relative'>
      {type === 'textarea' ? (
        <textarea
          value={localValue}
          onChange={e => handleInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          placeholder={placeholder}
          disabled={disabled || isSaving}
          rows={rows}
          maxLength={maxLength}
          className={`
            w-full rounded-[8px] bg-slate-100 px-[14px] py-[11px]
            text-sm text-slate-900 placeholder:text-muted-foreground
            focus:outline-none focus:ring-2 focus:ring-slate-300
            disabled:opacity-50 disabled:cursor-not-allowed
            resize-none
            ${saveError ? 'ring-2 ring-red-500' : ''}
            ${leftIcon ? 'pl-10' : ''}
          `}
        />
      ) : (
        <div className='relative'>
          <input
            type={type === 'password' ? (showPassword ? 'text' : 'password') : type}
            value={localValue}
            onChange={e => handleInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleBlur}
            placeholder={placeholder}
            disabled={disabled || isSaving}
            maxLength={maxLength}
            className={`
              w-full rounded-[8px] bg-slate-100 px-[14px] py-[11px]
              text-sm text-slate-900 placeholder:text-muted-foreground
              focus:outline-none focus:ring-2 focus:ring-slate-300
              disabled:opacity-50 disabled:cursor-not-allowed
              ${saveError ? 'ring-2 ring-red-500' : ''}
              ${type === 'password' && !isSaving ? 'pr-10' : ''}
              ${leftIcon ? 'pl-10' : ''}
            `}
          />
          {leftIcon && (
            <div className='absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground'>
              {leftIcon}
            </div>
          )}
          {isSaving && (
            <div className='absolute right-3 top-1/2 -translate-y-1/2'>
              <Loader2 className='w-4 h-4 animate-spin text-muted-foreground' />
            </div>
          )}
          {type === 'password' && !isSaving && (
            <button
              type='button'
              onClick={() => setShowPassword(!showPassword)}
              className='absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground'
              disabled={disabled}
            >
              {showPassword ? <EyeOff className='w-4 h-4' /> : <Eye className='w-4 h-4' />}
            </button>
          )}
        </div>
      )}
    </div>
  );

  const rightElement =
    showCharacterCount || maxLength ? (
      <span className='text-xs text-muted-foreground'>
        {localValue?.length || 0}
        {maxLength && ` / ${maxLength}`}
      </span>
    ) : undefined;

  const extraInfo = validationError ? (
    <p className='text-xs text-red-500'>{validationError}</p>
  ) : undefined;

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
      prefix={prefix}
    >
      {inputContent}
    </PreferenceWrapper>
  );
}
