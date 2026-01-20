import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * 格式化时间为相对时间显示
 *
 * @param dateStr - ISO 8601 格式的日期字符串
 * @returns 格式化后的时间字符串，如 "5m ago", "2h ago", "3d ago" 等
 *
 * @example
 * formatTime("2024-01-18T10:30:00Z") // "5m ago"
 * formatTime("2024-01-17T10:30:00Z") // "1d ago"
 * formatTime("2024-01-01T10:30:00Z") // "2024-01-01"
 */
export function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  // Format as YYYY-MM-DD
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * 格式化聊天消息时间戳
 * 根据时间距离现在的时间返回不同的格式：
 * - 今天：只显示时间 (如 "22:32")
 * - 昨天：显示 "Yesterday 22:32"
 * - 本年内：显示月日 (如 "Jan 17")
 * - 更早：显示完整日期 (如 "2023-12-25")
 *
 * @param dateStr - ISO 8601 格式的日期字符串
 * @returns 格式化后的时间字符串
 *
 * @example
 * formatChatTime("2024-01-18T22:32:00Z") // "22:32" (如果是今天)
 * formatChatTime("2024-01-17T22:32:00Z") // "Yesterday 22:32"
 * formatChatTime("2024-01-01T22:32:00Z") // "Jan 1"
 * formatChatTime("2023-12-25T22:32:00Z") // "2023-12-25"
 */
export function formatChatTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const messageDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diffDays = Math.floor(
    (today.getTime() - messageDate.getTime()) / (1000 * 60 * 60 * 24)
  );

  // 如果是今天，只显示时间
  if (diffDays === 0) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // 如果是昨天
  if (diffDays === 1) {
    return `Yesterday ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  }

  // 如果是本年内，显示 MM-DD
  if (date.getFullYear() === now.getFullYear()) {
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }

  // 否则显示完整日期
  return date.toLocaleDateString([], {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}
