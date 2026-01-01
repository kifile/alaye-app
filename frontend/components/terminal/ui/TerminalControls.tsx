import React from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Play, Square, RotateCcw, Settings, Monitor, Sun, Moon } from 'lucide-react';
import { useTerminalContext } from '../TerminalProvider';
import { TerminalConnectionStatus } from '../types';

// 类型声明
interface TerminalControlsProps {
  className?: string;
  showConfigButton?: boolean;
  onConfigClick?: () => void;
}

export function TerminalControls({
  className = '',
  showConfigButton = true,
  onConfigClick,
}: TerminalControlsProps) {
  const {
    status,
    instanceId,
    isConnected,
    createTerminalInstance,
    closeTerminalInstance,
    clearError,
    clearOutput,
    toggleTheme,
    config,
  } = useTerminalContext();

  // 处理创建终端
  const handleCreateTerminal = async () => {
    try {
      await createTerminalInstance({
        terminal_id: instanceId || undefined,
      });
    } catch (error) {
      console.error('创建终端失败:', error);
    }
  };

  // 处理关闭终端
  const handleCloseTerminal = async () => {
    try {
      await closeTerminalInstance();
    } catch (error) {
      console.error('关闭终端失败:', error);
    }
  };

  // 获取状态颜色
  const getStatusColor = (status: TerminalConnectionStatus) => {
    switch (status) {
      case 'connected':
        return 'bg-green-500';
      case 'ready':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  // 获取状态文本
  const getStatusText = (status: TerminalConnectionStatus) => {
    switch (status) {
      case 'connected':
        return '已连接';
      case 'ready':
        return '就绪';
      default:
        return '未连接';
    }
  };

  // 判断当前主题
  const isDarkTheme = config.theme.background === '#1a1a1a';

  return (
    <div
      className={`flex items-center justify-between p-2 border-b bg-gray-50 dark:bg-gray-900 ${className}`}
    >
      {/* 左侧：状态和控制按钮 */}
      <div className='flex items-center space-x-3'>
        {/* 状态指示器 */}
        <div className='flex items-center space-x-2'>
          <div className={`w-2 h-2 rounded-full ${getStatusColor(status)}`} />
          <Badge variant='secondary' className='text-xs'>
            {getStatusText(status)}
          </Badge>
          {instanceId && (
            <Badge variant='outline' className='text-xs'>
              ID: {instanceId}
            </Badge>
          )}
        </div>

        {/* 控制按钮组 */}
        <div className='flex items-center space-x-1'>
          <Button
            size='sm'
            variant='outline'
            onClick={handleCreateTerminal}
            disabled={isConnected}
            title='创建终端'
          >
            <Play className='h-4 w-4' />
          </Button>

          <Button
            size='sm'
            variant='outline'
            onClick={handleCloseTerminal}
            disabled={!isConnected}
            title='关闭终端'
          >
            <Square className='h-4 w-4' />
          </Button>

          <Button
            size='sm'
            variant='outline'
            onClick={() => {
              clearError();
              clearOutput();
            }}
            title='清理终端'
          >
            <RotateCcw className='h-4 w-4' />
          </Button>
        </div>
      </div>

      {/* 右侧：配置和主题切换 */}
      <div className='flex items-center space-x-2'>
        {/* 主题切换按钮 */}
        <Button
          size='sm'
          variant='outline'
          onClick={toggleTheme}
          title={isDarkTheme ? '切换到亮色主题' : '切换到暗色主题'}
        >
          {isDarkTheme ? <Sun className='h-4 w-4' /> : <Moon className='h-4 w-4' />}
        </Button>

        {/* 配置按钮 */}
        {showConfigButton && (
          <Button size='sm' variant='outline' onClick={onConfigClick} title='终端设置'>
            <Settings className='h-4 w-4' />
          </Button>
        )}

        {/* 监控模式按钮 */}
        <Button size='sm' variant='outline' disabled title='监控模式（开发中）'>
          <Monitor className='h-4 w-4' />
        </Button>
      </div>
    </div>
  );
}

// 简化版控制条，只显示基本状态
export function TerminalStatusBar({ className = '' }: { className?: string }) {
  const { status, instanceId, isConnected } = useTerminalContext();

  const getStatusColor = (status: TerminalConnectionStatus) => {
    switch (status) {
      case 'connected':
        return 'bg-green-500';
      case 'ready':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusText = (status: TerminalConnectionStatus) => {
    switch (status) {
      case 'connected':
        return '已连接';
      case 'ready':
        return '就绪';
      default:
        return '未连接';
    }
  };

  return (
    <div
      className={`flex items-center justify-between px-3 py-1 bg-gray-100 dark:bg-gray-800 border-t text-xs ${className}`}
    >
      <div className='flex items-center space-x-2'>
        <div className={`w-2 h-2 rounded-full ${getStatusColor(status)}`} />
        <span className='text-gray-600 dark:text-gray-400'>
          {getStatusText(status)}
        </span>
        {instanceId && (
          <span className='text-gray-500 dark:text-gray-500'>| {instanceId}</span>
        )}
      </div>

      <div className='text-gray-500 dark:text-gray-500'>
        {isConnected ? '就绪' : '离线'}
      </div>
    </div>
  );
}
