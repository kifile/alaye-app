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
import type { ConfigScope, SkillInfo } from '@/api/types';
import { ScopeBadge } from './ScopeBadge';

interface SkillSelectorProps {
  skillsList: SkillInfo[];
  selectedSkill: { name: string; scope?: ConfigScope } | null;
  currentSkill: SkillInfo | null | undefined;
  onSelectSkill: (skill: SkillInfo) => void;
  onRefresh: () => void;
  onNew: () => void;
}

export function SkillSelector({
  skillsList,
  selectedSkill,
  currentSkill,
  onSelectSkill,
  onRefresh,
  onNew,
}: SkillSelectorProps) {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showDropdown, setShowDropdown] = useState<boolean>(false);

  // 过滤后的 skills 列表
  const filteredSkills = useMemo(() => {
    if (!searchQuery) return skillsList;
    const query = searchQuery.toLowerCase();
    return skillsList.filter(skill => skill.name.toLowerCase().includes(query));
  }, [skillsList, searchQuery]);

  return (
    <div className='flex items-center gap-3'>
      <DropdownMenu open={showDropdown} onOpenChange={setShowDropdown}>
        <DropdownMenuTrigger asChild>
          <Button variant='outline' className='w-64 justify-between'>
            {selectedSkill ? (
              <div className='flex items-center gap-2 truncate'>
                {currentSkill?.scope && (
                  <ScopeBadge scope={currentSkill.scope} showLabel={false} />
                )}
                <span className='truncate'>{selectedSkill.name}</span>
              </div>
            ) : (
              <span className='text-muted-foreground'>Choose a skill...</span>
            )}
            <ChevronDown className='h-4 w-4 opacity-50' />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className='w-64' align='start'>
          <div className='p-2'>
            <div className='flex items-center gap-2 mb-2'>
              <Search className='h-4 w-4 text-muted-foreground' />
              <Input
                placeholder='Search skills...'
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className='h-8'
              />
            </div>
            <div className='max-h-64 overflow-y-auto'>
              {filteredSkills.length === 0 ? (
                <div className='text-sm text-muted-foreground text-center py-4'>
                  No skills found
                </div>
              ) : (
                filteredSkills.map(skill => (
                  <DropdownMenuItem
                    key={`${skill.name}-${skill.scope}`}
                    onSelect={() => {
                      onSelectSkill(skill);
                      setShowDropdown(false);
                    }}
                    className='flex items-center gap-2'
                  >
                    <ScopeBadge scope={skill.scope} showLabel={false} />
                    <span className='truncate'>{skill.name}</span>
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
        title='Refresh skills list'
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
