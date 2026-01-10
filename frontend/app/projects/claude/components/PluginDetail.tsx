import { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { Plus, Store, Tag, Filter, Package } from 'lucide-react';
import { PluginItem } from './PluginItem';
import {
  scanClaudePluginMarketplaces,
  scanClaudePlugins,
  installClaudePluginMarketplace,
} from '@/api/api';
import type { PluginMarketplaceInfo, PluginInfo } from '@/api/types';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Filter as FilterComponent, FilterOption } from '@/components/filter/Filter';
import { EmptyView } from '@/components/EmptyView';
import { TooltipProvider } from '@/components/ui/tooltip';
import { useTranslation } from 'react-i18next';

interface PluginDetailProps {
  projectId: number;
}

export function PluginDetail({ projectId }: PluginDetailProps) {
  const { t } = useTranslation('projects');
  const router = useRouter();
  const searchParams = useSearchParams();

  const [marketplaces, setMarketplaces] = useState<PluginMarketplaceInfo[]>([]);
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [selectedMarketplaces, setSelectedMarketplaces] = useState<string[]>(['_all_']);
  const [selectedCategories, setSelectedCategories] = useState<string[]>(['_all_']);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isAddMarketplaceOpen, setIsAddMarketplaceOpen] = useState(false);
  const [newMarketplaceSource, setNewMarketplaceSource] = useState('');
  const [isInstalling, setIsInstalling] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  // 判断是否有过滤器激活
  const hasActiveFilters = useMemo(() => {
    return !!(
      searchQuery ||
      !selectedCategories.includes('_all_') ||
      !selectedMarketplaces.includes('_all_')
    );
  }, [searchQuery, selectedCategories, selectedMarketplaces]);

  // 加载插件市场列表
  const loadMarketplaces = useCallback(async () => {
    try {
      const response = await scanClaudePluginMarketplaces({
        project_id: projectId,
      });

      if (response.success && response.data) {
        setMarketplaces(response.data);
      } else {
        console.warn('加载插件市场失败或无数据:', response.error);
        setMarketplaces([]);
      }
    } catch (error) {
      console.error('加载插件市场失败:', error);
      toast.error(t('plugins.loadMarketplaceFailed'));
      setMarketplaces([]);
    }
  }, [projectId, t]);

  // 加载插件列表
  const loadPlugins = useCallback(async () => {
    try {
      // 始终获取所有插件，前端过滤即可
      const response = await scanClaudePlugins({
        project_id: projectId,
      });

      if (response.success && response.data) {
        setPlugins(response.data);
      } else {
        console.warn('加载插件列表失败或无数据:', response.error);
        setPlugins([]);
      }
    } catch (error) {
      console.error('加载插件列表失败:', error);
      toast.error(t('plugins.loadListFailed'));
      setPlugins([]);
    }
  }, [projectId, t]);

  // 更新 URL 查询参数
  const updateURLParams = useCallback(
    (params: { search?: string; marketplaces?: string[]; categories?: string[] }) => {
      const newParams = new URLSearchParams(searchParams.toString());

      // 更新搜索参数
      if (params.search !== undefined) {
        if (params.search) {
          newParams.set('search', params.search);
        } else {
          newParams.delete('search');
        }
      }

      // 更新 marketplace 参数
      if (params.marketplaces !== undefined) {
        if (params.marketplaces.includes('_all_') || params.marketplaces.length === 0) {
          newParams.delete('marketplaces');
        } else {
          newParams.set('marketplaces', params.marketplaces.join(','));
        }
      }

      // 更新 categories 参数
      if (params.categories !== undefined) {
        if (params.categories.includes('_all_') || params.categories.length === 0) {
          newParams.delete('categories');
        } else {
          newParams.set('categories', params.categories.join(','));
        }
      }

      // 只有当参数真正改变时才更新 URL
      const newUrl = `?${newParams.toString()}`;
      if (newUrl !== `?${searchParams.toString()}`) {
        router.replace(newUrl);
      }
    },
    [searchParams, router]
  );

  // 从 URL 初始化筛选条件
  useEffect(() => {
    if (isInitialized) return;

    const search = searchParams.get('search');
    const marketplacesParam = searchParams.get('marketplaces');
    const categoriesParam = searchParams.get('categories');

    if (search) {
      setSearchQuery(search);
    }

    if (marketplacesParam) {
      setSelectedMarketplaces(marketplacesParam.split(','));
    }

    if (categoriesParam) {
      setSelectedCategories(categoriesParam.split(','));
    }

    setIsInitialized(true);
  }, [searchParams, isInitialized]);

  // 监听筛选条件变化，同步到 URL
  useEffect(() => {
    if (!isInitialized) return;

    updateURLParams({
      search: searchQuery,
      marketplaces: selectedMarketplaces,
      categories: selectedCategories,
    });
  }, [
    searchQuery,
    selectedMarketplaces,
    selectedCategories,
    isInitialized,
    updateURLParams,
  ]);

  // 组件加载时获取数据
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        await loadMarketplaces();
        // 等待市场列表加载完成后，立即加载插件列表
        // 这样可以避免中间态的空状态显示
        await loadPlugins();
      } finally {
        setIsLoading(false);
      }
    };

    if (projectId) {
      loadData();
    }
  }, [projectId, loadMarketplaces, loadPlugins]);

  // 提取 Marketplace 选项
  const marketplaceOptions: FilterOption[] = useMemo(
    () => marketplaces.map(m => ({ value: m.name, label: m.name })),
    [marketplaces]
  );

  // 提取 Category 选项
  const categoryOptions: FilterOption[] = useMemo(() => {
    const categories = new Set<string>();
    plugins.forEach(plugin => {
      if (plugin.config.category) {
        categories.add(plugin.config.category);
      }
    });
    return Array.from(categories)
      .sort()
      .map(c => ({ value: c, label: c }));
  }, [plugins]);

  // 当 categoryOptions 变化时，检查当前选择的 categories 是否仍然有效
  useEffect(() => {
    if (selectedCategories.length > 0 && !selectedCategories.includes('_all_')) {
      const validCategories = selectedCategories.filter(cat =>
        categoryOptions.some(option => option.value === cat)
      );
      // 如果当前选择的 categories 中有不再存在的，重置为 '_all_'
      if (validCategories.length === 0) {
        setSelectedCategories(['_all_']);
      } else if (validCategories.length !== selectedCategories.length) {
        setSelectedCategories(validCategories);
      }
    }
  }, [categoryOptions]);

  // 过滤后的插件列表
  const filteredPlugins = useMemo(() => {
    return plugins.filter(plugin => {
      // 搜索过滤
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const nameMatch = plugin.config.name.toLowerCase().includes(query);
        const descMatch = plugin.config.description?.toLowerCase().includes(query);
        if (!nameMatch && !descMatch) return false;
      }

      // Category 过滤
      if (!selectedCategories.includes('_all_') && selectedCategories.length > 0) {
        if (
          !plugin.config.category ||
          !selectedCategories.includes(plugin.config.category)
        ) {
          return false;
        }
      }

      // Marketplace 过滤
      if (!selectedMarketplaces.includes('_all_') && selectedMarketplaces.length > 0) {
        if (!plugin.marketplace || !selectedMarketplaces.includes(plugin.marketplace)) {
          return false;
        }
      }

      return true;
    });
  }, [plugins, searchQuery, selectedCategories, selectedMarketplaces]);

  // 处理添加 marketplace
  const handleAddMarketplace = async () => {
    if (!newMarketplaceSource.trim()) {
      toast.error(t('plugins.enterSourceUrl'));
      return;
    }

    setIsInstalling(true);
    try {
      const response = await installClaudePluginMarketplace({
        project_id: projectId,
        source: newMarketplaceSource.trim(),
      });

      if (response.success) {
        toast.success(t('plugins.addMarketplaceSuccess'));
        setNewMarketplaceSource('');
        setIsAddMarketplaceOpen(false);
        // 重新加载市场列表
        await loadMarketplaces();
      } else {
        toast.error(
          t('plugins.addMarketplaceError', {
            error: response.error || t('unknownError'),
          })
        );
      }
    } catch (error) {
      console.error('添加 marketplace 失败:', error);
      toast.error(t('plugins.addMarketplaceFailed'));
    } finally {
      setIsInstalling(false);
    }
  };

  return (
    <TooltipProvider>
      <div className='p-4'>
        <div className='space-y-6'>
          {/* 加载状态 */}
          {isLoading ? (
            <div className='flex items-center justify-center py-16'>
              <div className='text-center space-y-4'>
                <div className='w-8 h-8 mx-auto border-2 border-blue-600 border-t-transparent rounded-full animate-spin'></div>
                <p className='text-muted-foreground'>{t('plugins.loading')}</p>
              </div>
            </div>
          ) : (
            <>
              {/* Filter 区域 */}
              <div className='mb-6 space-y-4'>
                <div className='flex items-center gap-3 flex-wrap'>
                  {/* 搜索框 */}
                  <div className='flex-1 min-w-[200px] relative'>
                    <Filter className='w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none' />
                    <Input
                      placeholder={t('plugins.filter.searchPlaceholder')}
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      className='max-w-md pl-9'
                    />
                  </div>

                  {/* Marketplace 过滤器 */}
                  <FilterComponent
                    options={marketplaceOptions}
                    selected={selectedMarketplaces}
                    onSelectionChange={setSelectedMarketplaces}
                    displayValue={(selected, allLabel) => {
                      if (selected.includes('_all_')) {
                        return allLabel;
                      }
                      if (selected.length === 0) {
                        return t('plugins.selectMarketets');
                      }
                      return t('plugins.selectedCount', { count: selected.length });
                    }}
                    icon={<Store className='w-4 h-4 mr-2' />}
                    showAllOption={true}
                    allOptionValue='_all_'
                    allOptionLabel={t('plugins.all')}
                  />

                  {/* Category 过滤器 */}
                  <FilterComponent
                    options={categoryOptions}
                    selected={selectedCategories}
                    onSelectionChange={setSelectedCategories}
                    displayValue={(selected, allLabel) => {
                      if (selected.includes('_all_')) {
                        return allLabel;
                      }
                      if (selected.length === 0) {
                        return t('plugins.filter.allCategories');
                      }
                      return t('plugins.filter.selectedCategories', {
                        count: selected.length,
                      });
                    }}
                    icon={<Tag className='w-4 h-4 mr-2' />}
                    showAllOption={true}
                    allOptionValue='_all_'
                    allOptionLabel={t('plugins.all')}
                  />

                  {/* 添加 Marketplace 按钮 */}
                  <Popover
                    open={isAddMarketplaceOpen}
                    onOpenChange={setIsAddMarketplaceOpen}
                  >
                    <PopoverTrigger asChild>
                      <Button variant='outline' size='icon' className='h-9 w-9'>
                        <Plus className='h-4 w-4' />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className='w-[320px] p-4' align='end'>
                      <div className='space-y-4'>
                        <div className='space-y-2'>
                          <h4 className='font-medium text-sm'>
                            {t('plugins.addMarketplace')}
                          </h4>
                          <p className='text-xs text-muted-foreground'>
                            {t('plugins.addMarketplaceDesc')}
                          </p>
                        </div>
                        <div className='space-y-2'>
                          <Label htmlFor='marketplace-source' className='text-xs'>
                            {t('plugins.sourceLabel')}
                          </Label>
                          <Input
                            id='marketplace-source'
                            placeholder={t('plugins.sourcePlaceholder')}
                            value={newMarketplaceSource}
                            onChange={e => setNewMarketplaceSource(e.target.value)}
                            onKeyDown={e => {
                              if (e.key === 'Enter' && !isInstalling) {
                                handleAddMarketplace();
                              }
                            }}
                            disabled={isInstalling}
                          />
                          <p className='text-xs text-muted-foreground'>
                            {t('plugins.sourceSupport')}
                          </p>
                        </div>
                        <div className='flex justify-end gap-2'>
                          <Button
                            variant='ghost'
                            size='sm'
                            onClick={() => {
                              setIsAddMarketplaceOpen(false);
                              setNewMarketplaceSource('');
                            }}
                            disabled={isInstalling}
                          >
                            {t('plugins.cancel')}
                          </Button>
                          <Button
                            size='sm'
                            onClick={handleAddMarketplace}
                            disabled={isInstalling}
                          >
                            {isInstalling ? t('plugins.adding') : t('plugins.add')}
                          </Button>
                        </div>
                      </div>
                    </PopoverContent>
                  </Popover>
                </div>
              </div>

              {/* 插件列表 */}
              {filteredPlugins.length > 0 ? (
                <div className='space-y-4'>
                  <h3 className='text-sm font-medium text-muted-foreground'>
                    {t('plugins.pluginList', { count: filteredPlugins.length })}
                  </h3>
                  <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 items-start'>
                    {filteredPlugins.map(plugin => (
                      <PluginItem
                        key={`${plugin.marketplace || 'unknown'}-${plugin.config.name}`}
                        plugin={plugin}
                        projectId={projectId}
                        onPluginChange={loadPlugins}
                      />
                    ))}
                  </div>
                </div>
              ) : (
                /* 无插件时的空状态 */
                <EmptyView
                  icon={<Package />}
                  title={
                    hasActiveFilters
                      ? t('plugins.filter.noResults')
                      : t('plugins.noPlugins')
                  }
                  description={
                    hasActiveFilters
                      ? t('plugins.filter.noResultsDesc')
                      : selectedMarketplaces.length > 0
                        ? t('plugins.noPluginsInMarket')
                        : t('plugins.noPluginsFound')
                  }
                  actionLabel={t('plugins.addMarketplace')}
                  onAction={() => setIsAddMarketplaceOpen(true)}
                />
              )}
            </>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
}
