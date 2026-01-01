/**
 * 前端事件总线模块
 * 负责管理后端事件的监听、注册和解除注册
 * 支持 PyWebView 和 FastAPI (WebSocket) 两种模式
 */

import { log } from '@/lib/log';
import { is_pywebview } from '@/lib/env';

// 定义后端事件的数据结构
export interface BackendEvent {
  event_type: string;
  data: Record<string, any>;
  timestamp: string;
}

// 定义 WebSocket 事件消息结构
export interface WebSocketEventMessage {
  event_type: string;
  data: Record<string, any>;
  timestamp: string;
}

// 定义事件处理器函数类型
export type EventHandler = (event: CustomEvent<BackendEvent>) => void;

// WebSocket 连接管理
let websocket: WebSocket | null = null;
let wsReconnectTimer: NodeJS.Timeout | null = null;
let wsReconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000; // 3 seconds

/**
 * 初始化 WebSocket 连接
 */
function initWebSocket(): void {
  if (websocket || is_pywebview()) {
    return; // 已经连接或在 PyWebView 模式下不需要 WebSocket
  }

  try {
    const wsUrl = 'ws://127.0.0.1:8000/ws';
    log.info(`Connecting to WebSocket: ${wsUrl}`, 'event_bus');

    websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      log.info('WebSocket connected successfully', 'event_bus');
      wsReconnectAttempts = 0; // 重置重连计数

      // 发送 ping 消息测试连接
      websocket?.send(JSON.stringify({ type: 'ping' }));
    };

    websocket.onmessage = event => {
      try {
        const message = JSON.parse(event.data) as WebSocketEventMessage;

        // 处理 pong 响应
        if (message.event_type === 'pong' || (message as any).type === 'pong') {
          log.debug('Received pong from server', 'event_bus');
          return;
        }

        // 处理事件消息
        if (message.event_type) {
          const backendEvent: BackendEvent = {
            event_type: message.event_type,
            data: message.data,
            timestamp: message.timestamp,
          };

          // 触发自定义事件
          const customEvent = new CustomEvent(message.event_type, {
            detail: backendEvent,
          });
          window.dispatchEvent(customEvent);

          log.info(
            `Received backend event via WebSocket: ${message.event_type}`,
            'event_bus'
          );
        }
      } catch (error) {
        log.error(`Failed to parse WebSocket message: ${error}`, 'event_bus');
      }
    };

    websocket.onclose = event => {
      log.warn(
        `WebSocket connection closed: ${event.code} - ${event.reason}`,
        'event_bus'
      );
      websocket = null;

      // 尝试重新连接
      if (wsReconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        wsReconnectAttempts++;
        log.info(
          `Attempting to reconnect (${wsReconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`,
          'event_bus'
        );

        wsReconnectTimer = setTimeout(() => {
          initWebSocket();
        }, RECONNECT_DELAY);
      } else {
        log.error('Max reconnect attempts reached, giving up', 'event_bus');
      }
    };

    websocket.onerror = error => {
      log.error(`WebSocket error: ${error}`, 'event_bus');
    };

    // 定期发送 ping 消息保持连接活跃
    setInterval(() => {
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // 每30秒发送一次ping
  } catch (error) {
    log.error(`Failed to initialize WebSocket: ${error}`, 'event_bus');
  }
}

/**
 * 关闭 WebSocket 连接
 */
function closeWebSocket(): void {
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = null;
  }

  if (websocket) {
    websocket.close();
    websocket = null;
    log.info('WebSocket connection closed', 'event_bus');
  }
}

// 定义可用的事件类型
export const EVENT_TYPES = {
  // API相关事件
  API_SUCCESS: 'api_success',
  API_ERROR: 'api_error',

  // 用户操作事件
  USER_ACTION: 'user_action',

  // 系统事件
  SYSTEM_UPDATE: 'system_update',
  DATA_SYNC: 'data_sync',

  // 错误事件
  ERROR: 'error',

  // 其他自定义事件
  UNKNOWN: 'unknown_event',
} as const;

export type EventType = (typeof EVENT_TYPES)[keyof typeof EVENT_TYPES];

/**
 * 前端事件总线类
 */
class FrontendEventBus {
  private eventListeners: Map<EventType, Set<EventHandler>> = new Map();
  private isInitialized = false;

  /**
   * 初始化事件总线
   */
  initialize(): void {
    if (this.isInitialized) {
      log.warn('FrontendEventBus already initialized', 'event_bus');
      return;
    }

    // 为所有已知事件类型创建空的监听器集合
    Object.values(EVENT_TYPES).forEach(eventType => {
      this.eventListeners.set(eventType, new Set());
    });

    this.isInitialized = true;
    log.info('FrontendEventBus initialized', 'event_bus');

    // 如果不在 PyWebView 模式，初始化 WebSocket 连接
    if (!is_pywebview()) {
      initWebSocket();
    }
  }

  /**
   * 注册事件监听器
   * @param eventType 事件类型
   * @param handler 事件处理函数
   * @param options 可选的监听器选项
   */
  registerEventListener(
    eventType: EventType,
    handler: EventHandler,
    options?: AddEventListenerOptions
  ): void {
    if (!this.isInitialized) {
      this.initialize();
    }

    // 获取或创建该事件类型的监听器集合
    const listeners = this.eventListeners.get(eventType);
    if (!listeners) {
      // 如果事件类型不存在，创建一个新的集合
      this.eventListeners.set(eventType, new Set([handler]));
    } else {
      // 添加到现有集合
      listeners.add(handler);
    }

    // 添加到全局事件监听器
    window.addEventListener(eventType, handler as EventListener, options);

    log.info(`Event listener registered for: ${eventType}`, 'event_bus');
  }

  /**
   * 解除注册事件监听器
   * @param eventType 事件类型
   * @param handler 事件处理函数
   */
  unregisterEventListener(eventType: EventType, handler: EventHandler): void {
    const listeners = this.eventListeners.get(eventType);
    if (listeners) {
      listeners.delete(handler);

      // 从全局事件监听器中移除
      window.removeEventListener(eventType, handler as EventListener);

      log.info(`Event listener unregistered for: ${eventType}`, 'event_bus');
    }
  }

  /**
   * 解除注册特定事件类型的所有监听器
   * @param eventType 事件类型
   */
  unregisterAllListeners(eventType: EventType): void {
    const listeners = this.eventListeners.get(eventType);
    if (listeners) {
      // 移除所有监听器
      listeners.forEach(handler => {
        window.removeEventListener(eventType, handler as EventListener);
      });

      // 清空集合
      listeners.clear();

      log.info(`All event listeners unregistered for: ${eventType}`, 'event_bus');
    }
  }

  /**
   * 解除注册所有事件监听器
   */
  clearAllListeners(): void {
    this.eventListeners.forEach((listeners, eventType) => {
      listeners.forEach(handler => {
        window.removeEventListener(eventType, handler as EventListener);
      });
    });

    // 清空所有集合
    this.eventListeners.clear();

    log.info('All event listeners cleared', 'event_bus');

    // 关闭 WebSocket 连接
    if (!is_pywebview()) {
      closeWebSocket();
    }
  }

  /**
   * 获取特定事件类型的监听器数量
   * @param eventType 事件类型
   * @returns 监听器数量
   */
  getListenerCount(eventType: EventType): number {
    const listeners = this.eventListeners.get(eventType);
    return listeners ? listeners.size : 0;
  }

  /**
   * 获取所有已注册的事件类型
   * @returns 事件类型数组
   */
  getRegisteredEventTypes(): EventType[] {
    const types: EventType[] = [];
    this.eventListeners.forEach((listeners, eventType) => {
      if (listeners.size > 0) {
        types.push(eventType);
      }
    });
    return types;
  }

  /**
   * 创建通用的事件处理函数包装器
   * @param customHandler 自定义处理逻辑
   * @param logCategory 日志分类
   * @returns 包装后的事件处理函数
   */
  createEventHandler(
    customHandler: (event: BackendEvent) => void,
    logCategory: string = 'custom'
  ): EventHandler {
    return (event: CustomEvent<BackendEvent>) => {
      const backendEvent = event.detail;
      log.info(`Received backend event: ${backendEvent.event_type}`, logCategory);

      // 调用自定义处理逻辑
      try {
        customHandler(backendEvent);
      } catch (error) {
        log.error(
          `Error in event handler for ${backendEvent.event_type}: ${error}`,
          logCategory
        );
      }
    };
  }

  /**
   * 创建调试用的事件处理函数（用于测试）
   * @param logCategory 日志分类
   * @returns 调试用的事件处理函数
   */
  createDebugHandler(logCategory: string = 'debug'): EventHandler {
    return this.createEventHandler((event: BackendEvent) => {
      console.log(`[DEBUG] Backend Event (${logCategory}):`, event);
      log.debug(`Backend event data: ${JSON.stringify(event)}`, logCategory);
    }, logCategory);
  }
}

// 创建全局事件总线实例
export const frontendEventBus = new FrontendEventBus();

/**
 * React Hook: 使用事件监听器
 * @param eventType 事件类型
 * @param handler 事件处理函数
 * @param deps 依赖数组（类似useEffect的依赖）
 */
export const useBackendEventListener = (
  eventType: EventType,
  handler: EventHandler,
  deps: React.DependencyList = []
) => {
  // 注意：这个hook需要在React组件中使用
  // 在实际使用时需要导入React和useEffect
  return {
    register: () => frontendEventBus.registerEventListener(eventType, handler),
    unregister: () => frontendEventBus.unregisterEventListener(eventType, handler),
  };
};

// 导出便捷函数
export const registerEventListener = (
  eventType: EventType,
  handler: EventHandler,
  options?: AddEventListenerOptions
): void => {
  frontendEventBus.registerEventListener(eventType, handler, options);
};

export const unregisterEventListener = (
  eventType: EventType,
  handler: EventHandler
): void => {
  frontendEventBus.unregisterEventListener(eventType, handler);
};

export const clearAllListeners = (): void => {
  frontendEventBus.clearAllListeners();
};

// 导出 WebSocket 相关函数
export { initWebSocket, closeWebSocket };

/**
 * 获取 WebSocket 连接状态
 * @returns WebSocket 连接状态
 */
export const getWebSocketStatus = (): string => {
  if (!websocket) {
    return 'DISCONNECTED';
  }

  switch (websocket.readyState) {
    case WebSocket.CONNECTING:
      return 'CONNECTING';
    case WebSocket.OPEN:
      return 'OPEN';
    case WebSocket.CLOSING:
      return 'CLOSING';
    case WebSocket.CLOSED:
      return 'CLOSED';
    default:
      return 'UNKNOWN';
  }
};

// 默认导出事件总线实例
export default frontendEventBus;
