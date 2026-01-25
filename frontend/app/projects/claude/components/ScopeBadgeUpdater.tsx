'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { ScopeBadge } from './ScopeBadge';
import { ConfigScope } from '@/api/types';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ChevronsUpDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface ScopeBadgeUpdaterProps {
  currentScope: ConfigScope | null | undefined;
  disabled?: boolean;
  onScopeChange: (oldScope: ConfigScope, newScope: ConfigScope) => Promise<void>; // 作用域切换回调
}

export function ScopeBadgeUpdater({
  currentScope,
  disabled = false,
  onScopeChange,
}: ScopeBadgeUpdaterProps) {
  const { t } = useTranslation('projects');
  const [isUpdating, setIsUpdating] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  // 从翻译文件中获取作用域选项
  const SCOPE_OPTIONS = useMemo(
    () => [
      {
        value: ConfigScope.USER,
        label: t('detail.scopeBadge.user.label'),
      },
      {
        value: ConfigScope.PROJECT,
        label: t('detail.scopeBadge.project.label'),
      },
      {
        value: ConfigScope.LOCAL,
        label: t('detail.scopeBadge.local.label'),
      },
    ],
    [t]
  );

  // 是否有值
  const hasValue = !!currentScope;

  // 是否禁用（外部禁用 或 没有值 或 正在更新）
  const isDisabled = disabled || !hasValue || isUpdating;

  // 切换作用域 - 委托给调用方处理
  const handleScopeChange = useCallback(
    async (newScope: ConfigScope) => {
      if (!currentScope || isUpdating || !hasValue) return;

      setIsUpdating(true);
      setIsOpen(false);

      try {
        await onScopeChange(currentScope, newScope);
      } catch (error) {
        console.error('更新作用域失败:', error);
        // 错误由调用方处理，这里只负责重置状态
      } finally {
        setIsUpdating(false);
      }
    },
    [currentScope, hasValue, isUpdating, onScopeChange]
  );

  if (!currentScope && !hasValue) {
    // 如果没有值，显示灰色的 local badge
    return (
      <div
        className='opacity-50 cursor-not-allowed'
        title={t('detail.scopeBadge.noValue')}
      >
        <ScopeBadge scope={ConfigScope.LOCAL} showLabel={false} />
      </div>
    );
  }

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <div
          className={`cursor-pointer flex items-center gap-0 ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''} ${isUpdating ? 'animate-pulse' : ''}`}
          title={
            isDisabled
              ? t('detail.scopeBadge.cannotChangeScope')
              : t('detail.scopeBadge.currentScope', { scope: currentScope })
          }
          onClick={() => {
            if (!isDisabled) {
              // 仅当不禁用时才打开菜单
            } else {
              setIsOpen(false);
            }
          }}
        >
          <ScopeBadge scope={currentScope || ConfigScope.LOCAL} showLabel={false} />
          {!isDisabled && <ChevronsUpDown className='w-3 h-3 text-gray-500' />}
        </div>
      </DropdownMenuTrigger>
      {!isDisabled && (
        <DropdownMenuContent align='start' className='w-56'>
          <div className='px-2 py-1.5 text-sm font-semibold text-gray-700 border-b'>
            {t('detail.scopeBadge.selectScope')}
          </div>
          {SCOPE_OPTIONS.map(option => (
            <DropdownMenuItem
              key={option.value}
              className='flex items-center gap-2 py-2'
              onClick={() => handleScopeChange(option.value)}
              disabled={option.value === currentScope || isUpdating}
            >
              <ScopeBadge scope={option.value} showLabel={false} />
              <span className='font-medium'>{option.label}</span>
              {option.value === currentScope && (
                <span className='ml-auto text-xs text-gray-500'>
                  ({t('detail.scopeBadge.current')})
                </span>
              )}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      )}
    </DropdownMenu>
  );
}
