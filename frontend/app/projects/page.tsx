'use client';

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
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
import { RefreshCw, Folder, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import {
  listProjects,
  scanAllProjects,
  favoriteProject,
  unfavoriteProject,
  deleteProject,
  clearRemovedProjects,
} from '@/api/api';
import type { AIProjectInDB } from '@/api/types';
import { ProjectCard } from './components/ProjectCard';
import { Skeleton } from '@/components/ui/skeleton';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { loadAllPageTranslations } from '@/lib/i18n';

export default function ProjectsPage() {
  const { t } = useTranslation('projects');
  const router = useRouter();
  const [projects, setProjects] = useState<AIProjectInDB[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [clearingRemoved, setClearingRemoved] = useState(false);
  const [isClearDialogOpen, setIsClearDialogOpen] = useState(false);
  const [translationsLoaded, setTranslationsLoaded] = useState(false);

  // 加载项目列表
  const loadProjects = async () => {
    try {
      setLoading(true);

      // 首先加载页面的翻译文件
      if (!translationsLoaded) {
        await loadAllPageTranslations('projects');
        setTranslationsLoaded(true);
      }

      const response = await listProjects();

      if (response.success && response.data) {
        setProjects(response.data);
      } else {
        toast.error(t('loadFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error('Failed to load projects:', error);
      toast.error(t('loadFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    } finally {
      setLoading(false);
    }
  };

  // 刷新项目列表（强制扫描）
  const handleRefresh = async () => {
    try {
      setRefreshing(true);

      // 先触发扫描
      const scanResponse = await scanAllProjects({ force_refresh: true });

      if (!scanResponse.success) {
        toast.error(t('scanFailed'), {
          description: scanResponse.error || t('scanError'),
        });
        return;
      }

      toast.success(t('scanComplete'), {
        description: t('scanCompleteDesc'),
      });

      // 重新加载项目列表
      await loadProjects();
    } catch (error) {
      console.error('Failed to refresh projects:', error);
      toast.error(t('refreshFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    } finally {
      setRefreshing(false);
    }
  };

  // 处理项目卡片点击
  const handleProjectClick = (project: AIProjectInDB) => {
    router.push(`/projects/claude?id=${project.id}`);
  };

  // 处理收藏/取消收藏
  const handleToggleFavorite = async (project: AIProjectInDB) => {
    try {
      const response = project.favorited
        ? await unfavoriteProject({ id: project.id })
        : await favoriteProject({ id: project.id });

      if (response.success && response.data) {
        // 更新本地项目列表中的项目
        setProjects(prevProjects =>
          prevProjects.map(p => (p.id === project.id ? response.data! : p))
        );
        toast.success(
          project.favorited ? t('unfavoriteSuccess') : t('favoriteSuccess'),
          {
            description: project.project_name,
          }
        );
      } else {
        toast.error(project.favorited ? t('unfavoriteFailed') : t('favoriteFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
      toast.error(project.favorited ? t('unfavoriteFailed') : t('favoriteFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    }
  };

  // 处理删除（硬删除）
  const handleDelete = async (project: AIProjectInDB) => {
    try {
      const response = await deleteProject({ id: project.id });

      if (response.success) {
        // 从本地项目列表中移除
        setProjects(prevProjects => prevProjects.filter(p => p.id !== project.id));
        toast.success(t('deleteSuccess'), {
          description: project.project_name,
        });
      } else {
        toast.error(t('deleteFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error('Failed to delete project:', error);
      toast.error(t('deleteFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    }
  };

  // 清理已删除项目
  const handleClearRemoved = () => {
    setIsClearDialogOpen(true);
  };

  // 确认清理已删除项目
  const confirmClearRemoved = async () => {
    try {
      setClearingRemoved(true);

      const removedCount = projects.filter(p => p.removed).length;
      const response = await clearRemovedProjects();

      if (response.success) {
        // 重新加载项目列表
        await loadProjects();
        toast.success(t('clearRemovedSuccess', { count: removedCount }));
      } else {
        toast.error(t('clearRemovedFailed'), {
          description: response.error || t('unknownError'),
        });
      }
    } catch (error) {
      console.error('Failed to clear removed projects:', error);
      toast.error(t('clearRemovedFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    } finally {
      setClearingRemoved(false);
    }
  };

  // 组件挂载时加载项目列表
  useEffect(() => {
    loadProjects();
  }, []);

  // 计算是否有已删除的项目
  const hasRemovedProjects = projects.some(p => p.removed === true);

  return (
    <div className='container mx-auto p-6 space-y-6'>
      {/* 页面标题和刷新按钮 */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-3xl font-bold tracking-tight'>{t('title')}</h1>
          <p className='text-muted-foreground'>{t('description')}</p>
        </div>
        <div className='flex items-center gap-2'>
          {hasRemovedProjects && (
            <Button
              onClick={handleClearRemoved}
              disabled={clearingRemoved}
              variant='outline'
              className='flex items-center gap-2'
            >
              <Trash2 className={`h-4 w-4 ${clearingRemoved ? 'animate-pulse' : ''}`} />
              {clearingRemoved ? t('clearingRemoved') : t('clearRemoved')}
            </Button>
          )}
          <Button
            onClick={handleRefresh}
            disabled={refreshing}
            className='flex items-center gap-2'
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? t('refreshing') : t('refresh')}
          </Button>
        </div>
      </div>

      {/* 项目列表 */}
      {loading ? (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
          {[...Array(6)].map((_, i) => (
            <Card key={i} className='h-64'>
              <CardHeader>
                <Skeleton className='h-6 w-3/4' />
                <Skeleton className='h-4 w-1/2' />
              </CardHeader>
              <CardContent className='space-y-4'>
                <Skeleton className='h-4 w-full' />
                <Skeleton className='h-4 w-2/3' />
                <div className='flex justify-between'>
                  <Skeleton className='h-6 w-16' />
                  <Skeleton className='h-6 w-20' />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : projects.length === 0 ? (
        <Card className='text-center py-12'>
          <CardContent>
            <Folder className='mx-auto h-12 w-12 text-muted-foreground mb-4' />
            <h3 className='text-lg font-semibold mb-2'>{t('noProjects')}</h3>
            <p className='text-muted-foreground mb-4'>{t('noProjectsDesc')}</p>
            <Button onClick={handleRefresh} disabled={refreshing}>
              <RefreshCw
                className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`}
              />
              {t('scanProjects')}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
          {projects.map(project => (
            <ProjectCard
              key={project.id}
              project={project}
              onItemClick={handleProjectClick}
              onToggleFavorite={handleToggleFavorite}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* 清理已删除项目确认对话框 */}
      <AlertDialog open={isClearDialogOpen} onOpenChange={setIsClearDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('clearRemovedConfirmTitle')}</AlertDialogTitle>
            <AlertDialogDescription className='whitespace-pre-line'>
              {t('clearRemovedConfirmDescription')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('clearRemovedCancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmClearRemoved}
              disabled={clearingRemoved}
              className='bg-destructive text-destructive-foreground hover:bg-destructive/90'
            >
              {clearingRemoved ? t('clearingRemoved') : t('clearRemovedConfirm')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
