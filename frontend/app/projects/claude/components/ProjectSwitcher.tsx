'use client';

import React, { useEffect, useState, useCallback } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { listProjects } from '@/api/api';
import type { AIProjectInDB } from '@/api/types';
import { useTranslation } from 'react-i18next';

interface ProjectSwitcherProps {
  currentProjectId: number;
  onProjectChange: (projectId: number) => void;
}

export function ProjectSwitcher({
  currentProjectId,
  onProjectChange,
}: ProjectSwitcherProps) {
  const { t } = useTranslation('projects');
  const [projects, setProjects] = useState<AIProjectInDB[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentValue, setCurrentValue] = useState(String(currentProjectId));
  const [open, setOpen] = useState(false);

  // 加载项目列表
  const loadProjects = useCallback(async () => {
    try {
      setLoading(true);
      const response = await listProjects();

      if (!response.success) {
        toast.error(t('switcher.loadFailed'), {
          description: response.error || t('unknownError'),
        });
        return;
      }

      setProjects(response.data || []);
    } catch (error) {
      console.error('Failed to load projects:', error);
      toast.error(t('switcher.loadFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // 同步外部传入的 projectId
  useEffect(() => {
    setCurrentValue(String(currentProjectId));
  }, [currentProjectId]);

  const handleValueChange = (value: string) => {
    const newProjectId = Number(value);
    setCurrentValue(value);
    setOpen(false);
    onProjectChange(newProjectId);
  };

  // 查找当前项目
  const currentProject = projects.find(p => p.id === Number(currentValue));

  if (loading) {
    return (
      <div className='flex items-center gap-2 h-7'>
        <Loader2 className='h-3.5 w-3.5 animate-spin text-gray-400' />
      </div>
    );
  }

  if (projects.length === 0) {
    return null;
  }

  return (
    <Select
      value={currentValue}
      onValueChange={handleValueChange}
      onOpenChange={setOpen}
      open={open}
    >
      <SelectTrigger className='h-7 px-2.5 pr-2 gap-1.5 rounded-md bg-gray-100/80 hover:bg-gray-200/80 data-[state=open]:bg-gray-200/80 transition-all duration-200 border-0 shadow-none'>
        <SelectValue placeholder={t('switcher.selectProject')}>
          <div className='flex items-center gap-1.5 min-w-0'>
            <span className='text-sm font-medium text-gray-700 truncate block max-w-[180px]'>
              {currentProject?.project_name || t('switcher.selectProject')}
            </span>
          </div>
        </SelectValue>
      </SelectTrigger>
      <SelectContent
        align='start'
        className='w-[280px] min-w-0 border-gray-200/60 shadow-lg'
      >
        {projects.map(project => (
          <SelectItem
            key={project.id}
            value={String(project.id)}
            className='rounded-md py-2.5 px-2.5 focus:bg-gray-100 data-[highlighted]:bg-gray-100 cursor-pointer'
          >
            <div className='flex flex-col items-start gap-0.5 min-w-0'>
              <span className='text-sm font-medium text-gray-900 truncate w-full'>
                {project.project_name}
              </span>
              {project.project_path && (
                <span
                  className='text-xs text-gray-500 truncate w-full'
                  title={project.project_path}
                >
                  {project.project_path}
                </span>
              )}
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
