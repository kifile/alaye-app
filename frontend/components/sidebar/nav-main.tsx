'use client';

import { type LucideIcon } from 'lucide-react';
import { useRouter } from 'next/navigation';

import {
  SidebarGroup,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';

// 判断是否为外部链接
function isExternalLink(url: string): boolean {
  return url.startsWith('http://') || url.startsWith('https://');
}

export function NavMain({
  items,
}: {
  items: {
    title: string;
    url: string;
    icon?: LucideIcon;
    isActive?: boolean;
    items?: {
      title: string;
      url: string;
    }[];
  }[];
}) {
  const router = useRouter();

  // 处理点击事件
  const handleItemClick = (url: string) => {
    if (isExternalLink(url)) {
      // 外部链接在新窗口打开
      window.open(url, '_blank', 'noopener,noreferrer');
    } else {
      // 内部路由使用 router 跳转
      router.push(url);
    }
  };
  return (
    <SidebarGroup className='px-1'>
      <SidebarMenu>
        {items.map(item => {
          return (
            <SidebarMenuItem key={item.title}>
              <SidebarMenuButton
                tooltip={item.title}
                onClick={() => handleItemClick(item.url)}
                className={item.isActive ? 'bg-sidebar-accent' : ''}
                style={{
                  flexDirection: 'column',
                  padding: '12px 6px',
                  gap: '4px',
                  height: 'auto',
                  minHeight: '60px',
                }}
              >
                {item.icon && <item.icon size={18} />}
                <span
                  style={{
                    fontSize: '12px',
                    textAlign: 'center',
                    lineHeight: '1.2',
                  }}
                >
                  {item.title}
                </span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          );
        })}
      </SidebarMenu>
    </SidebarGroup>
  );
}
