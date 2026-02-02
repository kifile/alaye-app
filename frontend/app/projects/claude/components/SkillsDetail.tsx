import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { BookOpen, Plus, ExternalLink } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useDetailHeader } from '../context/DetailHeaderContext';
import { EmptyView } from '@/components/EmptyView';
import { ClaudeToolSelectBar, ToolGroup } from './ClaudeToolSelectBar';
import { SkillContentView } from './SkillContentView';
import { scanClaudeSkills, saveClaudeMarkdownContent } from '@/api/api';
import { ConfigScope, SkillInfo } from '@/api/types';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';

// 分组函数：按照 scope + pluginName 分组
function groupSkillsByScope(
  skills: SkillInfo[],
  t: (key: string, params?: Record<string, string | number>) => string
): ToolGroup[] {
  const scopeOrder: ConfigScope[] = [
    ConfigScope.LOCAL,
    ConfigScope.PROJECT,
    ConfigScope.USER,
    ConfigScope.PLUGIN,
  ];
  const groups: ToolGroup[] = [];

  // 非插件 scope 的分组
  for (const scope of scopeOrder) {
    if (scope === ConfigScope.PLUGIN) continue; // 插件单独处理

    const items = skills
      .filter(skill => skill.scope === scope)
      .map(skill => ({
        name: skill.name,
        scope: skill.scope,
        description: skill.description,
      }));

    if (items.length > 0) {
      groups.push({
        label: t(`toolSelectBar.groups.${scope}`),
        items,
      });
    }
  }

  // 插件 scope：按 pluginName 分组
  const pluginSkills = skills.filter(skill => skill.scope === ConfigScope.PLUGIN);
  const pluginsMap = new Map<string, SkillInfo[]>();

  pluginSkills.forEach(skill => {
    const pluginName = skill.plugin_name || 'Unknown';
    if (!pluginsMap.has(pluginName)) {
      pluginsMap.set(pluginName, []);
    }
    pluginsMap.get(pluginName)!.push(skill);
  });

  // 按插件名称排序后添加分组
  Array.from(pluginsMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .forEach(([pluginName, skills]) => {
      groups.push({
        label: t('toolSelectBar.groups.plugin', { name: pluginName }),
        items: skills.map(skill => ({
          name: skill.name,
          scope: skill.scope,
          description: skill.description,
          pluginName,
        })),
      });
    });

  return groups;
}

// 加载状态组件
function LoadingState({ message }: { message: string }) {
  return (
    <div className='flex items-center justify-center py-16'>
      <div className='text-center space-y-4'>
        <div className='w-8 h-8 mx-auto border-2 border-blue-600 border-t-transparent rounded-full animate-spin'></div>
        <p className='text-muted-foreground'>{message}</p>
      </div>
    </div>
  );
}

type ViewMode = 'select' | 'edit';

interface SkillsDetailProps {
  projectId: number;
}

export function SkillsDetail({ projectId }: SkillsDetailProps) {
  const { t } = useTranslation('projects');
  const router = useRouter();
  const searchParams = useSearchParams();
  const { scopeSwitcher, setScopeSwitcher, clearScopeSwitcher } = useDetailHeader();

  // 视图模式
  const [viewMode, setViewMode] = useState<ViewMode>('select');

  // Popover 控制状态
  const [newPopoverOpen, setNewPopoverOpen] = useState<boolean>(false);

  // 选中的 skill
  const [selectedSkill, setSelectedSkill] = useState<{
    name: string;
    scope?: ConfigScope;
  } | null>(null);

  // 列表状态
  const [skillsList, setSkillsList] = useState<SkillInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isInitialLoaded, setIsInitialLoaded] = useState(true);

  // 当前作用域
  const [currentScope, setCurrentScope] = useState<ConfigScope | 'mixed' | null>(null);

  // 获取当前选中的 skill 配置
  const currentSkill = useMemo(() => {
    if (!selectedSkill) return null;
    return skillsList.find(
      skill =>
        skill.name === selectedSkill.name &&
        (!selectedSkill.scope || skill.scope === selectedSkill.scope)
    );
  }, [selectedSkill, skillsList]);

  // 分组后的 skills 列表
  const groupedSkills = useMemo(() => {
    return groupSkillsByScope(skillsList, t);
  }, [skillsList, t]);

  // 扫描 skills 列表
  const scanSkillsList = useCallback(
    async (keepSelection?: { name: string; scope?: ConfigScope }) => {
      if (!isInitialLoaded) {
        setIsLoading(true);
      }

      try {
        const scopeParam =
          currentScope === null || currentScope === 'mixed' ? undefined : currentScope;
        const response = await scanClaudeSkills({
          project_id: projectId,
          scope: scopeParam as ConfigScope,
        });

        if (response.success && response.data) {
          setSkillsList(response.data);

          // 如果列表为空，切换到选择模式
          if (response.data.length === 0) {
            setSelectedSkill(null);
            setViewMode('select');
          } else {
            // 优先使用 keepSelection 参数（用于重命名场景）
            const targetSkill = keepSelection || selectedSkill;

            // 检查目标 skill 是否还在列表中
            const stillExists =
              targetSkill &&
              response.data.some(
                skill =>
                  skill.name === targetSkill.name && skill.scope === targetSkill.scope
              );

            if (stillExists) {
              // 目标 skill 还在列表中，保持选中
              if (keepSelection) {
                setSelectedSkill(keepSelection);
              }
              setViewMode('edit');
            } else {
              // 没有选中项，选中第一个
              const firstSkill = response.data[0];
              setSelectedSkill({
                name: firstSkill.name,
                scope: firstSkill.scope,
              });
              setViewMode('edit');
            }
          }
        }
      } catch (error) {
        console.error(t('skills.scanFailed') + ':', error);
      } finally {
        setIsLoading(false);
        setIsInitialLoaded(true);
      }
    },
    [projectId, currentScope, t, selectedSkill, isInitialLoaded]
  );

  // 组件加载时获取数据
  useEffect(() => {
    if (projectId && !isInitialLoaded) {
      scanSkillsList();
    }
  }, [projectId, isInitialLoaded, scanSkillsList]);

  // 当 scope 变化时重新加载（不显示 loading）
  useEffect(() => {
    if (projectId && isInitialLoaded) {
      scanSkillsList();
    }
  }, [currentScope, projectId, isInitialLoaded, scanSkillsList]);

  // 配置 DetailHeader 的 scopeSwitcher - Skills 只需要 project
  useEffect(() => {
    setScopeSwitcher({
      enabled: true,
      supportedScopes: ['mixed', 'project', 'user', 'plugin'] as ConfigScope[],
      value: currentScope,
      onChange: setCurrentScope,
    });

    return () => {
      clearScopeSwitcher();
    };
  }, [setScopeSwitcher, clearScopeSwitcher, currentScope]);

  // 新建 skill - 通过 Popover 创建空 skill
  const handleCreateSkill = useCallback(
    async (name: string, scope: ConfigScope) => {
      try {
        const response = await saveClaudeMarkdownContent({
          project_id: projectId,
          content_type: 'skill',
          name: name.trim(),
          content: '', // 内容为空
          scope,
        });

        if (response.success) {
          toast.success(t('skills.createSuccess'), {
            description: t('skills.createSuccessDesc', { name }),
          });
          // 关闭 Popover
          setNewPopoverOpen(false);
          // 选中新建的 skill 并切换到编辑模式
          setSelectedSkill({ name: name.trim(), scope });
          setViewMode('edit');
          // 重新扫描列表
          scanSkillsList({ name: name.trim(), scope });
        } else {
          toast.error(t('skills.createFailed'), {
            description: response.error || t('unknownError'),
          });
        }
      } catch (error) {
        console.error('Create skill error:', error);
        toast.error(t('skills.createFailed'), {
          description: error instanceof Error ? error.message : t('networkError'),
        });
      }
    },
    [projectId, t, scanSkillsList]
  );

  // 选择 skill - 切换到编辑模式
  const handleSelectSkill = useCallback((skill: SkillInfo) => {
    setSelectedSkill({ name: skill.name, scope: skill.scope });
    setViewMode('edit');
  }, []);

  // skill 删除完成 - 切换到选择模式
  const handleSkillDeleted = useCallback(() => {
    setSelectedSkill(null);
    setViewMode('select');
    // 重新扫描列表
    scanSkillsList();
  }, [scanSkillsList]);

  // skill 重命名完成 - 更新选中的 skill
  const handleSkillRenamed = useCallback(
    (newName: string, newScope?: ConfigScope) => {
      // 重新扫描列表，并保持选中重命名后的 skill
      scanSkillsList({ name: newName, scope: newScope });
    },
    [scanSkillsList]
  );

  // 跳转到插件页面
  const handleGoToPlugins = useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('section', 'plugins');
    router.push(`?${params.toString()}`);
  }, [router, searchParams]);

  // 打开新建 Popover
  const handleOpenNewPopover = useCallback(() => {
    setNewPopoverOpen(true);
  }, []);

  // 处理 Popover 状态变化
  const handlePopoverOpenChange = useCallback((open: boolean) => {
    setNewPopoverOpen(open);
  }, []);

  // 根据视图模式渲染不同内容
  return (
    <div className='p-4 flex flex-col h-full'>
      {/* 加载状态 */}
      {isLoading && <LoadingState message={t('skills.loading')} />}

      {/* 视图内容 */}
      {!isLoading && (
        <>
          {viewMode === 'edit' && selectedSkill && currentSkill && (
            <>
              {/* skill 选择器 */}
              <div className='mb-4 flex-shrink-0'>
                <ClaudeToolSelectBar
                  groups={groupedSkills}
                  selectedItem={selectedSkill}
                  onSelectItem={handleSelectSkill}
                  onRefresh={() => selectedSkill && scanSkillsList(selectedSkill)}
                  onCreateItem={handleCreateSkill}
                  newPopoverOpen={newPopoverOpen}
                  onPopoverOpenChange={handlePopoverOpenChange}
                />
              </div>

              {/* 编辑 skill 内容 */}
              <div className='flex-1 min-h-0'>
                <SkillContentView
                  key={`${selectedSkill.scope}-${selectedSkill.name}`}
                  projectId={projectId}
                  selectedSkill={selectedSkill}
                  currentSkill={currentSkill}
                  onDeleted={handleSkillDeleted}
                  onRenamed={handleSkillRenamed}
                />
              </div>
            </>
          )}

          {viewMode === 'select' && (
            <>
              {/* skill 选择器 */}
              <div className='mb-4'>
                <ClaudeToolSelectBar
                  groups={groupedSkills}
                  selectedItem={selectedSkill}
                  onSelectItem={handleSelectSkill}
                  onRefresh={() => selectedSkill && scanSkillsList(selectedSkill)}
                  onCreateItem={handleCreateSkill}
                  newPopoverOpen={newPopoverOpen}
                  onPopoverOpenChange={handlePopoverOpenChange}
                />
              </div>

              {/* 提示用户选择 skill */}
              {currentScope === 'plugin' ? (
                <EmptyView
                  icon={<BookOpen />}
                  title={t('skills.pluginScopeTitle')}
                  description={t('skills.pluginScopeDesc')}
                  actionLabel={t('skills.goToPlugins')}
                  onAction={handleGoToPlugins}
                  actionIcon={<ExternalLink className='h-4 w-4' />}
                />
              ) : (
                <EmptyView
                  icon={<BookOpen />}
                  title={t('skills.noSelection')}
                  description={t('skills.noSelectionDesc')}
                  actionLabel={t('skills.createNew')}
                  onAction={handleOpenNewPopover}
                  actionIcon={<Plus className='h-4 w-4' />}
                />
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
