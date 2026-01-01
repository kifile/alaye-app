'use client';

import { useState, useRef, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Loader2, Eye, EyeOff, Check, X } from 'lucide-react';
import { toast } from 'sonner';
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
  rows?: number; // 仅对 textarea 有效
  maxLength?: number;
  showCharacterCount?: boolean;
  validate?: (value: string) => string | null; // 验证函数，返回错误信息或null
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  size?: 'sm' | 'default' | 'lg';
  hasError?: boolean;
  infoLink?: string;
  prefix?: React.ReactNode; // 新增：Label 前缀
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
  leftIcon,
  rightIcon,
  size = 'default',
  hasError = false,
  infoLink,
  prefix,
}: InputPreferenceProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [localValue, setLocalValue] = useState(value);
  const [showPassword, setShowPassword] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [originalValue, setOriginalValue] = useState(value);

  // 同步外部value变化
  useEffect(() => {
    setLocalValue(value);
    setOriginalValue(value);
    if (!isEditing) {
      setValidationError(null);
      setSaveError(false);
    }
  }, [value, isEditing]);

  // 保存配置到后端
  const saveSetting = async (newValue: string) => {
    try {
      setIsSaving(true);
      setSaveError(false);

      // 验证输入
      if (validate) {
        const error = validate(newValue);
        if (error) {
          setValidationError(error);
          return false;
        }
      }
      setValidationError(null);

      // 调用父组件的回调
      const success = await onSettingChange(settingKey, newValue);

      if (success) {
        setSaveError(false);
        return true;
      } else {
        setSaveError(true);
        // 恢复原值
        setLocalValue(value);
        return false;
      }
    } catch (error) {
      setSaveError(true);
      log.error(`保存输入配置失败: ${error}`);
      // 恢复原值
      setLocalValue(value);
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  // 开始编辑
  const startEdit = () => {
    setIsEditing(true);
    setOriginalValue(localValue);
    setValidationError(null);
  };

  // 处理输入变化
  const handleInputChange = (newValue: string) => {
    setLocalValue(newValue);
    setValidationError(null);
  };

  // 保存编辑
  const saveEdit = async () => {
    if (!isEditing) return;

    // 验证输入
    if (validate) {
      const error = validate(localValue);
      if (error) {
        setValidationError(error);
        return;
      }
    }

    const success = await saveSetting(localValue);
    if (success) {
      setIsEditing(false);
    }
  };

  // 取消编辑
  const cancelEdit = () => {
    if (!isEditing) return;

    setLocalValue(originalValue);
    setValidationError(null);
    setIsEditing(false);
  };

  // 处理按键事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isEditing) {
      if (e.key === 'Enter' && type !== 'textarea') {
        e.preventDefault();
        saveEdit();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        cancelEdit();
      }
    } else {
      // 非编辑状态下，Enter 开始编辑
      if (e.key === 'Enter' && type !== 'textarea') {
        e.preventDefault();
        startEdit();
      }
    }
  };

  // 获取输入框尺寸类
  const getInputSize = () => {
    switch (size) {
      case 'sm':
        return 'text-sm px-2 py-1';
      case 'lg':
        return 'text-lg px-4 py-3';
      default:
        return 'px-3 py-2';
    }
  };

  // 获取实际的输入类型
  const getInputType = () => {
    if (type === 'password') {
      return showPassword ? 'text' : 'password';
    }
    return type;
  };

  const inputContent = (
    <div className='relative'>
      {type === 'textarea' ? (
        <Textarea
          value={localValue}
          onChange={e => handleInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={isEditing ? undefined : startEdit}
          placeholder={placeholder}
          disabled={disabled || isSaving}
          rows={rows}
          maxLength={maxLength}
          readOnly={!isEditing}
          className={`${getInputSize()} resize-none ${
            hasError || saveError ? 'border-red-500 focus:ring-red-500' : ''
          } ${leftIcon ? 'pl-10' : ''} ${
            isEditing ? 'pr-24' : rightIcon ? 'pr-10' : ''
          } ${!isEditing ? 'cursor-pointer' : ''}`}
        />
      ) : (
        <>
          {/* 左侧图标 */}
          {leftIcon && (
            <div className='absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground'>
              {leftIcon}
            </div>
          )}

          <Input
            type={getInputType()}
            value={localValue}
            onChange={e => handleInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={isEditing ? undefined : startEdit}
            placeholder={placeholder}
            disabled={disabled || isSaving}
            maxLength={maxLength}
            readOnly={!isEditing}
            className={`${getInputSize()} ${
              hasError || saveError ? 'border-red-500 focus:ring-red-500' : ''
            } ${leftIcon ? 'pl-10' : ''} ${
              isEditing || type === 'password' ? 'pr-24' : rightIcon ? 'pr-10' : ''
            } ${!isEditing && type !== 'password' ? 'cursor-pointer' : ''}`}
          />

          {/* 右侧图标区域 */}
          {!isEditing && type !== 'password' && (
            <div className='absolute right-3 top-1/2 transform -translate-y-1/2'>
              {rightIcon && !isSaving && rightIcon}
              {isSaving && (
                <Loader2 className='w-4 h-4 animate-spin text-muted-foreground' />
              )}
            </div>
          )}

          {/* 密码显示切换 */}
          {type === 'password' && !isEditing && (
            <div className='absolute right-3 top-1/2 transform -translate-y-1/2'>
              <button
                type='button'
                onClick={() => setShowPassword(!showPassword)}
                className='text-muted-foreground hover:text-foreground'
                disabled={disabled || isSaving}
              >
                {showPassword ? (
                  <EyeOff className='w-4 h-4' />
                ) : (
                  <Eye className='w-4 h-4' />
                )}
              </button>
            </div>
          )}
        </>
      )}

      {/* 编辑状态按钮 */}
      {isEditing && (
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

  const rightElement =
    showCharacterCount || maxLength ? (
      <span className='text-xs text-muted-foreground'>
        {localValue?.length || 0}
        {maxLength && ` / ${maxLength}`}
      </span>
    ) : undefined;

  const extraInfo = validationError ? (
    <p className='text-xs text-yellow-600'>{validationError}</p>
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
