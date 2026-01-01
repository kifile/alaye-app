import React from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity } from 'lucide-react';
import type { AIProjectInDB } from '@/api/types';
import { useTranslation } from 'react-i18next';

interface ProjectCardProps {
  project: AIProjectInDB;
  onItemClick?: (project: AIProjectInDB) => void;
}

export function ProjectCard({ project, onItemClick }: ProjectCardProps) {
  const { t } = useTranslation('projects');

  // 获取 AI 工具标签颜色
  const getAiToolBadgeVariant = (toolType: string) => {
    switch (toolType) {
      case 'claude':
        return 'default';
      default:
        return 'secondary';
    }
  };

  return (
    <Card
      className={`hover:shadow-md transition-shadow ${onItemClick ? 'cursor-pointer' : ''}`}
      onClick={() => onItemClick?.(project)}
    >
      <CardHeader>
        <div className='flex items-start justify-between'>
          <div className='flex-1'>
            <CardTitle className='text-lg line-clamp-2'>
              {project.project_name}
            </CardTitle>
            <CardDescription className='line-clamp-1 mt-1'>
              {project.project_path || t('card.noPathInfo')}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className='space-y-4'>
        {/* AI 工具标签 */}
        <div className='flex flex-wrap gap-2'>
          {project.ai_tools.map(tool => (
            <Badge key={tool} variant={getAiToolBadgeVariant(tool)} className='text-xs'>
              {tool.toUpperCase()}
            </Badge>
          ))}
        </div>

        {/* 项目信息 */}
        <div className='space-y-2 text-xs text-muted-foreground'>
          {project.last_active_at_str && (
            <div className='flex items-center gap-2'>
              <Activity className='h-3 w-3' />
              <span>
                {t('card.lastActive')} {project.last_active_at_str}
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
