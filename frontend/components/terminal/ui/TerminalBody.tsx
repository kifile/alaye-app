import React, { useEffect, useRef, useCallback } from 'react';
import { log } from '@/lib/log';
import { useTerminalContext } from '../TerminalProvider';
import type { TerminalSize } from '../types';

// 导入 xterm 样式
import '@xterm/xterm/css/xterm.css';

const logger = log.child('TerminalBody');

// 类型声明，用于 TypeScript 支持
interface TerminalBodyProps {
  className?: string;
  emptyView?: React.ReactNode;
  onTerminalSizeChange?: (size: TerminalSize) => void;
}

export function TerminalBody({
  className = '',
  emptyView,
  onTerminalSizeChange,
}: TerminalBodyProps) {
  // 直接从 useTerminalContext hook 获取所有需要的数据和方法
  const {
    terminalRef,
    isReady,
    getXtermOptions,
    isConnected,
    resizeTerminal,
    onTerminalReady,
    instanceId,
    status,
  } = useTerminalContext();

  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const isInitializingRef = useRef(false); // 防止重复初始化的标志
  const lastSizeRef = useRef<{ rows: number; cols: number } | null>(null); // 记录上一次尺寸
  // 移除自动创建终端逻辑，由页面层级的 TerminalControlPanel 统一管理

  // 使用 ref 来存储最新的回调函数，避免循环依赖
  const latestCallbacksRef = useRef({
    getXtermOptions,
    isConnected,
    resizeTerminal,
    onTerminalReady,
    onTerminalSizeChange,
  });

  // 更新 ref 值
  latestCallbacksRef.current = {
    getXtermOptions,
    isConnected,
    resizeTerminal,
    onTerminalReady,
    onTerminalSizeChange,
  };

  // 初始化终端实例
  const initializeTerminal = useCallback(async () => {
    logger.debug(
      `开始初始化终端，terminalRef.current: ${terminalRef.current ? '存在' : '不存在'}`
    );

    // 多重检查，确保不会重复初始化
    if (!terminalRef.current) {
      logger.error('终端容器元素不存在');
      return;
    }

    if (isInitializingRef.current) {
      logger.debug('终端正在初始化中，跳过重复初始化');
      return;
    }

    try {
      logger.info('初始化终端实例');

      // 设置初始化标志
      isInitializingRef.current = true;

      // 动态加载 xterm 模块
      const [{ Terminal }, { FitAddon }, { WebLinksAddon }] = await Promise.all([
        import('@xterm/xterm'),
        import('@xterm/addon-fit'),
        import('@xterm/addon-web-links'),
      ]);

      const { getXtermOptions, resizeTerminal, onTerminalReady, onTerminalSizeChange } =
        latestCallbacksRef.current;

      const terminal = new Terminal(getXtermOptions());
      const fitAddon = new FitAddon();
      const webLinksAddon = new WebLinksAddon();

      // 加载插件
      terminal.loadAddon(fitAddon);
      terminal.loadAddon(webLinksAddon);

      // 打开终端
      terminal.open(terminalRef.current);

      // 显示就绪消息
      terminal.writeln('\x1b[32m终端已就绪\x1b[0m');
      if (instanceId) {
        terminal.writeln(`\x1b[36m实例 ID: ${instanceId}\x1b[0m`);
      }

      // 使用 ResizeObserver 监听容器尺寸变化，增加防抖和尺寸变化检测
      resizeObserverRef.current = new ResizeObserver(entries => {
        for (const entry of entries) {
          if (entry.target === terminalRef.current) {
            try {
              fitAddon.fit();
              const currentSize = { rows: terminal.rows, cols: terminal.cols };

              // 只有尺寸真正变化时才处理
              if (
                !lastSizeRef.current ||
                lastSizeRef.current.rows !== currentSize.rows ||
                lastSizeRef.current.cols !== currentSize.cols
              ) {
                logger.debug(`终端尺寸已调整: ${terminal.rows}x${terminal.cols}`);
                lastSizeRef.current = currentSize;

                // 同步调整后端终端尺寸
                resizeTerminal({
                  rows: terminal.rows,
                  cols: terminal.cols,
                });

                // 调用父组件的尺寸变化回调
                if (onTerminalSizeChange) {
                  onTerminalSizeChange({
                    rows: terminal.rows,
                    cols: terminal.cols,
                  });
                }
              }
            } catch (error) {
              logger.warn(`ResizeObserver 调整终端尺寸失败: ${error}`);
            }
          }
        }
      });

      // 开始观察容器元素
      resizeObserverRef.current.observe(terminalRef.current);

      // 立即进行一次尺寸调整，并记录初始尺寸
      try {
        fitAddon.fit();
        const initialSize = { rows: terminal.rows, cols: terminal.cols };
        lastSizeRef.current = initialSize;
        logger.debug(`初始终端尺寸: ${terminal.rows}x${terminal.cols}`);

        // 调用父组件的尺寸变化回调
        if (onTerminalSizeChange) {
          onTerminalSizeChange({
            rows: terminal.rows,
            cols: terminal.cols,
          });
        }
      } catch (error) {
        logger.warn(`初始终端尺寸调整失败: ${error}`);
      }

      // 监听终端数据变化，自动滚动到底部
      terminal.onData(() => {
        requestAnimationFrame(() => terminal.scrollToBottom());
      });

      terminal.onKey(() => {
        requestAnimationFrame(() => terminal.scrollToBottom());
      });

      logger.info('终端实例初始化成功');

      // 通知父组件终端已就绪
      onTerminalReady(terminal, fitAddon, webLinksAddon);
    } catch (error) {
      logger.error(`初始化终端失败: ${error}`);
    } finally {
      // 无论成功或失败，都清除初始化标志
      isInitializingRef.current = false;
    }
  }, []); // 移除所有依赖项，避免循环依赖

  // 清理终端实例
  const cleanupTerminal = useCallback(() => {
    if (resizeObserverRef.current) {
      resizeObserverRef.current.disconnect();
      resizeObserverRef.current = null;
      logger.debug('ResizeObserver 已清理');
    }
    isInitializingRef.current = false; // 清除初始化标志
    lastSizeRef.current = null; // 清除尺寸记录
  }, []);

  // 统一的生命周期管理：初始化和清理
  useEffect(() => {
    let timer: NodeJS.Timeout | undefined;

    logger.debug(
      `TerminalBody useEffect 触发 - isReady: ${isReady}, status: ${status}`
    );

    // 当组件挂载且配置就绪时初始化终端
    if (isReady && terminalRef.current && !isInitializingRef.current) {
      logger.info('TerminalBody useEffect 满足初始化条件，准备初始化终端');
      timer = setTimeout(() => {
        logger.info('TerminalBody setTimeout 回调执行，开始初始化终端');
        initializeTerminal();
      }, 100); // 稍微延迟，确保动态导入的组件完全挂载
    } else {
      const reasons = [];
      if (!isReady) reasons.push('isReady=false');
      if (!terminalRef.current) reasons.push('terminalRef不存在');
      if (isInitializingRef.current) reasons.push('正在初始化中');
      logger.debug(`TerminalBody useEffect 跳过初始化 - 原因: ${reasons.join(', ')}`);
    }

    // 统一的清理函数
    return () => {
      logger.debug('TerminalBody useEffect 清理函数执行');
      if (timer) {
        clearTimeout(timer);
        logger.debug('TerminalBody clearTimeout 执行');
      }
      // 组件卸载时清理资源
      cleanupTerminal();
    };
  }, [isReady]); // 只依赖 isReady，避免循环依赖

  // 终端实例创建由页面层级的 TerminalControlPanel 统一管理
  // 这里不再需要自动创建逻辑，避免与页面层级的创建逻辑冲突

  // 调试日志（开发环境专用）
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      logger.debug(
        `TerminalBody 渲染 - isReady: ${isReady}, terminalRef: ${terminalRef.current ? '已挂载' : '未挂载'}, status: ${status}`
      );
    }
  }, [isReady, status]);

  return (
    <div className={`flex-1 border rounded-lg bg-black overflow-hidden ${className}`}>
      {/* 终端容器 - 固定高度，避免内容变化导致的尺寸循环 */}
      <div
        ref={terminalRef}
        className='w-full h-full min-h-[400px] relative'
        style={{ height: '100%', minHeight: '400px' }}
        data-testid='terminal-container'
      >
        {/* 空状态覆盖层 - 当没有instanceId时显示，完全覆盖终端但不影响尺寸计算 */}
        {!instanceId && emptyView && (
          <div className='absolute inset-0 flex items-center justify-center bg-black z-10'>
            {emptyView}
          </div>
        )}

        {/* 终端状态指示器 */}
        {instanceId && (
          <div className='absolute top-2 right-2 z-10 flex items-center space-x-2'>
            <div
              className={`w-2 h-2 rounded-full ${
                status === 'connected'
                  ? 'bg-green-500'
                  : status === 'ready'
                    ? 'bg-yellow-500'
                    : 'bg-gray-500'
              }`}
            />
            <span className='text-xs text-gray-400'>
              {status === 'connected'
                ? '已连接'
                : status === 'ready'
                  ? '就绪'
                  : '未连接'}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
