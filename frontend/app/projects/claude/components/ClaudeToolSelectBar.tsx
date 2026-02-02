import React, { useState, useMemo, useCallback } from 'react';
import { type LucideIcon } from 'lucide-react';
import {
  Search,
  ChevronDown,
  RefreshCw,
  Plus,
  Home,
  Folder,
  User,
  Puzzle,
  Check,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ConfigScope } from '@/api/types';
import { useTranslation } from 'react-i18next';

// 与 ScopeBadge.tsx 保持一致的图标配置
const SCOPE_ICONS = {
  user: Home,
  project: Folder,
  local: User,
  plugin: Puzzle,
};

export interface ToolItem {
  name: string;
  scope: ConfigScope;
  description?: string;
  pluginName?: string;
}

export interface ToolGroup {
  label: string;
  items: ToolItem[];
}

interface ClaudeToolSelectBarProps {
  // 分组数据
  groups: ToolGroup[];

  // 当前选中项
  selectedItem: { name: string; scope?: ConfigScope } | null;

  // 回调函数
  onSelectItem: (item: ToolItem) => void;
  onRefresh: () => void;
  onCreateItem?: (name: string, scope: ConfigScope) => void; // 新建项的回调

  // Popover 控制
  newPopoverOpen?: boolean; // 外部控制 Popover 的开关状态
  onPopoverOpenChange?: (open: boolean) => void; // Popover 状态变化回调

  // UI 文本 (可选，如果未提供则使用翻译)
  placeholder?: string;
  searchPlaceholder?: string;
  emptyText?: string;

  // 额外的 className
  triggerClassName?: string;
}

export function ClaudeToolSelectBar({
  groups,
  selectedItem,
  onSelectItem,
  onRefresh,
  onCreateItem,
  newPopoverOpen,
  onPopoverOpenChange,
  placeholder,
  searchPlaceholder,
  emptyText,
  triggerClassName = 'w-64',
}: ClaudeToolSelectBarProps) {
  const { t } = useTranslation('projects');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showDropdown, setShowDropdown] = useState<boolean>(false);

  // Popover 状态 - 支持外部控制
  const [internalPopoverOpen, setInternalPopoverOpen] = useState<boolean>(false);
  const showNewPopover =
    newPopoverOpen !== undefined ? newPopoverOpen : internalPopoverOpen;

  const [newItemName, setNewItemName] = useState<string>('');
  const [newItemScope, setNewItemScope] = useState<ConfigScope>(ConfigScope.PROJECT);

  // Use translation with fallback to provided props
  const finalPlaceholder = placeholder ?? t('toolSelectBar.selectCommand');
  const finalSearchPlaceholder = searchPlaceholder ?? t('toolSelectBar.searchCommands');
  const finalEmptyText = emptyText ?? t('toolSelectBar.noCommands');

  // 扁平化所有 items 用于搜索和查找当前项
  const allItems = useMemo(() => {
    return groups.flatMap(group => group.items);
  }, [groups]);

  // 当前选中的完整项
  const currentItem = useMemo(() => {
    if (!selectedItem) return null;
    return allItems.find(
      item =>
        item.name === selectedItem.name &&
        (!selectedItem.scope || item.scope === selectedItem.scope)
    );
  }, [selectedItem, allItems]);

  // 过滤后的分组
  const filteredGroups = useMemo(() => {
    if (!searchQuery) return groups;
    const query = searchQuery.toLowerCase();
    return groups
      .map(group => ({
        ...group,
        items: group.items.filter(item => item.name.toLowerCase().includes(query)),
      }))
      .filter(group => group.items.length > 0);
  }, [groups, searchQuery]);

  // 处理新建项
  const handleCreateItem = useCallback(() => {
    if (!newItemName.trim()) return;

    onCreateItem?.(newItemName.trim(), newItemScope);

    // 重置表单并关闭 Popover
    setNewItemName('');
    setNewItemScope(ConfigScope.PROJECT);
    if (newPopoverOpen === undefined) {
      setInternalPopoverOpen(false);
    } else if (onPopoverOpenChange) {
      onPopoverOpenChange(false);
    }
  }, [newItemName, newItemScope, onCreateItem, newPopoverOpen, onPopoverOpenChange]);

  // 处理 Popover 打开时的状态重置
  const handlePopoverOpenChange = useCallback(
    (open: boolean) => {
      if (newPopoverOpen === undefined) {
        // 非受控模式：内部管理状态
        setInternalPopoverOpen(open);
      } else if (onPopoverOpenChange) {
        // 受控模式：通知父组件
        onPopoverOpenChange(open);
      }

      if (!open) {
        // 关闭时重置表单
        setNewItemName('');
        setNewItemScope(ConfigScope.PROJECT);
      }
    },
    [newPopoverOpen, onPopoverOpenChange]
  );

  // scope 选项
  const scopeOptions: { value: ConfigScope; label: string; icon: LucideIcon }[] = [
    {
      value: ConfigScope.PROJECT,
      label: t('detail.scopeBadge.project.label'),
      icon: Folder,
    },
    {
      value: ConfigScope.USER,
      label: t('detail.scopeBadge.user.label'),
      icon: Home,
    },
  ];

  return (
    <TooltipProvider>
      <div className='flex items-center gap-3'>
        <DropdownMenu open={showDropdown} onOpenChange={setShowDropdown}>
          <DropdownMenuTrigger asChild>
            <Button variant='outline' className={`${triggerClassName} justify-between`}>
              {selectedItem && currentItem ? (
                <div className='flex items-center gap-2 truncate'>
                  {(() => {
                    const ScopeIcon =
                      SCOPE_ICONS[currentItem.scope] || SCOPE_ICONS.project;
                    return <ScopeIcon className='h-4 w-4 flex-shrink-0' />;
                  })()}
                  <span className='truncate'>{selectedItem.name}</span>
                </div>
              ) : (
                <span className='text-muted-foreground'>{finalPlaceholder}</span>
              )}
              <ChevronDown className='h-4 w-4 opacity-50' />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className='w-80' align='start'>
            <div className='p-2'>
              <div className='flex items-center gap-2 mb-2'>
                <Search className='h-4 w-4 text-muted-foreground' />
                <Input
                  placeholder={finalSearchPlaceholder}
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className='h-8'
                />
              </div>
              <div className='max-h-64 overflow-y-auto'>
                {filteredGroups.length === 0 ? (
                  <div className='text-sm text-muted-foreground text-center py-4'>
                    {finalEmptyText}
                  </div>
                ) : (
                  filteredGroups.map((group, groupIndex) => (
                    <div key={group.label}>
                      {/* Group Label */}
                      <div className='px-2 py-1 text-xs font-medium text-muted-foreground sticky top-0 bg-background'>
                        {group.label}
                      </div>
                      {/* Group Items */}
                      {group.items.map(item => (
                        <DropdownMenuItem
                          key={`${item.name}-${item.scope}`}
                          onSelect={() => {
                            onSelectItem(item);
                            setShowDropdown(false);
                          }}
                          className='flex flex-col items-start gap-1 py-2 px-2'
                        >
                          <div className='flex items-center gap-2 w-full'>
                            <span className='truncate font-medium'>{item.name}</span>
                          </div>
                          {item.description && (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <div className='text-xs text-muted-foreground line-clamp-2 w-full cursor-help'>
                                  {item.description}
                                </div>
                              </TooltipTrigger>
                              <TooltipContent side='right' className='max-w-xs'>
                                <p>{item.description}</p>
                              </TooltipContent>
                            </Tooltip>
                          )}
                        </DropdownMenuItem>
                      ))}
                      {/* Separator between groups (except last group) */}
                      {groupIndex < filteredGroups.length - 1 && (
                        <div className='my-1 h-px bg-border' />
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          variant='outline'
          size='icon'
          onClick={() => onRefresh?.()}
          title={t('toolSelectBar.refreshList')}
        >
          <RefreshCw className='h-4 w-4' />
        </Button>

        <Popover open={showNewPopover} onOpenChange={handlePopoverOpenChange}>
          <PopoverTrigger asChild>
            <Button variant='default' size='icon' title={t('toolSelectBar.newCommand')}>
              <Plus className='h-4 w-4' />
            </Button>
          </PopoverTrigger>
          <PopoverContent className='w-80 p-4' align='end'>
            <div className='space-y-4'>
              <div className='space-y-2'>
                <label className='text-sm font-medium'>Scope</label>
                <Select
                  value={newItemScope}
                  onValueChange={value => setNewItemScope(value as ConfigScope)}
                >
                  <SelectTrigger className='w-full'>
                    <SelectValue placeholder='Select scope' />
                  </SelectTrigger>
                  <SelectContent>
                    {scopeOptions.map(option => {
                      const Icon = option.icon;
                      return (
                        <SelectItem key={option.value} value={option.value}>
                          <div className='flex items-center gap-2'>
                            <Icon className='h-4 w-4' />
                            <span>{option.label}</span>
                          </div>
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>
              </div>

              <div className='space-y-2'>
                <label className='text-sm font-medium'>{t('skills.enterName')}</label>
                <Input
                  placeholder={t('toolSelectBar.newCommand')}
                  value={newItemName}
                  onChange={e => setNewItemName(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && newItemName.trim()) {
                      handleCreateItem();
                    }
                  }}
                  autoFocus
                />
              </div>

              <div className='flex justify-end gap-2'>
                <Button
                  variant='outline'
                  size='sm'
                  onClick={() => {
                    if (newPopoverOpen === undefined) {
                      setInternalPopoverOpen(false);
                    } else if (onPopoverOpenChange) {
                      onPopoverOpenChange(false);
                    }
                    setNewItemName('');
                    setNewItemScope(ConfigScope.PROJECT);
                  }}
                >
                  {t('skills.cancel')}
                </Button>
                <Button
                  variant='default'
                  size='sm'
                  onClick={handleCreateItem}
                  disabled={!newItemName.trim()}
                >
                  <Check className='h-4 w-4 mr-2' />
                  {t('skills.save')}
                </Button>
              </div>
            </div>
          </PopoverContent>
        </Popover>
      </div>
    </TooltipProvider>
  );
}
