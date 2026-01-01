import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { ConfigScope } from '@/api/types';

interface ScopeSelectProps {
  value: ConfigScope | 'mixed' | null;
  onChange: (scope: ConfigScope | 'mixed' | null) => void;
  disabled?: boolean;
}

const SCOPE_OPTIONS = [
  {
    value: 'mixed',
    label: '混合模式',
    description: '显示所有作用域的配置',
    color: 'text-gray-600',
  },
  {
    value: ConfigScope.USER,
    label: 'User',
    description: '用户全局配置 (~/.claude/settings.json)',
    color: 'text-blue-600',
  },
  {
    value: ConfigScope.PROJECT,
    label: 'Project',
    description: '项目配置 (.claude/settings.json)',
    color: 'text-blue-700',
  },
  {
    value: ConfigScope.LOCAL,
    label: 'Local',
    description: '本地配置 (.claude/settings.local.json)',
    color: 'text-green-600',
  },
] as const;

export function ScopeSelect({ value, onChange, disabled = false }: ScopeSelectProps) {
  const getDisplayValue = () => {
    if (!value || value === 'mixed') {
      return '混合模式';
    }
    const option = SCOPE_OPTIONS.find(opt => opt.value === value);
    return option?.label || '混合模式';
  };

  const handleSelect = (scopeValue: (typeof SCOPE_OPTIONS)[number]['value']) => {
    onChange(scopeValue);
  };

  return (
    <div className='flex items-center gap-4'>
      <span className='text-sm text-muted-foreground'>配置作用域:</span>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            variant='outline'
            className='w-[200px] justify-start'
            disabled={disabled}
          >
            {getDisplayValue()}
          </Button>
        </PopoverTrigger>
        <PopoverContent className='w-[320px] p-4' align='start'>
          <div className='space-y-3'>
            {SCOPE_OPTIONS.map(option => (
              <div key={option.value} className='flex items-start space-x-3'>
                <Checkbox
                  id={`scope-${option.value}`}
                  checked={value === option.value}
                  onCheckedChange={() => handleSelect(option.value)}
                  disabled={disabled}
                />
                <div className='flex-1'>
                  <label
                    htmlFor={`scope-${option.value}`}
                    className={`text-sm font-medium cursor-pointer block ${option.color}`}
                  >
                    {option.label}
                  </label>
                  <p className='text-xs text-muted-foreground'>{option.description}</p>
                </div>
              </div>
            ))}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}
