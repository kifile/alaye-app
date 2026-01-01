'use client';

import { useEffect, useState } from 'react';
import { AppSidebar } from '@/components/sidebar/app-sidebar';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';
import { Toaster } from '@/components/ui/sonner';
import { getSetting } from '@/api/api';
import { changeLanguage, type SupportedLanguage } from '@/lib/i18n';
import { preloadMonacoEditor } from '@/lib/monaco-preloader';
import './globals.css';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [appInitialized, setAppInitialized] = useState(false);
  const [language, setLanguage] = useState<SupportedLanguage>('en');

  useEffect(() => {
    let retryCount = 0;
    const MAX_RETRIES = 20; // 最大重试次数
    const INITIAL_DELAY = 500; // 初始延迟 500ms
    const MAX_DELAY = 3000; // 最大延迟 3秒

    const initApp = async (): Promise<void> => {
      // 立即开始预加载 Monaco Editor（不等待后端响应）
      // 这样可以与后端初始化并行进行，充分利用等待时间
      const monacoPreloadPromise = preloadMonacoEditor().catch(err => {
        console.warn('[Layout] Monaco Editor preload failed (non-critical):', err);
      });

      try {
        // 从后端获取语言配置（同时验证后端服务是否已启动）
        const response = await getSetting({ key: 'app.language' });

        if (response.success && response.data) {
          const lang = response.data as SupportedLanguage;
          // 设置当前语言
          await changeLanguage(lang);
          setLanguage(lang);
          console.log(`[Layout] App initialized with language: ${lang}`);
          setAppInitialized(true);
        } else {
          throw new Error('Invalid response from getSetting API');
        }
      } catch (err) {
        retryCount++;

        if (retryCount < MAX_RETRIES) {
          // 指数退避重试
          const delay = Math.min(
            INITIAL_DELAY * Math.pow(1.5, retryCount - 1),
            MAX_DELAY
          );
          console.warn(
            `[Layout] Backend not ready (attempt ${retryCount}/${MAX_RETRIES}), retrying in ${delay}ms...`
          );
          await new Promise(resolve => setTimeout(resolve, delay));
          return initApp();
        } else {
          // 达到最大重试次数，使用默认语言
          console.error('[Layout] Max retries reached, using default language: en');
          await changeLanguage('en');
          setLanguage('en');
          setAppInitialized(true);
        }
      }
    };

    initApp();
  }, []);

  // 在应用初始化完成前显示加载状态
  if (!appInitialized) {
    return (
      <html lang='en' className='h-full'>
        <body className='h-full' suppressHydrationWarning>
          <div className='flex h-full items-center justify-center bg-background'>
            <div className='text-center space-y-4'>
              <div className='inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]' />
              <p className='text-sm text-muted-foreground'>
                Initializing application...
              </p>
            </div>
          </div>
        </body>
      </html>
    );
  }

  return (
    <html lang={language} className='h-full'>
      <body className='h-full' suppressHydrationWarning>
        <SidebarProvider className='h-full'>
          <AppSidebar />
          <SidebarInset className='overflow-auto h-svh flex-1'>{children}</SidebarInset>
        </SidebarProvider>
        <Toaster position='top-center' duration={1000} />
      </body>
    </html>
  );
}
