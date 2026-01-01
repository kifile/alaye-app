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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Save, X } from 'lucide-react';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import type { HookConfigInfo, HookEvent, ConfigScope, HookConfig } from '@/api/types';
import {
  HookEvent as HookEventEnum,
  ConfigScope as ConfigScopeEnum,
} from '@/api/types';
import { useTranslation } from 'react-i18next';
import { Separator } from '@/components/ui/separator';

// Hook 类型
type HookType = 'command' | 'prompt';

// 表单验证 Schema
const hookFormSchema = z.object({
  event: z.enum(
    [
      'PreToolUse',
      'PermissionRequest',
      'PostToolUse',
      'Notification',
      'UserPromptSubmit',
      'Stop',
      'SubagentStop',
      'PreCompact',
      'SessionStart',
      'SessionEnd',
    ],
    {
      message: '请选择事件类型',
    }
  ),
  scope: z.enum(['user', 'project', 'local', 'plugin'], {
    message: '请选择作用域',
  }),
  hookType: z.enum(['command', 'prompt'], {
    message: '请选择 Hook 类型',
  }),
  matcher: z.string().optional(),
  command: z.string().optional(),
  prompt: z.string().optional(),
  timeout: z.string().optional(),
});

type HookFormData = z.infer<typeof hookFormSchema>;

interface HookDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  hookInfo: HookConfigInfo | null;
  onSave: (data: {
    event: HookEvent;
    hook: HookConfig;
    matcher?: string;
    scope?: ConfigScope;
  }) => Promise<void>;
  isProcessing?: boolean;
  currentScope?: ConfigScope | 'mixed' | null; // 当前页面选中的 scope
}

export function HookDialog({
  open,
  onOpenChange,
  hookInfo,
  onSave,
  isProcessing = false,
  currentScope,
}: HookDialogProps) {
  const { t } = useTranslation('projects');
  const isEdit = !!hookInfo;

  // 判断是否应该禁用 scope 选择：当当前页面有明确的 scope 设置时（非 mixed 且非 null）
  const shouldDisableScope =
    currentScope && currentScope !== 'mixed' && currentScope !== null;

  // 获取默认的 scope 值
  const getDefaultScope = (): ConfigScope => {
    if (isEdit && hookInfo) {
      return hookInfo.scope;
    }
    // 如果当前页面有明确的 scope 设置，使用该值；否则默认为 PROJECT
    return shouldDisableScope && currentScope
      ? (currentScope as ConfigScope)
      : ConfigScopeEnum.PROJECT;
  };

  const form = useForm<HookFormData>({
    resolver: zodResolver(hookFormSchema),
    defaultValues: {
      event: HookEventEnum.PreToolUse,
      scope: getDefaultScope(),
      hookType: 'command',
      matcher: '',
      command: '',
      prompt: '',
      timeout: '',
    },
    mode: 'onChange',
  });

  React.useEffect(() => {
    if (open && hookInfo) {
      // 编辑模式：使用现有数据填充表单
      const { event, scope, matcher, hook_config } = hookInfo;

      form.reset({
        event,
        scope,
        hookType: hook_config.type as HookType,
        matcher: matcher || '',
        command: hook_config.command || '',
        prompt: hook_config.prompt || '',
        timeout: hook_config.timeout?.toString() || '',
      });
    } else if (open && !hookInfo) {
      // 新增模式：重置为默认值，使用 currentScope 作为默认 scope
      form.reset({
        event: HookEventEnum.PreToolUse,
        scope: getDefaultScope(),
        hookType: 'command',
        matcher: '',
        command: '',
        prompt: '',
        timeout: '',
      });
    }
  }, [hookInfo, open, form, currentScope]);

  const handleSave = async (data: HookFormData) => {
    try {
      // 根据类型构建 HookConfig
      const hookConfig: HookConfig = {
        type: data.hookType,
      };

      if (data.hookType === 'command') {
        if (data.command) {
          hookConfig.command = data.command;
        }
      } else {
        if (data.prompt) {
          hookConfig.prompt = data.prompt;
        }
      }

      if (data.timeout) {
        const timeoutNum = parseInt(data.timeout, 10);
        if (!isNaN(timeoutNum)) {
          hookConfig.timeout = timeoutNum;
        }
      }

      await onSave({
        event: data.event as HookEvent,
        hook: hookConfig,
        matcher: data.matcher || undefined,
        scope: data.scope as ConfigScope,
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className='max-w-2xl max-h-[90vh] overflow-y-auto p-0'>
        <DialogHeader className='px-4 pt-4 pb-3 border-b'>
          <DialogTitle className='text-base font-semibold'>
            {isEdit ? t('hookDialog.editTitle') : t('hookDialog.addTitle')}
          </DialogTitle>
          <DialogDescription className='text-xs mt-0.5'>
            {t('hookDialog.description')}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSave)} className='space-y-0'>
            <div className='px-4 py-3 space-y-3'>
              {/* 基本信息行 - 使用更紧凑的布局 */}
              <div className='grid grid-cols-1 md:grid-cols-3 gap-3'>
                <FormField
                  control={form.control}
                  name='event'
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className='text-xs font-medium'>
                        {t('hookDialog.eventType')}
                      </FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        value={field.value}
                        disabled={isProcessing || isEdit}
                      >
                        <FormControl>
                          <SelectTrigger className='h-8 text-xs'>
                            <SelectValue
                              placeholder={t('hookDialog.eventTypePlaceholder')}
                            />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value={HookEventEnum.PreToolUse}>
                            {t('hookDialog.eventTypes.PreToolUse')}
                          </SelectItem>
                          <SelectItem value={HookEventEnum.PermissionRequest}>
                            {t('hookDialog.eventTypes.PermissionRequest')}
                          </SelectItem>
                          <SelectItem value={HookEventEnum.PostToolUse}>
                            {t('hookDialog.eventTypes.PostToolUse')}
                          </SelectItem>
                          <SelectItem value={HookEventEnum.Notification}>
                            {t('hookDialog.eventTypes.Notification')}
                          </SelectItem>
                          <SelectItem value={HookEventEnum.UserPromptSubmit}>
                            {t('hookDialog.eventTypes.UserPromptSubmit')}
                          </SelectItem>
                          <SelectItem value={HookEventEnum.Stop}>
                            {t('hookDialog.eventTypes.Stop')}
                          </SelectItem>
                          <SelectItem value={HookEventEnum.SubagentStop}>
                            {t('hookDialog.eventTypes.SubagentStop')}
                          </SelectItem>
                          <SelectItem value={HookEventEnum.PreCompact}>
                            {t('hookDialog.eventTypes.PreCompact')}
                          </SelectItem>
                          <SelectItem value={HookEventEnum.SessionStart}>
                            {t('hookDialog.eventTypes.SessionStart')}
                          </SelectItem>
                          <SelectItem value={HookEventEnum.SessionEnd}>
                            {t('hookDialog.eventTypes.SessionEnd')}
                          </SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                      {isEdit && (
                        <FormDescription className='text-[10px]'>
                          {t('hookDialog.editEventDisabled')}
                        </FormDescription>
                      )}
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name='scope'
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className='text-xs font-medium'>
                        {t('hookDialog.scope')}
                      </FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        value={field.value}
                        disabled={isProcessing || isEdit || shouldDisableScope || false}
                      >
                        <FormControl>
                          <SelectTrigger className='h-8 text-xs'>
                            <SelectValue
                              placeholder={t('hookDialog.scopePlaceholder')}
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
                      <FormMessage />
                      {(isEdit || shouldDisableScope) && (
                        <FormDescription className='text-[10px]'>
                          {shouldDisableScope && !isEdit
                            ? t('mcpServerDialog.scopeLockedByCurrentScope')
                            : t('hookDialog.editScopeDisabled')}
                        </FormDescription>
                      )}
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name='timeout'
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className='text-xs font-medium'>
                        {t('hookDialog.timeout')}
                      </FormLabel>
                      <FormControl>
                        <Input
                          type='number'
                          placeholder={t('hookDialog.timeoutPlaceholder')}
                          min='1'
                          disabled={isProcessing}
                          className='h-8 text-xs'
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                      <FormDescription className='text-[10px]'>
                        {t('hookDialog.timeoutDescription')}
                      </FormDescription>
                    </FormItem>
                  )}
                />
              </div>

              <Separator className='my-2' />

              {/* 匹配器 */}
              <FormField
                control={form.control}
                name='matcher'
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className='text-xs font-medium'>
                      {t('hookDialog.matcher')}
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder={t('hookDialog.matcherPlaceholder')}
                        disabled={isProcessing}
                        className='h-8 text-xs'
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                    <FormDescription className='text-[10px]'>
                      {t('hookDialog.matcherDescription')}
                    </FormDescription>
                  </FormItem>
                )}
              />

              <Separator className='my-2' />

              {/* Hook 类型选择和配置 */}
              <FormField
                control={form.control}
                name='hookType'
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className='text-xs font-medium'>
                      {t('hookDialog.hookType')}
                    </FormLabel>
                    <FormControl>
                      <Tabs
                        value={field.value}
                        onValueChange={value => field.onChange(value as HookType)}
                        className='w-full'
                      >
                        <TabsList className='grid w-full grid-cols-2 h-8'>
                          <TabsTrigger
                            value='command'
                            disabled={isProcessing}
                            className='text-xs'
                          >
                            {t('hookDialog.commandType')}
                          </TabsTrigger>
                          <TabsTrigger
                            value='prompt'
                            disabled={isProcessing}
                            className='text-xs'
                          >
                            {t('hookDialog.promptType')}
                          </TabsTrigger>
                        </TabsList>

                        {/* 命令类型配置 */}
                        <TabsContent value='command' className='space-y-3 mt-3'>
                          <FormField
                            control={form.control}
                            name='command'
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className='text-xs font-medium'>
                                  {t('hookDialog.executeCommand')}
                                </FormLabel>
                                <FormControl>
                                  <Textarea
                                    placeholder={t(
                                      'hookDialog.executeCommandPlaceholder'
                                    )}
                                    rows={4}
                                    disabled={isProcessing}
                                    className='font-mono text-xs'
                                    {...field}
                                  />
                                </FormControl>
                                <FormMessage />
                                <FormDescription className='text-[10px]'>
                                  {t('hookDialog.executeCommandDescription')}
                                </FormDescription>
                              </FormItem>
                            )}
                          />
                        </TabsContent>

                        {/* 提示类型配置 */}
                        <TabsContent value='prompt' className='space-y-3 mt-3'>
                          <FormField
                            control={form.control}
                            name='prompt'
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className='text-xs font-medium'>
                                  {t('hookDialog.llmPrompt')}
                                </FormLabel>
                                <FormControl>
                                  <Textarea
                                    placeholder={t('hookDialog.llmPromptPlaceholder')}
                                    rows={6}
                                    disabled={isProcessing}
                                    className='text-xs'
                                    {...field}
                                  />
                                </FormControl>
                                <FormMessage />
                                <FormDescription className='text-[10px]'>
                                  {t('hookDialog.llmPromptDescription')}
                                </FormDescription>
                              </FormItem>
                            )}
                          />
                        </TabsContent>
                      </Tabs>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
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
                {t('hookDialog.cancel')}
              </Button>
              <Button
                type='submit'
                disabled={isProcessing}
                className='h-8 px-3 text-xs'
              >
                <Save className='w-3.5 h-3.5 mr-1.5' />
                {isProcessing ? t('hookDialog.saving') : t('hookDialog.save')}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
