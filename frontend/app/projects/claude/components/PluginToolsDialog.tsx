import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { PluginInfo } from '@/api/types';
import { useTranslation } from 'react-i18next';

interface ToolItemProps {
  name: string;
  description?: string;
  lastModified?: string;
}

// 通用的工具项渲染组件
function ToolItem({ name, description, lastModified }: ToolItemProps) {
  const { t } = useTranslation('projects');

  return (
    <div className='flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors'>
      <div className='flex-1'>
        <div className='flex items-center gap-2'>
          <span className='font-medium'>{name}</span>
        </div>
        {description && (
          <Tooltip delayDuration={400}>
            <TooltipTrigger asChild>
              <p className='text-sm text-muted-foreground mt-1 line-clamp-2 cursor-help'>
                {description}
              </p>
            </TooltipTrigger>
            <TooltipContent>
              <p className='max-w-md'>{description}</p>
            </TooltipContent>
          </Tooltip>
        )}
        {lastModified && (
          <p className='text-xs text-muted-foreground mt-1'>
            {t('pluginToolsDialog.lastModified', { date: lastModified })}
          </p>
        )}
      </div>
    </div>
  );
}

interface PluginToolsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  plugin: PluginInfo | null;
}

export function PluginToolsDialog({
  open,
  onOpenChange,
  plugin,
}: PluginToolsDialogProps) {
  const { t } = useTranslation('projects');
  const tools = plugin?.tools;

  // 工具类型配置
  const toolConfigs = [
    {
      key: 'commands',
      label: 'Commands',
      value: 'commands',
      count: tools?.commands?.length || 0,
    },
    {
      key: 'skills',
      label: 'Skills',
      value: 'skills',
      count: tools?.skills?.length || 0,
    },
    {
      key: 'agents',
      label: 'Agents',
      value: 'agents',
      count: tools?.agents?.length || 0,
    },
    { key: 'mcp', label: 'MCP', value: 'mcp', count: tools?.mcp_servers?.length || 0 },
    { key: 'hooks', label: 'Hooks', value: 'hooks', count: tools?.hooks?.length || 0 },
  ] as const;

  // 过滤出有内容的工具
  const availableTools = toolConfigs.filter(t => t.count > 0);
  const totalCount = availableTools.reduce((sum, t) => sum + t.count, 0);

  // 获取默认的 tab（第一个有内容的工具）
  const defaultTab = availableTools[0]?.value;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className='max-w-3xl max-h-[80vh]'>
        <DialogHeader>
          <DialogTitle>
            Plugin: {plugin?.config.name}
            {totalCount > 0 && (
              <span className='ml-2 text-sm text-muted-foreground'>
                ({t('pluginToolsDialog.toolsCount', { count: totalCount })})
              </span>
            )}
          </DialogTitle>
          {plugin?.config.description && (
            <DialogDescription>{plugin.config.description}</DialogDescription>
          )}
        </DialogHeader>

        {!tools || totalCount === 0 ? (
          <div className='py-8 text-center text-muted-foreground'>
            {t('pluginToolsDialog.noTools')}
          </div>
        ) : (
          <Tabs defaultValue={defaultTab} className='w-full'>
            <TabsList
              className='grid w-full'
              style={{
                gridTemplateColumns: `repeat(${availableTools.length}, minmax(0, 1fr))`,
              }}
            >
              {availableTools.map(tool => (
                <TabsTrigger key={tool.value} value={tool.value}>
                  {tool.label}
                  <Badge variant='secondary' className='ml-1'>
                    {tool.count}
                  </Badge>
                </TabsTrigger>
              ))}
            </TabsList>

            {/* Commands Tab */}
            {tools?.commands && tools.commands.length > 0 && (
              <TabsContent value='commands' className='mt-4'>
                <ScrollArea className='h-[400px] pr-4'>
                  <div className='space-y-2'>
                    {tools.commands.map((command, index) => (
                      <ToolItem
                        key={`command-${index}`}
                        name={command.name}
                        description={command.description}
                        lastModified={command.last_modified_str}
                      />
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>
            )}

            {/* Skills Tab */}
            {tools?.skills && tools.skills.length > 0 && (
              <TabsContent value='skills' className='mt-4'>
                <ScrollArea className='h-[400px] pr-4'>
                  <div className='space-y-2'>
                    {tools.skills.map((skill, index) => (
                      <ToolItem
                        key={`skill-${index}`}
                        name={skill.name}
                        description={skill.description}
                        lastModified={skill.last_modified_str}
                      />
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>
            )}

            {/* Agents Tab */}
            {tools?.agents && tools.agents.length > 0 && (
              <TabsContent value='agents' className='mt-4'>
                <ScrollArea className='h-[400px] pr-4'>
                  <div className='space-y-2'>
                    {tools.agents.map((agent, index) => (
                      <ToolItem
                        key={`agent-${index}`}
                        name={agent.name}
                        description={agent.description}
                        lastModified={agent.last_modified_str}
                      />
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>
            )}

            {/* MCP Servers Tab */}
            {tools?.mcp_servers && tools.mcp_servers.length > 0 && (
              <TabsContent value='mcp' className='mt-4'>
                <ScrollArea className='h-[400px] pr-4'>
                  <div className='space-y-2'>
                    {tools.mcp_servers.map((server, index) => (
                      <div
                        key={`mcp-${index}`}
                        className='flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors'
                      >
                        <div className='flex-1'>
                          <div className='flex items-center gap-2'>
                            <span className='text-xs text-muted-foreground'>
                              {server.mcpServer.type}
                            </span>
                            <span className='font-medium'>{server.name}</span>
                          </div>
                          <div className='text-xs text-muted-foreground mt-1'>
                            {server.mcpServer.command && (
                              <div>
                                {t('pluginToolsDialog.command')}{' '}
                                {server.mcpServer.command}
                              </div>
                            )}
                            {server.mcpServer.url && (
                              <div>
                                {t('pluginToolsDialog.url')}: {server.mcpServer.url}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>
            )}

            {/* Hooks Tab */}
            {tools?.hooks && tools.hooks.length > 0 && (
              <TabsContent value='hooks' className='mt-4'>
                <ScrollArea className='h-[400px] pr-4'>
                  <div className='space-y-2'>
                    {tools.hooks.map((hook, index) => (
                      <div
                        key={`hook-${index}`}
                        className='p-3 border rounded-lg hover:bg-muted/50 transition-colors'
                      >
                        <div className='flex items-center gap-2 mb-2'>
                          <span className='font-medium'>{hook.event}</span>
                        </div>
                        <div className='text-xs text-muted-foreground space-y-1'>
                          <div>
                            <span className='font-medium'>
                              {t('pluginToolsDialog.hookType')}
                            </span>{' '}
                            {hook.hook_config.type}
                          </div>
                          {hook.matcher && (
                            <div>
                              <span className='font-medium'>
                                {t('pluginToolsDialog.matcher')}
                              </span>{' '}
                              {hook.matcher}
                            </div>
                          )}
                          {hook.hook_config.command && (
                            <div>
                              <span className='font-medium'>
                                {t('pluginToolsDialog.commandLabel')}
                              </span>{' '}
                              <code className='bg-muted px-1 py-0.5 rounded'>
                                {hook.hook_config.command}
                              </code>
                            </div>
                          )}
                          {hook.hook_config.prompt && (
                            <div>
                              <span className='font-medium'>
                                {t('pluginToolsDialog.promptLabel')}
                              </span>{' '}
                              <span className='line-clamp-2'>
                                {hook.hook_config.prompt}
                              </span>
                            </div>
                          )}
                          {hook.hook_config.timeout && (
                            <div>
                              <span className='font-medium'>
                                {t('pluginToolsDialog.timeoutLabel')}
                              </span>{' '}
                              {hook.hook_config.timeout}s
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>
            )}
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  );
}
