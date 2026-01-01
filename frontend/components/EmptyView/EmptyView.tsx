import { Button } from '@/components/ui/button';
import { ReactNode, isValidElement, ComponentType } from 'react';
import { LucideIcon } from 'lucide-react';

export interface EmptyViewProps {
  /** 图标组件（可以是 LucideIcon 或自定义 ReactNode） */
  icon?: LucideIcon | ReactNode;
  /** 标题 */
  title: string;
  /** 描述文本 */
  description?: string;
  /** 操作按钮文本 */
  actionLabel?: string;
  /** 操作按钮点击回调 */
  onAction?: () => void;
  /** 操作按钮是否禁用 */
  actionDisabled?: boolean;
  /** 操作按钮大小 */
  actionSize?: 'default' | 'sm' | 'lg' | 'icon';
  /** 操作按钮图标（可选） */
  actionIcon?: ReactNode;
  /** 自定义容器类名 */
  className?: string;
  /** 是否显示边框 */
  bordered?: boolean;
}

/**
 * 内部图标渲染组件
 */
function IconRenderer({ icon }: { icon: LucideIcon | ReactNode }) {
  if (isValidElement(icon)) {
    return icon;
  }

  if (typeof icon === 'function') {
    const IconComponent = icon as ComponentType<{ className?: string }>;
    return <IconComponent className='w-8 h-8 text-muted-foreground' />;
  }

  return <>{icon}</>;
}

/**
 * 通用空状态视图组件
 */
export function EmptyView({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  actionDisabled = false,
  actionSize = 'lg',
  actionIcon,
  className = '',
  bordered = false,
}: EmptyViewProps) {
  return (
    <div
      className={`text-center py-16 ${bordered ? 'border-2 border-dashed border-muted-foreground/25 rounded-lg' : ''} ${className}`}
    >
      <div className='space-y-4'>
        {icon && (
          <div className='w-16 h-16 mx-auto bg-muted rounded-full flex items-center justify-center'>
            {isValidElement(icon) ? (
              icon
            ) : typeof icon === 'function' ? (
              // @ts-ignore
              <icon className='w-8 h-8 text-muted-foreground' />
            ) : (
              icon
            )}
          </div>
        )}
        <div>
          <h3 className='text-lg font-semibold mb-2'>{title}</h3>
          {description && (
            <p className={`text-muted-foreground ${actionLabel ? 'mb-6' : ''}`}>
              {description}
            </p>
          )}
          {actionLabel && onAction && (
            <Button onClick={onAction} disabled={actionDisabled} size={actionSize}>
              {actionIcon}
              {actionLabel}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
