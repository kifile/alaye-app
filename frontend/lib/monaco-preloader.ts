/**
 * Monaco Editor 预加载工具
 * 用于在应用启动时预加载 Monaco Editor 资源，提升后续页面的首次加载速度
 */

import { loader } from '@monaco-editor/react';

// 配置 Monaco Editor 使用本地资源而非 CDN
// 这样可以支持离线使用，避免在打包后的应用中访问外部 CDN
loader.config({
  paths: {
    vs: '/monaco-assets/vs', // 指向 public/monaco-assets/vs 目录
  },
});

let preloadPromise: Promise<void> | null = null;
let isPreloaded = false;

/**
 * 预加载 Monaco Editor 及其依赖
 * 使用动态导入来提前加载 Monaco Editor 的核心资源
 */
export async function preloadMonacoEditor(): Promise<void> {
  // 如果已经预加载完成，直接返回
  if (isPreloaded) {
    return Promise.resolve();
  }

  // 如果正在预加载中，返回同一个 Promise
  if (preloadPromise) {
    return preloadPromise;
  }

  preloadPromise = (async () => {
    try {
      console.time('[MonacoPreloader] Preload time');

      // 动态导入 Monaco Editor 的 React 组件和核心库
      // 这样会在浏览器中提前加载这些资源
      const [{ default: monaco }] = await Promise.all([import('monaco-editor')]);

      // 初始化 Monaco Editor loader
      // 这会触发 Monaco Editor 的 worker 文件预加载
      // 并且会自动加载所有必要的语言支持（包括 markdown）
      await loader.init();

      isPreloaded = true;
      console.timeEnd('[MonacoPreloader] Preload time');
      console.log(
        '[MonacoPreloader] Monaco Editor preloaded successfully (offline mode)'
      );
    } catch (error) {
      console.error('[MonacoPreloader] Failed to preload Monaco Editor:', error);
      // 失败时重置状态，允许重试
      preloadPromise = null;
      isPreloaded = false;
      throw error;
    }
  })();

  return preloadPromise;
}

/**
 * 检查 Monaco Editor 是否已预加载
 */
export function isMonacoPreloaded(): boolean {
  return isPreloaded;
}

/**
 * 获取预加载 Promise（如果正在预加载中）
 */
export function getPreloadPromise(): Promise<void> | null {
  return preloadPromise;
}
