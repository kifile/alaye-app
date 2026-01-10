'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import { getProject } from '@/api/api';
import type { AIProjectInDB } from '@/api/types';
import { ClaudeConfigSideBar } from './components/ClaudeConfigSideBar';
import { DetailHeader } from './components/DetailHeader';
import { DetailHeaderProvider } from './context/DetailHeaderContext';
import { MemoryDetail } from './components/MemoryDetail';
import { McpServersDetail } from './components/McpServersDetail';
import { CommandsDetail } from './components/CommandsDetail';
import { SubAgentsDetail } from './components/SubAgentsDetail';
import { HooksDetail } from './components/HooksDetail';
import { SkillsDetail } from './components/SkillsDetail';
import { SettingsDetail } from './components/SettingsDetail';
import { PluginDetail } from './components/PluginDetail';
import { ProjectSwitcher } from './components/ProjectSwitcher';
import { LspServersDetail } from './components/LspServersDetail';
import { useTranslation } from 'react-i18next';
import { loadAllPageTranslations } from '@/lib/i18n';

type ConfigSection =
  | 'memory'
  | 'plugins'
  | 'mcpServers'
  | 'lspServers'
  | 'commands'
  | 'subAgents'
  | 'hooks'
  | 'skills'
  | 'settings';

function ProjectDetailPageContent() {
  const { t } = useTranslation('projects');
  const searchParams = useSearchParams();
  const router = useRouter();

  const projectId = Number(searchParams?.get('id') || 0);
  const sectionParam = (searchParams?.get('section') as ConfigSection) || 'memory';

  const [project, setProject] = useState<AIProjectInDB | null>(null);
  const [currentProjectId, setCurrentProjectId] = useState(projectId);
  const [loading, setLoading] = useState(true);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [selectedSection, setSelectedSection] = useState<ConfigSection>(sectionParam);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
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

  useEffect(() => {
    if (currentProjectId && currentProjectId > 0) {
      loadProjectData();
    }
  }, [currentProjectId]);

  // 处理项目切换
  const handleProjectChange = (newProjectId: number) => {
    // 如果选择的是同一个项目，不做处理
    if (newProjectId === currentProjectId) {
      return;
    }

    // 更新URL参数
    const currentParams = new URLSearchParams(
      Array.from(searchParams?.entries() || [])
    );
    currentParams.set('id', String(newProjectId));
    const newUrl = `${window.location.pathname}?${currentParams.toString()}`;
    router.replace(newUrl, { scroll: false });

    // 更新状态（不触发 loading，避免闪烁）
    setCurrentProjectId(newProjectId);
    setProject(null);
  };

  // 监听URL参数变化，同步状态
  useEffect(() => {
    const currentSection = (searchParams?.get('section') as ConfigSection) || 'memory';

    // 只有当URL参数与当前状态不一致时才更新
    if (currentSection !== selectedSection) {
      setSelectedSection(currentSection);
    }
  }, [searchParams]);

  // 切换侧边栏折叠状态
  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  // 处理section选择
  const handleSectionSelect = (section: ConfigSection) => {
    setSelectedSection(section);

    // 更新URL参数
    const currentParams = new URLSearchParams(
      Array.from(searchParams?.entries() || [])
    );
    currentParams.set('section', section);
    const newUrl = `${window.location.pathname}?${currentParams.toString()}`;
    router.replace(newUrl, { scroll: false });
  };

  // 渲染详情内容（根据选中的section）
  const renderDetailContent = () => {
    switch (selectedSection) {
      case 'memory':
        return <MemoryDetail projectId={currentProjectId} />;
      case 'plugins':
        return <PluginDetail projectId={currentProjectId} />;
      case 'mcpServers':
        return <McpServersDetail projectId={currentProjectId} />;
      case 'lspServers':
        return <LspServersDetail projectId={currentProjectId} />;
      case 'commands':
        return <CommandsDetail projectId={currentProjectId} />;
      case 'subAgents':
        return <SubAgentsDetail projectId={currentProjectId} />;
      case 'hooks':
        return <HooksDetail projectId={currentProjectId} />;
      case 'skills':
        return <SkillsDetail projectId={currentProjectId} />;
      case 'settings':
        return <SettingsDetail projectId={currentProjectId} />;
      default:
        return (
          <div className='p-6 text-center text-muted-foreground'>
            {t('detail.selectConfig')}
          </div>
        );
    }
  };

  // 初始加载时显示全屏 loading
  if (isInitialLoading) {
    return (
      <div className='container mx-auto p-6 flex items-center justify-center min-h-screen'>
        <div className='text-center'>
          <Loader2 className='h-8 w-8 animate-spin mx-auto mb-4' />
          <p className='text-muted-foreground'>{t('detail.loading')}</p>
        </div>
      </div>
    );
  }

  return (
    <DetailHeaderProvider>
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
                  title={t('detail.back')}
                >
                  <ArrowLeft className='h-4 w-4' />
                </Button>
                <div className='border-l border-gray-300 pl-2 h-4'></div>
                <ProjectSwitcher
                  currentProjectId={currentProjectId}
                  onProjectChange={handleProjectChange}
                />
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
        <div className='mx-auto p-2 relative'>
          {/* 悬浮折叠按钮 */}
          <div
            className='absolute top-8 bg-white border border-gray-300 rounded-full shadow-md hover:shadow-lg transition-all duration-200 z-30'
            style={{
              left: sidebarCollapsed ? '8px' : '182px',
              transform: sidebarCollapsed ? 'translateX(-50%)' : 'translateX(-50%)', // 始终使按钮中心对准边线
            }}
          >
            <Button
              variant='ghost'
              size='icon'
              onClick={toggleSidebar}
              className='h-7 w-7 p-0 rounded-full hover:bg-gray-100 transition-colors'
              title={
                sidebarCollapsed
                  ? t('detail.expandSidebar')
                  : t('detail.collapseSidebar')
              }
            >
              {sidebarCollapsed ? (
                <ChevronRight className='h-3 w-3 text-gray-600' />
              ) : (
                <ChevronLeft className='h-3 w-3 text-gray-600' />
              )}
            </Button>
          </div>

          <div className='bg-white rounded-xl border border-gray-200 shadow-sm h-[calc(100vh-90px)] overflow-hidden'>
            <div className='flex h-full'>
              {/* 左侧配置导航栏 */}
              <div
                className={`${sidebarCollapsed ? 'w-0' : 'w-44'} flex-shrink-0 transition-all duration-300 overflow-hidden border-r border-gray-200 relative z-20 ${
                  !sidebarCollapsed &&
                  'md:static absolute left-0 top-0 h-full shadow-xl md:shadow-none'
                }`}
              >
                {!sidebarCollapsed && (
                  <ClaudeConfigSideBar
                    selectedSection={selectedSection}
                    onSectionSelect={handleSectionSelect}
                  />
                )}
              </div>

              {/* 右侧详情内容 */}
              <div className='flex-1 min-w-0 flex flex-col'>
                <div className='border-b border-gray-200 px-6 py-3 bg-gray-50/50'>
                  <DetailHeader selectedSection={selectedSection} />
                </div>
                <div className='flex-1 overflow-auto'>
                  {loading ? (
                    <div className='flex items-center justify-center h-full'>
                      <Loader2 className='h-6 w-6 animate-spin text-gray-400' />
                    </div>
                  ) : !project ? (
                    <div className='flex items-center justify-center h-full'>
                      <div className='text-center'>
                        <h3 className='text-lg font-semibold mb-2'>
                          {t('detail.notFound')}
                        </h3>
                        <p className='text-muted-foreground mb-4'>
                          {t('detail.notFoundDesc')}
                        </p>
                      </div>
                    </div>
                  ) : (
                    renderDetailContent()
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DetailHeaderProvider>
  );
}

export default function ProjectDetailPage() {
  const { t } = useTranslation('projects');

  return (
    <Suspense
      fallback={
        <div className='container mx-auto p-6 flex items-center justify-center min-h-screen'>
          <div className='text-center'>
            <Loader2 className='h-8 w-8 animate-spin mx-auto mb-4' />
            <p className='text-muted-foreground'>{t('detail.loading')}</p>
          </div>
        </div>
      }
    >
      <ProjectDetailPageContent />
    </Suspense>
  );
}
