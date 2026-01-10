import React, { useState, useMemo } from 'react';
import {
  Search,
  ChevronDown,
  RefreshCw,
  Plus,
  Home,
  Folder,
  User,
  Puzzle,
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
import type { ConfigScope } from '@/api/types';
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
  onNew: () => void;

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
  onNew,
  placeholder,
  searchPlaceholder,
  emptyText,
  triggerClassName = 'w-64',
}: ClaudeToolSelectBarProps) {
  const { t } = useTranslation('projects');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showDropdown, setShowDropdown] = useState<boolean>(false);

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

        <Button variant='default' size='sm' onClick={onNew}>
          <Plus className='h-4 w-4 mr-2' />
          {t('toolSelectBar.newCommand')}
        </Button>
      </div>
    </TooltipProvider>
  );
}
