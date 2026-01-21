'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
import { RefreshCw, Folder, Trash2, Search, Star } from 'lucide-react';
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
  const [searchQuery, setSearchQuery] = useState('');
  const [filterFavorites, setFilterFavorites] = useState(false);

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

  // 筛选和搜索逻辑
  const filteredProjects = useMemo(() => {
    return projects.filter(project => {
      // 如果启用了收藏筛选，只显示收藏的项目
      if (filterFavorites && !project.favorited) {
        return false;
      }

      // 如果有搜索查询，按项目名称或路径搜索
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        return (
          project.project_name.toLowerCase().includes(query) ||
          (project.project_path && project.project_path.toLowerCase().includes(query))
        );
      }

      return true;
    });
  }, [projects, searchQuery, filterFavorites]);

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

      {/* 搜索和筛选 */}
      <div className='flex items-center gap-4'>
        {/* 搜索框 */}
        <div className='relative flex-1 max-w-md'>
          <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground' />
          <Input
            type='text'
            placeholder={t('searchPlaceholder') || 'Search projects...'}
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className='pl-9 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background transition-all'
            aria-label='Search projects'
          />
        </div>

        {/* 筛选按钮 */}
        <Button
          variant={filterFavorites ? 'default' : 'outline'}
          size='sm'
          onClick={() => setFilterFavorites(!filterFavorites)}
          className='flex items-center gap-2'
          aria-label={filterFavorites ? 'Show all projects' : 'Show only favorites'}
          aria-pressed={filterFavorites}
        >
          <Star className={`h-4 w-4 ${filterFavorites ? 'fill-white' : ''}`} />
          {filterFavorites
            ? t('showAll') || 'Show All'
            : t('showFavorites') || 'Favorites Only'}
        </Button>
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
      ) : filteredProjects.length === 0 ? (
        <Card className='text-center py-16'>
          <CardContent className='space-y-4'>
            {/* 根据不同情况显示不同的空状态 */}
            {searchQuery || filterFavorites ? (
              <>
                {/* 搜索/筛选无结果 */}
                <Search className='mx-auto h-16 w-16 text-muted-foreground mb-4' />
                <h3 className='text-xl font-semibold mb-2'>
                  {t('noSearchResults') || 'No projects found'}
                </h3>
                <p className='text-muted-foreground mb-6 max-w-md mx-auto'>
                  {searchQuery && filterFavorites
                    ? t('noSearchResultsDescBoth', { query: searchQuery })
                    : searchQuery
                      ? t('noSearchResultsDescSearch', { query: searchQuery })
                      : t('noSearchResultsDescFilter')}
                </p>
                <div className='flex items-center justify-center gap-3'>
                  {searchQuery && (
                    <Button
                      variant='outline'
                      onClick={() => setSearchQuery('')}
                      className='flex items-center gap-2'
                    >
                      {t('clearSearch') || 'Clear Search'}
                    </Button>
                  )}
                  {filterFavorites && (
                    <Button
                      variant='outline'
                      onClick={() => setFilterFavorites(false)}
                      className='flex items-center gap-2'
                    >
                      <Star className='h-4 w-4' />
                      {t('showAll') || 'Show All'}
                    </Button>
                  )}
                </div>
              </>
            ) : (
              <>
                {/* 完全没有项目 */}
                <Folder className='mx-auto h-16 w-16 text-muted-foreground mb-4' />
                <h3 className='text-xl font-semibold mb-2'>
                  {t('noProjects') || 'No projects found'}
                </h3>
                <p className='text-muted-foreground mb-6 max-w-md mx-auto'>
                  {t('noProjectsDesc') ||
                    'Get started by creating your first Claude project. Click the button below to scan for projects.'}
                </p>
                <Button onClick={handleRefresh} disabled={refreshing} size='lg'>
                  <RefreshCw
                    className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`}
                  />
                  {t('scanProjects') || 'Scan Projects'}
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
          {filteredProjects.map(project => (
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
