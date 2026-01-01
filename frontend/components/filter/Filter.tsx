import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { ReactNode, useState } from 'react';

export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterProps {
  /** 可选项列表 */
  options: FilterOption[];
  /** 已选择的值列表 */
  selected: string[];
  /** 选择变更回调 */
  onSelectionChange: (selected: string[]) => void;
  /** 显示文本函数，根据已选项返回显示文本 */
  displayValue: (selected: string[], allSelectedLabel: string) => string;
  /** 未选择时的占位文本 */
  placeholder?: string;
  /** 左侧图标 */
  icon?: ReactNode;
  /** 是否显示"全部"选项 */
  showAllOption?: boolean;
  /** "全部"选项的值 */
  allOptionValue?: string;
  /** "全部"选项的标签 */
  allOptionLabel?: string;
  /** 按钮宽度 */
  buttonWidth?: string;
  /** Popover 内容宽度 */
  popoverWidth?: string;
  /** 按钮对齐方式 */
  align?: 'start' | 'center' | 'end';
  /** 是否禁用 */
  disabled?: boolean;
}

/**
 * 通用多选过滤器组件
 *
 * @example
 * ```tsx
 * <Filter
 *   options={[{ value: 'cat1', label: 'Category 1' }, { value: 'cat2', label: 'Category 2' }]}
 *   selected={['cat1']}
 *   onSelectionChange={(selected) => setSelected(selected)}
 *   displayValue={(selected) => selected.length > 0 ? `${selected.length} selected` : 'All Categories'}
 *   placeholder="Select categories"
 *   icon={<Tag className="w-4 h-4" />}
 * />
 * ```
 */
export function Filter({
  options,
  selected,
  onSelectionChange,
  displayValue,
  placeholder = 'Select...',
  icon,
  showAllOption = false,
  allOptionValue = '_all_',
  allOptionLabel = 'All',
  buttonWidth = '180px',
  popoverWidth = '200px',
  align = 'start',
  disabled = false,
}: FilterProps) {
  const [open, setOpen] = useState(false);
  const [pendingSelected, setPendingSelected] = useState<string[]>(selected);

  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen) {
      setPendingSelected(selected);
    }
    setOpen(newOpen);
  };

  const handleToggle = (value: string) => {
    // 点击"全部"选项
    if (showAllOption && value === allOptionValue) {
      setPendingSelected([allOptionValue]);
      return;
    }

    // 从"全部"切换到具体选项
    if (pendingSelected.includes(allOptionValue)) {
      setPendingSelected([value]);
      return;
    }

    // 切换具体选项
    setPendingSelected(prev => {
      const isSelected = prev.includes(value);
      const newSelected = isSelected
        ? prev.filter(item => item !== value)
        : [...prev, value];

      // 如果没有选中项且支持"全部"选项，则默认选中"全部"
      return newSelected.length > 0
        ? newSelected
        : showAllOption
          ? [allOptionValue]
          : [];
    });
  };

  const handleConfirm = () => {
    onSelectionChange(pendingSelected);
    setOpen(false);
  };

  const handleCancel = () => {
    setOpen(false);
  };

  const displayText = displayValue(selected, allOptionLabel);

  // 所有可渲染的选项（包括"全部"选项）
  const allOptions = showAllOption
    ? [{ value: allOptionValue, label: allOptionLabel }, ...options]
    : options;

  // "全部"选项后的索引，用于显示分隔线
  const dividerIndex = showAllOption ? 0 : -1;

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button
          variant='outline'
          className={`${buttonWidth} justify-start`}
          disabled={disabled}
        >
          {icon}
          <span className='truncate'>{displayText || placeholder}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className={`${popoverWidth} p-0`} align={align}>
        <div className='flex flex-col max-h-[400px]'>
          {/* 选项列表 */}
          <div className='flex-1 overflow-y-auto p-4 space-y-3'>
            {allOptions.map((option, index) => (
              <div key={option.value}>
                <div className='flex items-center space-x-2'>
                  <Checkbox
                    id={`filter-${option.value}`}
                    checked={pendingSelected.includes(option.value)}
                    onCheckedChange={() => handleToggle(option.value)}
                  />
                  <label
                    htmlFor={`filter-${option.value}`}
                    className={`text-sm cursor-pointer flex-1 ${
                      index === dividerIndex ? 'font-medium' : ''
                    }`}
                  >
                    {option.label}
                  </label>
                </div>
                {/* 在"全部"选项后显示分隔线 */}
                {index === dividerIndex && <div className='border-t mt-3' />}
              </div>
            ))}
          </div>

          {/* 底部按钮区域 */}
          <div className='border-t p-3 flex gap-2 bg-background'>
            <Button variant='ghost' size='sm' className='flex-1' onClick={handleCancel}>
              Cancel
            </Button>
            <Button size='sm' className='flex-1' onClick={handleConfirm}>
              Confirm
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
