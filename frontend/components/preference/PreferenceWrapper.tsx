'use client';

import { ReactNode } from 'react';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Loader2, Info } from 'lucide-react';

export interface PreferenceWrapperProps {
  title: string | React.ReactNode;
  description?: string | React.ReactNode;
  infoLink?: string;
  disabled?: boolean;
  hasError?: boolean;
  saveError?: boolean;
  isSaving?: boolean;
  rightElement?: ReactNode;
  prefix?: ReactNode; // 新增：Label 前缀插槽，用于显示 ScopeBadge 等
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  size?: 'sm' | 'default' | 'lg';
  variant?: 'vertical' | 'horizontal';
  extraInfo?: ReactNode;
  errorMessage?: string; // 错误提示信息（支持多语言）
  savingMessage?: string; // 保存中提示信息（支持多语言）
  saveFailedMessage?: string; // 保存失败提示信息（支持多语言）
}

export function PreferenceWrapper({
  title,
  description,
  infoLink,
  disabled = false,
  hasError = false,
  saveError = false,
  isSaving = false,
  rightElement,
  prefix,
  children,
  className = '',
  contentClassName = '',
  size = 'default',
  variant = 'vertical',
  extraInfo,
  errorMessage,
  savingMessage,
  saveFailedMessage,
}: PreferenceWrapperProps) {
  // 获取基础容器类
  const getContainerClass = () => {
    const baseClass =
      variant === 'horizontal' ? 'flex items-center justify-between py-3' : 'space-y-2';

    return `${baseClass} ${className}`.trim();
  };

  // 获取标题部分类
  const getHeaderClass = () => {
    const baseClass =
      variant === 'horizontal'
        ? 'space-y-1 flex-1'
        : 'flex items-center justify-between';

    return baseClass;
  };

  // 获取标签类
  const getLabelClass = () => {
    const baseClass = 'text-sm font-medium';
    const disabledClass = disabled ? 'opacity-50' : '';

    return `${baseClass} ${disabledClass}`.trim();
  };

  // 获取描述类
  const getDescriptionClass = () => {
    const baseClass = 'text-xs text-muted-foreground';
    const disabledClass = disabled ? 'opacity-50' : '';

    return `${baseClass} ${disabledClass}`.trim();
  };

  // 标题部分
  const headerContent = (
    <div className={getHeaderClass()}>
      <div className='flex items-center gap-2'>
        {prefix && <div className='flex-shrink-0'>{prefix}</div>}
        {typeof title === 'string' ? (
          <Label className={getLabelClass()}>{title}</Label>
        ) : (
          <div className={getLabelClass()}>{title}</div>
        )}
        {infoLink && (
          <Button
            type='button'
            variant='ghost'
            size='sm'
            className='h-6 w-6 p-0 hover:bg-transparent'
            onClick={() => window.open(infoLink, '_blank')}
          >
            <Info className='h-3 w-3 text-muted-foreground hover:text-foreground' />
          </Button>
        )}
      </div>

      {/* 错误状态或附加信息 */}
      <div className='flex items-center gap-2'>
        {hasError && !saveError && errorMessage && (
          <span className='text-xs text-red-500'>{errorMessage}</span>
        )}
        {rightElement}
      </div>
    </div>
  );

  // 错误信息部分
  const errorContent = (
    <>
      {saveError && saveFailedMessage && (
        <p className='text-xs text-red-500'>{saveFailedMessage}</p>
      )}
      {isSaving && savingMessage && (
        <div className='flex items-center gap-2 text-sm text-muted-foreground'>
          <Loader2 className='w-3 h-3 animate-spin' />
          {savingMessage}
        </div>
      )}
      {extraInfo}
    </>
  );

  return (
    <div className={getContainerClass()}>
      {variant === 'vertical' ? (
        <>
          {headerContent}
          <div className={contentClassName}>{children}</div>
          {description && <p className={getDescriptionClass()}>{description}</p>}
          {errorContent}
        </>
      ) : (
        <>
          <div className={getHeaderClass()}>
            <div>
              <div className='flex items-center justify-between'>
                <div className='flex items-center gap-2'>
                  {prefix && <div className='flex-shrink-0'>{prefix}</div>}
                  {typeof title === 'string' ? (
                    <Label className={getLabelClass()}>{title}</Label>
                  ) : (
                    <div className={getLabelClass()}>{title}</div>
                  )}
                </div>
                <div className='flex items-center gap-2'>
                  {infoLink && (
                    <Button
                      type='button'
                      variant='ghost'
                      size='sm'
                      className='h-6 w-6 p-0 hover:bg-transparent'
                      onClick={() => window.open(infoLink, '_blank')}
                    >
                      <Info className='h-3 w-3 text-muted-foreground hover:text-foreground' />
                    </Button>
                  )}
                  {hasError && !saveError && errorMessage && (
                    <span className='text-xs text-red-500'>{errorMessage}</span>
                  )}
                  {rightElement}
                </div>
              </div>
              {description && <p className={getDescriptionClass()}>{description}</p>}
              {errorContent}
            </div>
          </div>
          <div className={`ml-4 ${contentClassName}`}>{children}</div>
        </>
      )}
    </div>
  );
}
