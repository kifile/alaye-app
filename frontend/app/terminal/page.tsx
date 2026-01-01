'use client';

import React, { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Terminal, TerminalProvider } from '@/components/terminal';
import { log } from '@/lib/log';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Terminal as TerminalIcon,
  Play,
  Square,
  RotateCcw,
  Settings,
  Monitor,
  Sun,
  Moon,
  Copy,
  Download,
} from 'lucide-react';

// 终端实例类型
interface TerminalInstance {
  id: string;
  name: string;
  createdAt: Date;
  lastActivity: Date;
}

// 终端控制面板组件
function TerminalControlPanel() {
  const [terminals, setTerminals] = useState<TerminalInstance[]>([]);
  const [activeTerminalId, setActiveTerminalId] = useState<string>('');

  // 直接使用 API 进行终端管理，不依赖 Terminal Context
  const [config, setConfig] = useState({
    fontSize: 14,
    theme: {
      background: '#1a1a1a',
      foreground: '#ffffff',
      cursor: '#ffffff',
      selectionBackground: '#ffffff40',
      black: '#000000',
      red: '#ff5555',
      green: '#50fa7b',
      yellow: '#f1fa8c',
      blue: '#6272a4',
      magenta: '#ff79c6',
      cyan: '#8be9fd',
      white: '#f8f8f2',
      brightBlack: '#6272a4',
      brightRed: '#ff6e6e',
      brightGreen: '#69ff94',
      brightYellow: '#ffffa5',
      brightBlue: '#d6acff',
      brightMagenta: '#ff92df',
      brightCyan: '#a4ffff',
      brightWhite: '#ffffff',
    },
  });

  // 创建新终端实例
  const createNewTerminal = async () => {
    try {
      const newTerminalId = `terminal-${Date.now()}`;
      const newTerminal: TerminalInstance = {
        id: newTerminalId,
        name: `终端 ${terminals.length + 1}`,
        createdAt: new Date(),
        lastActivity: new Date(),
      };

      setTerminals(prev => [...prev, newTerminal]);
      setActiveTerminalId(newTerminalId);

      // 传递终端ID给后端，确保前后端实例ID一致
      const { createNewTerminal } = await import('@/api/api');
      await createNewTerminal({ terminal_id: newTerminalId });

      log.info(`新终端实例创建成功: ${newTerminalId}`);
    } catch (error) {
      log.error(`创建终端实例失败: ${error}`);
    }
  };

  // 关闭终端实例
  const closeTerminal = async (terminalId: string) => {
    try {
      // 调用 API 关闭终端
      const { closeTerminal } = await import('@/api/api');
      await closeTerminal({ instance_id: terminalId });

      setTerminals(prev => prev.filter(t => t.id !== terminalId));

      if (activeTerminalId === terminalId) {
        const remainingTerminals = terminals.filter(t => t.id !== terminalId);
        setActiveTerminalId(
          remainingTerminals.length > 0 ? remainingTerminals[0].id : ''
        );
      }

      log.info(`终端实例关闭成功: ${terminalId}`);
    } catch (error) {
      log.error(`关闭终端实例失败: ${error}`);
    }
  };

  // 更新配置
  const updateConfig = (updates: any) => {
    setConfig(prev => ({ ...prev, ...updates }));
  };

  // 格式化时间
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className='min-h-screen bg-background'>
      {/* 页面头部 */}
      <div className='border-b bg-card'>
        <div className='container mx-auto px-4 py-4'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center space-x-3'>
              <TerminalIcon className='h-8 w-8 text-primary' />
              <div>
                <h1 className='text-2xl font-bold'>终端管理</h1>
                <p className='text-sm text-muted-foreground'>
                  基于 PyWebview 的交互式终端
                </p>
              </div>
            </div>

            <div className='flex items-center space-x-2'>
              <Badge variant={activeTerminalId ? 'default' : 'secondary'}>
                {activeTerminalId ? '终端就绪' : '未选择'}
              </Badge>
              <Badge variant='outline'>{terminals.length} 个终端</Badge>
            </div>
          </div>
        </div>
      </div>

      {/* 主要内容区域 */}
      <div className='container mx-auto px-4 py-6'>
        <div className='grid grid-cols-1 lg:grid-cols-4 gap-6'>
          {/* 左侧控制面板 */}
          <div className='lg:col-span-1 space-y-4'>
            {/* 终端实例管理 */}
            <Card>
              <div className='p-4 border-b'>
                <h3 className='font-semibold flex items-center'>
                  <Monitor className='h-4 w-4 mr-2' />
                  终端实例
                </h3>
              </div>
              <div className='p-4 space-y-3'>
                <Button
                  onClick={createNewTerminal}
                  className='w-full'
                  disabled={terminals.length >= 4}
                >
                  <Play className='h-4 w-4 mr-2' />
                  创建新终端
                </Button>

                <div className='space-y-2'>
                  {terminals.map(terminal => (
                    <div
                      key={terminal.id}
                      className={`p-2 rounded border cursor-pointer transition-colors ${
                        activeTerminalId === terminal.id
                          ? 'border-primary bg-primary/10'
                          : 'border-border hover:bg-muted'
                      }`}
                      onClick={() => setActiveTerminalId(terminal.id)}
                    >
                      <div className='flex items-center justify-between'>
                        <span className='font-medium text-sm'>{terminal.name}</span>
                        <Button
                          size='sm'
                          variant='ghost'
                          onClick={e => {
                            e.stopPropagation();
                            closeTerminal(terminal.id);
                          }}
                        >
                          <Square className='h-3 w-3' />
                        </Button>
                      </div>
                      <div className='text-xs text-muted-foreground mt-1'>
                        创建: {formatTime(terminal.createdAt)}
                      </div>
                    </div>
                  ))}
                </div>

                {terminals.length === 0 && (
                  <div className='text-center text-muted-foreground py-4'>
                    暂无终端实例
                  </div>
                )}
              </div>
            </Card>

            {/* 终端配置 */}
            <Card>
              <div className='p-4 border-b'>
                <h3 className='font-semibold flex items-center'>
                  <Settings className='h-4 w-4 mr-2' />
                  终端配置
                </h3>
              </div>
              <div className='p-4 space-y-4'>
                <div>
                  <Label htmlFor='fontSize'>字体大小</Label>
                  <Select
                    value={config.fontSize.toString()}
                    onValueChange={value => updateConfig({ fontSize: parseInt(value) })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value='12'>12px</SelectItem>
                      <SelectItem value='14'>14px</SelectItem>
                      <SelectItem value='16'>16px</SelectItem>
                      <SelectItem value='18'>18px</SelectItem>
                      <SelectItem value='20'>20px</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>主题</Label>
                  <div className='flex space-x-2 mt-2'>
                    <Button
                      size='sm'
                      variant={
                        config.theme.background === '#1a1a1a' ? 'default' : 'outline'
                      }
                      onClick={() =>
                        updateConfig({
                          theme: {
                            background: '#1a1a1a',
                            foreground: '#ffffff',
                            cursor: '#ffffff',
                            selectionBackground: '#ffffff40',
                            black: '#000000',
                            red: '#ff5555',
                            green: '#50fa7b',
                            yellow: '#f1fa8c',
                            blue: '#6272a4',
                            magenta: '#ff79c6',
                            cyan: '#8be9fd',
                            white: '#f8f8f2',
                            brightBlack: '#6272a4',
                            brightRed: '#ff6e6e',
                            brightGreen: '#69ff94',
                            brightYellow: '#ffffa5',
                            brightBlue: '#d6acff',
                            brightMagenta: '#ff92df',
                            brightCyan: '#a4ffff',
                            brightWhite: '#ffffff',
                          },
                        })
                      }
                    >
                      <Moon className='h-4 w-4 mr-1' />
                      暗色
                    </Button>
                    <Button
                      size='sm'
                      variant={
                        config.theme.background === '#ffffff' ? 'default' : 'outline'
                      }
                      onClick={() =>
                        updateConfig({
                          theme: {
                            background: '#ffffff',
                            foreground: '#000000',
                            cursor: '#000000',
                            selectionBackground: '#00000040',
                            black: '#000000',
                            red: '#cc0000',
                            green: '#4e9a06',
                            yellow: '#c4a000',
                            blue: '#3465a4',
                            magenta: '#75507b',
                            cyan: '#06989a',
                            white: '#d3d7cf',
                            brightBlack: '#555753',
                            brightRed: '#ef2929',
                            brightGreen: '#8ae234',
                            brightYellow: '#fce94f',
                            brightBlue: '#729fcf',
                            brightMagenta: '#ad7fa8',
                            brightCyan: '#34e2e2',
                            brightWhite: '#eeeeec',
                          },
                        })
                      }
                    >
                      <Sun className='h-4 w-4 mr-1' />
                      亮色
                    </Button>
                  </div>
                </div>

                <div className='flex space-x-2'>
                  <Button size='sm' variant='outline'>
                    <Copy className='h-4 w-4 mr-1' />
                    复制
                  </Button>
                  <Button size='sm' variant='outline'>
                    <Download className='h-4 w-4 mr-1' />
                    导出
                  </Button>
                </div>
              </div>
            </Card>
          </div>

          {/* 右侧终端区域 */}
          <div className='lg:col-span-3'>
            <Card className='h-[700px] flex flex-col'>
              {/* 终端头部 */}
              <div className='p-3 border-b bg-muted/50 flex-shrink-0'>
                <div className='flex items-center justify-between'>
                  <div className='flex items-center space-x-2'>
                    <TerminalIcon className='h-4 w-4' />
                    <span className='font-medium'>
                      {terminals.find(t => t.id === activeTerminalId)?.name ||
                        (activeTerminalId ? '终端交互' : '选择终端实例')}
                    </span>
                    {activeTerminalId && (
                      <Badge variant='secondary' className='text-xs'>
                        ID: {activeTerminalId.slice(-8)}
                      </Badge>
                    )}
                  </div>

                  <div className='flex items-center space-x-2'>
                    <Badge variant={activeTerminalId ? 'default' : 'secondary'}>
                      {activeTerminalId ? '已选择' : '未连接'}
                    </Badge>
                    <Button
                      size='sm'
                      variant='outline'
                      onClick={() =>
                        activeTerminalId && closeTerminal(activeTerminalId)
                      }
                      disabled={!activeTerminalId}
                    >
                      <RotateCcw className='h-4 w-4 mr-1' />
                      关闭
                    </Button>
                  </div>
                </div>
              </div>

              {/* 终端内容 - 占满剩余空间 */}
              <div className='flex-1 p-0 overflow-hidden relative'>
                {activeTerminalId ? (
                  <Terminal
                    instanceId={activeTerminalId}
                    onTerminalSizeChange={size => {
                      log.info(`终端大小变化: ${size.rows}x${size.cols}`);
                    }}
                    className='w-full h-full'
                  />
                ) : (
                  <div className='flex items-center justify-center h-full bg-muted/10'>
                    <div className='text-center space-y-4'>
                      <TerminalIcon className='h-16 w-16 mx-auto text-muted-foreground' />
                      <div>
                        <h3 className='text-lg font-medium text-muted-foreground'>
                          请创建或选择一个终端实例
                        </h3>
                        <p className='text-sm text-muted-foreground mt-1'>
                          点击左侧的"创建新终端"按钮开始使用
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

// 主页面组件
export default function TerminalPage() {
  return <TerminalControlPanel />;
}
