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
