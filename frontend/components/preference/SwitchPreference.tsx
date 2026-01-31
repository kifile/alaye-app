'use client';

import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import log from '@/lib/log';
import { toast } from 'sonner';
import { PreferenceWrapper } from './PreferenceWrapper';

interface SwitchPreferenceProps {
  title: string;
  description?: string | React.ReactNode;
  checked: boolean;
  settingKey: string;
  onSettingChange: (key: string, value: string) => Promise<boolean>;
  disabled?: boolean;
  infoLink?: string;
  prefix?: React.ReactNode;
}

export function SwitchPreference({
  title,
  description,
  checked,
  settingKey,
  onSettingChange,
  disabled = false,
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
        toast.error('Failed to save switch setting');
        // 恢复原状态
        setLocalChecked(checked);
      }
    } catch (error) {
      setSaveError(true);
      log.error(`保存开关配置失败: ${error}`);
      toast.error('Failed to save switch setting');
      // 恢复原状态
      setLocalChecked(checked);
    } finally {
      setIsSaving(false);
    }
  };

  const switchContent = (
    <div className='relative'>
      <div
        onClick={() => !disabled && !isSaving && handleSwitchChange(!localChecked)}
        className={`
          relative inline-flex items-center
          h-7 w-12 rounded-full
          cursor-pointer select-none
          transition-colors duration-200
          ${localChecked ? 'bg-slate-900' : 'bg-slate-200'}
          ${disabled || isSaving ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <span
          className={`
            inline-block h-[22px] w-[22px] rounded-full bg-white shadow
            transition-transform duration-200
            ${localChecked ? 'translate-x-6' : 'translate-x-0.5'}
          `}
          style={{
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
          }}
        />
      </div>
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
      prefix={prefix}
    >
      {switchContent}
    </PreferenceWrapper>
  );
}
