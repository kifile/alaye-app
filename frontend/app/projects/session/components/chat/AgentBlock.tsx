'use client';

import React, { useState, memo } from 'react';
import { Bot, ChevronDown, ChevronRight } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import type { ClaudeMessage } from '@/api/types';

interface AgentBlockProps {
  item: {
    type: 'subagent';
    agent_type: string;
    description: string;
    session: {
      session_id: string;
      title: string;
      message_count: number;
      messages: ClaudeMessage[];
    };
    tool_use_id: string;
  };
  theme?: 'user' | 'assistant';
}

/**
 * SubAgent 调用块组件
 * 默认只显示 agent 类型和描述，点击后展开查看详细的对话过程
 * 使用 ChatMessage 组件渲染每条消息，复用所有现有能力
 */
export const AgentBlock = memo(({ item }: AgentBlockProps) => {
  const [expanded, setExpanded] = useState(false);

  // 获取友好的 agent 类型名称
  const getAgentDisplayName = (agentType: string): string => {
    const agentNames: Record<string, string> = {
      uiux_reviewer: 'UI/UX Reviewer',
      general_purpose: 'General Purpose',
      explore: 'Explorer',
      statusline_setup: 'Statusline Setup',
      claude_code_guide: 'Claude Code Guide',
      rust_minimal_developer: 'Rust Developer',
    };
    return agentNames[agentType] || agentType;
  };

  const { session } = item;
  const messageCount = session.message_count || 0;

  return (
    <div className='my-3 rounded-lg border border-purple-200 dark:border-purple-800 bg-purple-50/50 dark:bg-purple-950/20 transition-all duration-200'>
      {/* 默认显示的摘要行 */}
      <div
        className='flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-purple-100/50 dark:hover:bg-purple-950/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2'
        onClick={() => setExpanded(!expanded)}
        role='button'
        tabIndex={0}
        aria-expanded={expanded}
        aria-label={expanded ? 'Collapse agent details' : 'Expand agent details'}
        onKeyDown={e => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setExpanded(!expanded);
          }
        }}
      >
        {/* 图标 */}
        <div className='p-1 rounded bg-purple-500'>
          <Bot className='h-3 w-3 text-white' />
        </div>

        {/* Agent 类型和描述 */}
        <div className='flex items-center gap-2 flex-1 min-w-0'>
          <span className='px-2 py-0.5 text-xs rounded font-mono font-medium bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300'>
            {getAgentDisplayName(item.agent_type)}
          </span>
          {item.description && (
            <span
              className='text-xs text-gray-600 dark:text-gray-400 truncate'
              title={item.description}
            >
              {item.description.length > 40
                ? `${item.description.slice(0, 40)}...`
                : item.description}
            </span>
          )}
          <span className='text-xs text-gray-500 dark:text-gray-500'>
            ({messageCount} message{messageCount !== 1 ? 's' : ''})
          </span>
        </div>

        {/* 展开指示器 */}
        <div className='ml-1 text-gray-500'>
          {expanded ? (
            <ChevronDown className='h-4 w-4' />
          ) : (
            <ChevronRight className='h-4 w-4' />
          )}
        </div>
      </div>

      {/* 展开的详细对话 */}
      {expanded && (
        <div className='px-3 pb-3 pt-1 border-t border-purple-200 dark:border-purple-800'>
          <div className='w-full mt-2 max-h-96 overflow-y-auto'>
            <div className='space-y-3'>
              {session.messages.map((msg, index) => (
                <ChatMessage key={msg.timestamp || index} message={msg} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

AgentBlock.displayName = 'AgentBlock';
