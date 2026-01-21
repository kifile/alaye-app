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
} from 'lucide-react';
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
  const messagesContainerRef = useRef<HTMLDivElement>(null);

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

  // 使用 useCallback 避免函数重新创建
  const loadSessionContent = useCallback(
    async (skipLoading = false) => {
      if (!sessionId) return;

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
          return;
        }

        setSession(response.data || null);
      } catch (error) {
        console.error('Failed to load session content:', error);
        toast.error('Failed to load session', {
          description: error instanceof Error ? error.message : 'Unknown error',
        });
      } finally {
        setLoading(false);
      }
    },
    [sessionId, projectId]
  );

  useEffect(() => {
    if (sessionId && projectId > 0) {
      // 首次加载时显示 loading
      loadSessionContent(false);
    } else {
      setSession(null);
    }
  }, [sessionId, projectId, loadSessionContent]);

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

          {/* 刷新按钮 */}
          <button
            onClick={() => loadSessionContent(true)}
            disabled={loading}
            className='p-1 hover:bg-gray-100 rounded transition-colors shrink-0 disabled:opacity-50 disabled:cursor-not-allowed'
            title='Refresh session'
          >
            <RefreshCw
              className={`h-4 w-4 text-gray-600 ${loading ? 'animate-spin' : ''}`}
            />
          </button>
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
