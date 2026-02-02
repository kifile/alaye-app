'use client';

import { useState, useCallback } from 'react';
import { toast } from 'sonner';
import log from '@/lib/log';
import { PreferenceWrapper } from './PreferenceWrapper';
import { TagsInput } from '@/components/input/TagsInput';

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
  validator?: (value: string) => string | null;
  infoLink?: string;
  prefix?: React.ReactNode;
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

  const convertToString = useCallback(
    (list: string[]) => {
      // 当 allowEmptyValues 为 true 时，保留空值；否则过滤掉空值
      const filteredList = allowEmptyValues ? list : list.filter(item => item.trim());
      return JSON.stringify(filteredList);
    },
    [allowEmptyValues]
  );

  const saveSetting = async (newItems: string[]) => {
    try {
      setIsSaving(true);
      setSaveError(false);

      const success = await onSettingChange(settingKey, convertToString(newItems));

      if (success) {
        setSaveError(false);
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

  const handleTagsChange = async (newTags: string[]) => {
    const success = await saveSetting(newTags);
    if (!success) {
      // 保存失败，显示错误提示
      toast.error('Failed to save tags');
    }
  };

  const handleValidationError = (error: string) => {
    toast.error(error);
  };

  const rightElement = maxItems ? (
    <span className='text-xs text-muted-foreground'>
      {value?.length || 0}
      {maxItems && ` / ${maxItems}`}
    </span>
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
      prefix={prefix}
    >
      <TagsInput
        value={value || []}
        onChange={handleTagsChange}
        placeholder={placeholder}
        disabled={disabled}
        saving={isSaving}
        allowEmptyValues={allowEmptyValues}
        maxItems={maxItems}
        validator={validator}
        onValidationError={handleValidationError}
      />
    </PreferenceWrapper>
  );
}
