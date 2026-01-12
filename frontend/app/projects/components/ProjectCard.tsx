import React from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Activity, MessageSquare, Settings } from 'lucide-react';
import type { AIProjectInDB } from '@/api/types';
import { useTranslation } from 'react-i18next';
import { useRouter } from 'next/navigation';

interface ProjectCardProps {
  project: AIProjectInDB;
  onItemClick?: (project: AIProjectInDB) => void;
}

export function ProjectCard({ project, onItemClick }: ProjectCardProps) {
  const { t } = useTranslation('projects');
  const router = useRouter();

  // 处理进入配置页面
  const handleConfig = (e: React.MouseEvent) => {
    e.stopPropagation();
    onItemClick?.(project);
  };

  // 处理进入会话列表
  const handleViewSessions = (e: React.MouseEvent) => {
    e.stopPropagation();
    router.push(`/projects/session?id=${project.id}`);
  };

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
    <Card className='hover:shadow-md transition-shadow'>
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

        {/* 操作按钮 */}
        <div className='pt-2 border-t'>
          <div className='flex gap-2'>
            <Button
              variant='outline'
              size='sm'
              className='flex-1'
              onClick={handleConfig}
            >
              <Settings className='h-4 w-4 mr-2' />
              {t('card.config') || 'Config'}
            </Button>
            <Button
              variant='outline'
              size='sm'
              className='flex-1'
              onClick={handleViewSessions}
            >
              <MessageSquare className='h-4 w-4 mr-2' />
              {t('card.viewSessions') || 'View Sessions'}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
