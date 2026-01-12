'use client';

import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { ArrowLeft, Loader2, MessageSquare, Calendar, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { readSessionContents } from '@/api/api';
import type { ClaudeSession } from '@/api/types';
import ChatMessage from './chat/ChatMessage';

interface SessionDetailProps {
  projectId: number;
  sessionId: string | null;
  onBack: () => void;
}

export function SessionDetail({ projectId, sessionId, onBack }: SessionDetailProps) {
  const [session, setSession] = useState<ClaudeSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [visibleCount, setVisibleCount] = useState(20); // 初始显示20条消息
  const observerTarget = useRef<HTMLDivElement>(null);

  // 使用 useCallback 避免函数重新创建
  const loadSessionContent = useCallback(async () => {
    if (!sessionId) return;

    try {
      setLoading(true);
      const response = await readSessionContents({
        project_id: projectId,
        session_id: sessionId,
      });

      if (!response.success) {
        toast.error('Failed to load session', {
          description: response.error || 'Unknown error',
        });
        return;
      }

      setSession(response.data || null);
      // 重置可见数量
      setVisibleCount(20);
    } catch (error) {
      console.error('Failed to load session content:', error);
      toast.error('Failed to load session', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setLoading(false);
    }
  }, [sessionId, projectId]);

  useEffect(() => {
    if (sessionId && projectId > 0) {
      loadSessionContent();
    } else {
      setSession(null);
    }
  }, [sessionId, projectId, loadSessionContent]);

  // 实现无限滚动加载更多消息
  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (
          entries[0].isIntersecting &&
          session &&
          visibleCount < session.messages.length
        ) {
          setVisibleCount(prev => Math.min(prev + 20, session.messages.length));
        }
      },
      { threshold: 0.1 }
    );

    const currentTarget = observerTarget.current;
    if (currentTarget) {
      observer.observe(currentTarget);
    }

    return () => {
      if (currentTarget) {
        observer.unobserve(currentTarget);
      }
    };
  }, [session, visibleCount]);

  // 使用 useMemo 缓存可见的消息列表
  const visibleMessages = useMemo(() => {
    if (!session) return [];
    return session.messages.slice(0, visibleCount);
  }, [session, visibleCount]);

  const hasMore = session && visibleCount < session.messages.length;

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

  if (loading) {
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
      <div className='border-b border-gray-200 px-4 py-2 bg-white'>
        <div className='flex items-center gap-3'>
          {/* 返回按钮 */}
          <button
            onClick={onBack}
            className='p-1.5 hover:bg-gray-100 rounded-lg transition-colors shrink-0'
            title='Back to session list'
          >
            <ArrowLeft className='h-4 w-4 text-gray-600' />
          </button>

          {/* 刷新按钮 */}
          <button
            onClick={loadSessionContent}
            disabled={loading}
            className='p-1.5 hover:bg-gray-100 rounded-lg transition-colors shrink-0 disabled:opacity-50 disabled:cursor-not-allowed'
            title='Refresh session'
          >
            <RefreshCw className={`h-4 w-4 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {/* 标题和徽章 */}
          <div className='flex items-center gap-2 shrink-0'>
            <h2 className='text-sm font-semibold text-gray-900'>
              {session.is_agent_session && '🤖 '}
              {session.session_id.slice(0, 8)}...
            </h2>
            {session.is_agent_session && (
              <span className='px-1.5 py-0.5 text-[10px] bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded'>
                Agent
              </span>
            )}
          </div>

          {/* 分隔线 */}
          <div className='w-px h-4 bg-gray-200 shrink-0' />

          {/* 元数据 */}
          <div className='flex items-center gap-3 text-xs text-gray-500 min-w-0'>
            <div className='flex items-center gap-1 shrink-0'>
              <MessageSquare className='h-3 w-3' />
              <span>{session.message_count}</span>
            </div>
            {session.last_modified_str && (
              <div className='flex items-center gap-1 shrink-0'>
                <Calendar className='h-3 w-3' />
                <span className='truncate'>{session.last_modified_str}</span>
              </div>
            )}
            {session.project_path && (
              <div className='flex items-center gap-1 min-w-0'>
                <span className='truncate text-gray-400' title={session.project_path}>
                  {session.project_path}
                </span>
              </div>
            )}
            {session.git_branch && (
              <div className='flex items-center gap-1 shrink-0 px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded'>
                <svg className='h-3 w-3' fill='currentColor' viewBox='0 0 24 24'>
                  <path d='M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z' />
                </svg>
                <span className='truncate'>{session.git_branch}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className='flex-1 overflow-y-auto p-6'>
        {session.messages.length === 0 ? (
          <div className='flex items-center justify-center h-full'>
            <p className='text-sm text-gray-500'>No messages in this session</p>
          </div>
        ) : (
          <div className='max-w-4xl mx-auto'>
            {visibleMessages.map((message, index) => (
              <ChatMessage
                key={`${message.message?.id || 'msg'}-${index}`}
                message={message}
              />
            ))}
            {hasMore && (
              <div ref={observerTarget} className='flex justify-center py-4'>
                <div className='flex items-center gap-2 text-sm text-gray-500'>
                  <Loader2 className='h-4 w-4 animate-spin' />
                  <span>
                    Loading {visibleCount} of {session.messages.length} messages...
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
