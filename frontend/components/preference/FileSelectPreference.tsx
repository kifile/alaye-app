'use client';

import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { selectFile, type FileDialogFilter } from '@/lib/file';
import { Loader2, FolderOpen } from 'lucide-react';
import { toast } from 'sonner';
import isAbsolute from 'is-absolute';
import { PreferenceWrapper } from './PreferenceWrapper';

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
}: FileSelectPreferenceProps) {
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
    return [
      { name: '可执行文件', extensions: ['exe', 'cmd', 'app', 'sh', 'bash', 'zsh'] },
      { name: '应用程序', extensions: ['exe', 'app', 'msi', 'dmg', 'deb', 'rpm'] },
    ];
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
          toast.error(
            '文件路径选择功能仅在 PyWebView 桌面应用环境中支持。在浏览器环境中，出于安全考虑，只能获取文件名而非完整路径。'
          );
        }
      } else if (result.error) {
        // 显示其他错误信息
        toast.error(result.error);
      }
    } catch (error) {
      toast.error('文件选择失败，请重试');
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
      <Input
        value={displayText}
        readOnly
        onClick={handleInputClick}
        placeholder={placeholder}
        disabled={disabled || isSaving}
        className={`cursor-pointer pr-10 ${
          hasError || saveError ? 'border-red-500 focus:ring-red-500' : ''
        } ${!value ? 'text-muted-foreground' : ''}`}
      />

      {/* 文件夹图标 */}
      <div className='absolute right-3 top-1/2 transform -translate-y-1/2 pointer-events-none'>
        {isSaving ? (
          <Loader2 className='w-4 h-4 animate-spin text-muted-foreground' />
        ) : (
          <FolderOpen className='w-4 h-4 text-muted-foreground' />
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
