'use client';

import { useState } from 'react';
import { selectFile, type FileDialogFilter } from '@/lib/file';
import { Loader2, FolderOpen } from 'lucide-react';
import { toast } from 'sonner';
import isAbsolute from 'is-absolute';
import { PreferenceWrapper } from './PreferenceWrapper';
import { useTranslation } from 'react-i18next';

interface FileSelectPreferenceProps {
  title: string;
  description: string | React.ReactNode;
  value: string;
  settingKey: string;
  onSettingChange: (key: string, value: string) => Promise<boolean>;
  placeholder?: string;
  disabled?: boolean;
  accept?: string;
  hasError?: boolean;
  infoLink?: string;
  errorMessage?: string;
  savingMessage?: string;
  saveFailedMessage?: string;
}

export function FileSelectPreference({
  title,
  description,
  value,
  settingKey,
  onSettingChange,
  placeholder = '',
  disabled = false,
  hasError = false,
  infoLink,
  errorMessage,
  savingMessage,
  saveFailedMessage,
  accept,
}: FileSelectPreferenceProps) {
  const { t } = useTranslation('preference');
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);

  // 获取当前路径的目录路径
  const getCurrentDirectory = () => {
    if (!value) return undefined;

    // 对于不同操作系统，处理路径分隔符
    const separator = value.includes('\\') ? '\\' : '/';
    const lastIndex = value.lastIndexOf(separator);

    if (lastIndex > 0) {
      return value.substring(0, lastIndex);
    }

    return undefined;
  };

  // 获取文件过滤器
  const getFileFilters = (): FileDialogFilter[] => {
    if (accept) {
      // 解析 accept 字符串，如 ".exe,.cmd" 或 "image/*"
      if (accept.includes('/*')) {
        // MIME 类型暂不支持，返回所有文件
        return [{ name: 'All Files', extensions: ['*'] }];
      } else {
        // 扩展名列表，如 ".exe,.cmd"
        const extensions = accept.split(',').map(ext => ext.trim().replace(/^\./, ''));
        return [{ name: 'Files', extensions }];
      }
    }
    return [{ name: 'All Files', extensions: ['*'] }];
  };

  // 检查路径是否为绝对路径 - 使用专门的库
  const checkIsAbsolutePath = (p: string): boolean => {
    return isAbsolute.posix(p) || isAbsolute.win32(p);
  };

  // 处理文件选择
  const handleFileSelect = async () => {
    if (disabled || isSaving) return;

    try {
      const currentDir = getCurrentDirectory();
      const result = await selectFile({
        title: `选择 ${title}`,
        defaultPath: currentDir,
        filters: getFileFilters(),
      });

      if (result.success && result.filePath) {
        if (checkIsAbsolutePath(result.filePath)) {
          // 绝对路径，通过回调更新配置
          setIsSaving(true);
          setSaveError(false);

          const success = await onSettingChange(settingKey, result.filePath);

          if (success) {
            setSaveError(false);
          } else {
            setSaveError(true);
          }
        } else {
          // 不是绝对路径，显示错误提示
          toast.error(t('fileSelect.desktopOnly'));
        }
      } else if (result.error) {
        // 显示其他错误信息
        toast.error(result.error);
      }
    } catch {
      toast.error(t('fileSelect.selectFailed'));
      setSaveError(true);
    } finally {
      setIsSaving(false);
    }
  };

  // 处理输入框点击（触发文件选择）
  const handleInputClick = (event: React.MouseEvent) => {
    event.preventDefault();
    if (disabled || isSaving) return;

    handleFileSelect();
  };

  // 显示文本：直接显示路径或占位符
  const displayText = value || placeholder;

  const inputContent = (
    <div className='relative'>
      <div
        onClick={handleInputClick}
        className={`
          flex items-center justify-between gap-2
          rounded-[8px] bg-slate-100 px-[14px] py-[11px]
          cursor-pointer select-none
          ${hasError || saveError ? 'ring-2 ring-red-500' : ''}
          ${disabled || isSaving ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <span
          className={`text-sm truncate ${
            !value ? 'text-muted-foreground' : 'text-slate-900'
          }`}
        >
          {displayText}
        </span>
        {isSaving ? (
          <Loader2 className='w-4 h-4 animate-spin text-muted-foreground flex-shrink-0' />
        ) : (
          <FolderOpen className='w-4 h-4 text-muted-foreground flex-shrink-0' />
        )}
      </div>
    </div>
  );

  return (
    <PreferenceWrapper
      title={title}
      description={description}
      infoLink={infoLink}
      disabled={disabled}
      hasError={hasError}
      saveError={saveError}
      isSaving={isSaving}
      errorMessage={errorMessage}
      savingMessage={savingMessage}
      saveFailedMessage={saveFailedMessage}
    >
      {inputContent}
    </PreferenceWrapper>
  );
}
