'use client';

import React, { useEffect, useState } from 'react';
import { MessageSquare, Loader2, Calendar } from 'lucide-react';
import { toast } from 'sonner';
import { scanSessions } from '@/api/api';
import type { ClaudeSessionInfo } from '@/api/types';
import { useTranslation } from 'react-i18next';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { formatTime } from '@/lib/utils';

interface SessionListProps {
  projectId: number;
  selectedSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
}

export function SessionList({
  projectId,
  selectedSessionId,
  onSessionSelect,
}: SessionListProps) {
  const { t } = useTranslation('projects');
  const [sessions, setSessions] = useState<ClaudeSessionInfo[]>([]);
  const [loading, setLoading] = useState(true);

  // 加载 session 列表
  const loadSessions = async () => {
    try {
      setLoading(true);
      const response = await scanSessions({ project_id: projectId });

      if (!response.success) {
        toast.error('Failed to load sessions', {
          description: response.error || 'Unknown error',
        });
        return;
      }

      setSessions(response.data || []);
    } catch (error) {
      console.error('Failed to load sessions:', error);
      toast.error('Failed to load sessions', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (projectId > 0) {
      loadSessions();
    }
  }, [projectId]);

  return (
    <div className='h-full flex flex-col bg-white'>
      {/* 标题 */}
      <div className='p-4 border-b border-gray-200'>
        <div className='flex items-center justify-between'>
          <h3 className='font-semibold text-sm text-gray-900'>Sessions</h3>
          <button
            onClick={loadSessions}
            className='p-1 hover:bg-gray-100 rounded transition-colors'
            title='Refresh'
          >
            <Loader2
              className={`h-4 w-4 text-gray-600 ${loading ? 'animate-spin' : ''}`}
            />
          </button>
        </div>
        <div className='text-xs text-gray-500 mt-1'>
          {sessions.length} {sessions.length === 1 ? 'session' : 'sessions'}
        </div>
      </div>

      {/* Session 列表 */}
      <div className='flex-1 overflow-y-auto'>
        {loading ? (
          <div className='flex items-center justify-center h-32'>
            <Loader2 className='h-6 w-6 animate-spin text-gray-400' />
          </div>
        ) : sessions.length === 0 ? (
          <div className='flex flex-col items-center justify-center h-32 text-center p-4'>
            <MessageSquare className='h-8 w-8 text-gray-400 mb-2' />
            <p className='text-sm text-gray-500'>No sessions found</p>
            <p className='text-xs text-gray-400 mt-1'>
              Sessions will appear here when you use Claude
            </p>
          </div>
        ) : (
          <div className='divide-y divide-gray-100'>
            {sessions.map(session => (
              <button
                key={session.session_id}
                onClick={() => onSessionSelect(session.session_id)}
                className={`w-full p-4 text-left hover:bg-gray-50 transition-colors ${
                  selectedSessionId === session.session_id
                    ? 'bg-blue-50 border-l-4 border-blue-500'
                    : 'border-l-4 border-transparent'
                }`}
              >
                <div className='flex items-start gap-3'>
                  <MessageSquare
                    className={`h-4 w-4 mt-0.5 flex-shrink-0 ${
                      selectedSessionId === session.session_id
                        ? 'text-blue-600'
                        : 'text-gray-400'
                    }`}
                  />
                  <div className='flex-1 min-w-0'>
                    <div className='flex items-center gap-2 mb-1'>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <p className='text-sm font-medium text-gray-900 truncate cursor-help'>
                              {session.is_agent_session && '🤖 '}
                              {session.title || session.session_id}
                            </p>
                          </TooltipTrigger>
                          <TooltipContent>
                            <div className='text-xs max-w-xs space-y-2'>
                              {session.title && (
                                <div>
                                  <div className='font-semibold mb-0.5'>Title</div>
                                  <div>{session.title}</div>
                                </div>
                              )}
                              <div>
                                <div className='font-semibold mb-0.5'>Session ID</div>
                                <div className='break-all font-mono text-[10px]'>
                                  {session.session_id}
                                </div>
                              </div>
                              <div>
                                <div className='font-semibold mb-0.5'>
                                  Last Modified
                                </div>
                                <div>
                                  {session.file_mtime_str
                                    ? formatTime(session.file_mtime_str)
                                    : 'Unknown'}
                                </div>
                              </div>
                            </div>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                      {session.is_agent_session && (
                        <span className='px-1.5 py-0.5 text-xs bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded border border-purple-300 dark:border-purple-700'>
                          Agent
                        </span>
                      )}
                    </div>
                    <div className='flex items-center gap-2 text-xs text-gray-500'>
                      <div className='flex items-center gap-1'>
                        <Calendar className='h-3 w-3' />
                        <span>
                          {session.file_mtime_str
                            ? formatTime(session.file_mtime_str)
                            : 'Unknown'}
                        </span>
                      </div>
                      <span className='text-gray-300'>•</span>
                      <span className='truncate font-mono text-[10px]'>
                        {session.session_id.slice(0, 8)}
                      </span>
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
