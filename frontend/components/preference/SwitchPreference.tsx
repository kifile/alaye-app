'use client';

import { useState, useEffect } from 'react';
import { Switch } from '@/components/ui/switch';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import log from '@/lib/log';
import { PreferenceWrapper } from './PreferenceWrapper';

interface SwitchPreferenceProps {
  title: string;
  description?: string | React.ReactNode;
  checked: boolean;
  settingKey: string;
  onSettingChange: (key: string, value: string) => Promise<boolean>;
  disabled?: boolean;
  size?: 'sm' | 'default' | 'lg';
  labelPosition?: 'left' | 'right';
  infoLink?: string;
  prefix?: React.ReactNode; // 新增：Label 前缀
}

export function SwitchPreference({
  title,
  description,
  checked,
  settingKey,
  onSettingChange,
  disabled = false,
  size = 'default',
  labelPosition = 'right',
  infoLink,
  prefix,
}: SwitchPreferenceProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [localChecked, setLocalChecked] = useState(checked);

  // 监听 checked prop 的变化，更新内部状态
  useEffect(() => {
    setLocalChecked(checked);
  }, [checked]);

  // 处理开关状态变化
  const handleSwitchChange = async (newChecked: boolean) => {
    if (disabled || isSaving) return;

    try {
      setIsSaving(true);
      setSaveError(false);
      setLocalChecked(newChecked);

      // 调用父组件的回调
      const success = await onSettingChange(settingKey, newChecked.toString());

      if (success) {
        setSaveError(false);
      } else {
        setSaveError(true);
        // 恢复原状态
        setLocalChecked(checked);
      }
    } catch (error) {
      setSaveError(true);
      log.error(`保存开关配置失败: ${error}`);
      // 恢复原状态
      setLocalChecked(checked);
    } finally {
      setIsSaving(false);
    }
  };

  // 根据尺寸调整开关大小
  const getSwitchSize = () => {
    switch (size) {
      case 'sm':
        return 'h-3 w-7';
      case 'lg':
        return 'h-6 w-11';
      default:
        return 'h-5 w-9';
    }
  };

  const switchContent = (
    <div className='relative'>
      <Switch
        checked={localChecked}
        onCheckedChange={handleSwitchChange}
        disabled={disabled || isSaving}
        className={`${getSwitchSize()} ${
          saveError ? 'border-red-500 focus:ring-red-500' : ''
        }`}
      />
      {isSaving && (
        <div className='absolute inset-0 flex items-center justify-center pointer-events-none'>
          <Loader2 className='w-4 h-4 animate-spin text-primary' />
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
      variant='horizontal'
      className={labelPosition === 'left' ? 'flex-row-reverse' : ''}
      contentClassName={labelPosition === 'left' ? 'mr-4 ml-0' : 'ml-4'}
      prefix={prefix}
    >
      {switchContent}
    </PreferenceWrapper>
  );
}
