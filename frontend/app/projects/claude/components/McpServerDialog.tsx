import React, { useCallback, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Save,
  X,
  Plus,
  Trash2,
  Variable,
  Globe,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import type { MCPServerInfo, MCPServer, ConfigScope } from '@/api/types';
import { ConfigScope as ConfigScopeEnum } from '@/api/types';
import { useTranslation } from 'react-i18next';
import { Separator } from '@/components/ui/separator';

type McpServerFormData = {
  name: string;
  scope: ConfigScope;
  type: 'stdio' | 'sse' | 'http';
  fullCommand: string; // 合并后的完整命令，包含参数
  env: Record<string, string>;
  cwd?: string;
  url?: string;
  headers: Record<string, string>;
};

interface McpServerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  serverInfo: MCPServerInfo | null;
  onSave: (data: {
    name: string;
    server: MCPServer;
    scope?: ConfigScope;
  }) => Promise<void>;
  isProcessing?: boolean;
  currentScope?: ConfigScope | 'mixed' | null; // 当前页面选中的 scope
}

export function McpServerDialog({
  open,
  onOpenChange,
  serverInfo,
  onSave,
  isProcessing = false,
  currentScope,
}: McpServerDialogProps) {
  const { t } = useTranslation('projects');
  const isEdit = !!serverInfo;

  // 折叠状态
  const [headersExpanded, setHeadersExpanded] = useState(false);
  const [envExpanded, setEnvExpanded] = useState(false);

  // 判断是否应该禁用 scope 选择：当当前页面有明确的 scope 设置时（非 mixed 且非 null）
  const shouldDisableScope =
    currentScope && currentScope !== 'mixed' && currentScope !== null;

  // 获取默认的 scope 值
  const getDefaultScope = (): ConfigScope => {
    if (isEdit && serverInfo) {
      return serverInfo.scope;
    }
    // 如果当前页面有明确的 scope 设置，使用该值；否则默认为 PROJECT
    return shouldDisableScope && currentScope
      ? (currentScope as ConfigScope)
      : ConfigScopeEnum.PROJECT;
  };

  const form = useForm<McpServerFormData>({
    defaultValues: {
      name: '',
      scope: getDefaultScope(),
      type: 'stdio',
      fullCommand: '',
      env: {},
      cwd: '',
      url: '',
      headers: {},
    },
    mode: 'onChange',
  });

  // 监听类型变化
  const serverType = form.watch('type');

  React.useEffect(() => {
    if (open && serverInfo) {
      // 编辑模式：使用现有数据填充表单
      const { name, scope, mcpServer: server } = serverInfo;

      // 合并 command 和 args 为 fullCommand
      const fullCommand =
        server.command && server.args && server.args.length > 0
          ? `${server.command} ${server.args.join(' ')}`
          : server.command || '';

      form.reset({
        name,
        scope,
        type: server.type as 'stdio' | 'sse' | 'http',
        fullCommand,
        env: server.env || {},
        cwd: server.cwd || '',
        url: server.url || '',
        headers: server.headers || {},
      });
    } else if (open && !serverInfo) {
      // 新增模式：重置为默认值，使用 currentScope 作为默认 scope
      form.reset({
        name: '',
        scope: getDefaultScope(),
        type: 'stdio',
        fullCommand: '',
        env: {},
        cwd: '',
        url: '',
        headers: {},
      });
    }
  }, [serverInfo, open, form, currentScope]);

  const handleSave = async (data: McpServerFormData) => {
    try {
      // 将 fullCommand 拆分为 command 和 args
      const commandParts = data.fullCommand.trim().split(/\s+/);
      const command = commandParts.length > 0 ? commandParts[0] : undefined;
      const args = commandParts.length > 1 ? commandParts.slice(1) : undefined;

      const serverData: MCPServer = {
        type: data.type,
        command: command,
        args: args,
        env: data.env && Object.keys(data.env).length > 0 ? data.env : undefined,
        cwd: data.cwd || undefined,
        url: data.url || undefined,
        headers:
          data.headers && Object.keys(data.headers).length > 0
            ? data.headers
            : undefined,
      };

      await onSave({
        name: data.name,
        server: serverData,
        scope: data.scope,
      });

      onOpenChange(false);
      form.reset();
    } catch (error) {
      console.error('保存失败:', error);
    }
  };

  const handleCancel = () => {
    form.reset();
    onOpenChange(false);
  };

  // Headers 操作函数
  const addHeader = useCallback(() => {
    const currentHeaders = form.getValues('headers') || {};
    form.setValue('headers', {
      ...currentHeaders,
      '': '',
    });
  }, [form]);

  const removeHeader = useCallback(
    (key: string) => {
      const currentHeaders = form.getValues('headers') || {};
      const newHeaders = { ...currentHeaders };
      delete newHeaders[key];
      form.setValue('headers', Object.keys(newHeaders).length > 0 ? newHeaders : {});
    },
    [form]
  );

  const updateHeaderKey = useCallback(
    (oldKey: string, newKey: string) => {
      const currentHeaders = form.getValues('headers') || {};
      const newHeaders = { ...currentHeaders };
      if (newKey !== oldKey) {
        const value = newHeaders[oldKey];
        delete newHeaders[oldKey];
        newHeaders[newKey] = value;
      }
      form.setValue('headers', newHeaders, { shouldDirty: false });
    },
    [form]
  );

  const updateHeaderValue = useCallback(
    (key: string, value: string) => {
      const currentHeaders = form.getValues('headers') || {};
      form.setValue(
        'headers',
        {
          ...currentHeaders,
          [key]: value,
        },
        { shouldDirty: false }
      );
    },
    [form]
  );

  // 环境变量操作函数
  const addEnv = useCallback(() => {
    const currentEnv = form.getValues('env') || {};
    form.setValue('env', {
      ...currentEnv,
      '': '',
    });
  }, [form]);

  const removeEnv = useCallback(
    (key: string) => {
      const currentEnv = form.getValues('env') || {};
      const newEnv = { ...currentEnv };
      delete newEnv[key];
      form.setValue('env', Object.keys(newEnv).length > 0 ? newEnv : {});
    },
    [form]
  );

  const updateEnvKey = useCallback(
    (oldKey: string, newKey: string) => {
      const currentEnv = form.getValues('env') || {};
      const newEnv = { ...currentEnv };
      if (newKey !== oldKey) {
        const value = newEnv[oldKey];
        delete newEnv[oldKey];
        newEnv[newKey] = value;
      }
      form.setValue('env', newEnv, { shouldDirty: false });
    },
    [form]
  );

  const updateEnvValue = useCallback(
    (key: string, value: string) => {
      const currentEnv = form.getValues('env') || {};
      form.setValue(
        'env',
        {
          ...currentEnv,
          [key]: value,
        },
        { shouldDirty: false }
      );
    },
    [form]
  );

  const isHttpType = serverType === 'http' || serverType === 'sse';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className='max-w-2xl max-h-[90vh] overflow-y-auto p-0'>
        <DialogHeader className='px-4 pt-4 pb-3 border-b'>
          <DialogTitle className='text-base font-semibold'>
            {isEdit ? t('mcpServerDialog.editTitle') : t('mcpServerDialog.addTitle')}
          </DialogTitle>
          <DialogDescription className='text-xs mt-0.5'>
            {t('mcpServerDialog.dialogDescription')}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSave)} className='space-y-0'>
            <div className='px-4 py-3 space-y-3'>
              {/* 作用域和服务器类型 - 同行展示 */}
              <div className='grid grid-cols-1 md:grid-cols-2 gap-3'>
                <FormField
                  control={form.control}
                  name='scope'
                  render={({ field }) => (
                    <FormItem>
                      <div className='flex items-center gap-2'>
                        <FormLabel className='text-xs font-medium whitespace-nowrap mb-0'>
                          {t('mcpServerDialog.scope')}
                        </FormLabel>
                        <Select
                          onValueChange={field.onChange}
                          value={field.value}
                          disabled={
                            isProcessing || isEdit || shouldDisableScope || false
                          }
                        >
                          <FormControl>
                            <SelectTrigger className='h-8 text-xs'>
                              <SelectValue
                                placeholder={t('mcpServerDialog.scopePlaceholder')}
                              />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value='project'>
                              {t('detail.scopeBadge.project.label')}
                            </SelectItem>
                            <SelectItem value='local'>
                              {t('detail.scopeBadge.local.label')}
                            </SelectItem>
                            <SelectItem value='user'>
                              {t('detail.scopeBadge.user.label')}
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <FormMessage />
                      {(isEdit || shouldDisableScope) && (
                        <FormDescription className='text-[10px]'>
                          {shouldDisableScope && !isEdit
                            ? t('mcpServerDialog.scopeLockedByCurrentScope')
                            : t('mcpServerDialog.editScopeDisabled')}
                        </FormDescription>
                      )}
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name='type'
                  render={({ field }) => (
                    <FormItem>
                      <div className='flex items-center gap-2'>
                        <FormLabel className='text-xs font-medium whitespace-nowrap mb-0'>
                          {t('mcpServerDialog.serverType')}
                        </FormLabel>
                        <Select
                          onValueChange={field.onChange}
                          value={field.value}
                          disabled={isProcessing}
                        >
                          <FormControl>
                            <SelectTrigger className='h-8 text-xs'>
                              <SelectValue
                                placeholder={t('mcpServerDialog.serverTypePlaceholder')}
                              />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value='stdio'>stdio</SelectItem>
                            <SelectItem value='sse'>sse</SelectItem>
                            <SelectItem value='http'>http</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* 服务器名称 */}
              <FormField
                control={form.control}
                name='name'
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className='text-xs font-medium'>
                      {t('mcpServerDialog.serverName')}
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder={t('mcpServerDialog.serverNamePlaceholder')}
                        disabled={isProcessing || isEdit}
                        className='h-8 text-sm'
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                    {isEdit && (
                      <FormDescription className='text-[10px]'>
                        {t('mcpServerDialog.editNameDisabled')}
                      </FormDescription>
                    )}
                  </FormItem>
                )}
              />

              <Separator className='my-2' />

              {/* HTTP 类型服务器配置 */}
              {isHttpType && (
                <div className='space-y-3'>
                  <FormField
                    control={form.control}
                    name='url'
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className='text-xs font-medium flex items-center gap-1.5'>
                          <Globe className='w-3.5 h-3.5 text-muted-foreground' />
                          {t('mcpServerDialog.serverUrl')}
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder={t('mcpServerDialog.serverUrlPlaceholder')}
                            disabled={isProcessing}
                            className='h-8 text-sm'
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* HTTP 请求头配置 - 可折叠 */}
                  <div className='space-y-2'>
                    <FormField
                      control={form.control}
                      name='headers'
                      render={({ field }) => {
                        const headers = field.value || {};
                        const headersArray = Object.entries(headers);
                        const hasHeaders = headersArray.length > 0;

                        return (
                          <FormItem>
                            <div className='flex items-center justify-between'>
                              <button
                                type='button'
                                onClick={() => setHeadersExpanded(!headersExpanded)}
                                className='flex items-center gap-1.5 text-xs font-medium hover:text-foreground/80 transition-colors'
                              >
                                {headersExpanded ? (
                                  <ChevronDown className='w-3.5 h-3.5' />
                                ) : (
                                  <ChevronRight className='w-3.5 h-3.5' />
                                )}
                                {t('mcpServerDialog.httpHeaders')}
                                {hasHeaders && (
                                  <span className='ml-1 px-1.5 py-0.5 bg-muted text-[10px] rounded'>
                                    {headersArray.length}
                                  </span>
                                )}
                              </button>
                              <Button
                                type='button'
                                variant='ghost'
                                size='sm'
                                onClick={() => {
                                  addHeader();
                                  if (!headersExpanded) setHeadersExpanded(true);
                                }}
                                disabled={isProcessing}
                                className='h-7 px-2 text-[10px]'
                              >
                                <Plus className='w-3 h-3 mr-1' />
                                {t('mcpServerDialog.addHeader')}
                              </Button>
                            </div>
                            <FormControl>
                              {(headersExpanded || hasHeaders) && (
                                <div className='space-y-1.5'>
                                  {headersArray.map(([key, value], index) => (
                                    <div
                                      key={`header-${index}`}
                                      className='flex gap-1.5 items-center group'
                                    >
                                      <div className='flex-1 grid grid-cols-2 gap-1.5'>
                                        <Input
                                          value={key}
                                          onChange={e =>
                                            updateHeaderKey(key, e.target.value)
                                          }
                                          placeholder={t(
                                            'mcpServerDialog.headerNamePlaceholder'
                                          )}
                                          disabled={isProcessing}
                                          className='h-8 text-xs'
                                        />
                                        <Input
                                          value={value}
                                          onChange={e =>
                                            updateHeaderValue(key, e.target.value)
                                          }
                                          placeholder={t(
                                            'mcpServerDialog.headerValuePlaceholder'
                                          )}
                                          disabled={isProcessing}
                                          className='h-8 text-xs'
                                        />
                                      </div>
                                      <Button
                                        type='button'
                                        variant='ghost'
                                        size='sm'
                                        onClick={() => removeHeader(key)}
                                        disabled={isProcessing}
                                        className='h-8 w-8 p-0 opacity-60 group-hover:opacity-100 transition-opacity'
                                      >
                                        <Trash2 className='w-3.5 h-3.5' />
                                      </Button>
                                    </div>
                                  ))}
                                  {headersArray.length === 0 && (
                                    <div className='py-6 px-3 border border-dashed rounded-md flex flex-col items-center justify-center text-center'>
                                      <Globe className='w-8 h-8 text-muted-foreground/40 mb-1.5' />
                                      <p className='text-xs text-muted-foreground'>
                                        {t('mcpServerDialog.noHeaders')}
                                      </p>
                                      <p className='text-[10px] text-muted-foreground/70 mt-0.5'>
                                        点击上方按钮添加 HTTP 请求头
                                      </p>
                                    </div>
                                  )}
                                </div>
                              )}
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        );
                      }}
                    />
                  </div>
                </div>
              )}

              {/* 非 HTTP 类型服务器配置 */}
              {!isHttpType && (
                <div className='space-y-3'>
                  <FormField
                    control={form.control}
                    name='fullCommand'
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className='text-xs font-medium'>
                          {t('mcpServerDialog.startupCommand')}
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder={t('mcpServerDialog.startupCommandPlaceholder')}
                            disabled={isProcessing}
                            className='h-8 font-mono text-xs'
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name='cwd'
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className='text-xs font-medium'>
                          {t('mcpServerDialog.workingDirectory')}
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder={t(
                              'mcpServerDialog.workingDirectoryPlaceholder'
                            )}
                            disabled={isProcessing}
                            className='h-8 text-xs'
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* 环境变量配置 - 可折叠 */}
                  <div className='space-y-2'>
                    <FormField
                      control={form.control}
                      name='env'
                      render={({ field }) => {
                        const env = field.value || {};
                        const envArray = Object.entries(env);
                        const hasEnv = envArray.length > 0;

                        return (
                          <FormItem>
                            <div className='flex items-center justify-between'>
                              <button
                                type='button'
                                onClick={() => setEnvExpanded(!envExpanded)}
                                className='flex items-center gap-1.5 text-xs font-medium hover:text-foreground/80 transition-colors'
                              >
                                {envExpanded ? (
                                  <ChevronDown className='w-3.5 h-3.5' />
                                ) : (
                                  <ChevronRight className='w-3.5 h-3.5' />
                                )}
                                <Variable className='w-3.5 h-3.5 text-muted-foreground' />
                                {t('mcpServerDialog.envVars')}
                                {hasEnv && (
                                  <span className='ml-1 px-1.5 py-0.5 bg-muted text-[10px] rounded'>
                                    {envArray.length}
                                  </span>
                                )}
                              </button>
                              <Button
                                type='button'
                                variant='ghost'
                                size='sm'
                                onClick={() => {
                                  addEnv();
                                  if (!envExpanded) setEnvExpanded(true);
                                }}
                                disabled={isProcessing}
                                className='h-7 px-2 text-[10px]'
                              >
                                <Plus className='w-3 h-3 mr-1' />
                                {t('mcpServerDialog.addEnv')}
                              </Button>
                            </div>
                            <FormControl>
                              {(envExpanded || hasEnv) && (
                                <div className='space-y-1.5'>
                                  {envArray.map(([key, value], index) => (
                                    <div
                                      key={`env-${index}`}
                                      className='flex gap-1.5 items-center group'
                                    >
                                      <div className='flex-1 grid grid-cols-2 gap-1.5'>
                                        <Input
                                          value={key}
                                          onChange={e =>
                                            updateEnvKey(key, e.target.value)
                                          }
                                          placeholder={t(
                                            'mcpServerDialog.envNamePlaceholder'
                                          )}
                                          disabled={isProcessing}
                                          className='h-8 text-xs'
                                        />
                                        <Input
                                          value={value}
                                          onChange={e =>
                                            updateEnvValue(key, e.target.value)
                                          }
                                          placeholder={t(
                                            'mcpServerDialog.envValuePlaceholder'
                                          )}
                                          disabled={isProcessing}
                                          className='h-8 text-xs'
                                        />
                                      </div>
                                      <Button
                                        type='button'
                                        variant='ghost'
                                        size='sm'
                                        onClick={() => removeEnv(key)}
                                        disabled={isProcessing}
                                        className='h-8 w-8 p-0 opacity-60 group-hover:opacity-100 transition-opacity'
                                      >
                                        <Trash2 className='w-3.5 h-3.5' />
                                      </Button>
                                    </div>
                                  ))}
                                  {envArray.length === 0 && (
                                    <div className='py-6 px-3 border border-dashed rounded-md flex flex-col items-center justify-center text-center'>
                                      <Variable className='w-8 h-8 text-muted-foreground/40 mb-1.5' />
                                      <p className='text-xs text-muted-foreground'>
                                        {t('mcpServerDialog.noEnv')}
                                      </p>
                                      <p className='text-[10px] text-muted-foreground/70 mt-0.5'>
                                        点击上方按钮添加环境变量
                                      </p>
                                    </div>
                                  )}
                                </div>
                              )}
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        );
                      }}
                    />
                  </div>
                </div>
              )}
            </div>

            <DialogFooter className='px-4 py-3 border-t bg-muted/20'>
              <Button
                type='button'
                variant='outline'
                onClick={handleCancel}
                disabled={isProcessing}
                className='h-8 px-3 text-xs'
              >
                <X className='w-3.5 h-3.5 mr-1.5' />
                {t('mcpServerDialog.cancel')}
              </Button>
              <Button
                type='submit'
                disabled={isProcessing}
                className='h-8 px-3 text-xs'
              >
                <Save className='w-3.5 h-3.5 mr-1.5' />
                {isProcessing ? t('mcpServerDialog.saving') : t('mcpServerDialog.save')}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
