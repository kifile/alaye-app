'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Terminal } from './index';
import { TerminalControls, TerminalStatusBar } from './ui/TerminalControls';
import { useTerminalContext } from './TerminalProvider';

// 终端容器属性接口
interface TerminalContainerProps {
  instanceId?: string;
  emptyView?: React.ReactNode;
  showControls?: boolean;
  showStatusBar?: boolean;
  className?: string;
  onTerminalSizeChange?: (size: { rows: number; cols: number }) => void;
}

// 创建日志器
const logger = console;

// TerminalContainer 组件 - 包含控制条的完整终端组件
export function TerminalContainer({
  instanceId,
  emptyView,
  showControls = true,
  showStatusBar = true,
  className = '',
  onTerminalSizeChange,
}: TerminalContainerProps) {
  const [showConfig, setShowConfig] = useState(false);
  const { config, updateConfig } = useTerminalContext();

  logger.info(`渲染终端容器: ${instanceId || 'no instanceId'}`);

  // 处理配置按钮点击
  const handleConfigClick = () => {
    setShowConfig(!showConfig);
  };

  // 处理字体大小变化
  const handleFontSizeChange = (fontSize: number) => {
    updateConfig({ fontSize });
  };

  // 处理主题切换
  const handleThemeToggle = () => {
    const newTheme = config.theme.background === '#1a1a1a' ? 'light' : 'dark';
    // 这里可以更新配置的主题
  };

  return (
    <Card className={`flex flex-col h-full ${className}`}>
      {/* 顶部控制条 */}
      {showControls && (
        <TerminalControls
          onConfigClick={handleConfigClick}
          className='border-none rounded-t-lg'
        />
      )}

      {/* 配置面板（可折叠） */}
      {showConfig && (
        <div className='border-x border-t p-3 bg-gray-50 dark:bg-gray-900'>
          <div className='flex items-center justify-between mb-3'>
            <h3 className='text-sm font-medium'>终端设置</h3>
            <button
              onClick={() => setShowConfig(false)}
              className='text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            >
              ×
            </button>
          </div>

          <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
            {/* 字体设置 */}
            <div>
              <label className='block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1'>
                字体大小
              </label>
              <div className='flex items-center space-x-2'>
                <input
                  type='range'
                  min='10'
                  max='24'
                  value={config.fontSize}
                  onChange={e => handleFontSizeChange(Number(e.target.value))}
                  className='flex-1'
                />
                <span className='text-sm w-8'>{config.fontSize}</span>
              </div>
            </div>

            {/* 滚动缓冲区设置 */}
            <div>
              <label className='block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1'>
                滚动缓冲区
              </label>
              <select
                value={config.scrollback}
                onChange={e => updateConfig({ scrollback: Number(e.target.value) })}
                className='w-full text-sm border rounded px-2 py-1'
              >
                <option value={100}>100 行</option>
                <option value={500}>500 行</option>
                <option value={1000}>1000 行</option>
                <option value={2000}>2000 行</option>
                <option value={5000}>5000 行</option>
              </select>
            </div>

            {/* 光标设置 */}
            <div>
              <label className='block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1'>
                光标闪烁
              </label>
              <div className='flex items-center space-x-2'>
                <input
                  type='checkbox'
                  checked={config.cursorBlink}
                  onChange={e => updateConfig({ cursorBlink: e.target.checked })}
                  className='rounded'
                />
                <span className='text-sm'>启用光标闪烁</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 终端主体 */}
      <div className='flex-1 overflow-hidden'>
        <Terminal
          instanceId={instanceId}
          emptyView={emptyView}
          onTerminalSizeChange={onTerminalSizeChange}
        />
      </div>

      {/* 底部状态栏 */}
      {showStatusBar && <TerminalStatusBar className='border-none rounded-b-lg' />}
    </Card>
  );
}

// 带有预设配置的终端容器
export function PresetTerminalContainer({
  preset = 'default',
  instanceId,
  ...props
}: TerminalContainerProps & {
  preset?: 'compact' | 'comfortable' | 'accessibility' | 'default';
}) {
  const { applyPreset } = useTerminalContext();

  React.useEffect(() => {
    if (preset !== 'default') {
      applyPreset(preset);
    }
  }, [preset, applyPreset]);

  return <TerminalContainer instanceId={instanceId} {...props} />;
}

TerminalContainer.displayName = 'TerminalContainer';
PresetTerminalContainer.displayName = 'PresetTerminalContainer';
