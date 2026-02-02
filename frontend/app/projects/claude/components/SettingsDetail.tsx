import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Settings, Save, RefreshCw, Globe, Shield, Cpu, Bot } from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import {
  loadClaudeSettings,
  updateClaudeSettingsValue,
  updateClaudeSettingsScope,
} from '@/api/api';
import { SwitchPreference } from '@/components/preference/SwitchPreference';
import { InputPreference } from '@/components/preference/InputPreference';
import { KVsPreference } from '@/components/preference/KVsPreference';
import { InputListPreference } from '@/components/preference/InputListPreference';
import { SelectPreference } from '@/components/preference/SelectPreference';
import { GroupWrapper } from '@/components/preference/GroupWrapper';
import { ScopeBadgeUpdater } from './ScopeBadgeUpdater';
import { useDetailHeader } from '../context/DetailHeaderContext';
import type { ClaudeSettingsInfoDTO } from '@/api/types';
import { ConfigScope } from '@/api/types';

interface SettingsDetailProps {
  projectId: number;
}

export function SettingsDetail({ projectId }: SettingsDetailProps) {
  const { setScopeSwitcher, clearScopeSwitcher } = useDetailHeader();

  // 使用 page 层级的翻译
  const { t } = useTranslation('projects');

  const [settingsInfo, setSettingsInfo] = useState<ClaudeSettingsInfoDTO | null>(null);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [selectedScope, setSelectedScope] = useState<ConfigScope | 'mixed' | null>(
    'mixed'
  );

  // 从扁平化的 settings 中获取值（优先级：local > project > user）
  const getValue = useCallback(
    <T extends string | boolean | number | string[] | Record<string, string> = string>(
      key: string
    ): T | undefined => {
      if (!settingsInfo) return undefined;
      return settingsInfo.settings[key]?.[0] as T;
    },
    [settingsInfo]
  );

  // 获取值及其作用域
  const getValueWithScope = useCallback(
    (key: string): [any, ConfigScope] | undefined => {
      if (!settingsInfo) return undefined;
      return settingsInfo.settings[key];
    },
    [settingsInfo]
  );

  // 从 env 列表中按作用域分组获取环境变量
  const getEnvByScope = useCallback(
    (scope: ConfigScope): Record<string, string> => {
      if (!settingsInfo) return {};
      const env: Record<string, string> = {};
      for (const [key, value, itemScope] of settingsInfo.env) {
        if (itemScope === scope) {
          env[key] = value;
        }
      }
      return env;
    },
    [settingsInfo]
  );

  // 获取所有作用域的环境变量（用于合并显示）
  const getEnv = useCallback((): Record<string, string> => {
    if (!settingsInfo) return {};
    const env: Record<string, string> = {};
    for (const [key, value] of settingsInfo.env) {
      env[key] = value;
    }
    return env;
  }, [settingsInfo]);

  // 权限模式选项
  const permissionModeOptions = [
    {
      value: 'default',
      label: t('detail.settings.permissions.modeConfig.defaultMode.options.default'),
      description: t(
        'detail.settings.permissions.modeConfig.defaultMode.options.defaultDescription'
      ),
    },
    {
      value: 'acceptEdits',
      label: t(
        'detail.settings.permissions.modeConfig.defaultMode.options.acceptEdits'
      ),
      description: t(
        'detail.settings.permissions.modeConfig.defaultMode.options.acceptEditsDescription'
      ),
    },
    {
      value: 'plan',
      label: t('detail.settings.permissions.modeConfig.defaultMode.options.plan'),
      description: t(
        'detail.settings.permissions.modeConfig.defaultMode.options.planDescription'
      ),
    },
    {
      value: 'bypassPermissions',
      label: t(
        'detail.settings.permissions.modeConfig.defaultMode.options.bypassPermissions'
      ),
      description: t(
        'detail.settings.permissions.modeConfig.defaultMode.options.bypassPermissionsDescription'
      ),
    },
  ];

  // 权限绕过模式选项
  const bypassPermissionModeOptions = [
    {
      value: 'disable',
      label: t(
        'detail.settings.permissions.modeConfig.disableBypassPermissionsMode.options.disable'
      ),
      description: t(
        'detail.settings.permissions.modeConfig.disableBypassPermissionsMode.options.disableDescription'
      ),
    },
  ];

  // 加载设置内容（根据 selectedScope 决定是否传 scope 参数）
  const loadSettingsContent = useCallback(async () => {
    if (!projectId) return;

    try {
      // 根据 selectedScope 决定是否传 scope 参数
      const request: { project_id: number; scope?: ConfigScope } = {
        project_id: projectId,
      };

      // 只有在选择了具体 scope 时才传递 scope 参数
      if (selectedScope && selectedScope !== 'mixed') {
        request.scope = selectedScope;
      }

      const response = await loadClaudeSettings(request);

      if (response.success && response.data) {
        setSettingsInfo(response.data);
      } else {
        setSettingsInfo(null);
        toast.warning(t('detail.settings.settingsNotFound'));
      }
    } catch (error) {
      console.error('加载设置失败:', error);
      toast.error(t('detail.settings.loadFailed'), {
        description:
          error instanceof Error ? error.message : t('detail.settings.unknownError'),
      });
      setSettingsInfo(null);
    }
  }, [projectId, selectedScope]);

  // 更新设置值（使用当前选中的 scope）
  const updateSetting = useCallback(
    async (
      key: string,
      value: string,
      valueType: 'string' | 'boolean' | 'integer' | 'array' | 'object' | 'dict',
      scope?: ConfigScope
    ): Promise<boolean> => {
      if (!projectId) return false;

      // 如果没有传入 scope，使用当前选中的 scope
      // 如果是 mixed 模式，默认使用 LOCAL
      const targetScope =
        scope ||
        (selectedScope && selectedScope !== 'mixed'
          ? selectedScope
          : ConfigScope.LOCAL);

      setIsUpdating(true);
      try {
        const response = await updateClaudeSettingsValue({
          project_id: projectId,
          scope: targetScope,
          key,
          value,
          value_type: valueType,
        });

        if (response.success) {
          // 重新加载设置以获取最新值
          await loadSettingsContent();
          return true;
        } else {
          toast.error(t('detail.settings.updateFailed'), {
            description: response.error || t('detail.settings.unknownError'),
          });
          return false;
        }
      } catch (error) {
        console.error('更新设置失败:', error);
        toast.error(t('detail.settings.updateFailed'), {
          description:
            error instanceof Error ? error.message : t('detail.settings.unknownError'),
        });
        return false;
      } finally {
        setIsUpdating(false);
      }
    },
    [projectId, loadSettingsContent, selectedScope]
  );

  // 处理设置项作用域切换
  const handleSettingScopeChange = useCallback(
    async (settingKey: string, oldScope: ConfigScope, newScope: ConfigScope) => {
      if (!projectId) return;

      try {
        const response = await updateClaudeSettingsScope({
          project_id: projectId,
          old_scope: oldScope,
          new_scope: newScope,
          key: settingKey,
        });

        if (response.success) {
          toast.success(t('detail.scopeBadge.scopeMoved', { scope: newScope }));
          await loadSettingsContent();
        } else {
          toast.error(t('detail.scopeBadge.moveScopeFailed'), {
            description: response.error || t('detail.scopeBadge.unknownError'),
          });
        }
      } catch (error) {
        console.error('更新作用域失败:', error);
        toast.error(t('detail.scopeBadge.moveScopeFailed'), {
          description:
            error instanceof Error
              ? error.message
              : t('detail.scopeBadge.unknownError'),
        });
      }
    },
    [projectId, loadSettingsContent, t]
  );

  // 初始加载设置
  useEffect(() => {
    loadSettingsContent();
  }, [loadSettingsContent]);

  // 配置 Scope Switcher
  useEffect(() => {
    setScopeSwitcher({
      enabled: true,
      supportedScopes: [
        'mixed',
        ConfigScope.USER,
        ConfigScope.PROJECT,
        ConfigScope.LOCAL,
      ],
      value: selectedScope,
      onChange: setSelectedScope,
    });

    return () => {
      clearScopeSwitcher();
    };
  }, [selectedScope, setScopeSwitcher, clearScopeSwitcher]);

  // 判断是否应该显示 Scope Badge（只有在 mixed 模式下才显示）
  const shouldShowScopeBadge = useMemo(() => {
    return selectedScope === 'mixed' || !selectedScope;
  }, [selectedScope]);

  // 创建带 ScopeBadgeUpdater 的 prefix 的辅助函数
  const createScopePrefix = useCallback(
    (settingKey: string) => {
      if (!shouldShowScopeBadge) return undefined;
      return (
        <ScopeBadgeUpdater
          currentScope={getValueWithScope(settingKey)?.[1]}
          onScopeChange={(oldScope, newScope) =>
            handleSettingScopeChange(settingKey, oldScope, newScope)
          }
        />
      );
    },
    [shouldShowScopeBadge, getValueWithScope, handleSettingScopeChange]
  );

  // 渲染环境变量设置（根据 selectedScope 决定显示哪个 scope 的 env）
  const renderEnvironmentSettings = () => {
    // 如果是 mixed 模式，显示所有 scope 的 env
    const showAllScopes = !selectedScope || selectedScope === 'mixed';

    return (
      <div className='space-y-6'>
        <h3 className='text-lg font-medium flex items-center gap-2'>
          <Cpu className='h-5 w-5' />
          {t('detail.settings.environment.title')}
        </h3>
        <p className='text-sm text-gray-500'>
          {t('detail.settings.environment.description')}
          {!showAllScopes &&
            selectedScope &&
            ` ${t('detail.settings.environment.currentScope', { scope: selectedScope })}`}
        </p>

        <div className='space-y-6'>
          {/* User 作用域 */}
          {(showAllScopes || selectedScope === ConfigScope.USER) && (
            <div className='border rounded-lg p-4 bg-gray-50'>
              <KVsPreference
                title={
                  <div className='flex items-center gap-2'>
                    <Globe className='h-4 w-4 text-blue-500' />
                    <span className='truncate'>
                      {t('detail.settings.environment.user.title')}(
                      {t('detail.settings.environment.user.path')})
                    </span>
                  </div>
                }
                description={t('detail.settings.environment.user.description')}
                value={getEnvByScope(ConfigScope.USER)}
                settingKey='env'
                onSettingChange={(key, value) =>
                  updateSetting(key, value, 'dict', ConfigScope.USER)
                }
                disabled={isUpdating}
                keyPlaceholder={t('detail.settings.environment.user.keyPlaceholder')}
                valuePlaceholder={t(
                  'detail.settings.environment.user.valuePlaceholder'
                )}
                keyValidator={key => {
                  if (!key.trim())
                    return t('detail.settings.environment.user.validation.emptyName');
                  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
                    return t('detail.settings.environment.user.validation.invalidName');
                  }
                  return null;
                }}
              />
            </div>
          )}

          {/* Project 作用域 */}
          {(showAllScopes || selectedScope === ConfigScope.PROJECT) && (
            <div className='border rounded-lg p-4 bg-blue-50'>
              <KVsPreference
                title={
                  <div className='flex items-center gap-2'>
                    <Shield className='h-4 w-4 text-blue-600' />
                    <span className='truncate'>
                      {t('detail.settings.environment.project.title')}(
                      {t('detail.settings.environment.project.path')})
                    </span>
                  </div>
                }
                description={t('detail.settings.environment.project.description')}
                value={getEnvByScope(ConfigScope.PROJECT)}
                settingKey='env'
                onSettingChange={(key, value) =>
                  updateSetting(key, value, 'dict', ConfigScope.PROJECT)
                }
                disabled={isUpdating}
                keyPlaceholder={t('detail.settings.environment.project.keyPlaceholder')}
                valuePlaceholder={t(
                  'detail.settings.environment.project.valuePlaceholder'
                )}
                keyValidator={key => {
                  if (!key.trim())
                    return t(
                      'detail.settings.environment.project.validation.emptyName'
                    );
                  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
                    return t(
                      'detail.settings.environment.project.validation.invalidName'
                    );
                  }
                  return null;
                }}
              />
            </div>
          )}

          {/* Local 作用域 */}
          {(showAllScopes || selectedScope === ConfigScope.LOCAL) && (
            <div className='border rounded-lg p-4 bg-green-50'>
              <KVsPreference
                title={
                  <div className='flex items-center gap-2'>
                    <Shield className='h-4 w-4 text-green-600' />
                    <span className='truncate'>
                      {t('detail.settings.environment.local.title')}(
                      {t('detail.settings.environment.local.path')})
                    </span>
                  </div>
                }
                description={t('detail.settings.environment.local.description')}
                value={getEnvByScope(ConfigScope.LOCAL)}
                settingKey='env'
                onSettingChange={(key, value) =>
                  updateSetting(key, value, 'dict', ConfigScope.LOCAL)
                }
                disabled={isUpdating}
                keyPlaceholder={t('detail.settings.environment.local.keyPlaceholder')}
                valuePlaceholder={t(
                  'detail.settings.environment.local.valuePlaceholder'
                )}
                keyValidator={key => {
                  if (!key.trim())
                    return t('detail.settings.environment.local.validation.emptyName');
                  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
                    return t(
                      'detail.settings.environment.local.validation.invalidName'
                    );
                  }
                  return null;
                }}
              />
            </div>
          )}
        </div>
      </div>
    );
  };

  // 渲染基础设置
  const renderBasicSettings = () => {
    return (
      <div className='space-y-6'>
        <h3 className='text-lg font-medium flex items-center gap-2'>
          <Settings className='h-5 w-5' />
          {t('detail.settings.basic.title')}
        </h3>

        <div className='space-y-4'>
          {/* Model 设置 */}
          <InputPreference
            title='model'
            description={t('detail.settings.basic.model.description')}
            value={(getValue<string>('model') as string) || ''}
            settingKey='model'
            onSettingChange={(key, value) => updateSetting(key, value, 'string')}
            placeholder={t('detail.settings.basic.model.placeholder')}
            disabled={isUpdating}
            leftIcon={<Bot className='w-4 h-4' />}
            prefix={createScopePrefix('model')}
          />

          {/* Always Thinking Enabled */}
          <SwitchPreference
            title='alwaysThinkingEnabled'
            description={t('detail.settings.basic.alwaysThinkingEnabled.description')}
            checked={(getValue<boolean>('alwaysThinkingEnabled') as boolean) ?? false}
            settingKey='alwaysThinkingEnabled'
            onSettingChange={(key, value) => updateSetting(key, value, 'boolean')}
            disabled={isUpdating}
            prefix={createScopePrefix('alwaysThinkingEnabled')}
          />
        </div>
      </div>
    );
  };

  // 渲染权限设置
  const renderPermissionSettings = () => {
    return (
      <GroupWrapper
        title={
          <div className='flex items-center justify-between w-full'>
            <div className='flex items-center gap-2'>
              <Shield className='h-5 w-5' />
              <span>{t('detail.settings.permissions.title')}</span>
            </div>
          </div>
        }
        subtitle={t('detail.settings.permissions.subtitle')}
      >
        <div className='space-y-6'>
          {/* 权限控制列表 */}
          <div className='space-y-4'>
            <h4 className='text-md font-medium text-gray-700 border-b border-gray-100 pb-2'>
              {t('detail.settings.permissions.controlList.title')}
            </h4>
            <p className='text-sm text-gray-500 mb-3'>
              {t('detail.settings.permissions.controlList.description')}
            </p>

            <InputListPreference
              title='allow'
              description={t(
                'detail.settings.permissions.controlList.allow.description'
              )}
              value={getValue('permissions.allow') || []}
              settingKey='permissions.allow'
              onSettingChange={(key, value) => updateSetting(key, value, 'array')}
              placeholder={t(
                'detail.settings.permissions.controlList.allow.placeholder'
              )}
              prefix={createScopePrefix('permissions.allow')}
            />

            <InputListPreference
              title='ask'
              description={t('detail.settings.permissions.controlList.ask.description')}
              value={getValue('permissions.ask') || []}
              settingKey='permissions.ask'
              onSettingChange={(key, value) => updateSetting(key, value, 'array')}
              placeholder={t('detail.settings.permissions.controlList.ask.placeholder')}
              prefix={createScopePrefix('permissions.ask')}
            />

            <InputListPreference
              title='deny'
              description={t(
                'detail.settings.permissions.controlList.deny.description'
              )}
              value={getValue('permissions.deny') || []}
              settingKey='permissions.deny'
              onSettingChange={(key, value) => updateSetting(key, value, 'array')}
              placeholder={t(
                'detail.settings.permissions.controlList.deny.placeholder'
              )}
              prefix={createScopePrefix('permissions.deny')}
            />
          </div>

          {/* 权限模式设置 */}
          <div className='space-y-4'>
            <h4 className='text-md font-medium text-gray-700 border-b border-gray-100 pb-2'>
              {t('detail.settings.permissions.modeConfig.title')}
            </h4>
            <p className='text-sm text-gray-500 mb-3'>
              {t('detail.settings.permissions.modeConfig.description')}
            </p>

            <SelectPreference
              title='defaultMode'
              description={t(
                'detail.settings.permissions.modeConfig.defaultMode.description'
              )}
              value={getValue('permissions.defaultMode') || ''}
              settingKey='permissions.defaultMode'
              onSettingChange={(key, value) => updateSetting(key, value, 'string')}
              options={permissionModeOptions}
              placeholder={t(
                'detail.settings.permissions.modeConfig.defaultMode.placeholder'
              )}
              allowEmpty={true}
              emptyLabel={t(
                'detail.settings.permissions.modeConfig.defaultMode.notSet'
              )}
              infoLink='https://code.claude.com/docs/en/iam#permission-modes'
              prefix={createScopePrefix('permissions.defaultMode')}
            />

            <SelectPreference
              title='disableBypassPermissionsMode'
              description={t(
                'detail.settings.permissions.modeConfig.disableBypassPermissionsMode.description'
              )}
              value={getValue('permissions.disableBypassPermissionsMode') || ''}
              settingKey='permissions.disableBypassPermissionsMode'
              onSettingChange={(key, value) => updateSetting(key, value, 'string')}
              options={bypassPermissionModeOptions}
              placeholder={t(
                'detail.settings.permissions.modeConfig.disableBypassPermissionsMode.placeholder'
              )}
              allowEmpty={true}
              emptyLabel={t(
                'detail.settings.permissions.modeConfig.disableBypassPermissionsMode.notSet'
              )}
              prefix={createScopePrefix('permissions.disableBypassPermissionsMode')}
            />
          </div>

          {/* 附加目录设置 */}
          <div className='space-y-4'>
            <h4 className='text-md font-medium text-gray-700 border-b border-gray-100 pb-2'>
              {t('detail.settings.permissions.additionalDirectories.title')}
            </h4>
            <p className='text-sm text-gray-500 mb-3'>
              {t('detail.settings.permissions.additionalDirectories.description')}
            </p>

            <InputListPreference
              title='additionalDirectories'
              description={t(
                'detail.settings.permissions.additionalDirectories.description2'
              )}
              value={getValue('permissions.additionalDirectories') || []}
              settingKey='permissions.additionalDirectories'
              onSettingChange={(key, value) => updateSetting(key, value, 'array')}
              placeholder={t(
                'detail.settings.permissions.additionalDirectories.placeholder'
              )}
              prefix={createScopePrefix('permissions.additionalDirectories')}
            />
          </div>
        </div>
      </GroupWrapper>
    );
  };

  // 渲染沙盒设置
  const renderSandboxSettings = () => {
    const isSandboxEnabled = (getValue<boolean>('sandbox.enabled') as boolean) ?? false;

    return (
      <GroupWrapper
        title={
          <div className='flex items-center justify-between w-full'>
            <div className='flex items-center gap-2'>
              <Shield className='h-5 w-5' />
              <span>{t('detail.settings.sandbox.title')}</span>
            </div>
          </div>
        }
        subtitle={t('detail.settings.sandbox.subtitle')}
      >
        <div className='space-y-6'>
          {/* 沙盒启用控制 */}
          <div className='space-y-4'>
            <SwitchPreference
              title='enabled'
              description={t('detail.settings.sandbox.enabled.description')}
              checked={isSandboxEnabled}
              settingKey='sandbox.enabled'
              onSettingChange={(key, value) => updateSetting(key, value, 'boolean')}
              disabled={isUpdating}
              prefix={createScopePrefix('sandbox.enabled')}
            />
          </div>

          {/* 沙盒详细设置 - 仅在启用沙盒时显示 */}
          {isSandboxEnabled && (
            <>
              {/* 沙盒启用提示 */}
              <div className='bg-blue-50 border border-blue-200 rounded-md p-3'>
                <p className='text-sm text-blue-800'>
                  {t('detail.settings.sandbox.enabledMessage')}
                </p>
              </div>

              {/* 命令执行控制 */}
              <div className='space-y-4'>
                <h4 className='text-md font-medium text-gray-700 border-b border-gray-100 pb-2'>
                  {t('detail.settings.sandbox.commandControl.title')}
                </h4>
                <p className='text-sm text-gray-500 mb-3'>
                  {t('detail.settings.sandbox.commandControl.description')}
                </p>

                <SwitchPreference
                  title='autoAllowBashIfSandboxed'
                  description={t(
                    'detail.settings.sandbox.commandControl.autoAllowBashIfSandboxed.description'
                  )}
                  checked={getValue('sandbox.autoAllowBashIfSandboxed') || false}
                  settingKey='sandbox.autoAllowBashIfSandboxed'
                  onSettingChange={(key, value) => updateSetting(key, value, 'boolean')}
                  disabled={isUpdating}
                  prefix={createScopePrefix('sandbox.autoAllowBashIfSandboxed')}
                />

                <SwitchPreference
                  title='allowUnsandboxedCommands'
                  description={t(
                    'detail.settings.sandbox.commandControl.allowUnsandboxedCommands.description'
                  )}
                  checked={getValue('sandbox.allowUnsandboxedCommands') || false}
                  settingKey='sandbox.allowUnsandboxedCommands'
                  onSettingChange={(key, value) => updateSetting(key, value, 'boolean')}
                  disabled={isUpdating}
                  prefix={createScopePrefix('sandbox.allowUnsandboxedCommands')}
                />

                <SwitchPreference
                  title='enableWeakerNestedSandbox'
                  description={t(
                    'detail.settings.sandbox.commandControl.enableWeakerNestedSandbox.description'
                  )}
                  checked={getValue('sandbox.enableWeakerNestedSandbox') || false}
                  settingKey='sandbox.enableWeakerNestedSandbox'
                  onSettingChange={(key, value) => updateSetting(key, value, 'boolean')}
                  disabled={isUpdating}
                  prefix={createScopePrefix('sandbox.enableWeakerNestedSandbox')}
                />
              </div>

              {/* 排除命令列表 */}
              <div className='space-y-4'>
                <h4 className='text-md font-medium text-gray-700 border-b border-gray-100 pb-2'>
                  {t('detail.settings.sandbox.excludedCommands.title')}
                </h4>
                <p className='text-sm text-gray-500 mb-3'>
                  {t('detail.settings.sandbox.excludedCommands.description')}
                </p>

                <InputListPreference
                  title='excludedCommands'
                  description={t(
                    'detail.settings.sandbox.excludedCommands.description2'
                  )}
                  value={getValue('sandbox.excludedCommands') || []}
                  settingKey='sandbox.excludedCommands'
                  onSettingChange={(key, value) => updateSetting(key, value, 'array')}
                  placeholder={t(
                    'detail.settings.sandbox.excludedCommands.placeholder'
                  )}
                  validator={value => {
                    if (!value.trim())
                      return t(
                        'detail.settings.sandbox.excludedCommands.validation.emptyName'
                      );
                    // 简单的命令名称验证
                    if (!value.match(/^[a-zA-Z0-9_-]+$/)) {
                      return t(
                        'detail.settings.sandbox.excludedCommands.validation.invalidName'
                      );
                    }
                    return null;
                  }}
                  prefix={createScopePrefix('sandbox.excludedCommands')}
                />
              </div>

              {/* 网络设置 */}
              <GroupWrapper
                title={
                  <div className='flex items-center gap-2'>
                    <span>{t('detail.settings.sandbox.network.title')}</span>
                  </div>
                }
                subtitle={t('detail.settings.sandbox.network.subtitle')}
              >
                <div className='space-y-6'>
                  {/* 网络基础控制 */}
                  <div className='space-y-4'>
                    <h5 className='text-sm font-medium text-gray-600'>
                      {t('detail.settings.sandbox.network.basicControl.title')}
                    </h5>

                    <SwitchPreference
                      title='allowLocalBinding'
                      description={t(
                        'detail.settings.sandbox.network.basicControl.allowLocalBinding.description'
                      )}
                      checked={getValue('sandbox.network.allowLocalBinding') || false}
                      settingKey='sandbox.network.allowLocalBinding'
                      onSettingChange={(key, value) =>
                        updateSetting(key, value, 'boolean')
                      }
                      disabled={isUpdating}
                      prefix={createScopePrefix('sandbox.network.allowLocalBinding')}
                    />
                  </div>

                  {/* 代理配置 */}
                  <div className='space-y-4'>
                    <h5 className='text-sm font-medium text-gray-600'>
                      {t('detail.settings.sandbox.network.proxyConfig.title')}
                    </h5>

                    <InputPreference
                      title='httpProxyPort'
                      description={t(
                        'detail.settings.sandbox.network.proxyConfig.httpProxyPort.description'
                      )}
                      value={
                        getValue('sandbox.network.httpProxyPort')?.toString() || ''
                      }
                      settingKey='sandbox.network.httpProxyPort'
                      onSettingChange={(key, value) =>
                        updateSetting(key, value, 'integer')
                      }
                      type='number'
                      leftIcon={<Shield className='w-4 h-4' />}
                      prefix={createScopePrefix('sandbox.network.httpProxyPort')}
                    />

                    <InputPreference
                      title='socksProxyPort'
                      description={t(
                        'detail.settings.sandbox.network.proxyConfig.socksProxyPort.description'
                      )}
                      value={
                        getValue('sandbox.network.socksProxyPort')?.toString() || ''
                      }
                      settingKey='sandbox.network.socksProxyPort'
                      onSettingChange={(key, value) =>
                        updateSetting(key, value, 'integer')
                      }
                      type='number'
                      leftIcon={<Shield className='w-4 h-4' />}
                      prefix={createScopePrefix('sandbox.network.socksProxyPort')}
                    />
                  </div>

                  {/* Unix 套接字 */}
                  <div className='space-y-4'>
                    <h5 className='text-sm font-medium text-gray-600'>
                      {t('detail.settings.sandbox.network.unixSocket.title')}
                    </h5>

                    <InputListPreference
                      title='allowUnixSockets'
                      description={t(
                        'detail.settings.sandbox.network.unixSocket.allowUnixSockets.description'
                      )}
                      value={getValue('sandbox.network.allowUnixSockets') || []}
                      settingKey='sandbox.network.allowUnixSockets'
                      onSettingChange={(key, value) =>
                        updateSetting(key, value, 'array')
                      }
                      placeholder={t(
                        'detail.settings.sandbox.network.unixSocket.allowUnixSockets.placeholder'
                      )}
                      validator={value => {
                        if (!value.trim())
                          return t(
                            'detail.settings.sandbox.network.unixSocket.validation.emptyPath'
                          );
                        // Unix 套接字路径验证
                        if (!value.match(/^\/.+\.sock$/)) {
                          return t(
                            'detail.settings.sandbox.network.unixSocket.validation.invalidPath'
                          );
                        }
                        return null;
                      }}
                      prefix={createScopePrefix('sandbox.network.allowUnixSockets')}
                    />
                  </div>
                </div>
              </GroupWrapper>
            </>
          )}

          {/* 沙盒未启用时的提示 */}
          {!isSandboxEnabled && (
            <div className='space-y-4'>
              <h4 className='text-md font-medium text-gray-700 border-b border-gray-100 pb-2'>
                {t('detail.settings.sandbox.notEnabledTitle')}
              </h4>
              <p className='text-sm text-gray-500 mb-3'>
                {t('detail.settings.sandbox.notEnabledDescription')}
              </p>

              <div className='bg-gray-50 border border-gray-200 rounded-md p-4'>
                <div className='flex items-center gap-2 mb-2'>
                  <Shield className='h-4 w-4 text-gray-500' />
                  <p className='text-sm font-medium text-gray-700'>
                    {t('detail.settings.sandbox.notEnabledMessage')}
                  </p>
                </div>
                <p className='text-sm text-gray-600'>
                  {t('detail.settings.sandbox.notEnabledDetail')}
                </p>
              </div>
            </div>
          )}
        </div>
      </GroupWrapper>
    );
  };

  return (
    <div className='p-4'>
      <div className='space-y-8'>
        {renderEnvironmentSettings()}
        {renderBasicSettings()}
        {renderPermissionSettings()}
        {renderSandboxSettings()}
      </div>

      {/* 更新状态指示器 */}
      {isUpdating && (
        <div className='fixed bottom-4 right-4 bg-blue-600 text-white px-4 py-2 rounded-md shadow-lg flex items-center gap-2'>
          <RefreshCw className='w-4 h-4 animate-spin' />
          {t('detail.settings.updating')}
        </div>
      )}
    </div>
  );
}
