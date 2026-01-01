import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class TerminalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('TerminalErrorBoundary caught an error:', error, errorInfo);

    this.setState({
      error,
      errorInfo,
    });

    // 调用父组件的错误处理函数
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义的错误界面，使用自定义的
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // 默认的错误界面
      return (
        <Card className='flex flex-col items-center justify-center p-6 h-full bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800'>
          <div className='flex flex-col items-center space-y-4 text-center max-w-md'>
            <AlertTriangle className='h-12 w-12 text-red-500' />

            <div className='space-y-2'>
              <h3 className='text-lg font-semibold text-red-900 dark:text-red-100'>
                终端组件发生错误
              </h3>
              <p className='text-sm text-red-700 dark:text-red-300'>
                终端组件遇到了一个错误，无法正常显示。这可能是由于配置问题或组件冲突导致的。
              </p>
            </div>

            {/* 错误详情（仅在开发环境显示） */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <div className='w-full text-left'>
                <details className='text-xs'>
                  <summary className='cursor-pointer text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200'>
                    查看错误详情
                  </summary>
                  <div className='mt-2 p-2 bg-red-100 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800'>
                    <div className='font-mono text-red-800 dark:text-red-200'>
                      <div className='font-bold'>错误信息:</div>
                      <div className='whitespace-pre-wrap'>
                        {this.state.error.message}
                      </div>
                      <div className='font-bold mt-2'>错误堆栈:</div>
                      <div className='whitespace-pre-wrap text-xs'>
                        {this.state.error.stack}
                      </div>
                      {this.state.errorInfo && (
                        <>
                          <div className='font-bold mt-2'>组件堆栈:</div>
                          <div className='whitespace-pre-wrap text-xs'>
                            {this.state.errorInfo.componentStack}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </details>
              </div>
            )}

            <div className='flex space-x-2'>
              <Button
                onClick={this.handleReset}
                variant='outline'
                size='sm'
                className='flex items-center space-x-2'
              >
                <RefreshCw className='h-4 w-4' />
                <span>重试</span>
              </Button>

              <Button
                onClick={() => window.location.reload()}
                variant='default'
                size='sm'
              >
                刷新页面
              </Button>
            </div>

            {/* 建议操作 */}
            <div className='w-full text-left'>
              <div className='text-xs text-red-600 dark:text-red-400 space-y-1'>
                <p>建议的解决方法：</p>
                <ul className='list-disc list-inside space-y-1'>
                  <li>检查终端配置是否正确</li>
                  <li>确认网络连接正常</li>
                  <li>尝试刷新页面重新加载</li>
                  <li>如果问题持续存在，请报告此错误</li>
                </ul>
              </div>
            </div>
          </div>
        </Card>
      );
    }

    return this.props.children;
  }
}
