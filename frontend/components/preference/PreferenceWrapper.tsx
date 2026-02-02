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
  prefix?: ReactNode;
  children?: ReactNode;
  className?: string;
  contentClassName?: string;
  extraInfo?: ReactNode;
  errorMessage?: string;
  savingMessage?: string;
  saveFailedMessage?: string;
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
  extraInfo,
  errorMessage,
  savingMessage,
  saveFailedMessage,
}: PreferenceWrapperProps) {
  // 标题部分
  const headerContent = (
    <div
      className='flex flex-col gap-0.5 min-w-0'
      style={{ width: 236, maxWidth: 236 }}
    >
      <div className='flex items-center gap-2 min-w-0'>
        <div className='min-w-0 flex-1'>
          {typeof title === 'string' ? (
            <Label
              className={`text-[15px] font-normal text-slate-900 ${disabled ? 'opacity-50' : ''} truncate block`}
            >
              {title}
            </Label>
          ) : (
            <div
              className={`text-[15px] font-normal text-slate-900 ${disabled ? 'opacity-50' : ''} min-w-0`}
            >
              {title}
            </div>
          )}
        </div>
        {infoLink && (
          <Button
            type='button'
            variant='ghost'
            size='sm'
            className='h-6 w-6 p-0 hover:bg-transparent shrink-0'
            onClick={() => window.open(infoLink, '_blank')}
          >
            <Info className='h-3 w-3 text-muted-foreground hover:text-foreground' />
          </Button>
        )}
      </div>
      {description && (
        <p
          className={`text-[12px] text-slate-600 ${disabled ? 'opacity-50' : ''} truncate block`}
        >
          {description}
        </p>
      )}
    </div>
  );

  // 错误信息部分
  const errorContent = (
    <>
      {saveError && saveFailedMessage && (
        <p className='text-xs text-red-500 mt-1'>{saveFailedMessage}</p>
      )}
      {hasError && !saveError && errorMessage && (
        <p className='text-xs text-red-500 mt-1'>{errorMessage}</p>
      )}
      {isSaving && savingMessage && (
        <div className='flex items-center gap-2 text-sm text-muted-foreground mt-1'>
          <Loader2 className='w-3 h-3 animate-spin' />
          {savingMessage}
        </div>
      )}
      {extraInfo}
    </>
  );

  return (
    <div className={className}>
      <div className='flex items-center gap-4'>
        {/* 分隔线 */}
        <div className='shrink-0 w-px bg-slate-200 h-12' />
        {headerContent}
        <div className={`flex-1 ${contentClassName}`.trim()}>{children}</div>
        {rightElement && <div className='shrink-0'>{rightElement}</div>}
      </div>
      {errorContent}
    </div>
  );
}
