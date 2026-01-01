'use client';

import React, {
  createContext,
  useContext,
  useCallback,
  useRef,
  useEffect,
  useState,
} from 'react';
import { log } from '@/lib/log';
import {
  createNewTerminal,
  closeTerminal,
  writeToTerminal,
  setTerminalSize,
  TerminalServiceError,
} from '@/api/api';
import type { NewTerminalRequest, TerminalDTO } from '@/api/types';
import { frontendEventBus } from '@/api/event_bus';
import {
  TerminalConfig,
  DEFAULT_TERMINAL_CONFIG,
  TERMINAL_PRESETS,
  configToXtermOptions,
  TERMINAL_THEMES,
  TerminalInstance,
  TerminalState,
  EventListenerState,
  TerminalConnectionStatus,
  ANSI_COLORS,
  TERMINAL_MESSAGES,
  type TerminalSize,
} from './types';

// 动态导入类型定义，避免 SSR 问题
type Terminal = any;
type FitAddon = any;
type WebLinksAddon = any;

// 终端上下文类型
interface TerminalContextType {
  // 终端状态
  isReady: boolean;
  status: TerminalConnectionStatus;
  instanceId: string;
  output: string;
  error: string | null;
  isConnected: boolean;

  // 配置管理
  config: TerminalConfig;
  updateConfig: (updates: Partial<TerminalConfig>) => void;
  resetConfig: () => void;
  applyPreset: (presetName: keyof typeof TERMINAL_PRESETS) => void;
  toggleTheme: () => void;
  getXtermOptions: () => any;

  // 终端操作
  writeTerminal: (data: string) => Promise<void>;
  resizeTerminal: (size?: { rows: number; cols: number }) => void;
  scrollToBottom: () => void;
  readTerminalContent: () => Promise<string>;
  createTerminalInstance: (request?: NewTerminalRequest) => Promise<void>;
  closeTerminalInstance: () => Promise<void>;

  // 其他功能
  clearError: () => void;
  clearOutput: () => void;
  updateState: (updates: Partial<TerminalState>) => void;

  // 初始化回调
  onTerminalReady: (
    terminal: Terminal,
    fitAddon: FitAddon,
    webLinksAddon: WebLinksAddon
  ) => void;

  // 调试和清理
  cleanupTerminal: () => void;

  // DOM 引用
  terminalRef: React.RefObject<HTMLDivElement | null>;
}

// 创建上下文
const TerminalContext = createContext<TerminalContextType | null>(null);

// Provider 组件属性
interface TerminalProviderProps {
  children: React.ReactNode;
  instanceId: string;
}

// 创建日志器
const logger = log.child('TerminalProvider');

// TerminalProvider 组件
export function TerminalProvider({ children, instanceId }: TerminalProviderProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminalInstanceRef = useRef<TerminalInstance | null>(null);
  const currentHandlerRef = useRef<((data: string) => void) | null>(null);
  const eventListenersRef = useRef<EventListenerState>({ isListening: false });

  // 终端实例状态
  const [isReady, setIsReady] = useState(false);

  // 配置管理
  const [config, setConfig] = useState<TerminalConfig>({
    ...DEFAULT_TERMINAL_CONFIG,
  });

  // 连接状态
  const [state, setState] = useState<TerminalState>({
    status: 'disconnected',
    instanceId,
    output: '',
    error: null,
  });

  // 状态辅助函数 - connected 或 ready 都表示可以发送数据
  const isConnected = state.status === 'connected' || state.status === 'ready';

  // ========== 配置管理函数 ==========

  // 更新配置
  const updateConfig = useCallback((updates: Partial<TerminalConfig>) => {
    setConfig(prev => ({
      ...prev,
      ...updates,
    }));
  }, []);

  // 重置为默认配置
  const resetConfig = useCallback(() => {
    setConfig(DEFAULT_TERMINAL_CONFIG);
  }, []);

  // 应用预设配置
  const applyPreset = useCallback(
    (presetName: keyof typeof TERMINAL_PRESETS) => {
      const preset = TERMINAL_PRESETS[presetName];
      if (!preset) {
        logger.warn(`未找到预设配置: ${presetName}`);
        return;
      }

      updateConfig(preset);
    },
    [updateConfig]
  );

  // 切换主题
  const toggleTheme = useCallback(() => {
    const isDark = config.theme.background === '#1a1a1a';
    updateConfig({
      theme: isDark ? TERMINAL_THEMES.light : TERMINAL_THEMES.dark,
    });
  }, [config.theme, updateConfig]);

  // 获取 xterm 配置
  const getXtermOptions = useCallback(() => {
    return configToXtermOptions(config);
  }, [config]);

  // ========== 状态管理函数 ==========

  // 更新状态的辅助函数
  const updateState = useCallback((updates: Partial<TerminalState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);

  // ========== 终端操作函数 ==========

  // 创建终端实例
  const createTerminalInstance = useCallback(
    async (request?: NewTerminalRequest): Promise<void> => {
      try {
        if (isConnected) {
          logger.warn('终端实例已存在，无需重复创建');
          return;
        }

        logger.info('创建终端实例');

        // 如果没有提供请求参数，使用默认配置
        const terminalRequest: NewTerminalRequest = {
          command: undefined, // 使用系统默认 shell
          args: [],
          work_dir: undefined,
          env: undefined,
          size: {
            rows: 24,
            cols: 80,
          },
          metadata: {},
          terminal_id: instanceId || undefined,
          ...request,
        };

        const response = await createNewTerminal(terminalRequest);

        if (!response.success) {
          throw new TerminalServiceError(
            response.error || '创建终端失败',
            terminalRequest.terminal_id
          );
        }

        const terminalDTO: TerminalDTO = response.data!;

        // 只更新 instanceId，不改变连接状态
        // 等待后端的 state_changed 事件来更新连接状态
        updateState({
          instanceId: terminalDTO.instance_id,
          output: `正在启动终端实例: ${terminalDTO.instance_id}...\n`,
        });

        logger.info(`终端实例创建成功，等待启动: ${terminalDTO.instance_id}`);
      } catch (error) {
        const errorMsg = `创建终端实例失败: ${error}`;
        logger.error(errorMsg);
        updateState({ error: errorMsg });
      }
    },
    [instanceId, isConnected, updateState]
  );

  // 关闭终端实例
  const closeTerminalInstance = useCallback(async (): Promise<void> => {
    try {
      if (!isConnected || !state.instanceId) {
        return;
      }

      logger.info('关闭终端实例');

      const response = await closeTerminal({ instance_id: state.instanceId });

      if (!response.success) {
        throw new TerminalServiceError(
          response.error || '关闭终端失败',
          state.instanceId
        );
      }

      // 更新状态
      updateState({
        status: 'disconnected',
        output: `${TERMINAL_MESSAGES.DETACHED}\n`,
      });

      logger.info(`终端实例关闭成功: ${state.instanceId}`);
    } catch (error) {
      const errorMsg = `关闭终端实例失败: ${error}`;
      logger.error(errorMsg);
      updateState({ error: errorMsg });
    }
  }, [isConnected, state.instanceId, updateState]);

  // 写入数据到终端
  const writeTerminal = useCallback(
    async (data: string): Promise<void> => {
      logger.info(`writeTerminal 被调用: ${JSON.stringify(data)}`, 'TerminalProvider');
      logger.info(
        `writeTerminal 状态检查: isConnected=${isConnected}, instanceId=${state.instanceId}`,
        'TerminalProvider'
      );

      try {
        if (!isConnected || !state.instanceId) {
          logger.warn(
            `终端写入条件不满足 - isConnected: ${isConnected}, instanceId: ${state.instanceId}`
          );
          return;
        }

        logger.info(
          `调用 writeToTerminal API: instance_id=${state.instanceId}, data=${JSON.stringify(data)}`,
          'TerminalProvider'
        );
        const response = await writeToTerminal({ instance_id: state.instanceId, data });
        logger.info(
          `writeToTerminal API 响应: ${JSON.stringify(response)}`,
          'TerminalProvider'
        );

        if (!response.success) {
          throw new TerminalServiceError(
            response.error || '写入终端失败',
            state.instanceId
          );
        }
      } catch (error) {
        const errorMsg = `写入终端失败: ${error}`;
        logger.error(errorMsg);
        updateState({ error: errorMsg });
      }
    },
    [isConnected, state.instanceId, updateState]
  );

  // 调整终端尺寸
  const resizeTerminal = useCallback(
    async (size?: { rows: number; cols: number }) => {
      try {
        if (!isConnected || !state.instanceId) {
          return;
        }

        let terminalSize = size;

        // 如果没有提供尺寸，从 xterm 实例获取
        if (!terminalSize && terminalInstanceRef.current?.terminal) {
          const { terminal } = terminalInstanceRef.current;
          terminalSize = {
            rows: terminal.rows,
            cols: terminal.cols,
          };
        }

        if (terminalSize) {
          const response = await setTerminalSize({
            instance_id: state.instanceId,
            rows: terminalSize.rows,
            cols: terminalSize.cols,
          });

          if (!response.success) {
            throw new TerminalServiceError(
              response.error || '设置终端大小失败',
              state.instanceId
            );
          }

          logger.debug(`终端尺寸调整成功: ${terminalSize.rows}x${terminalSize.cols}`);
        }
      } catch (error) {
        const errorMsg = `调整终端尺寸失败: ${error}`;
        logger.error(errorMsg);
        updateState({ error: errorMsg });
      }
    },
    [isConnected, state.instanceId, updateState]
  );

  // 读取终端内容
  const readTerminalContent = useCallback(async (): Promise<string> => {
    try {
      if (!isConnected || !state.instanceId) {
        return '';
      }

      // TODO: 实现读取终端内容功能
      logger.warn('读取终端内容功能尚未实现');
      return '';
    } catch (error) {
      const errorMsg = `读取终端内容失败: ${error}`;
      logger.error(errorMsg);
      updateState({ error: errorMsg });
      return '';
    }
  }, [isConnected, state.instanceId, updateState]);

  // 自动滚动到底部
  const scrollToBottom = useCallback(() => {
    if (terminalRef.current) {
      const terminal = terminalInstanceRef.current?.terminal;
      if (terminal) {
        terminal.scrollToBottom();
      }
    }
  }, []);

  // 清除错误状态
  const clearError = useCallback(() => {
    updateState({ error: null });
  }, [updateState]);

  // 清除输出
  const clearOutput = useCallback(() => {
    updateState({ output: '' });
  }, [updateState]);

  // ========== 事件处理函数 ==========

  // 处理终端输入
  const handleTerminalInput = useCallback(
    (data: string) => {
      logger.info(`收到终端输入: ${JSON.stringify(data)}`, 'TerminalProvider');
      logger.info(
        `连接状态: isConnected=${isConnected}, instanceId=${state.instanceId}`,
        'TerminalProvider'
      );

      if (!isConnected || !state.instanceId) {
        logger.warn(
          `终端输入被忽略 - isConnected: ${isConnected}, instanceId: ${state.instanceId}`,
          'TerminalProvider'
        );
        return;
      }

      // 直接将数据发送到终端服务
      logger.info(
        `发送输入数据到终端服务: ${JSON.stringify(data)}`,
        'TerminalProvider'
      );
      writeTerminal(data);
    },
    [isConnected, state.instanceId, writeTerminal]
  );

  // 处理来自后端的终端事件
  const handleTerminalEvent = useCallback(
    (event: any) => {
      logger.info(
        `收到终端事件: ${event.event_type} ${JSON.stringify(event)}`,
        'TerminalProvider'
      );

      // 解析嵌套的事件数据结构
      const eventData = event.data || event;

      // 只处理属于当前实例的事件
      if (eventData.instance_id !== state.instanceId) {
        logger.debug(
          `忽略不属于当前实例的终端事件: ${eventData.instance_id}`,
          'TerminalProvider'
        );
        return;
      }

      const eventType = eventData.event_type;

      // 处理终端输出事件
      if (eventType === 'output' && eventData.text) {
        const terminal = terminalInstanceRef.current?.terminal;
        if (terminal) {
          terminal.write(eventData.text);
        }
      }

      // 处理终端状态变更事件
      if (eventType === 'state_changed') {
        const oldState = eventData.old_state;
        const newState = eventData.new_state;

        logger.info(`终端状态变更: ${oldState} -> ${newState}`, 'TerminalProvider');

        // 当终端状态变为 running 时，更新前端状态为 connected
        if (newState === 'running' && state.status !== 'connected') {
          logger.info(`终端已启动，更新状态为 connected`, 'TerminalProvider');
          updateState({ status: 'connected' });
        }

        // 当终端状态变为 stopped 或 terminated 时，更新前端状态
        if (
          (newState === 'stopped' || newState === 'terminated') &&
          state.status !== 'disconnected'
        ) {
          logger.info(`终端已停止，更新状态为 disconnected`, 'TerminalProvider');
          updateState({ status: 'disconnected' });
        }
      }
    },
    [state.instanceId, state.status, updateState]
  );

  // 处理终端实例就绪回调
  const handleTerminalReady = useCallback(
    (terminal: Terminal, fitAddon: FitAddon, webLinksAddon: WebLinksAddon) => {
      logger.info('终端实例就绪回调被调用', 'TerminalProvider');

      if (terminalInstanceRef.current) {
        logger.warn('终端实例已存在，忽略就绪回调', 'TerminalProvider');
        return;
      }

      terminalInstanceRef.current = {
        terminal,
        fitAddon,
        webLinksAddon,
      };

      // 当前端终端组件准备好时，更新状态为 ready
      // 这表示前端可以开始接收和发送数据了
      if (state.status === 'connected' || state.status === 'disconnected') {
        logger.info(`终端状态从 ${state.status} 更新为 ready`, 'TerminalProvider');
        updateState({ status: 'ready' });
      } else {
        logger.debug(`终端状态已经是 ${state.status}，无需更新`, 'TerminalProvider');
      }
    },
    [state.status, updateState]
  );

  // ========== 清理终端实例 ==========

  const cleanupTerminal = useCallback(() => {
    if (terminalInstanceRef.current) {
      try {
        terminalInstanceRef.current.terminal.dispose();
        terminalInstanceRef.current = null;
        currentHandlerRef.current = null;
        setIsReady(false);
        updateState({ status: 'disconnected' });
      } catch (error) {
        logger.warn(`清理终端实例失败: ${error}`);
      }
    }
  }, [updateState]);

  // ========== 生命周期管理 ==========

  // 终端实例管理和输入事件绑定
  useEffect(() => {
    const terminal = terminalInstanceRef.current?.terminal;
    if (!terminal || currentHandlerRef.current) return;

    // 绑定输入事件监听器
    terminal.onData(handleTerminalInput);
    currentHandlerRef.current = handleTerminalInput;

    return () => {
      currentHandlerRef.current = null;
    };
  }, [handleTerminalInput]);

  // 监听终端事件
  useEffect(() => {
    // 确保前端事件总线已初始化
    if (typeof window !== 'undefined') {
      frontendEventBus.initialize();
    }

    // 创建终端事件处理器
    const terminalEventHandler = (event: Event) => {
      const customEvent = event as CustomEvent;
      const terminalEventData = customEvent.detail;
      handleTerminalEvent(terminalEventData);
    };

    // 监听 terminal_event 事件
    window.addEventListener('terminal_event', terminalEventHandler as EventListener);

    logger.info('terminal_event 事件监听器已注册', 'TerminalProvider');

    // 清理函数
    return () => {
      window.removeEventListener('terminal_event', terminalEventHandler);
      logger.info('terminal_event 事件监听器已移除', 'TerminalProvider');
    };
  }, [handleTerminalEvent]);

  // instanceId 相关的生命周期管理（设置 isReady）
  useEffect(() => {
    if (!isReady) {
      logger.info(`TerminalProvider 就绪: ${instanceId || 'empty'}`);
      setIsReady(true);
    }
  }, [instanceId, isReady]);

  // 组件卸载时的统一清理逻辑
  useEffect(() => {
    return () => {
      logger.info('TerminalProvider 卸载，清理资源');

      // 只清理前端终端实例，不自动关闭后端终端
      // 因为终端生命周期由页面层级统一管理
      cleanupTerminal();

      // 重置状态
      setIsReady(false);
      updateState({ status: 'disconnected' });
    };
  }, [updateState, cleanupTerminal]);

  // 构建上下文值
  const contextValue: TerminalContextType = {
    // 终端状态
    isReady,
    status: state.status,
    instanceId,
    output: state.output,
    error: state.error,
    isConnected,

    // 配置管理
    config,
    updateConfig,
    resetConfig,
    applyPreset,
    toggleTheme,
    getXtermOptions,

    // 终端操作
    writeTerminal,
    resizeTerminal,
    scrollToBottom,
    readTerminalContent,
    createTerminalInstance,
    closeTerminalInstance,

    // 其他功能
    clearError,
    clearOutput,
    updateState,

    // 初始化回调
    onTerminalReady: handleTerminalReady,

    // 调试和清理
    cleanupTerminal,

    // DOM 引用
    terminalRef,
  };

  return (
    <TerminalContext.Provider value={contextValue}>{children}</TerminalContext.Provider>
  );
}

// Hook 用于使用终端上下文
export function useTerminalContext(): TerminalContextType {
  const context = useContext(TerminalContext);
  if (!context) {
    throw new Error('useTerminalContext must be used within a TerminalProvider');
  }
  return context;
}
