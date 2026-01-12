'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { getProject } from '@/api/api';
import type { AIProjectInDB } from '@/api/types';
import { ProjectSwitcher } from '../claude/components/ProjectSwitcher';
import { SessionList } from './components/SessionList';
import { SessionDetail } from './components/SessionDetail';
import { useTranslation } from 'react-i18next';
import { loadAllPageTranslations } from '@/lib/i18n';

function SessionPageContent() {
  const { t } = useTranslation('projects');
  const searchParams = useSearchParams();
  const router = useRouter();

  const projectId = Number(searchParams?.get('id') || 0);
  const sessionIdParam = searchParams?.get('sessionId') || null;

  const [project, setProject] = useState<AIProjectInDB | null>(null);
  const [currentProjectId, setCurrentProjectId] = useState(projectId);
  const [loading, setLoading] = useState(true);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    sessionIdParam
  );
  const [translationsLoaded, setTranslationsLoaded] = useState(false);

  // 加载项目详情
  const loadProjectData = async () => {
    try {
      setLoading(true);

      // 首先加载页面的翻译文件
      if (!translationsLoaded) {
        await loadAllPageTranslations('projects');
        setTranslationsLoaded(true);
      }

      // 加载项目信息
      const projectResponse = await getProject({ id: currentProjectId });

      if (!projectResponse.success) {
        toast.error(t('detail.loadInfoFailed'), {
          description: projectResponse.error || t('unknownError'),
        });
        return;
      }

      setProject(projectResponse.data || null);
    } catch (error) {
      console.error('Failed to load project data:', error);
      toast.error(t('detail.loadDataFailed'), {
        description: error instanceof Error ? error.message : t('networkError'),
      });
    } finally {
      setLoading(false);
      setIsInitialLoading(false);
    }
  };

  // 加载翻译
  useEffect(() => {
    const loadTranslations = async () => {
      if (!translationsLoaded) {
        await loadAllPageTranslations('projects');
        setTranslationsLoaded(true);
      }
    };
    loadTranslations();
  }, []);

  useEffect(() => {
    if (currentProjectId && currentProjectId > 0) {
      loadProjectData();
    }
  }, [currentProjectId]);

  // 处理项目切换
  const handleProjectChange = (newProjectId: number) => {
    if (newProjectId === currentProjectId) {
      return;
    }

    const currentParams = new URLSearchParams(
      Array.from(searchParams?.entries() || [])
    );
    currentParams.set('id', String(newProjectId));
    // 清除 sessionId
    currentParams.delete('sessionId');
    const newUrl = `${window.location.pathname}?${currentParams.toString()}`;
    router.replace(newUrl, { scroll: false });

    setCurrentProjectId(newProjectId);
    setProject(null);
    setSelectedSessionId(null);
  };

  // 处理 session 选择
  const handleSessionSelect = (sessionId: string) => {
    setSelectedSessionId(sessionId);

    // 更新 URL 参数
    const currentParams = new URLSearchParams(
      Array.from(searchParams?.entries() || [])
    );
    currentParams.set('sessionId', sessionId);
    const newUrl = `${window.location.pathname}?${currentParams.toString()}`;
    router.replace(newUrl, { scroll: false });
  };

  // 处理返回
  const handleBack = () => {
    setSelectedSessionId(null);

    // 更新 URL 参数
    const currentParams = new URLSearchParams(
      Array.from(searchParams?.entries() || [])
    );
    currentParams.delete('sessionId');
    const newUrl = `${window.location.pathname}?${currentParams.toString()}`;
    router.replace(newUrl, { scroll: false });
  };

  // 初始加载时显示全屏 loading
  if (isInitialLoading) {
    return (
      <div className='container mx-auto p-6 flex items-center justify-center min-h-screen'>
        <div className='text-center'>
          <Loader2 className='h-8 w-8 animate-spin mx-auto mb-4' />
          <p className='text-muted-foreground'>Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className='min-h-screen bg-gray-50'>
      {/* 页面头部 */}
      <div className='bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm'>
        <div className='mx-auto px-3 py-1.5'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center gap-2'>
              <Button
                variant='ghost'
                size='icon'
                onClick={() => router.back()}
                className='text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-all duration-200 rounded h-7 w-7'
                title='Back'
              >
                <ArrowLeft className='h-4 w-4' />
              </Button>
              <div className='border-l border-gray-300 pl-2 h-4'></div>
              <ProjectSwitcher
                currentProjectId={currentProjectId}
                onProjectChange={handleProjectChange}
              />
              <div className='border-l border-gray-300 pl-2 h-4 ml-2'></div>
              <h1 className='text-sm font-semibold text-gray-900'>Sessions</h1>
            </div>
            <div className='flex items-center gap-1.5'>
              {project?.ai_tools.map(tool => (
                <div
                  key={tool}
                  className='px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px] font-semibold border border-blue-200'
                >
                  {tool.toUpperCase()}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 主体内容 */}
      <div className='mx-auto p-2'>
        <div className='bg-white rounded-xl border border-gray-200 shadow-sm h-[calc(100vh-90px)] overflow-hidden'>
          <div className='flex h-full'>
            {/* 左侧 Session 列表 */}
            <div className='w-80 flex-shrink-0 border-r border-gray-200'>
              <SessionList
                projectId={currentProjectId}
                selectedSessionId={selectedSessionId}
                onSessionSelect={handleSessionSelect}
              />
            </div>

            {/* 右侧 Session 详情 */}
            <div className='flex-1 min-w-0'>
              {loading ? (
                <div className='flex items-center justify-center h-full'>
                  <Loader2 className='h-6 w-6 animate-spin text-gray-400' />
                </div>
              ) : !project ? (
                <div className='flex items-center justify-center h-full'>
                  <div className='text-center'>
                    <h3 className='text-lg font-semibold mb-2'>Project Not Found</h3>
                    <p className='text-muted-foreground mb-4'>
                      The requested project could not be found
                    </p>
                  </div>
                </div>
              ) : selectedSessionId ? (
                <SessionDetail
                  projectId={currentProjectId}
                  sessionId={selectedSessionId}
                  onBack={handleBack}
                />
              ) : (
                <div className='flex items-center justify-center h-full'>
                  <div className='text-center'>
                    <h3 className='text-lg font-semibold mb-2 text-gray-700'>
                      Select a Session
                    </h3>
                    <p className='text-sm text-gray-500'>
                      Choose a session from the list to view details
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SessionPage() {
  return (
    <Suspense
      fallback={
        <div className='container mx-auto p-6 flex items-center justify-center min-h-screen'>
          <div className='text-center'>
            <Loader2 className='h-8 w-8 animate-spin mx-auto mb-4' />
            <p className='text-muted-foreground'>Loading...</p>
          </div>
        </div>
      }
    >
      <SessionPageContent />
    </Suspense>
  );
}
