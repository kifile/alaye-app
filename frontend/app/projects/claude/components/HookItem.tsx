import React, { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Pencil,
  Trash2,
  Terminal,
  MessageSquare,
  Clock,
  Copy,
  Filter,
  Store,
} from 'lucide-react';
import type { HookConfigInfo, HookEvent } from '@/api/types';
import { toast } from 'sonner';
import { ScopeBadge } from './ScopeBadge';
import { useTranslation } from 'react-i18next';

interface HookItemProps {
  hookInfo: HookConfigInfo;
  onEdit: () => void;
  onDelete: () => void;
  isProcessing?: boolean;
}

// Hook 事件类型颜色映射
const HOOK_EVENT_COLORS: Record<HookEvent, string> = {
  PreToolUse: 'bg-blue-500',
  PermissionRequest: 'bg-yellow-500',
  PostToolUse: 'bg-green-500',
  Notification: 'bg-purple-500',
  UserPromptSubmit: 'bg-indigo-500',
  Stop: 'bg-red-500',
  SubagentStop: 'bg-orange-500',
  PreCompact: 'bg-cyan-500',
  SessionStart: 'bg-teal-500',
  SessionEnd: 'bg-pink-500',
};

export function HookItem({
  hookInfo,
  onEdit,
  onDelete,
  isProcessing = false,
}: HookItemProps) {
  const { t } = useTranslation('projects');
  const router = useRouter();
  const searchParams = useSearchParams();
  const { scope, event, matcher, hook_config, plugin_name, marketplace_name } =
    hookInfo;

  const [commandExpanded, setCommandExpanded] = useState(false);
  const [promptExpanded, setPromptExpanded] = useState(false);

  const isCommandType = hook_config.type === 'command';
  const eventDisplayName = t(`hookItem.eventTypes.${event}`) || event;
  const eventColorClass = HOOK_EVENT_COLORS[event] || 'bg-gray-500';
  const isPluginScope = scope === 'plugin';
  const isReadonly = isPluginScope;
  const isDisabled = isProcessing || isReadonly;

  const handleCopy = async (text: string, type: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(t('hookItem.copySuccess', { type }));
    } catch {
      toast.error(t('hookItem.copyFailed'));
    }
  };

  // 跳转到插件页面
  const handleGoToPlugin = () => {
    if (!plugin_name) return;

    const params = new URLSearchParams(searchParams.toString());
    params.set('section', 'plugins');
    params.set('search', plugin_name);

    if (marketplace_name) {
      params.set('marketplaces', marketplace_name);
    }

    router.push(`?${params.toString()}`);
  };

  return (
    <TooltipProvider>
      <div
        className={`p-4 border rounded-lg transition-colors ${
          isReadonly
            ? 'bg-blue-50/50 border-blue-200 dark:bg-blue-950/50 dark:border-blue-800'
            : 'hover:bg-accent/50'
        }`}
      >
        {/* 头部信息 */}
        <div className='flex items-center justify-between mb-3'>
          {/* 左侧：作用域标签、事件类型标签 */}
          <div className='flex items-center gap-3 flex-1 min-w-0'>
            <ScopeBadge scope={scope} />

            {/* 事件类型标签 */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge variant='default' className={`${eventColorClass} text-white`}>
                  {eventDisplayName}
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p>
                  {t('hookItem.eventType')} {event}
                </p>
              </TooltipContent>
            </Tooltip>

            {/* Hook 类型标签 */}
            <Badge variant={isCommandType ? 'default' : 'secondary'}>
              {isCommandType ? (
                <>
                  <Terminal className='w-3 h-3 mr-1' />
                  {t('hookItem.commandType')}
                </>
              ) : (
                <>
                  <MessageSquare className='w-3 h-3 mr-1' />
                  {t('hookItem.promptType')}
                </>
              )}
            </Badge>

            {/* 匹配器（如果有） */}
            {matcher && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge variant='outline' className='gap-1'>
                    <Filter className='w-3 h-3' />
                    <span className='max-w-[150px] truncate'>{matcher}</span>
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  <p className='max-w-xs break-all'>
                    {t('hookItem.matcher')} {matcher}
                  </p>
                </TooltipContent>
              </Tooltip>
            )}
          </div>

          {/* 右侧：操作按钮 */}
          <div className='flex items-center gap-2 flex-shrink-0'>
            {/* 跳转到插件按钮 */}
            {isReadonly && plugin_name && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size='sm'
                    variant='ghost'
                    onClick={handleGoToPlugin}
                    className='text-blue-600 hover:text-blue-700 hover:bg-blue-50'
                  >
                    <Store className='w-4 h-4' />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{t('hookItem.goToPlugin')}</p>
                </TooltipContent>
              </Tooltip>
            )}

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size='sm'
                  variant='ghost'
                  onClick={onEdit}
                  disabled={isDisabled}
                >
                  <Pencil className='w-4 h-4' />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {isReadonly ? t('hookItem.readonlyMode') : t('hookItem.editHook')}
              </TooltipContent>
            </Tooltip>

            {isReadonly ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button size='sm' variant='ghost' disabled={isDisabled}>
                    <Trash2 className='w-4 h-4 text-red-500' />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{t('hookItem.readonlyMode')}</p>
                </TooltipContent>
              </Tooltip>
            ) : (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button size='sm' variant='ghost' disabled={isProcessing}>
                    <Trash2 className='w-4 h-4 text-red-500' />
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>{t('hookItem.confirmDelete')}</AlertDialogTitle>
                    <AlertDialogDescription>
                      {t('hookItem.confirmDeleteMessage', { name: eventDisplayName })}
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>{t('hookItem.cancel')}</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={onDelete}
                      className='bg-red-600 hover:bg-red-700'
                    >
                      {t('hookItem.delete')}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
          </div>
        </div>

        {/* Hook 配置信息 */}
        <div className='space-y-2'>
          {/* 命令类型 Hook */}
          {isCommandType && hook_config.command && (
            <div className='flex items-start gap-2 text-sm text-muted-foreground'>
              <Terminal className='w-4 h-4 flex-shrink-0 mt-0.5' />
              <span className='flex-shrink-0'>{t('hookItem.executeCommand')}</span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <pre
                    className='font-mono bg-muted px-2 py-1 rounded text-green-600 cursor-pointer hover:bg-muted/80 transition-colors flex-1 min-w-0 whitespace-pre-wrap'
                    style={
                      commandExpanded
                        ? {}
                        : {
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                          }
                    }
                    onClick={() => setCommandExpanded(!commandExpanded)}
                  >
                    {hook_config.command}
                  </pre>
                </TooltipTrigger>
                <TooltipContent>
                  <p className='max-w-xs break-all whitespace-pre-wrap'>
                    {hook_config.command}
                  </p>
                </TooltipContent>
              </Tooltip>
              <Button
                size='sm'
                variant='ghost'
                className='h-6 w-6 p-0 flex-shrink-0'
                onClick={() => handleCopy(hook_config.command || '', '命令')}
              >
                <Copy className='w-3 h-3' />
              </Button>
            </div>
          )}

          {/* 提示类型 Hook */}
          {!isCommandType && hook_config.prompt && (
            <div className='flex items-start gap-2 text-sm text-muted-foreground'>
              <MessageSquare className='w-4 h-4 flex-shrink-0 mt-0.5' />
              <span className='flex-shrink-0'>{t('hookItem.llmPrompt')}</span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span
                    className='font-mono bg-muted px-2 py-1 rounded text-blue-600 cursor-pointer hover:bg-muted/80 transition-colors flex-1 min-w-0 whitespace-pre-wrap'
                    style={
                      promptExpanded
                        ? {}
                        : {
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                          }
                    }
                    onClick={() => setPromptExpanded(!promptExpanded)}
                  >
                    {hook_config.prompt}
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  <p className='max-w-xs break-whitespace'>{hook_config.prompt}</p>
                </TooltipContent>
              </Tooltip>
              <Button
                size='sm'
                variant='ghost'
                className='h-6 w-6 p-0 flex-shrink-0'
                onClick={() => handleCopy(hook_config.prompt || '', '提示')}
              >
                <Copy className='w-3 h-3' />
              </Button>
            </div>
          )}

          {/* 超时时间 */}
          {hook_config.timeout && (
            <div className='flex items-center gap-2 text-sm text-muted-foreground'>
              <Clock className='w-4 h-4 flex-shrink-0' />
              <span className='flex-shrink-0'>{t('hookItem.timeout')}</span>
              <span>{t('hookItem.seconds', { seconds: hook_config.timeout })}</span>
            </div>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
}
