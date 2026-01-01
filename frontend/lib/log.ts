/**
 * 日志工具类 - 用于前端日志记录，通过 pywebview bridge 输出到后端
 */

import { is_pywebview, get_pywebview_api } from './env';

export type LogLevel = 'debug' | 'info' | 'warn' | 'warning' | 'error' | 'critical';

export interface LogEntry {
  level: LogLevel;
  message: string;
  category?: string;
  timestamp?: string;
}

class Logger {
  private category: string;

  constructor(category: string = 'frontend') {
    this.category = category;
  }

  /**
   * 发送日志到后端
   */
  private async sendLog(
    level: LogLevel,
    message: string,
    category?: string
  ): Promise<void> {
    try {
      const logEntry: LogEntry = {
        level,
        message,
        category: category || this.category,
        timestamp: new Date().toISOString(),
      };

      // 使用 is_pywebview 检查环境
      if (is_pywebview()) {
        const api = get_pywebview_api();
        if (api && api.log) {
          await api.log(logEntry);
        } else {
          // 如果 API 不可用，回退到 console
          this.fallbackToConsole(level, message);
        }
      } else {
        // 如果不在 pywebview 环境中，回退到 console
        this.fallbackToConsole(level, message);
      }
    } catch (error) {
      // 如果发送失败，回退到 console
      this.fallbackToConsole(level, message);
      console.error('Failed to send log to backend:', error);
    }
  }

  /**
   * 回退到 console 输出
   */
  private fallbackToConsole(level: LogLevel, message: string): void {
    const formattedMessage = `[${this.category}] ${message}`;

    switch (level) {
      case 'debug':
        console.debug(formattedMessage);
        break;
      case 'info':
        console.info(formattedMessage);
        break;
      case 'warn':
      case 'warning':
        console.warn(formattedMessage);
        break;
      case 'error':
        console.error(formattedMessage);
        break;
      case 'critical':
        console.error(`[CRITICAL] ${formattedMessage}`);
        break;
      default:
        console.log(formattedMessage);
    }
  }

  /**
   * 调试级别日志
   */
  debug(message: string, category?: string): void {
    this.sendLog('debug', message, category);
  }

  /**
   * 信息级别日志
   */
  info(message: string, category?: string): void {
    this.sendLog('info', message, category);
  }

  /**
   * 警告级别日志
   */
  warn(message: string, category?: string): void {
    this.sendLog('warn', message, category);
  }

  /**
   * 错误级别日志
   */
  error(message: string, category?: string): void {
    this.sendLog('error', message, category);
  }

  /**
   * 严重错误级别日志
   */
  critical(message: string, category?: string): void {
    this.sendLog('critical', message, category);
  }

  /**
   * 创建带有特定分类的子 logger
   */
  child(category: string): Logger {
    return new Logger(`${this.category}:${category}`);
  }
}

// 创建默认 logger 实例
export const logger = new Logger('frontend');

// 导出便捷方法，可以直接使用而无需创建实例
export const log = {
  debug: (message: string, category?: string) => logger.debug(message, category),
  info: (message: string, category?: string) => logger.info(message, category),
  warn: (message: string, category?: string) => logger.warn(message, category),
  error: (message: string, category?: string) => logger.error(message, category),
  critical: (message: string, category?: string) => logger.critical(message, category),
  child: (category: string) => logger.child(category),
};

// 默认导出 logger
export default logger;
