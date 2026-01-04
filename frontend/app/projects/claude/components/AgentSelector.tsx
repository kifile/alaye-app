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
import type { ConfigScope, AgentInfo } from '@/api/types';
import { ScopeBadge } from './ScopeBadge';

interface AgentSelectorProps {
  agentsList: AgentInfo[];
  selectedAgent: { name: string; scope?: ConfigScope } | null;
  currentAgent: AgentInfo | null | undefined;
  onSelectAgent: (agent: AgentInfo) => void;
  onRefresh: () => void;
  onNew: () => void;
}

export function AgentSelector({
  agentsList,
  selectedAgent,
  currentAgent,
  onSelectAgent,
  onRefresh,
  onNew,
}: AgentSelectorProps) {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showDropdown, setShowDropdown] = useState<boolean>(false);

  // 过滤后的代理列表
  const filteredAgents = useMemo(() => {
    if (!searchQuery) return agentsList;
    const query = searchQuery.toLowerCase();
    return agentsList.filter(agent => agent.name.toLowerCase().includes(query));
  }, [agentsList, searchQuery]);

  return (
    <div className='flex items-center gap-3'>
      <DropdownMenu open={showDropdown} onOpenChange={setShowDropdown}>
        <DropdownMenuTrigger asChild>
          <Button variant='outline' className='w-64 justify-between'>
            {selectedAgent ? (
              <div className='flex items-center gap-2 truncate'>
                {currentAgent?.scope && (
                  <ScopeBadge scope={currentAgent.scope} showLabel={false} />
                )}
                <span className='truncate'>{selectedAgent.name}</span>
              </div>
            ) : (
              <span className='text-muted-foreground'>Choose an agent...</span>
            )}
            <ChevronDown className='h-4 w-4 opacity-50' />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className='w-64' align='start'>
          <div className='p-2'>
            <div className='flex items-center gap-2 mb-2'>
              <Search className='h-4 w-4 text-muted-foreground' />
              <Input
                placeholder='Search agents...'
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className='h-8'
              />
            </div>
            <div className='max-h-64 overflow-y-auto'>
              {filteredAgents.length === 0 ? (
                <div className='text-sm text-muted-foreground text-center py-4'>
                  No agents found
                </div>
              ) : (
                filteredAgents.map(agent => (
                  <DropdownMenuItem
                    key={`${agent.name}-${agent.scope}`}
                    onSelect={() => {
                      onSelectAgent(agent);
                      setShowDropdown(false);
                    }}
                    className='flex items-center gap-2'
                  >
                    <ScopeBadge scope={agent.scope} showLabel={false} />
                    <span className='truncate'>{agent.name}</span>
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
        onClick={() => onRefresh?.()}
        title='Refresh agents list'
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
