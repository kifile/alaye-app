import React from 'react';
import { cn } from '@/lib/utils';
import {
  Brain,
  Server,
  Terminal,
  Bot,
  Zap,
  Package,
  Settings,
  Puzzle,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';

type ConfigSection =
  | 'memory'
  | 'plugins'
  | 'mcpServers'
  | 'lspServers'
  | 'commands'
  | 'subAgents'
  | 'hooks'
  | 'skills'
  | 'settings';

interface ClaudeConfigSideBarProps {
  selectedSection: ConfigSection;
  onSectionSelect: (section: ConfigSection) => void;
}

export function ClaudeConfigSideBar({
  selectedSection,
  onSectionSelect,
}: ClaudeConfigSideBarProps) {
  const { t } = useTranslation('projects');

  const getSections = () => [
    {
      key: 'memory' as const,
      title: t('sidebar.sections.memory.title'),
      icon: <Brain className='h-3 w-3' />,
      description: t('sidebar.sections.memory.description'),
      color: 'text-violet-600 bg-violet-100 border-violet-200',
    },
    {
      key: 'plugins' as const,
      title: t('sidebar.sections.plugins.title'),
      icon: <Puzzle className='h-3 w-3' />,
      description: t('sidebar.sections.plugins.description'),
      color: 'text-teal-600 bg-teal-100 border-teal-200',
      docsUrl: 'https://code.claude.com/docs/en/plugins-reference',
    },
    {
      key: 'commands' as const,
      title: t('sidebar.sections.commands.title'),
      icon: <Terminal className='h-3 w-3' />,
      description: t('sidebar.sections.commands.description'),
      color: 'text-green-600 bg-green-100 border-green-200',
    },
    {
      key: 'subAgents' as const,
      title: t('sidebar.sections.subAgents.title'),
      icon: <Bot className='h-3 w-3' />,
      description: t('sidebar.sections.subAgents.description'),
      color: 'text-purple-600 bg-purple-100 border-purple-200',
    },
    {
      key: 'skills' as const,
      title: t('sidebar.sections.skills.title'),
      icon: <Package className='h-3 w-3' />,
      description: t('sidebar.sections.skills.description'),
      color: 'text-pink-600 bg-pink-100 border-pink-200',
    },
    {
      key: 'mcpServers' as const,
      title: t('sidebar.sections.mcpServers.title'),
      icon: <Server className='h-3 w-3' />,
      description: t('sidebar.sections.mcpServers.description'),
      color: 'text-blue-600 bg-blue-100 border-blue-200',
    },
    {
      key: 'lspServers' as const,
      title: t('sidebar.sections.lspServers.title'),
      icon: <Server className='h-3 w-3' />,
      description: t('sidebar.sections.lspServers.description'),
      color: 'text-cyan-600 bg-cyan-100 border-cyan-200',
    },
    {
      key: 'hooks' as const,
      title: t('sidebar.sections.hooks.title'),
      icon: <Zap className='h-3 w-3' />,
      description: t('sidebar.sections.hooks.description'),
      color: 'text-orange-600 bg-orange-100 border-orange-200',
    },
    {
      key: 'settings' as const,
      title: t('sidebar.sections.settings.title'),
      icon: <Settings className='h-3 w-3' />,
      description: t('sidebar.sections.settings.description'),
      color: 'text-gray-600 bg-gray-100 border-gray-200',
    },
  ];

  const sections = getSections();

  return (
    <div className='bg-white border border-gray-200/60 shadow-sm h-full overflow-hidden'>
      {/* 侧边栏头部 */}
      <div className='border-b border-gray-200/60 px-3 py-2.5 bg-gray-50/30'>
        <h3 className='font-semibold text-gray-900 text-sm'>{t('sidebar.title')}</h3>
      </div>

      {/* 配置项列表 */}
      <div className='p-1.5 space-y-0.5 h-[calc(100%-45px)] overflow-auto'>
        {sections.map((section, index) => (
          <React.Fragment key={section.key}>
            <div
              className={cn(
                'flex items-center justify-between px-2 py-1.5 rounded cursor-pointer transition-all group border border-transparent',
                'hover:bg-gray-50/80 hover:border-gray-300/60',
                selectedSection === section.key
                  ? 'bg-gray-100/80 border-gray-300/60 shadow-sm'
                  : ''
              )}
              onClick={() => onSectionSelect(section.key)}
            >
              <div className='flex items-center gap-2'>
                <div
                  className={cn(
                    'p-1.5 rounded border',
                    section.color
                      .split(' ')
                      .map(c =>
                        c
                          .replace('text-', 'text-opacity-90 text-')
                          .replace('bg-', 'bg-opacity-10 bg-')
                      )
                      .join(' ')
                  )}
                >
                  {section.icon}
                </div>
                <div className='font-medium text-gray-900 text-sm truncate'>
                  {section.title}
                </div>
              </div>
            </div>

            {/* 分隔线 */}
            {index < sections.length - 1 && (
              <div className='mx-2 h-px bg-gray-200/50 my-0.5'></div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
