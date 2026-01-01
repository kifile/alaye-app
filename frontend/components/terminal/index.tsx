'use client';

import { log } from '@/lib/log';
import { TerminalBody } from './ui/TerminalBody';
import { TerminalProvider, useTerminalContext } from './TerminalProvider';
import { TerminalErrorBoundary } from './ui/TerminalErrorBoundary';

// 终端组件属性接口
interface TerminalComponentProps {
  instanceId?: string;
  emptyView?: React.ReactNode;
  onTerminalSizeChange?: (size: { rows: number; cols: number }) => void;
  className?: string;
}

// 创建日志器
const logger = log.child('Terminal');

// Terminal 组件 - 合并 TerminalContainer，简化代码结构
function TerminalComponent(props: TerminalComponentProps) {
  logger.info(`渲染终端组件: ${props.instanceId || 'no instanceId'}`);

  // 错误边界错误处理
  const handleErrorBoundary = (error: Error) => {
    logger.error(`终端容器发生错误: ${error.message}`);
  };

  // 终端组件自带Provider，确保TerminalBody可以获取上下文
  return (
    <TerminalProvider
      key={props.instanceId || 'empty'}
      instanceId={props.instanceId || ''}
    >
      <TerminalErrorBoundary onError={handleErrorBoundary}>
        <TerminalBody
          className={props.className || 'h-full'}
          emptyView={props.emptyView}
          onTerminalSizeChange={props.onTerminalSizeChange}
        />
      </TerminalErrorBoundary>
    </TerminalProvider>
  );
}

TerminalComponent.displayName = 'TerminalComponent';

export default TerminalComponent;

// 导出子组件和类型，供外部使用
export { TerminalBody } from './ui/TerminalBody';
export { TerminalErrorBoundary } from './ui/TerminalErrorBoundary';
export { TerminalProvider, useTerminalContext } from './TerminalProvider';
export { TerminalContainer, PresetTerminalContainer } from './TerminalContainer';
export { TerminalControls, TerminalStatusBar } from './ui/TerminalControls';
export * from './types';

// 导出 Terminal 组件作为默认导出的命名导出
export { TerminalComponent as Terminal };
