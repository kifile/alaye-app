import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
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
import {
  Activity,
  Archive,
  History,
  Settings,
  Star,
  Trash2,
  MoreVertical,
} from 'lucide-react';
import type { AIProjectInDB } from '@/api/types';
import { AiToolType } from '@/api/types';
import { useTranslation } from 'react-i18next';
import { useRouter } from 'next/navigation';
import { formatTime } from '@/lib/utils';

interface ProjectCardProps {
  project: AIProjectInDB;
  onItemClick?: (project: AIProjectInDB) => void;
  onToggleFavorite?: (project: AIProjectInDB) => void;
  onDelete?: (project: AIProjectInDB) => void;
}

export function ProjectCard({
  project,
  onItemClick,
  onToggleFavorite,
  onDelete,
}: ProjectCardProps) {
  const { t } = useTranslation('projects');
  const router = useRouter();
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const isRemoved = project.removed === true;
  const isFavorited = project.favorited === true;

  // 处理进入配置页面
  const handleConfig = (e: React.MouseEvent) => {
    e.stopPropagation();
    onItemClick?.(project);
  };

  // 处理删除
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsDeleteDialogOpen(true);
  };

  // 确认删除
  const confirmDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete?.(project);
      setIsDeleteDialogOpen(false);
    } finally {
      setIsDeleting(false);
    }
  };

  // 处理收藏/取消收藏
  const handleToggleFavorite = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleFavorite?.(project);
  };

  // 处理进入会话列表
  const handleViewSessions = (e: React.MouseEvent) => {
    e.stopPropagation();
    router.push(`/projects/session?id=${project.id}`);
  };

  // 获取 AI 工具图标组件
  const getAiToolIcon = (toolType: string) => {
    switch (toolType) {
      case 'claude':
        return (
          <img
            src='/icons/claude.ico'
            alt='Claude'
            className='h-3.5 w-3.5 object-contain'
          />
        );
      default:
        return <span className='text-[10px]'>{toolType}</span>;
    }
  };

  return (
    <>
      <Card
        className={`group relative overflow-hidden transition-all duration-200 ${
          isRemoved
            ? 'opacity-60 bg-muted/30'
            : 'hover:shadow-lg hover:border-primary/20'
        }`}
      >
        <CardHeader className='pb-3'>
          {/* 顶部区域：标题、收藏按钮、更多菜单 */}
          <div className='flex items-start gap-3'>
            {/* 主内容区域 */}
            <div className='flex-1 min-w-0 space-y-1.5'>
              {/* 标题和状态标签 */}
              <div className='flex items-center gap-2'>
                {isRemoved && (
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className='cursor-help shrink-0'>
                          <Archive className='h-3.5 w-3.5 text-muted-foreground' />
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>
                          {t('card.removedTooltip') || 'This project has been deleted'}
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                )}
                <CardTitle
                  className={`text-base font-semibold line-clamp-1 transition-colors ${
                    isRemoved
                      ? 'line-through text-muted-foreground'
                      : 'group-hover:text-primary'
                  }`}
                >
                  {project.project_name}
                </CardTitle>
                {isFavorited && !isRemoved && (
                  <div className='w-4 h-4 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center shrink-0'>
                    <Star className='h-2.5 w-2.5 fill-amber-500 text-amber-500' />
                  </div>
                )}
              </div>

              {/* 路径 - 带 tooltip */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <CardDescription className='text-xs line-clamp-1 font-mono cursor-help opacity-70'>
                      {project.project_path || t('card.noPathInfo')}
                    </CardDescription>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className='font-mono text-xs'>
                      {project.project_path || t('card.noPathInfo')}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>

            {/* 操作按钮组 */}
            <div className='flex items-center gap-1 shrink-0'>
              {/* 收藏按钮 - 只在非 removed 状态显示 */}
              {!isRemoved && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant='ghost'
                        size='icon'
                        className='h-8 w-8 transition-opacity focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none'
                        onClick={handleToggleFavorite}
                        aria-label={
                          isFavorited
                            ? t('card.unfavorite') || 'Unfavorite'
                            : t('card.favorite') || 'Favorite'
                        }
                        aria-pressed={isFavorited}
                      >
                        {isFavorited ? (
                          <Star className='h-4 w-4 fill-yellow-400 text-yellow-400' />
                        ) : (
                          <Star className='h-4 w-4 text-muted-foreground/50 hover:text-amber-400 transition-colors' />
                        )}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>
                        {isFavorited
                          ? t('card.unfavorite') || 'Unfavorite'
                          : t('card.favorite') || 'Favorite'}
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}

              {/* View Sessions 按钮 */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant='ghost'
                      size='icon'
                      className='h-8 w-8 transition-opacity focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none'
                      onClick={handleViewSessions}
                      aria-label={t('card.viewSessions') || 'View Sessions'}
                    >
                      <History className='h-4 w-4' />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t('card.viewSessions') || 'View Sessions'}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              {/* 更多操作菜单 */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant='ghost'
                    size='icon'
                    className='h-8 w-8 transition-opacity focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none'
                    aria-label={t('card.moreActions') || 'More actions'}
                  >
                    <MoreVertical className='h-4 w-4' />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align='end' className='w-[180px]'>
                  <DropdownMenuItem
                    onClick={handleDelete}
                    className='text-destructive focus:text-destructive'
                  >
                    <Trash2 className='h-4 w-4 mr-2' />
                    <span>{t('card.delete') || 'Delete'}</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </CardHeader>

        <CardContent className='space-y-4 pt-0'>
          {/* AI 工具标签 */}
          <div className='flex items-center gap-2 flex-wrap'>
            {project.ai_tools.map(tool => (
              <div
                key={tool}
                className={`
                  relative h-8 w-8 rounded-full flex items-center justify-center
                  transition-all duration-200
                  ${
                    isRemoved
                      ? 'bg-muted/50 grayscale opacity-60'
                      : 'bg-muted shadow-sm hover:shadow-md hover:scale-110'
                  }
                `}
                title={tool}
              >
                {tool === 'claude' || tool === AiToolType.CLAUDE ? (
                  <img
                    src='/icons/claude.ico'
                    alt='Claude'
                    className='h-5 w-5 object-contain'
                  />
                ) : (
                  <span className='text-[10px] font-semibold text-foreground uppercase'>
                    {String(tool).slice(0, 2)}
                  </span>
                )}
              </div>
            ))}
          </div>

          {/* 底部信息栏 */}
          <div className='flex items-center justify-between text-xs text-muted-foreground'>
            {/* 最后活跃时间 */}
            {project.last_active_at_str && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className='flex items-center gap-1.5 cursor-help'>
                      <Activity className='h-3 w-3 opacity-60' />
                      <span className='opacity-80'>
                        {formatTime(project.last_active_at_str)}
                      </span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>
                      {t('card.lastActive')} {formatTime(project.last_active_at_str)}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}

            {/* 快速操作按钮 */}
            {!isRemoved && (
              <Button
                variant='outline'
                size='sm'
                className='h-7 px-2.5 text-xs font-medium transition-all hover:bg-primary hover:text-primary-foreground hover:border-primary hover:shadow-sm focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none'
                onClick={handleConfig}
                aria-label={`${t('card.configure') || 'Configure'} ${project.project_name}`}
              >
                <Settings className='h-3.5 w-3.5 mr-1.5' />
                {t('card.configure') || 'Configure'}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 删除确认对话框 */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t('card.deleteConfirmTitle') || 'Delete Project'}
            </AlertDialogTitle>
            <AlertDialogDescription className='whitespace-pre-line'>
              {t('card.deleteConfirmDescription', {
                projectName: project.project_name,
              }) ||
                `Are you sure you want to delete "${project.project_name}"? This action cannot be undone.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('card.deleteCancel') || 'Cancel'}</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={isDeleting}
              className='bg-destructive text-destructive-foreground hover:bg-destructive/90'
            >
              {isDeleting
                ? t('card.deleteInProgress') || 'Deleting...'
                : t('card.deleteConfirm') || 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
