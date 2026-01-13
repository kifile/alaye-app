'use client';

import { useEffect, useState } from 'react';
import { FileSelectPreference } from '@/components/preference/FileSelectPreference';
import { SelectPreference } from '@/components/preference/SelectPreference';
import { SwitchPreference } from '@/components/preference/SwitchPreference';
import { loadSettings, updateSetting, type LoadSettingsData } from '@/api/api';
import { useAnalytics } from '@/components/analytics';
import { Loader2, Settings as SettingsIcon } from 'lucide-react';
import { toast } from 'sonner';
import log from '@/lib/log';
import { useTranslation } from 'react-i18next';
import {
  changeLanguage,
  loadAllPageTranslations,
  type SupportedLanguage,
} from '@/lib/i18n';

export default function SettingsPage() {
  const { t } = useTranslation('settings'); // 使用 settings 命名空间
  const { enableAnalytics, disableAnalytics } = useAnalytics();
  const [settings, setSettings] = useState({
    'app.language': 'en',
    'npm.path': '',
    'npm.enable': '',
    'npm.version': '',
    'claude.path': '',
    'claude.enable': '',
    'claude.version': '',
    'analytics.enabled': 'false',
  });
  const [loading, setLoading] = useState(true);
  const [translationsLoaded, setTranslationsLoaded] = useState(false);

  // 加载配置
  const loadConfiguration = async () => {
    try {
      setLoading(true);

      // 首先加载页面的翻译文件
      if (!translationsLoaded) {
        await loadAllPageTranslations('settings');
        setTranslationsLoaded(true);
      }

      const response = await loadSettings();

      if (response.success && response.data) {
        const data = response.data as LoadSettingsData;
        setSettings({
          'app.language': data.settings['app.language'] || 'en',
          'npm.path': data.settings['npm.path'] || '',
          'npm.enable': data.settings['npm.enable'] || '',
          'npm.version': data.settings['npm.version'] || '',
          'claude.path': data.settings['claude.path'] || '',
          'claude.enable': data.settings['claude.enable'] || '',
          'claude.version': data.settings['claude.version'] || '',
          'analytics.enabled': data.settings['analytics.enabled'] || 'false',
        });
      }
    } catch (error) {
      console.error('加载配置失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 组件挂载时加载配置
  useEffect(() => {
    loadConfiguration();
  }, []);

  // 更新配置值
  const updateSettingValue = async (key: string, value: string): Promise<boolean> => {
    try {
      const response = await updateSetting({
        key,
        value,
      });

      if (response.success) {
        // 如果是语言切换，立即更新 i18n
        if (key === 'app.language') {
          await changeLanguage(value as SupportedLanguage);
        }

        // 如果是分析开关切换，使用 context 的方法
        if (key === 'analytics.enabled') {
          const isEnabled = value.toLowerCase() === 'true';
          if (isEnabled) {
            await enableAnalytics();
          } else {
            await disableAnalytics();
          }
        }

        // 保存成功，重新加载配置
        await loadConfiguration();
        toast.success(t('configSaveSuccess'));
        return true;
      } else {
        log.error(`保存配置失败: ${response.error}`);
        toast.error(t('configSaveFailed', { error: response.error }));
        return false;
      }
    } catch (error) {
      log.error(`保存配置失败: ${error}`);
      toast.error(t('configSaveRetry'));
      return false;
    }
  };

  // 获取 NPM 描述信息
  const getNpmDescription = () => {
    const isEnabled = settings['npm.enable']?.toLowerCase() === 'true';
    const version = settings['npm.version'];

    if (!isEnabled) {
      return (
        <span>
          {t('npmNotInstalled')}
          <a
            href='https://nodejs.org/en/download'
            target='_blank'
            rel='noopener noreferrer'
            className='text-blue-600 hover:text-blue-800 underline'
          >
            {t('nodejsWebsite')}
          </a>
        </span>
      );
    }

    return version ? t('npmInstalled', { version }) : t('npmInstalledSimple');
  };

  // 获取 Claude 描述信息
  const getClaudeDescription = () => {
    const isEnabled = settings['claude.enable']?.toLowerCase() === 'true';
    const version = settings['claude.version'];

    if (!isEnabled) {
      return (
        <span>
          {t('claudeNotInstalled')}
          <a
            href='https://claude.com/product/claude-code'
            target='_blank'
            rel='noopener noreferrer'
            className='text-blue-600 hover:text-blue-800 underline'
          >
            {t('claudeWebsite')}
          </a>
        </span>
      );
    }

    return version ? t('claudeInstalled', { version }) : t('claudeInstalledSimple');
  };

  return (
    <div className='container mx-auto px-4 py-6 max-w-2xl'>
      <div className='space-y-6'>
        {/* 页面标题 */}
        <div className='flex items-center gap-3'>
          <SettingsIcon className='w-6 h-6 text-primary' />
          <h1 className='text-2xl font-semibold'>{t('title')}</h1>
          {loading && (
            <div className='ml-auto'>
              <Loader2 className='w-5 h-5 animate-spin text-muted-foreground' />
            </div>
          )}
        </div>

        {/* 配置项列表 */}
        <div className='space-y-4'>
          <FileSelectPreference
            title={t('npmPath')}
            description={getNpmDescription()}
            value={settings['npm.path']}
            settingKey='npm.path'
            onSettingChange={updateSettingValue}
            placeholder={t('selectNpmExecutable')}
            disabled={loading}
            hasError={!loading && settings['npm.enable']?.toLowerCase() !== 'true'}
            errorMessage={t('toolNotConfigured')}
            savingMessage={t('savingConfig')}
            saveFailedMessage={t('saveFailedRetry')}
          />

          <FileSelectPreference
            title={t('claudePath')}
            description={getClaudeDescription()}
            value={settings['claude.path']}
            settingKey='claude.path'
            onSettingChange={updateSettingValue}
            placeholder={t('selectClaudeApp')}
            disabled={loading}
            hasError={!loading && settings['claude.enable']?.toLowerCase() !== 'true'}
            errorMessage={t('toolNotConfigured')}
            savingMessage={t('savingConfig')}
            saveFailedMessage={t('saveFailedRetry')}
          />

          <SelectPreference
            title={t('language')}
            description={t('languageDescription')}
            value={settings['app.language']}
            settingKey='app.language'
            onSettingChange={updateSettingValue}
            disabled={loading}
            options={[
              { value: 'en', label: 'English' },
              { value: 'zh', label: '中文' },
            ]}
          />

          <SwitchPreference
            title={t('analytics')}
            description={t('analyticsDescription')}
            checked={settings['analytics.enabled']?.toLowerCase() === 'true'}
            settingKey='analytics.enabled'
            onSettingChange={updateSettingValue}
            disabled={loading}
          />
        </div>
      </div>
    </div>
  );
}
