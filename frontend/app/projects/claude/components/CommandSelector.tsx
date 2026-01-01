import React, { useState, useMemo } from 'react';
import { Search, ChevronDown, RefreshCw, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { ConfigScope, CommandInfo } from '@/api/types';
import { ScopeBadge } from './ScopeBadge';

interface CommandSelectorProps {
  commandsList: CommandInfo[];
  selectedCommand: { name: string; scope?: ConfigScope } | null;
  currentCommand: CommandInfo | null | undefined;
  onSelectCommand: (command: CommandInfo) => void;
  onRefresh: () => void;
  onNew: () => void;
}

export function CommandSelector({
  commandsList,
  selectedCommand,
  currentCommand,
  onSelectCommand,
  onRefresh,
  onNew,
}: CommandSelectorProps) {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showDropdown, setShowDropdown] = useState<boolean>(false);

  // 过滤后的命令列表
  const filteredCommands = useMemo(() => {
    if (!searchQuery) return commandsList;
    const query = searchQuery.toLowerCase();
    return commandsList.filter(cmd => cmd.name.toLowerCase().includes(query));
  }, [commandsList, searchQuery]);

  return (
    <div className='flex items-center gap-3'>
      <DropdownMenu open={showDropdown} onOpenChange={setShowDropdown}>
        <DropdownMenuTrigger asChild>
          <Button variant='outline' className='w-64 justify-between'>
            {selectedCommand ? (
              <div className='flex items-center gap-2 truncate'>
                {currentCommand?.scope && (
                  <ScopeBadge scope={currentCommand.scope} showLabel={false} />
                )}
                <span className='truncate'>{selectedCommand.name}</span>
              </div>
            ) : (
              <span className='text-muted-foreground'>Choose a command...</span>
            )}
            <ChevronDown className='h-4 w-4 opacity-50' />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className='w-64' align='start'>
          <div className='p-2'>
            <div className='flex items-center gap-2 mb-2'>
              <Search className='h-4 w-4 text-muted-foreground' />
              <Input
                placeholder='Search commands...'
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className='h-8'
              />
            </div>
            <div className='max-h-64 overflow-y-auto'>
              {filteredCommands.length === 0 ? (
                <div className='text-sm text-muted-foreground text-center py-4'>
                  No commands found
                </div>
              ) : (
                filteredCommands.map(cmd => (
                  <DropdownMenuItem
                    key={`${cmd.name}-${cmd.scope}`}
                    onSelect={() => {
                      onSelectCommand(cmd);
                      setShowDropdown(false);
                    }}
                    className='flex items-center gap-2'
                  >
                    <ScopeBadge scope={cmd.scope} showLabel={false} />
                    <span className='truncate'>{cmd.name}</span>
                  </DropdownMenuItem>
                ))
              )}
            </div>
          </div>
        </DropdownMenuContent>
      </DropdownMenu>

      <Button
        variant='outline'
        size='icon'
        onClick={onRefresh}
        title='Refresh commands list'
      >
        <RefreshCw className='h-4 w-4' />
      </Button>

      <Button variant='default' size='sm' onClick={onNew}>
        <Plus className='h-4 w-4 mr-2' />
        New
      </Button>
    </div>
  );
}
