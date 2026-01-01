import React from 'react';
import { cn } from '@/lib/utils';
import { ConfigScope } from '@/api/types';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  ChevronDown,
  Layers,
  User,
  FolderKanban,
  HardDrive,
  Puzzle,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface ScopeSwitcherProps {
  value: ConfigScope | 'mixed' | null;
  onChange?: (scope: ConfigScope | 'mixed' | null) => void;
  className?: string;
  supportedScopes?: (ConfigScope | 'mixed')[];
}

const SCOPE_OPTIONS = [
  {
    value: 'mixed' as const,
    icon: Layers,
    i18nKey: 'mixed',
    colorClass: 'text-purple-700 bg-purple-50 border-purple-300 hover:bg-purple-100',
    dotColor: 'bg-purple-500',
  },
  {
    value: ConfigScope.PROJECT,
    icon: FolderKanban,
    i18nKey: 'project',
    colorClass: 'text-indigo-700 bg-indigo-50 border-indigo-300 hover:bg-indigo-100',
    dotColor: 'bg-indigo-500',
  },
  {
    value: ConfigScope.LOCAL,
    icon: HardDrive,
    i18nKey: 'local',
    colorClass:
      'text-emerald-700 bg-emerald-50 border-emerald-300 hover:bg-emerald-100',
    dotColor: 'bg-emerald-500',
  },
  {
    value: ConfigScope.USER,
    icon: User,
    i18nKey: 'user',
    colorClass: 'text-blue-700 bg-blue-50 border-blue-300 hover:bg-blue-100',
    dotColor: 'bg-blue-500',
  },
  {
    value: ConfigScope.PLUGIN,
    icon: Puzzle,
    i18nKey: 'plugin',
    colorClass: 'text-orange-700 bg-orange-50 border-orange-300 hover:bg-orange-100',
    dotColor: 'bg-orange-500',
  },
];

export function ScopeSwitcher({
  value = 'mixed',
  onChange,
  className,
  supportedScopes,
}: ScopeSwitcherProps) {
  const { t } = useTranslation('projects');
  const [open, setOpen] = React.useState(false);

  // 根据 supportedScopes 过滤选项
  const availableOptions = React.useMemo(() => {
    if (!supportedScopes || supportedScopes.length === 0) {
      return SCOPE_OPTIONS;
    }
    return SCOPE_OPTIONS.filter(option =>
      supportedScopes.includes(option.value as ConfigScope | 'mixed')
    );
  }, [supportedScopes]);

  const currentOption =
    SCOPE_OPTIONS.find(opt => opt.value === value) || SCOPE_OPTIONS[0];
  const CurrentIcon = currentOption.icon;

  const handleOptionClick = (optionValue: ConfigScope | 'mixed') => {
    onChange?.(optionValue);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type='button'
          className={cn(
            'flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md border transition-all duration-200 shadow-sm',
            'cursor-pointer hover:shadow-md',
            currentOption.colorClass,
            className
          )}
        >
          <CurrentIcon className='h-3.5 w-3.5' />
          <span>{t(`detail.scopeSwitcher.${currentOption.i18nKey}.label`)}</span>
          <ChevronDown className='h-3 w-3 opacity-60' />
        </button>
      </PopoverTrigger>
      <PopoverContent className='w-auto p-1' align='end'>
        <div className='space-y-0.5'>
          {availableOptions.map(option => {
            const isActive = value === option.value;
            const Icon = option.icon;
            return (
              <button
                key={option.value}
                type='button'
                className={cn(
                  'w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md transition-all duration-150',
                  'cursor-pointer',
                  isActive
                    ? 'bg-gray-100 text-gray-900 font-medium shadow-sm'
                    : 'text-gray-700 hover:bg-gray-50'
                )}
                onClick={() => handleOptionClick(option.value)}
                title={t(`detail.scopeSwitcher.${option.i18nKey}.description`)}
              >
                <div
                  className={cn(
                    'w-6 h-6 rounded-full flex items-center justify-center',
                    isActive ? option.colorClass : 'bg-gray-100'
                  )}
                >
                  <Icon
                    className={cn('h-3.5 w-3.5', isActive ? '' : 'text-gray-600')}
                  />
                </div>
                <div className='flex-1 text-left'>
                  <div className='text-xs font-medium'>
                    {t(`detail.scopeSwitcher.${option.i18nKey}.label`)}
                  </div>
                  <div className='text-[10px] text-gray-500'>
                    {t(`detail.scopeSwitcher.${option.i18nKey}.description`)}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}
