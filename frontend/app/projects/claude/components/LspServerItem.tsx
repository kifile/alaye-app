import React, { useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Terminal,
  ChevronDown,
  ChevronUp,
  Variable,
  Copy,
  FileCode,
  Globe,
  Store,
} from 'lucide-react';
import type { LSPServerInfo } from '@/api/types';
import { toast } from 'sonner';
import { ScopeBadge } from './ScopeBadge';
import { useTranslation } from 'react-i18next';

interface LspServerItemProps {
  serverInfo: LSPServerInfo;
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
  return (
    <button
      className='h-6 w-6 p-0 flex-shrink-0 flex items-center justify-center rounded hover:bg-accent transition-colors'
      onClick={() => onCopy(text, type)}
    >
      <Copy className='w-3 h-3' />
    </button>
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

export function LspServerItem({ serverInfo }: LspServerItemProps) {
  const { t } = useTranslation('projects');
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    name: serverName,
    scope,
    lspServer: server,
    plugin_name,
    marketplace_name,
  } = serverInfo;

  const [envExpanded, setEnvExpanded] = useState(false);

  const handleCopy = useCallback(
    async (text: string, type: string) => {
      try {
        await navigator.clipboard.writeText(text);
        toast.success(t('lspServerItem.copySuccess', { type }));
      } catch (error) {
        toast.error(t('lspServerItem.copyFailed'));
      }
    },
    [t]
  );

  // 跳转到插件页面
  const handleGoToPlugin = useCallback(() => {
    if (!plugin_name) return;

    const params = new URLSearchParams(searchParams.toString());
    params.set('section', 'plugins');
    params.set('search', plugin_name);

    if (marketplace_name) {
      params.set('marketplaces', marketplace_name);
    }

    router.push(`?${params.toString()}`);
  }, [plugin_name, marketplace_name, router, searchParams]);

  const hasArgs = server.args && server.args.length > 0;
  const hasEnv = server.env && Object.keys(server.env).length > 0;
  const hasExtensions =
    server.extensionToLanguage && Object.keys(server.extensionToLanguage).length > 0;
  const commandNotInstalled = serverInfo.command_installed === false;

  return (
    <TooltipProvider>
      <div
        className={`p-4 border rounded-lg transition-colors bg-blue-50/50 border-blue-200 dark:bg-blue-950/50 dark:border-blue-800`}
      >
        {/* 头部信息 */}
        <div className='flex items-center justify-between mb-3'>
          {/* 左侧：作用域标签、类型标签和服务器名称 */}
          <div className='flex items-center gap-3'>
            <ScopeBadge scope={scope} />
            <Badge variant='default'>{server.transport || 'stdio'}</Badge>
            <div className='flex items-center gap-2'>
              <h4 className='font-medium'>{serverName}</h4>
              {commandNotInstalled && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge
                      variant='outline'
                      className='gap-1 bg-yellow-50 text-yellow-700 border-yellow-200'
                    >
                      <Terminal className='w-3 h-3' />
                      {t('lspServerItem.commandNotInstalled')}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t('lspServerItem.commandNotInstalledTooltip')}</p>
                  </TooltipContent>
                </Tooltip>
              )}
            </div>
          </div>

          {/* 右侧：跳转到插件按钮 */}
          {plugin_name && (
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
                <p>{t('lspServerItem.goToPlugin')}</p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>

        {/* 插件信息 */}
        {(plugin_name || marketplace_name) && (
          <div className='flex items-center gap-2 text-xs text-muted-foreground mb-3'>
            <FileCode className='w-3.5 h-3.5' />
            {plugin_name && (
              <span>
                {t('lspServerItem.fromPlugin')} <strong>{plugin_name}</strong>
              </span>
            )}
            {marketplace_name && plugin_name && <span> • </span>}
            {marketplace_name && (
              <span>
                {t('lspServerItem.fromMarketplace')} <strong>{marketplace_name}</strong>
              </span>
            )}
          </div>
        )}

        {/* 服务器配置信息 */}
        <div className='space-y-2'>
          {/* 命令信息 */}
          {server.command && (
            <CopyableText
              label={t('lspServerItem.command')}
              text={`${server.command} ${hasArgs ? server.args?.join(' ') : ''}`.trim()}
              icon={Terminal}
              colorClass='text-green-600'
              onCopy={handleCopy}
            />
          )}

          {/* 扩展名到语言映射 */}
          {hasExtensions && (
            <div className='flex items-start gap-2 text-sm text-muted-foreground ml-6'>
              <FileCode className='w-4 h-4 flex-shrink-0 mt-0.5' />
              <div className='flex-1'>
                <span className='font-medium'>
                  {t('lspServerItem.extensionMapping')}:
                </span>
                <div className='mt-1 flex flex-wrap gap-1'>
                  {Object.entries(server.extensionToLanguage).map(([ext, lang]) => (
                    <Badge key={ext} variant='secondary' className='text-xs'>
                      {ext} → {lang}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 环境变量折叠面板 */}
          {hasEnv && (
            <Collapsible open={envExpanded} onOpenChange={setEnvExpanded}>
              <CollapsibleTrigger asChild>
                <button className='flex items-center gap-1.5 text-xs hover:text-foreground transition-colors'>
                  <Variable className='w-3.5 h-3.5 text-muted-foreground' />
                  {t('lspServerItem.envVars', {
                    count: Object.keys(server.env!).length,
                  })}
                  {envExpanded ? (
                    <ChevronDown className='w-3 h-3 ml-1' />
                  ) : (
                    <ChevronUp className='w-3 h-3 ml-1' />
                  )}
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent className='space-y-1 mt-2'>
                {Object.entries(server.env!).map(([key, value]) => (
                  <div key={key} className='ml-6 flex items-center gap-2 text-xs'>
                    <span className='font-semibold text-muted-foreground flex-shrink-0'>
                      {key}:
                    </span>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className='font-mono bg-muted px-2 py-1 rounded truncate cursor-pointer hover:bg-muted/80 transition-colors flex-1 min-w-0'>
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

          {/* 工作目录 */}
          {server.workspaceFolder && (
            <div className='flex items-center gap-2 text-sm text-muted-foreground ml-6'>
              <Globe className='w-4 h-4 flex-shrink-0' />
              <span className='flex-shrink-0'>
                {t('lspServerItem.workspaceFolder')}:
              </span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className='font-mono bg-muted px-2 py-1 rounded truncate cursor-pointer hover:bg-muted/80 transition-colors flex-1 min-w-0'>
                    {server.workspaceFolder}
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  <p className='max-w-xs break-all'>{server.workspaceFolder}</p>
                </TooltipContent>
              </Tooltip>
            </div>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
}
