import React, { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
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
  Globe,
  Terminal,
  ChevronDown,
  ChevronUp,
  Variable,
  Webhook,
  Copy,
  Layers,
} from 'lucide-react';
import type { MCPServerInfo } from '@/api/types';
import { toast } from 'sonner';
import { ScopeBadge } from './ScopeBadge';
import { ScopeBadgeUpdater } from './ScopeBadgeUpdater';
import { useTranslation } from 'react-i18next';

interface McpServerItemProps {
  serverInfo: MCPServerInfo;
  onEdit: () => void;
  onDelete: () => void;
  onToggleEnable: (enabled: boolean) => void;
  isProcessing?: boolean;
  onScopeChange?: (oldScope: string, newScope: string) => Promise<void>;
}

// 复制按钮组件
function CopyButton({
  text,
  type,
  onCopy,
}: {
  text: string;
  type: string;
  onCopy: (text: string, type: string) => void;
}) {
  const { t } = useTranslation('projects');

  return (
    <Button
      size='sm'
      variant='ghost'
      className='h-6 w-6 p-0 flex-shrink-0'
      onClick={() => onCopy(text, type)}
    >
      <Copy className='w-3 h-3' />
    </Button>
  );
}

// 可复制的文本显示组件
function CopyableText({
  label,
  text,
  icon: Icon,
  colorClass = 'text-blue-600',
  onCopy,
}: {
  label: string;
  text: string;
  icon: React.ComponentType<{ className?: string }>;
  colorClass?: string;
  onCopy: (text: string, type: string) => void;
}) {
  return (
    <div className='flex items-center gap-2 text-sm text-muted-foreground'>
      <Icon className='w-4 h-4 flex-shrink-0' />
      <span className='flex-shrink-0'>{label}</span>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className={`font-mono bg-muted px-2 py-1 rounded ${colorClass} truncate cursor-pointer hover:bg-muted/80 transition-colors flex-1 min-w-0`}
            onClick={() => onCopy(text, label)}
          >
            {text}
          </span>
        </TooltipTrigger>
        <TooltipContent>
          <p className='max-w-xs break-all'>{text}</p>
        </TooltipContent>
      </Tooltip>
      <CopyButton text={text} type={label} onCopy={onCopy} />
    </div>
  );
}

// 操作按钮组组件
function ActionButtons({
  enabled,
  isProcessing,
  isReadonly,
  onToggleEnable,
  onEdit,
  onDelete,
  serverName,
}: {
  enabled: boolean | undefined;
  isProcessing: boolean;
  isReadonly: boolean;
  onToggleEnable: (enabled: boolean) => void;
  onEdit: () => void;
  onDelete: () => void;
  serverName: string;
}) {
  const { t } = useTranslation('projects');

  const isDisabled = isProcessing || isReadonly;

  return (
    <div className='flex items-center gap-2'>
      {/* 启用/禁用开关 */}
      <Tooltip>
        <TooltipTrigger asChild>
          <div className='flex items-center'>
            <Switch
              checked={enabled}
              onCheckedChange={onToggleEnable}
              disabled={isDisabled}
            />
          </div>
        </TooltipTrigger>
        {isReadonly && (
          <TooltipContent>
            <p>{t('mcpServerItem.readonlyMode')}</p>
          </TooltipContent>
        )}
      </Tooltip>

      {/* 编辑按钮 */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Button size='sm' variant='ghost' onClick={onEdit} disabled={isDisabled}>
            <Pencil className='w-4 h-4' />
          </Button>
        </TooltipTrigger>
        {isReadonly && (
          <TooltipContent>
            <p>{t('mcpServerItem.readonlyMode')}</p>
          </TooltipContent>
        )}
      </Tooltip>

      {/* 删除按钮 */}
      {isReadonly ? (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button size='sm' variant='ghost' disabled={isDisabled}>
              <Trash2 className='w-4 h-4 text-red-500' />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>{t('mcpServerItem.readonlyMode')}</p>
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
              <AlertDialogTitle>{t('mcpServerItem.confirmDelete')}</AlertDialogTitle>
              <AlertDialogDescription>
                {t('mcpServerItem.confirmDeleteMessage', { name: serverName })}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{t('mcpServerItem.cancel')}</AlertDialogCancel>
              <AlertDialogAction
                onClick={onDelete}
                className='bg-red-600 hover:bg-red-700'
              >
                {t('mcpServerItem.delete')}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  );
}

export function McpServerItem({
  serverInfo,
  onEdit,
  onDelete,
  onToggleEnable,
  isProcessing = false,
  onScopeChange,
}: McpServerItemProps) {
  const { t } = useTranslation('projects');
  const { name: serverName, scope, mcpServer: server, enabled, override } = serverInfo;

  const isHttpType = server.type === 'http' || server.type === 'sse';
  const isOverridden = override === true;
  const isPluginScope = scope === 'plugin';
  const isReadonly = isPluginScope;
  const [envExpanded, setEnvExpanded] = useState(false);
  const [headersExpanded, setHeadersExpanded] = useState(false);

  const handleCopy = useCallback(
    async (text: string, type: string) => {
      try {
        await navigator.clipboard.writeText(text);
        toast.success(t('mcpServerItem.copySuccess', { type }));
      } catch (error) {
        toast.error(t('mcpServerItem.copyFailed'));
      }
    },
    [t]
  );

  const handleToggleEnable = useCallback(
    (enabled: boolean) => {
      onToggleEnable(enabled);
    },
    [onToggleEnable]
  );

  return (
    <TooltipProvider>
      <div
        className={`p-4 border rounded-lg transition-colors ${
          isReadonly
            ? 'bg-blue-50/50 border-blue-200 dark:bg-blue-950/50 dark:border-blue-800'
            : isOverridden
              ? 'bg-muted/50 opacity-60'
              : 'hover:bg-accent/50'
        }`}
      >
        {/* 头部信息 */}
        <div className='flex items-center justify-between mb-3'>
          {/* 左侧：作用域标签、类型标签和服务器名称 */}
          <div className='flex items-center gap-3'>
            {isReadonly ? (
              <ScopeBadge scope={scope} />
            ) : (
              <ScopeBadgeUpdater
                currentScope={scope}
                disabled={isProcessing}
                onScopeChange={onScopeChange || (async () => {})}
              />
            )}
            <Badge variant='default'>{server.type}</Badge>
            <div className='flex items-center gap-2'>
              <h4 className='font-medium'>{serverName}</h4>
              {isOverridden && !isReadonly && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge variant='outline' className='gap-1'>
                      <Layers className='w-3 h-3' />
                      {t('mcpServerItem.overridden')}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t('mcpServerItem.overriddenTooltip')}</p>
                  </TooltipContent>
                </Tooltip>
              )}
            </div>
          </div>

          {/* 右侧：操作按钮 */}
          <ActionButtons
            enabled={enabled}
            isProcessing={isProcessing}
            isReadonly={isReadonly}
            onToggleEnable={handleToggleEnable}
            onEdit={onEdit}
            onDelete={onDelete}
            serverName={serverName}
          />
        </div>

        {/* 服务器配置信息 */}
        <div className='space-y-2'>
          {isHttpType ? (
            <>
              {/* URL 信息 */}
              {server.url && (
                <CopyableText
                  label={t('mcpServerItem.url')}
                  text={server.url}
                  icon={Globe}
                  colorClass='text-blue-600'
                  onCopy={handleCopy}
                />
              )}

              {/* HTTP 请求头折叠面板 */}
              {server.headers && Object.keys(server.headers).length > 0 && (
                <Collapsible open={headersExpanded} onOpenChange={setHeadersExpanded}>
                  <CollapsibleTrigger asChild>
                    <Button variant='ghost' size='sm' className='h-8 px-2 text-xs'>
                      <Webhook className='w-3 h-3 mr-1' />
                      {t('mcpServerItem.httpHeaders', {
                        count: Object.keys(server.headers).length,
                      })}
                      {headersExpanded ? (
                        <ChevronUp className='w-3 h-3 ml-1' />
                      ) : (
                        <ChevronDown className='w-3 h-3 ml-1' />
                      )}
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className='space-y-1 mt-2'>
                    {Object.entries(server.headers).map(([key, value]) => (
                      <div key={key} className='ml-6 flex items-center gap-2 text-xs'>
                        <span className='font-semibold text-muted-foreground flex-shrink-0'>
                          {key}:
                        </span>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span
                              className='font-mono bg-muted px-2 py-1 rounded truncate cursor-pointer hover:bg-muted/80 transition-colors flex-1 min-w-0'
                              onClick={() => handleCopy(value, `HTTP请求头 ${key}`)}
                            >
                              {value}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className='max-w-xs break-all'>{value}</p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                    ))}
                  </CollapsibleContent>
                </Collapsible>
              )}
            </>
          ) : (
            <>
              {/* 命令信息 */}
              {server.command && (
                <CopyableText
                  label={t('mcpServerItem.command')}
                  text={`${server.command} ${server.args?.join(' ') || ''}`.trim()}
                  icon={Terminal}
                  colorClass='text-green-600'
                  onCopy={handleCopy}
                />
              )}

              {/* 工作目录 */}
              {server.cwd && (
                <div className='flex items-center gap-2 text-sm text-muted-foreground ml-6'>
                  <span className='flex-shrink-0'>
                    {t('mcpServerItem.workingDirectory')}
                  </span>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span
                        className='font-mono bg-muted px-2 py-1 rounded truncate cursor-pointer hover:bg-muted/80 transition-colors flex-1 min-w-0'
                        onClick={() => handleCopy(server.cwd || '', '工作目录')}
                      >
                        {server.cwd}
                      </span>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className='max-w-xs break-all'>{server.cwd}</p>
                    </TooltipContent>
                  </Tooltip>
                  <CopyButton text={server.cwd} type='工作目录' onCopy={handleCopy} />
                </div>
              )}

              {/* 环境变量折叠面板 */}
              {server.env && Object.keys(server.env).length > 0 && (
                <Collapsible open={envExpanded} onOpenChange={setEnvExpanded}>
                  <CollapsibleTrigger asChild>
                    <Button variant='ghost' size='sm' className='h-8 px-2 text-xs'>
                      <Variable className='w-3 h-3 mr-1' />
                      {t('mcpServerItem.envVars', {
                        count: Object.keys(server.env).length,
                      })}
                      {envExpanded ? (
                        <ChevronUp className='w-3 h-3 ml-1' />
                      ) : (
                        <ChevronDown className='w-3 h-3 ml-1' />
                      )}
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className='space-y-1 mt-2'>
                    {Object.entries(server.env).map(([key, value]) => (
                      <div key={key} className='ml-6 flex items-center gap-2 text-xs'>
                        <span className='font-semibold text-muted-foreground flex-shrink-0'>
                          {key}:
                        </span>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span
                              className='font-mono bg-muted px-2 py-1 rounded truncate cursor-pointer hover:bg-muted/80 transition-colors flex-1 min-w-0'
                              onClick={() => handleCopy(value, `环境变量 ${key}`)}
                            >
                              {value}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className='max-w-xs break-all'>{value}</p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                    ))}
                  </CollapsibleContent>
                </Collapsible>
              )}
            </>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
}
