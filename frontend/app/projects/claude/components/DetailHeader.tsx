import React from 'react';
import {
  Brain,
  Server,
  Terminal,
  Bot,
  Zap,
  Package,
  Settings,
  BookOpen,
  Puzzle,
} from 'lucide-react';
import { useDetailHeader } from '../context/DetailHeaderContext';
import { useTranslation } from 'react-i18next';
import { ScopeSwitcher } from './ScopeSwitcher';
import { ConfigScope } from '@/api/types';

type ConfigSection =
  | 'memory'
  | 'mcpServers'
  | 'lspServers'
  | 'commands'
  | 'subAgents'
  | 'hooks'
  | 'skills'
  | 'plugins'
  | 'settings';

interface SectionConfig {
  title: string;
  description: string;
  icon: React.ReactNode;
  doc?: string;
}

interface DetailHeaderProps {
  selectedSection: ConfigSection;
  scope?: ConfigScope | 'mixed' | null;
  onScopeChange?: (scope: ConfigScope | 'mixed' | null) => void;
  enableScopeSwitcher?: boolean;
  supportedScopes?: (ConfigScope | 'mixed')[];
}

export function DetailHeader({
  selectedSection,
  scope = 'mixed',
  onScopeChange,
  enableScopeSwitcher: propEnableScopeSwitcher,
  supportedScopes: propSupportedScopes,
}: DetailHeaderProps) {
  const { t } = useTranslation('projects');
  const { rightContent, scopeSwitcher: contextScopeSwitcher } = useDetailHeader();

  // 优先使用 context 配置，否则使用 props
  const showScopeSwitcher =
    contextScopeSwitcher.enabled ?? propEnableScopeSwitcher ?? false;
  const supportedScopes = contextScopeSwitcher.supportedScopes ?? propSupportedScopes;
  const scopeValue = contextScopeSwitcher.value ?? scope;
  const scopeChangeHandler = contextScopeSwitcher.onChange ?? onScopeChange;

  // 获取配置项的所有信息
  const getSectionConfig = (section: ConfigSection): SectionConfig => {
    const configs: Record<ConfigSection, SectionConfig> = {
      memory: {
        title: t('header.memory.title'),
        description: t('header.memory.description'),
        icon: <Brain className='h-4 w-4' />,
        doc: 'https://code.claude.com/docs/en/memory',
      },
      mcpServers: {
        title: t('header.mcpServers.title'),
        description: t('header.mcpServers.description'),
        icon: <Server className='h-4 w-4' />,
        doc: 'https://code.claude.com/docs/en/mcp',
      },
      lspServers: {
        title: t('header.lspServers.title'),
        description: t('header.lspServers.description'),
        icon: <Server className='h-4 w-4' />,
        doc: 'https://code.claude.com/docs/en/plugins-reference#lsp-servers',
      },
      commands: {
        title: t('header.commands.title'),
        description: t('header.commands.description'),
        icon: <Terminal className='h-4 w-4' />,
        doc: 'https://code.claude.com/docs/en/slash-commands',
      },
      subAgents: {
        title: t('header.subAgents.title'),
        description: t('header.subAgents.description'),
        icon: <Bot className='h-4 w-4' />,
        doc: 'https://code.claude.com/docs/en/sub-agents',
      },
      hooks: {
        title: t('header.hooks.title'),
        description: t('header.hooks.description'),
        icon: <Zap className='h-4 w-4' />,
        doc: 'https://code.claude.com/docs/en/hooks',
      },
      skills: {
        title: t('header.skills.title'),
        description: t('header.skills.description'),
        icon: <Package className='h-4 w-4' />,
        doc: 'https://code.claude.com/docs/en/skills',
      },
      plugins: {
        title: t('header.plugins.title'),
        description: t('header.plugins.description'),
        icon: <Puzzle className='h-4 w-4' />,
        doc: 'https://code.claude.com/docs/en/plugins-reference',
      },
      settings: {
        title: t('header.settings.title'),
        description: t('header.settings.description'),
        icon: <Settings className='h-4 w-4' />,
        doc: 'https://code.claude.com/docs/en/settings',
      },
    };

    return configs[section] || configs.settings;
  };

  const config = getSectionConfig(selectedSection);

  const handleDocClick = () => {
    if (config.doc) {
      window.open(config.doc, '_blank');
    }
  };

  return (
    <div className='flex items-center gap-3'>
      <div className='p-2 bg-blue-50 text-blue-600 rounded-lg border border-blue-200'>
        {config.icon}
      </div>
      <div className='flex-1'>
        <div className='flex items-center gap-2 min-w-0'>
          <h2 className='text-xl font-bold text-gray-900 whitespace-nowrap'>
            {config.title}
          </h2>
          {config.doc && (
            <button
              onClick={handleDocClick}
              className='p-1.5 text-gray-500 bg-gray-100 hover:text-blue-600 hover:bg-blue-100 rounded-full transition-colors'
              title={config.doc}
            >
              <BookOpen className='h-3.5 w-3.5' />
            </button>
          )}
        </div>
        <p className='text-xs text-gray-600 font-medium mt-0.5'>{config.description}</p>
      </div>
      {/* 右侧控制区域：Scope 切换器和自定义内容 */}
      {(rightContent || showScopeSwitcher) && (
        <div className='flex flex-col items-center h-full'>
          {showScopeSwitcher && (
            <ScopeSwitcher
              value={scopeValue}
              onChange={scopeChangeHandler}
              supportedScopes={supportedScopes}
              className='ml-auto'
            />
          )}
          <div className='flex-1' />
          {rightContent && <div className='flex items-center'>{rightContent}</div>}
        </div>
      )}
    </div>
  );
}
