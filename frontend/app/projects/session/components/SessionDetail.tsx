'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  ArrowLeft,
  ArrowUp,
  ArrowDown,
  Loader2,
  MessageSquare,
  Calendar,
  RefreshCw,
  Copy,
  ChevronDown,
  Timer,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { readSessionContents } from '@/api/api';
import type { ClaudeSession } from '@/api/types';
import ChatMessage from './chat/ChatMessage';

// 自动刷新相关常量
const REFRESH_INTERVALS = {
  OFF: null,
  FAST: 1000, // 1s
  MEDIUM: 2000, // 2s (default)
  SLOW: 5000, // 5s
} as const;

const AUTO_REFRESH_TIME_THRESHOLD_MINUTES = 2; // 2分钟内自动开启刷新
const NEAR_BOTTOM_THRESHOLD = 100; // 距离底部 100px 以内视为"在底部"
const SCROLL_DELAY = 100; // 滚动延迟（ms）

interface SessionDetailProps {
  projectId: number;
  sessionId: string | null;
  onBack: () => void;
}

export function SessionDetail({ projectId, sessionId, onBack }: SessionDetailProps) {
  const [session, setSession] = useState<ClaudeSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState<number | null>(null); // null = 手动, 1000 = 1s, 2000 = 2s, 5000 = 5s
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const autoRefreshTimerRef = useRef<NodeJS.Timeout | null>(null);
  const requestIdRef = useRef<number>(0); // 用于追踪最新的请求，避免竞态条件

  // 滚动到顶部
  const scrollToTop = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return;
    container.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
  }, []);

  // 检查用户是否已经在底部（允许一定误差）
  const isNearBottom = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return true;
    return (
      container.scrollHeight - container.scrollTop - container.clientHeight <=
      NEAR_BOTTOM_THRESHOLD
    );
  }, []);

  // 判断是否应该自动开启自动刷新（文件修改时间在阈值时间内，默认使用 MEDIUM）
  const getAutoRefreshInterval = useCallback((sessionData: ClaudeSession | null) => {
    if (!sessionData?.file_mtime_str) return null;

    // 解析日期字符串 "YYYY-MM-DD HH:MM:SS"
    // 将空格替换为 'T' 以确保兼容性，但不改变整体格式
    const dateStr = sessionData.file_mtime_str.replace(' ', 'T');
    const fileTime = new Date(dateStr);

    if (isNaN(fileTime.getTime())) {
      console.warn('Invalid file_mtime_str format:', sessionData.file_mtime_str);
      return null;
    }

    const now = new Date();
    const diffInMinutes = (now.getTime() - fileTime.getTime()) / (1000 * 60);

    return diffInMinutes <= AUTO_REFRESH_TIME_THRESHOLD_MINUTES
      ? REFRESH_INTERVALS.MEDIUM
      : null;
  }, []);

  // 使用 useCallback 避免函数重新创建
  const loadSessionContent = useCallback(
    async (
      skipLoading = false,
      scrollToBottomAfterLoad = false
    ): Promise<ClaudeSession | null> => {
      if (!sessionId) return null;

      // 只在首次加载或明确需要时显示 loading
      if (!skipLoading) {
        setLoading(true);
      }

      try {
        const response = await readSessionContents({
          project_id: projectId,
          session_id: sessionId,
        });

        if (!response.success) {
          toast.error('Failed to load session', {
            description: response.error || 'Unknown error',
          });
          return null;
        }

        const sessionData = response.data || null;
        setSession(sessionData);

        // 自动滚动到底部（仅在自动刷新模式下，且用户已经在底部时）
        if (scrollToBottomAfterLoad && isNearBottom()) {
          // 使用 setTimeout 等待 DOM 更新后再滚动
          setTimeout(() => scrollToBottom(), SCROLL_DELAY);
        }

        return sessionData;
      } catch (error) {
        console.error('Failed to load session content:', error);
        toast.error('Failed to load session', {
          description: error instanceof Error ? error.message : 'Unknown error',
        });
        return null;
      } finally {
        setLoading(false);
      }
    },
    [sessionId, projectId, scrollToBottom, isNearBottom]
  );

  // 使用 ref 保持 loadSessionContent 的稳定引用，避免 useEffect 依赖循环
  const loadSessionContentRef = useRef(loadSessionContent);
  loadSessionContentRef.current = loadSessionContent;

  useEffect(() => {
    if (sessionId && projectId > 0) {
      // 生成新的请求 ID
      const requestId = ++requestIdRef.current;

      // 首次加载时显示 loading，并获取 session 数据
      loadSessionContent(false).then(sessionData => {
        // 只处理最新的请求，忽略过期的响应
        if (requestId !== requestIdRef.current) return;

        if (sessionData) {
          // 根据 session 的文件修改时间判断刷新间隔
          const interval = getAutoRefreshInterval(sessionData);
          setRefreshInterval(interval);

          // 如果开启了自动刷新（1s、2s、5s），自动滚动到底部
          if (interval !== null) {
            setTimeout(() => scrollToBottom(), SCROLL_DELAY);
          }
        }
      });
    } else {
      setSession(null);
      setRefreshInterval(null);
    }

    // 清理函数：组件卸载时清理定时器
    return () => {
      if (autoRefreshTimerRef.current) {
        clearInterval(autoRefreshTimerRef.current);
        autoRefreshTimerRef.current = null;
      }
    };
  }, [
    sessionId,
    projectId,
    loadSessionContent,
    getAutoRefreshInterval,
    scrollToBottom,
  ]);

  // 处理自动刷新定时器
  useEffect(() => {
    // 清理之前的定时器
    if (autoRefreshTimerRef.current) {
      clearInterval(autoRefreshTimerRef.current);
      autoRefreshTimerRef.current = null;
    }

    // 如果设置了刷新间隔，启动定时器
    if (refreshInterval && sessionId) {
      autoRefreshTimerRef.current = setInterval(() => {
        // 跳过 loading 状态，并自动滚动到底部
        // 使用 ref 来避免依赖 loadSessionContent
        loadSessionContentRef.current(true, true);
      }, refreshInterval);
    }

    // 清理函数
    return () => {
      if (autoRefreshTimerRef.current) {
        clearInterval(autoRefreshTimerRef.current);
        autoRefreshTimerRef.current = null;
      }
    };
  }, [refreshInterval, sessionId]); // 移除 loadSessionContent 依赖

  if (!sessionId) {
    return (
      <div className='h-full flex flex-col items-center justify-center text-center p-8 bg-gray-50'>
        <MessageSquare className='h-16 w-16 text-gray-400 mb-4' />
        <h3 className='text-lg font-semibold text-gray-900 mb-2'>
          No Session Selected
        </h3>
        <p className='text-sm text-gray-500 mb-4'>
          Select a session from the sidebar to view the conversation
        </p>
      </div>
    );
  }

  if (loading && !session) {
    return (
      <div className='h-full flex items-center justify-center'>
        <div className='text-center'>
          <Loader2 className='h-8 w-8 animate-spin text-gray-400 mx-auto mb-4' />
          <p className='text-sm text-gray-500'>Loading session...</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className='h-full flex items-center justify-center text-center p-8'>
        <div>
          <MessageSquare className='h-16 w-16 text-gray-400 mx-auto mb-4' />
          <h3 className='text-lg font-semibold text-gray-900 mb-2'>
            Session Not Found
          </h3>
          <p className='text-sm text-gray-500 mb-4'>
            The selected session could not be loaded
          </p>
          <button
            onClick={onBack}
            className='px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors'
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className='h-full flex flex-col bg-white'>
      {/* Header */}
      <div className='border-b border-gray-200 px-4 py-3 bg-white'>
        {/* 主要信息 */}
        <div className='flex items-center gap-3'>
          {/* 返回按钮 */}
          <button
            onClick={onBack}
            className='p-1.5 hover:bg-gray-100 rounded-lg transition-colors shrink-0'
            title='Back to session list'
          >
            <ArrowLeft className='h-4 w-4 text-gray-600' />
          </button>

          {/* 标题和下方信息 - 限制最大宽度，确保刷新按钮可见 */}
          <div className='flex flex-col gap-0.5 min-w-0 flex-1 max-w-[calc(100%-8rem)]'>
            {/* 标题和徽章 */}
            <div className='flex items-center gap-2'>
              <h2 className='text-base font-semibold text-gray-900 truncate'>
                {session.is_agent_session && '🤖 '}
                {session.title || 'Untitled Session'}
              </h2>
              {session.is_agent_session && (
                <span className='shrink-0 px-1.5 py-0.5 text-[10px] bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded border border-purple-300 dark:border-purple-700'>
                  Agent
                </span>
              )}
            </div>

            {/* 消息数、时间、Session ID */}
            <div className='flex items-center gap-1.5 text-xs text-gray-500'>
              {/* 消息数量 */}
              <div className='flex items-center gap-1 shrink-0'>
                <MessageSquare className='h-3 w-3' />
                <span className='font-medium'>{session.message_count}</span>
              </div>

              {/* 时间 */}
              {session.last_modified_str && (
                <>
                  <span className='text-gray-300'>•</span>
                  <div className='flex items-center gap-1 shrink-0'>
                    <Calendar className='h-3 w-3' />
                    <span className='truncate'>{session.last_modified_str}</span>
                  </div>
                </>
              )}

              {/* Session ID */}
              <span className='text-gray-300'>•</span>
              <div className='flex items-center gap-1 min-w-0'>
                <span className='truncate font-mono'>{session.session_id}</span>
                <button
                  type='button'
                  onClick={e => {
                    e.stopPropagation();
                    navigator.clipboard
                      .writeText(session.session_id)
                      .then(() => toast.success('Session ID copied to clipboard'))
                      .catch(() => toast.error('Failed to copy'));
                  }}
                  className='shrink-0 p-0.5 hover:bg-gray-100 rounded transition-colors text-gray-400 hover:text-gray-600'
                  title='Copy session ID'
                >
                  <Copy className='h-3 w-3' />
                </button>
              </div>
            </div>
          </div>

          {/* 手动刷新按钮 */}
          <button
            onClick={() => loadSessionContent(true)}
            disabled={loading}
            className='p-1.5 hover:bg-gray-100 rounded transition-colors shrink-0 disabled:opacity-50 disabled:cursor-not-allowed'
            title='Refresh session now'
          >
            <RefreshCw
              className={`h-4 w-4 text-gray-600 ${loading ? 'animate-spin' : ''}`}
            />
          </button>

          {/* 刷新间隔选择下拉菜单 */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                disabled={loading}
                className='px-2 py-1 text-xs font-medium border border-gray-300 rounded hover:bg-gray-50 transition-colors shrink-0 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1'
              >
                <Timer
                  className={`h-3 w-3 text-gray-600 ${refreshInterval ? 'animate-pulse' : ''}`}
                />
                <span>
                  {refreshInterval === null
                    ? 'Off'
                    : refreshInterval === REFRESH_INTERVALS.FAST
                      ? '1s'
                      : refreshInterval === REFRESH_INTERVALS.MEDIUM
                        ? '2s'
                        : '5s'}
                </span>
                <ChevronDown className='h-3 w-3 text-gray-500' />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align='end'>
              <DropdownMenuItem
                onClick={() => setRefreshInterval(REFRESH_INTERVALS.OFF)}
                className={
                  refreshInterval === REFRESH_INTERVALS.OFF ? 'bg-gray-100' : ''
                }
              >
                Off
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setRefreshInterval(REFRESH_INTERVALS.FAST)}
                className={
                  refreshInterval === REFRESH_INTERVALS.FAST ? 'bg-gray-100' : ''
                }
              >
                1s
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setRefreshInterval(REFRESH_INTERVALS.MEDIUM)}
                className={
                  refreshInterval === REFRESH_INTERVALS.MEDIUM ? 'bg-gray-100' : ''
                }
              >
                2s
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setRefreshInterval(REFRESH_INTERVALS.SLOW)}
                className={
                  refreshInterval === REFRESH_INTERVALS.SLOW ? 'bg-gray-100' : ''
                }
              >
                5s
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Messages */}
      <div className='flex-1 overflow-y-auto p-6 relative' ref={messagesContainerRef}>
        {session.messages.length === 0 ? (
          <div className='flex items-center justify-center h-full'>
            <p className='text-sm text-gray-500'>No messages in this session</p>
          </div>
        ) : (
          <div className='max-w-4xl mx-auto'>
            <div className='w-full'>
              {session.messages.map((message, index) => (
                <ChatMessage
                  key={`${message.message?.id || 'msg'}-${index}`}
                  message={message}
                />
              ))}
            </div>
          </div>
        )}

        {/* 浮动滚动按钮 */}
        <div className='fixed bottom-20 right-12 flex flex-col gap-2'>
          <button
            onClick={scrollToTop}
            className='p-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all duration-200'
            title='Scroll to top'
          >
            <ArrowUp className='h-4 w-4 text-gray-600 dark:text-gray-400' />
          </button>
          <button
            onClick={scrollToBottom}
            className='p-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all duration-200'
            title='Scroll to bottom'
          >
            <ArrowDown className='h-4 w-4 text-gray-600 dark:text-gray-400' />
          </button>
        </div>
      </div>
    </div>
  );
}
