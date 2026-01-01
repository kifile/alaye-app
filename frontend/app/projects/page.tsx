'use client';

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RefreshCw, Folder } from 'lucide-react';
import { toast } from 'sonner';
import { listProjects, scanAllProjects } from '@/api/api';
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

  // 组件挂载时加载项目列表
  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <div className='container mx-auto p-6 space-y-6'>
      {/* 页面标题和刷新按钮 */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-3xl font-bold tracking-tight'>{t('title')}</h1>
          <p className='text-muted-foreground'>{t('description')}</p>
        </div>
        <Button
          onClick={handleRefresh}
          disabled={refreshing}
          className='flex items-center gap-2'
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? t('refreshing') : t('refresh')}
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
            />
          ))}
        </div>
      )}
    </div>
  );
}
