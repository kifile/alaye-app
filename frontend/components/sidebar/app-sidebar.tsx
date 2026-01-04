'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FolderOpen, Settings } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useEffect, useState } from 'react';

import { NavMain } from '@/components/sidebar/nav-main';
// import { NavUser } from '@/components/sidebar/nav-user';
import {
  Sidebar,
  SidebarContent,
  // SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar';
import { loadAllComponentTranslations } from '@/lib/i18n';

// 菜单项配置（不包含 title，title 将通过 i18n 动态获取）
const navMainConfig = [
  // {
  //   url: '/terminal',
  //   icon: SquareTerminal,
  //   key: 'terminal',
  // },
  {
    url: '/projects',
    icon: FolderOpen,
    key: 'projects',
  },
  {
    url: '/settings',
    icon: Settings,
    key: 'settings',
  },
];

// 用户数据（暂时不使用）
// const userData = {
//   name: 'shadcn',
//   email: 'm@example.com',
//   avatar: '/avatars/shadcn.jpg',
// };

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { t } = useTranslation('sidebar');
  const pathname = usePathname();
  const [translationsLoaded, setTranslationsLoaded] = useState(false);

  // 加载翻译
  useEffect(() => {
    const loadTranslations = async () => {
      if (!translationsLoaded) {
        await loadAllComponentTranslations('sidebar');
        setTranslationsLoaded(true);
      }
    };
    loadTranslations();
  }, [translationsLoaded]);

  // 根据当前路径判断菜单项是否激活，并添加翻译后的标题
  const navMainWithActive = navMainConfig.map(item => ({
    ...item,
    title: t(item.key),
    isActive:
      pathname === item.url ||
      (item.url !== '/' && pathname.startsWith(item.url + '/')),
  }));

  return (
    <Sidebar
      collapsible='none'
      className='h-full min-h-full w-[64px] border-r border-sidebar-border/60'
      {...props}
    >
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size='lg' asChild>
              <Link href='/'>
                <div className='flex aspect-square size-8 items-center justify-center'>
                  <img src='/favicon.ico' alt='Alaye' className='size-8 rounded-lg' />
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={navMainWithActive} />
      </SidebarContent>
      {/* <SidebarFooter>
        <NavUser user={userData} />
      </SidebarFooter> */}
      <SidebarRail />
    </Sidebar>
  );
}
