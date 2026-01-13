'use client';

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
  ReactNode,
} from 'react';
import { getSetting, updateSetting } from '@/api/api';

interface AnalyticsContextType {
  // 分析是否已启用
  isEnabled: boolean;
  // 是否正在加载中
  isLoading: boolean;
  // 启用分析
  enableAnalytics: () => Promise<void>;
  // 禁用分析
  disableAnalytics: () => Promise<void>;
  // 切换分析状态
  toggleAnalytics: () => Promise<void>;
}

const AnalyticsContext = createContext<AnalyticsContextType | undefined>(undefined);

export function useAnalytics() {
  const context = useContext(AnalyticsContext);
  if (context === undefined) {
    throw new Error('useAnalytics must be used within an AnalyticsProvider');
  }
  return context;
}

interface AnalyticsProviderProps {
  children: ReactNode;
  websiteId?: string;
  collectUrl?: string;
}

/**
 * Umami 内部组件 - 集成在 Provider 中
 */
function UmamiAnalyticsInternal({
  websiteId,
  collectUrl,
  isEnabled,
}: {
  websiteId?: string;
  collectUrl?: string;
  isEnabled: boolean;
}) {
  const initializedRef = useRef(false);
  const scriptRef = useRef<HTMLScriptElement | null>(null);

  /**
   * 加载 Umami 脚本
   */
  const loadUmamiScript = useCallback(() => {
    try {
      // 从环境变量获取配置
      const umamiWebsiteId = websiteId || process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID;
      const umamiCollectUrl = collectUrl || process.env.NEXT_PUBLIC_UMAMI_COLLECT_URL;

      if (!umamiWebsiteId || !umamiCollectUrl) {
        console.warn(
          '[Umami] Missing configuration (NEXT_PUBLIC_UMAMI_WEBSITE_ID or NEXT_PUBLIC_UMAMI_COLLECT_URL)'
        );
        return;
      }

      // 如果脚本已存在，先移除
      if (scriptRef.current) {
        scriptRef.current.remove();
      }

      // 初始化 Umami 跟踪脚本
      const script = document.createElement('script');
      script.async = true;
      script.defer = true;
      script.dataset.websiteId = umamiWebsiteId;
      script.src = `${umamiCollectUrl.replace('/api/collect', '')}/script.js`;
      script.dataset.dataHostUrl = umamiCollectUrl;

      // 对于桌面应用，配置自动跟踪
      script.setAttribute('data-auto-track', 'true');
      script.setAttribute('data-exclude-search', 'false');
      script.setAttribute('data-do-not-track', 'false');

      scriptRef.current = script;
      document.head.appendChild(script);

      // 监听脚本加载完成
      script.onload = () => {
        console.log('[Umami] Analytics initialized successfully');

        // 发送初始页面视图
        if ((window as any).umami) {
          (window as any).umami.track();
        }
      };

      script.onerror = () => {
        console.error('[Umami] Failed to load analytics script');
        scriptRef.current = null;
      };
    } catch (error) {
      console.error('[Umami] Load script error:', error);
    }
  }, [websiteId, collectUrl]);

  /**
   * 卸载 Umami 脚本
   */
  const unloadUmamiScript = useCallback(() => {
    if (scriptRef.current) {
      scriptRef.current.remove();
      scriptRef.current = null;
      console.log('[Umami] Analytics script removed');

      // 清理 window.umami 对象
      if (typeof window !== 'undefined' && (window as any).umami) {
        delete (window as any).umami;
      }
    }
  }, []);

  /**
   * 监听 isEnabled 状态变化，动态加载/卸载脚本
   */
  useEffect(() => {
    // 避免重复初始化
    if (initializedRef.current) {
      // 已初始化，只响应状态变化
      if (isEnabled) {
        loadUmamiScript();
      } else {
        unloadUmamiScript();
      }
      return;
    }

    initializedRef.current = true;

    // 首次初始化
    if (isEnabled) {
      loadUmamiScript();
    } else {
      console.log('[Umami] Analytics disabled by user');
    }

    // 清理函数
    return () => {
      unloadUmamiScript();
    };
  }, [isEnabled, loadUmamiScript, unloadUmamiScript]);

  return null;
}

/**
 * Analytics Provider
 * 管理分析功能的启用/禁用状态，内部集成 UmamiAnalytics
 */
export function AnalyticsProvider({
  children,
  websiteId,
  collectUrl,
}: AnalyticsProviderProps) {
  const [isEnabled, setIsEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // 从后端加载初始状态
  useEffect(() => {
    const loadInitialState = async () => {
      try {
        const response = await getSetting({ key: 'analytics.enabled' });
        const enabled = response.success ? response.data === 'true' : false;
        setIsEnabled(enabled);
        console.log(
          `[AnalyticsProvider] Initial state: ${enabled ? 'enabled' : 'disabled'}`
        );
      } catch (error) {
        console.error('[AnalyticsProvider] Failed to load initial state:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadInitialState();
  }, []);

  // 启用分析
  const enableAnalytics = useCallback(async () => {
    if (isEnabled) {
      console.log('[AnalyticsProvider] Analytics already enabled');
      return;
    }

    try {
      const response = await updateSetting({
        key: 'analytics.enabled',
        value: 'true',
      });

      if (response.success) {
        setIsEnabled(true);
        console.log('[AnalyticsProvider] Analytics enabled');
      } else {
        console.error(
          '[AnalyticsProvider] Failed to enable analytics:',
          response.error
        );
        throw new Error(response.error);
      }
    } catch (error) {
      console.error('[AnalyticsProvider] Error enabling analytics:', error);
      throw error;
    }
  }, [isEnabled]);

  // 禁用分析
  const disableAnalytics = useCallback(async () => {
    if (!isEnabled) {
      console.log('[AnalyticsProvider] Analytics already disabled');
      return;
    }

    try {
      const response = await updateSetting({
        key: 'analytics.enabled',
        value: 'false',
      });

      if (response.success) {
        setIsEnabled(false);
        console.log('[AnalyticsProvider] Analytics disabled');
      } else {
        console.error(
          '[AnalyticsProvider] Failed to disable analytics:',
          response.error
        );
        throw new Error(response.error);
      }
    } catch (error) {
      console.error('[AnalyticsProvider] Error disabling analytics:', error);
      throw error;
    }
  }, [isEnabled]);

  // 切换分析状态
  const toggleAnalytics = useCallback(async () => {
    if (isEnabled) {
      await disableAnalytics();
    } else {
      await enableAnalytics();
    }
  }, [isEnabled, enableAnalytics, disableAnalytics]);

  const value: AnalyticsContextType = {
    isEnabled,
    isLoading,
    enableAnalytics,
    disableAnalytics,
    toggleAnalytics,
  };

  return (
    <AnalyticsContext.Provider value={value}>
      <UmamiAnalyticsInternal
        websiteId={websiteId}
        collectUrl={collectUrl}
        isEnabled={isEnabled}
      />
      {children}
    </AnalyticsContext.Provider>
  );
}

/**
 * 发送自定义事件到 Umami
 * @param eventName 事件名称
 * @param eventData 事件数据
 */
export function trackEvent(eventName: string, eventData?: Record<string, unknown>) {
  if (typeof window !== 'undefined' && (window as any).umami) {
    (window as any).umami.track(eventName, eventData);
  } else {
    console.debug('[Umami] Track event (not initialized):', eventName, eventData);
  }
}

/**
 * 发送页面视图到 Umami
 * @param url 页面 URL
 * @param referrer 来源页面
 */
export function trackPageView(url?: string, referrer?: string) {
  if (typeof window !== 'undefined' && (window as any).umami) {
    (window as any).umami.track(url, referrer);
  } else {
    console.debug('[Umami] Track page view (not initialized):', url);
  }
}
