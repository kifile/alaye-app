import React, { createContext, useContext, ReactNode, useRef } from 'react';
import { ConfigScope } from '@/api/types';

interface ScopeSwitcherConfig {
  enabled: boolean;
  supportedScopes?: (ConfigScope | 'mixed')[];
  value?: ConfigScope | 'mixed' | null;
  onChange?: (scope: ConfigScope | 'mixed' | null) => void;
}

interface DetailHeaderContextValue {
  rightContent: ReactNode;
  setRightContent: (content: ReactNode) => void;
  clearRightContent: () => void;
  scopeSwitcher: ScopeSwitcherConfig;
  setScopeSwitcher: (config: ScopeSwitcherConfig) => void;
  clearScopeSwitcher: () => void;
}

const DetailHeaderContext = createContext<DetailHeaderContextValue | undefined>(
  undefined
);

export function useDetailHeader() {
  const context = useContext(DetailHeaderContext);
  if (!context) {
    throw new Error('useDetailHeader must be used within DetailHeaderProvider');
  }
  return context;
}

interface DetailHeaderProviderProps {
  children: ReactNode;
}

export function DetailHeaderProvider({ children }: DetailHeaderProviderProps) {
  const [rightContent, setRightContent] = React.useState<ReactNode>(null);
  const contentRef = useRef<ReactNode>(null);

  const defaultScopeSwitcherConfig: ScopeSwitcherConfig = {
    enabled: false,
    supportedScopes: undefined,
    value: undefined,
    onChange: undefined,
  };

  const [scopeSwitcher, setScopeSwitcherState] = React.useState<ScopeSwitcherConfig>(
    defaultScopeSwitcherConfig
  );

  // 使用 ref 来存储最新的渲染函数，避免触发重新渲染
  const renderContent = React.useCallback((renderer: () => ReactNode) => {
    const content = renderer();
    contentRef.current = content;
    setRightContent(content);
  }, []);

  const clearRightContent = React.useCallback(() => {
    contentRef.current = null;
    setRightContent(null);
  }, []);

  const setScopeSwitcher = React.useCallback((config: ScopeSwitcherConfig) => {
    setScopeSwitcherState(config);
  }, []);

  const clearScopeSwitcher = React.useCallback(() => {
    setScopeSwitcherState(defaultScopeSwitcherConfig);
  }, []);

  const value = React.useMemo(
    () => ({
      rightContent,
      setRightContent: (content: ReactNode) => {
        contentRef.current = content;
        setRightContent(content);
      },
      clearRightContent,
      renderContent,
      scopeSwitcher,
      setScopeSwitcher,
      clearScopeSwitcher,
    }),
    [
      rightContent,
      clearRightContent,
      renderContent,
      scopeSwitcher,
      setScopeSwitcher,
      clearScopeSwitcher,
    ]
  );

  return (
    <DetailHeaderContext.Provider value={value}>
      {children}
    </DetailHeaderContext.Provider>
  );
}
