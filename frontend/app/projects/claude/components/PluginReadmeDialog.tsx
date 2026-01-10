import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { FileText, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { MarkdownEditor } from '@/components/editor/MarkdownEditor';
import { readPluginReadme } from '@/api/api';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import type { PluginInfo } from '@/api/types';

interface PluginReadmeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  plugin: PluginInfo | null;
  projectId: number;
}

export function PluginReadmeDialog({
  open,
  onOpenChange,
  plugin,
  projectId,
}: PluginReadmeDialogProps) {
  const { t } = useTranslation('projects');
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // 加载 README 内容
  const loadReadme = async (showLoading = true) => {
    if (!plugin || !plugin.marketplace) return;

    if (showLoading) {
      setIsLoading(true);
    } else {
      setIsRefreshing(true);
    }

    try {
      const response = await readPluginReadme({
        project_id: projectId,
        marketplace_name: plugin.marketplace,
        plugin_name: plugin.config.name,
      });

      if (response.success && response.data) {
        setContent(response.data);
      } else {
        toast.error(t('pluginReadmeDialog.loadFailed'), {
          description: response.error || t('unknownError'),
        });
        setContent('');
      }
    } catch (error) {
      console.error('加载 README 失败:', error);
      toast.error(t('pluginReadmeDialog.loadFailed'), {
        description: error instanceof Error ? error.message : t('unknownError'),
      });
      setContent('');
    } finally {
      if (showLoading) {
        setIsLoading(false);
      } else {
        setIsRefreshing(false);
      }
    }
  };

  // 当对话框打开或插件变化时，加载 README 内容
  useEffect(() => {
    if (open && plugin) {
      loadReadme(true);
    } else {
      setContent('');
    }
  }, [open, plugin, projectId]);

  // 处理刷新
  const handleRefresh = async () => {
    await loadReadme(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className='!max-w-6xl !max-w-[calc(100%-10rem)] max-h-[85vh] overflow-hidden flex flex-col p-0'>
        <DialogHeader className='flex-shrink-0 px-6 pt-6 pb-4'>
          <DialogTitle className='flex items-center gap-2'>
            <FileText className='w-5 h-5' />
            {plugin?.config.name} {t('pluginReadmeDialog.title')}
          </DialogTitle>
        </DialogHeader>

        <div className='flex-1 overflow-hidden flex flex-col min-h-0 px-6 pb-6'>
          {isLoading ? (
            <div className='flex items-center justify-center h-full'>
              <div className='text-center space-y-4'>
                <div className='w-8 h-8 mx-auto border-2 border-blue-600 border-t-transparent rounded-full animate-spin'></div>
                <p className='text-sm text-muted-foreground'>
                  {t('pluginReadmeDialog.loading')}
                </p>
              </div>
            </div>
          ) : (
            <MarkdownEditor
              value={content}
              onChange={setContent}
              onRefresh={handleRefresh}
              isLoading={isRefreshing}
              readonly
              height={600}
              customToolbar={
                <Button
                  variant='outline'
                  size='icon'
                  onClick={handleRefresh}
                  disabled={isRefreshing}
                  className='h-8 w-8'
                  title={t('pluginReadmeDialog.refresh')}
                >
                  <RefreshCw
                    className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`}
                  />
                </Button>
              }
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
