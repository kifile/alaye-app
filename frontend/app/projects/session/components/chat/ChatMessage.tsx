'use client';

import React, { useState, memo, useMemo } from 'react';
import { Bot, User } from 'lucide-react';
import type { ClaudeMessage } from '@/api/types';
import { MarkdownRenderer } from './MarkdownRenderer';
import { ThinkingBlock } from './ThinkingBlock';
import { ToolUseBlock } from './ToolUseBlock';
import type { ContentItem } from './ContentItem';

interface ChatMessageProps {
  message: ClaudeMessage;
  isLoading?: boolean;
}

export function ChatMessage({ message, isLoading }: ChatMessageProps) {
  const isUser = message.message?.role === 'user' || !message.message?.role;

  // 根据用户类型调整圆角样式
  const getBubbleClass = () => {
    if (isUser) {
      return 'bg-blue-500 text-white px-4 py-2.5 rounded-2xl rounded-tr-sm shadow-sm';
    }
    return 'bg-gray-100 dark:bg-gray-800 px-4 py-2.5 rounded-2xl rounded-tl-sm shadow-sm overflow-x-auto';
  };

  // 缓存 content 解析结果，避免每次渲染都重新处理
  const parsedContent = useMemo(() => {
    if (!message.message) return null;

    const rawContent = message.message.content;

    // 处理数组类型的 content（Assistant 消息）
    if (Array.isArray(rawContent)) {
      return rawContent;
    }

    // 处理字符串类型的 content（User 消息）
    let content = '';
    if (typeof rawContent === 'string') {
      content = rawContent;
    } else if (rawContent && typeof rawContent === 'object') {
      content = JSON.stringify(rawContent, null, 2);
    } else {
      content = String(rawContent || '');
    }

    return content;
  }, [message.message]);

  // 渲染 text 内容（Markdown）
  const renderTextContent = (text: string, index: number) => {
    return <MarkdownRenderer key={`text-${index}`} text={text} />;
  };

  // 渲染内容
  const renderContent = () => {
    if (!parsedContent) return null;

    // 处理数组类型的 content（Assistant 消息）
    if (Array.isArray(parsedContent)) {
      return (
        <div className='space-y-1'>
          {parsedContent.map((item: ContentItem, index: number) => {
            switch (item.type) {
              case 'tool_use':
                return <ToolUseBlock key={`tool-use-${index}`} item={item} />;
              case 'thinking':
                return <ThinkingBlock key={`thinking-${index}`} item={item} />;
              case 'text':
                return item.text ? renderTextContent(item.text, index) : null;
              default:
                return null;
            }
          })}
        </div>
      );
    }

    if (!parsedContent) return null;

    // 对 user 消息使用 pre-wrap 保留换行和空格
    return (
      <div className='whitespace-pre-wrap break-words text-sm'>{parsedContent}</div>
    );
  };

  return (
    <div
      className={`flex gap-3 mb-6 ${isUser ? 'justify-end' : 'justify-start'}`}
      data-testid='chat-message'
    >
      {isUser ? (
        <>
          <div className='max-w-[80%] flex flex-col items-end'>
            <div className='flex items-center gap-2 mb-1'>
              <span className='text-sm text-gray-600 dark:text-gray-400'>You</span>
              <User className='h-4 w-4 text-gray-600 dark:text-gray-400' />
            </div>
            <div className='bg-blue-500 text-white px-4 py-2.5 rounded-2xl rounded-tr-sm shadow-sm'>
              {renderContent()}
            </div>
            {message.timestamp && (
              <span className='text-xs text-gray-500 mt-1'>
                {new Date(message.timestamp).toLocaleTimeString()}
              </span>
            )}
          </div>
        </>
      ) : (
        <>
          <Bot className='h-6 w-6 text-gray-600 dark:text-gray-400 flex-shrink-0 mt-1' />
          <div className='max-w-[80%] flex flex-col items-start'>
            <div className='flex items-center gap-2 mb-1'>
              <span className='text-sm text-gray-600 dark:text-gray-400'>
                Assistant
              </span>
            </div>
            {isLoading ? (
              <div className='bg-gray-100 dark:bg-gray-800 px-4 py-2.5 rounded-2xl rounded-tl-sm'>
                <div className='flex space-x-1'>
                  <div className='w-2 h-2 bg-gray-400 rounded-full animate-bounce'></div>
                  <div className='w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100'></div>
                  <div className='w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200'></div>
                </div>
              </div>
            ) : (
              <div className={getBubbleClass()}>{renderContent()}</div>
            )}
            {message.timestamp && (
              <span className='text-xs text-gray-500 mt-1'>
                {new Date(message.timestamp).toLocaleTimeString()}
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// 使用 React.memo 优化渲染，只在 message 或 isLoading 变化时重新渲染
export default memo(ChatMessage, (prevProps, nextProps) => {
  return (
    prevProps.isLoading === nextProps.isLoading &&
    prevProps.message === nextProps.message
  );
});
