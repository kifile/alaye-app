'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { TerminalContainer } from '../TerminalContainer';
import { useTerminalContext } from '../TerminalProvider';

// 演示组件属性
interface TerminalDemoProps {
  className?: string;
}

// 基本终端演示
export function BasicTerminalDemo({ className = '' }: TerminalDemoProps) {
  const [instanceId] = useState(`demo-terminal-${Date.now()}`);

  return (
    <Card className={`h-96 ${className}`}>
      <div className='p-4 border-b'>
        <h3 className='text-lg font-semibold'>基本终端演示</h3>
        <p className='text-sm text-gray-600 dark:text-gray-400'>
          这是一个基本的终端实例，可以创建和管理终端会话。
        </p>
      </div>
      <div className='flex-1'>
        <TerminalContainer
          instanceId={instanceId}
          showControls={true}
          showStatusBar={true}
        />
      </div>
    </Card>
  );
}

// 带自定义操作的终端演示
export function CustomTerminalDemo({ className = '' }: TerminalDemoProps) {
  const [instanceId] = useState(`custom-terminal-${Date.now()}`);
  const [command, setCommand] = useState('');

  return (
    <Card className={`h-96 ${className}`}>
      <div className='p-4 border-b space-y-3'>
        <div>
          <h3 className='text-lg font-semibold'>自定义操作演示</h3>
          <p className='text-sm text-gray-600 dark:text-gray-400'>
            演示如何与终端进行交互操作。
          </p>
        </div>

        <div className='flex space-x-2'>
          <Input
            placeholder='输入命令...'
            value={command}
            onChange={e => setCommand(e.target.value)}
            onKeyPress={e => {
              if (e.key === 'Enter' && command.trim()) {
                // TODO: 实现命令发送到终端
                console.log('发送命令:', command);
                setCommand('');
              }
            }}
            className='flex-1'
          />
          <Button size='sm' disabled={!command.trim()}>
            发送
          </Button>
        </div>
      </div>

      <div className='flex-1'>
        <TerminalContainer
          instanceId={instanceId}
          showControls={true}
          showStatusBar={false}
        />
      </div>
    </Card>
  );
}

// 终端 Hook 使用演示
function TerminalHookDemoComponent() {
  const {
    status,
    instanceId,
    isConnected,
    config,
    createTerminalInstance,
    closeTerminalInstance,
    writeTerminal,
    updateConfig,
  } = useTerminalContext();

  const handleWriteHello = async () => {
    try {
      await writeTerminal("echo 'Hello from Terminal Hook!'\n");
    } catch (error) {
      console.error('写入终端失败:', error);
    }
  };

  const handleFontSizeChange = (size: number) => {
    updateConfig({ fontSize: size });
  };

  return (
    <div className='space-y-4'>
      <div className='grid grid-cols-2 gap-4 text-sm'>
        <div>
          <strong>状态:</strong> {status}
        </div>
        <div>
          <strong>实例ID:</strong> {instanceId || '无'}
        </div>
        <div>
          <strong>连接状态:</strong> {isConnected ? '已连接' : '未连接'}
        </div>
        <div>
          <strong>字体大小:</strong> {config.fontSize}px
        </div>
      </div>

      <div className='flex space-x-2'>
        <Button
          size='sm'
          onClick={() => createTerminalInstance()}
          disabled={isConnected}
        >
          创建终端
        </Button>

        <Button
          size='sm'
          variant='outline'
          onClick={handleWriteHello}
          disabled={!isConnected}
        >
          发送 Hello
        </Button>

        <Button size='sm' variant='outline' onClick={() => handleFontSizeChange(16)}>
          字体 16px
        </Button>

        <Button
          size='sm'
          variant='outline'
          onClick={closeTerminalInstance}
          disabled={!isConnected}
        >
          关闭终端
        </Button>
      </div>
    </div>
  );
}

export function TerminalHookDemo({ className = '' }: TerminalDemoProps) {
  const [instanceId] = useState(`hook-demo-terminal-${Date.now()}`);

  return (
    <Card className={`h-96 ${className}`}>
      <div className='p-4 border-b'>
        <h3 className='text-lg font-semibold'>Terminal Hook 演示</h3>
        <p className='text-sm text-gray-600 dark:text-gray-400'>
          演示如何使用 useTerminalContext Hook 来控制终端。
        </p>
      </div>

      <div className='flex-1 flex'>
        <div className='w-2/3 border-r'>
          <TerminalContainer
            instanceId={instanceId}
            showControls={false}
            showStatusBar={false}
          />
        </div>

        <div className='w-1/3 p-4 overflow-auto'>
          <TerminalHookDemoComponent />
        </div>
      </div>
    </Card>
  );
}

// 多终端演示
export function MultiTerminalDemo({ className = '' }: TerminalDemoProps) {
  const [terminals] = useState([
    { id: `multi-terminal-1-${Date.now()}`, name: '终端 1' },
    { id: `multi-terminal-2-${Date.now()}`, name: '终端 2' },
  ]);

  return (
    <Card className={`h-96 ${className}`}>
      <div className='p-4 border-b'>
        <h3 className='text-lg font-semibold'>多终端演示</h3>
        <p className='text-sm text-gray-600 dark:text-gray-400'>
          演示同时管理多个终端实例。
        </p>
      </div>

      <div className='flex-1 flex'>
        {terminals.map((terminal, index) => (
          <div
            key={terminal.id}
            className={`${index === 0 ? 'border-r' : ''} ${
              terminals.length === 2 ? 'w-1/2' : ''
            }`}
          >
            <div className='p-2 border-b bg-gray-50 dark:bg-gray-900'>
              <span className='text-sm font-medium'>{terminal.name}</span>
              <span className='text-xs text-gray-500 ml-2'>
                ID: {terminal.id.slice(-8)}
              </span>
            </div>
            <div className='h-full'>
              <TerminalContainer
                instanceId={terminal.id}
                showControls={false}
                showStatusBar={false}
                emptyView={
                  <div className='text-center text-gray-500'>点击上方按钮创建终端</div>
                }
              />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// 完整的演示页面
export function TerminalDemo({ className = '' }: TerminalDemoProps) {
  return (
    <div className={`space-y-6 ${className}`}>
      <div className='text-center'>
        <h2 className='text-2xl font-bold'>PyWebview Terminal 组件演示</h2>
        <p className='text-gray-600 dark:text-gray-400 mt-2'>
          基于 PyWebview API 的终端组件，支持多实例、配置管理和错误处理
        </p>
      </div>

      <div className='grid gap-6'>
        <BasicTerminalDemo />
        <CustomTerminalDemo />
        <TerminalHookDemo />
        <MultiTerminalDemo />
      </div>

      <Card className='p-6'>
        <h3 className='text-lg font-semibold mb-3'>功能特性</h3>
        <div className='grid md:grid-cols-2 gap-4 text-sm'>
          <div>
            <h4 className='font-medium mb-2'>核心功能</h4>
            <ul className='space-y-1 text-gray-600 dark:text-gray-400'>
              <li>✅ 终端实例创建和管理</li>
              <li>✅ 数据写入和读取</li>
              <li>✅ 终端大小调整</li>
              <li>✅ 主题切换（亮色/暗色）</li>
              <li>✅ 字体和配置管理</li>
              <li>✅ 错误边界和异常处理</li>
            </ul>
          </div>
          <div>
            <h4 className='font-medium mb-2'>高级功能</h4>
            <ul className='space-y-1 text-gray-600 dark:text-gray-400'>
              <li>🚧 事件监听和实时输出</li>
              <li>🚧 终端内容读取和恢复</li>
              <li>🚧 进程状态监控</li>
              <li>🚧 多标签页支持</li>
              <li>🚧 命令历史记录</li>
              <li>🚧 快捷键支持</li>
            </ul>
          </div>
        </div>

        <div className='mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800'>
          <p className='text-sm text-blue-800 dark:text-blue-200'>
            <strong>注意：</strong>read_terminal_content 功能已标记为
            TODO，当前版本中尚未实现。 终端组件已集成到 PyWebview
            API，支持在桌面应用环境中运行。
          </p>
        </div>
      </Card>
    </div>
  );
}

export default TerminalDemo;
