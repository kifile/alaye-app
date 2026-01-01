/**
 * Terminal 相关类型定义和配置
 * 基于 pywebview-demo 的 API 接口
 */

// 导入 xterm 类型
import type { Terminal } from '@xterm/xterm';
import type { FitAddon } from '@xterm/addon-fit';
import type { WebLinksAddon } from '@xterm/addon-web-links';
import type { ITerminalOptions } from '@xterm/xterm';

// 导入 API 类型
import type {
  LogLevel,
  EventType,
  TerminalSize as APITerminalSize,
  TerminalDTO,
  NewTerminalRequest,
  CloseTerminalRequest,
  WriteToTerminalRequest,
  SetTerminalSizeRequest,
} from '@/api/types';

// ===== 终端状态管理类型 =====

// 终端连接状态枚举
export type TerminalConnectionStatus = 'disconnected' | 'ready' | 'connected';

// 终端状态类型
export interface TerminalState {
  status: TerminalConnectionStatus;
  instanceId: string;
  output: string;
  error: string | null;
}

// 终端操作类型
export interface TerminalActions {
  createTerminal: (request: NewTerminalRequest) => Promise<TerminalDTO | null>;
  closeTerminal: () => Promise<void>;
  resizeTerminal: (size: APITerminalSize) => Promise<void>;
  writeTerminal: (data: string) => Promise<void>;
  readTerminalContent: () => Promise<string>; // TODO: 标记为待实现
}

// 终端组件属性
export interface TerminalComponentProps {
  instanceId?: string; // 可选的实例ID，用于多终端支持
  emptyView?: React.ReactNode;
  onTerminalSizeChange?: (size: APITerminalSize) => void;
}

// 终端实例状态
export interface TerminalInstance {
  terminal: Terminal; // xterm Terminal 实例
  fitAddon: FitAddon; // FitAddon 实例
  webLinksAddon: WebLinksAddon; // WebLinksAddon 实例
}

// 统一 TerminalSize 类型（与 API 保持一致）
export type TerminalSize = APITerminalSize;

// ===== 终端配置相关类型定义 =====

// 终端主题配置
export interface TerminalTheme {
  background: string;
  foreground: string;
  cursor: string;
  selectionBackground: string;
  black: string;
  red: string;
  green: string;
  yellow: string;
  blue: string;
  magenta: string;
  cyan: string;
  white: string;
  brightBlack: string;
  brightRed: string;
  brightGreen: string;
  brightYellow: string;
  brightBlue: string;
  brightMagenta: string;
  brightCyan: string;
  brightWhite: string;
}

// 终端配置接口
export interface TerminalConfig {
  fontSize: number;
  fontFamily: string;
  theme: TerminalTheme;
  scrollback: number;
  cursorBlink: boolean;
  convertEol: boolean;
  rightClickSelectsWord: boolean;
  wordSeparator: string;
  allowTransparency: boolean;
  bellStyle: 'none' | 'visual' | 'sound' | 'both';
  fastScrollModifier: 'alt' | 'ctrl' | 'shift';
  fontSizeZoomSteps: number;
  letterSpacing: number;
  lineHeight: number;
  minimumContrastRatio: number;
  rendererType: 'dom' | 'canvas';
}

// 终端主题预设
export const TERMINAL_THEMES: Record<string, TerminalTheme> = {
  dark: {
    background: '#1a1a1a',
    foreground: '#ffffff',
    cursor: '#ffffff',
    selectionBackground: '#ffffff40',
    black: '#000000',
    red: '#ff5555',
    green: '#50fa7b',
    yellow: '#f1fa8c',
    blue: '#6272a4',
    magenta: '#ff79c6',
    cyan: '#8be9fd',
    white: '#f8f8f2',
    brightBlack: '#6272a4',
    brightRed: '#ff6e6e',
    brightGreen: '#69ff94',
    brightYellow: '#ffffa5',
    brightBlue: '#d6acff',
    brightMagenta: '#ff92df',
    brightCyan: '#a4ffff',
    brightWhite: '#ffffff',
  },
  light: {
    background: '#ffffff',
    foreground: '#000000',
    cursor: '#000000',
    selectionBackground: '#00000040',
    black: '#000000',
    red: '#cc0000',
    green: '#4e9a06',
    yellow: '#c4a000',
    blue: '#3465a4',
    magenta: '#75507b',
    cyan: '#06989a',
    white: '#d3d7cf',
    brightBlack: '#555753',
    brightRed: '#ef2929',
    brightGreen: '#8ae234',
    brightYellow: '#fce94f',
    brightBlue: '#729fcf',
    brightMagenta: '#ad7fa8',
    brightCyan: '#34e2e2',
    brightWhite: '#eeeeec',
  },
};

// 默认终端配置
export const DEFAULT_TERMINAL_CONFIG: TerminalConfig = {
  fontSize: 14,
  fontFamily: 'Monaco, Menlo, "Ubuntu Mono", "Consolas", monospace',
  theme: TERMINAL_THEMES.dark,
  scrollback: 1000,
  cursorBlink: true,
  convertEol: true,
  rightClickSelectsWord: true,
  wordSeparator: ' \t~!@#$%^&*()=+[{]}|;:\'",.<>/?',
  allowTransparency: false,
  bellStyle: 'none',
  fastScrollModifier: 'alt',
  fontSizeZoomSteps: 1,
  letterSpacing: 0,
  lineHeight: 1.0,
  minimumContrastRatio: 1,
  rendererType: 'canvas',
};

// 将配置转换为 xterm 的 ITerminalOptions
export function configToXtermOptions(config: TerminalConfig): ITerminalOptions {
  return {
    fontSize: config.fontSize,
    fontFamily: config.fontFamily,
    theme: config.theme,
    scrollback: config.scrollback,
    cursorBlink: config.cursorBlink,
    convertEol: config.convertEol,
    rightClickSelectsWord: config.rightClickSelectsWord,
    wordSeparator: config.wordSeparator,
    allowTransparency: config.allowTransparency,
  };
}

// 预设配置
export const TERMINAL_PRESETS: Record<string, Partial<TerminalConfig>> = {
  compact: {
    fontSize: 12,
    scrollback: 500,
    lineHeight: 0.9,
  },
  comfortable: {
    fontSize: 16,
    scrollback: 2000,
    lineHeight: 1.2,
  },
  accessibility: {
    fontSize: 18,
    fontFamily: 'Menlo, Monaco, "DejaVu Sans Mono", monospace',
    minimumContrastRatio: 4.5,
  },
};

// ANSI 颜色代码常量
export const ANSI_COLORS = {
  RESET: '\x1b[0m',
  RED: '\x1b[31m',
  GREEN: '\x1b[32m',
  YELLOW: '\x1b[33m',
  BLUE: '\x1b[34m',
  MAGENTA: '\x1b[35m',
  CYAN: '\x1b[36m',
  WHITE: '\x1b[37m',
} as const;

// 终端消息常量
export const TERMINAL_MESSAGES = {
  DISCONNECTING: '\r\n正在断开连接...',
  PROCESS_COMPLETED: '\r\n[进程已完成]',
  ERROR_PREFIX: '\r\n错误: ',
  READY: '\r\n终端已就绪，等待连接...',
  ATTACHED: '\r\n已连接到终端实例',
  DETACHED: '\r\n已断开终端实例连接',
} as const;

// 事件监听器状态
export interface EventListenerState {
  outputCallback?: (data: any) => void;
  errorCallback?: (data: any) => void;
  statusCallback?: (data: any) => void;
  isListening: boolean;
}

// PyWebview 事件数据类型
export interface PyWebviewTerminalOutputEvent {
  instance_id: string;
  data: string;
}

export interface PyWebviewTerminalErrorEvent {
  instance_id: string;
  error: string;
}

export interface PyWebviewTerminalStatusEvent {
  instance_id: string;
  status: any;
}
