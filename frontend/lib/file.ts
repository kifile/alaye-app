/**
 * 文件选择器库
 * 提供跨环境的文件选择功能，支持 PyWebView 和浏览器环境
 */

import { is_pywebview } from '@/lib/env';
import { showFileDialog, type FileDialogFilter } from '@/api/api';

export interface FileSelectOptions {
  /** 对话框标题 */
  title?: string;
  /** 默认打开路径 */
  defaultPath?: string;
  /** 是否允许多选 */
  multiple?: boolean;
  /** 文件类型过滤器 */
  filters?: FileDialogFilter[];
}

export interface FileSelectResult {
  /** 是否成功 */
  success: boolean;
  /** 选择的文件路径列表 */
  filePaths: string[];
  /** 错误信息 */
  error?: string;
}

/**
 * 打开文件选择对话框
 *
 * @param options 文件选择选项
 * @returns Promise<FileSelectResult> 选择结果
 */
export async function selectFiles(
  options: FileSelectOptions = {}
): Promise<FileSelectResult> {
  const { title = '选择文件', defaultPath, multiple = false, filters = [] } = options;

  // PyWebView 环境
  if (is_pywebview()) {
    return await selectFilesPyWebView({ title, defaultPath, multiple, filters });
  }

  // 浏览器环境
  return await selectFilesBrowser({ title, multiple, filters });
}

/**
 * PyWebView 环境文件选择
 */
async function selectFilesPyWebView(
  options: FileSelectOptions
): Promise<FileSelectResult> {
  try {
    // 调用统一的 API 接口
    const result = await showFileDialog({
      title: options.title || '选择文件',
      default_path: options.defaultPath,
      filters: options.filters || [],
      multiple: options.multiple || false,
    });

    if (result && result.success && result.data) {
      return {
        success: true,
        filePaths: result.data.file_paths || [],
      };
    } else {
      return {
        success: false,
        filePaths: [],
        error: result?.error || result?.data?.message || '用户取消了文件选择',
      };
    }
  } catch (error) {
    return {
      success: false,
      filePaths: [],
      error: `文件选择失败: ${error instanceof Error ? error.message : '未知错误'}`,
    };
  }
}

/**
 * 浏览器环境文件选择
 */
async function selectFilesBrowser(
  options: FileSelectOptions
): Promise<FileSelectResult> {
  return new Promise(resolve => {
    // 创建隐藏的文件选择器
    const input = document.createElement('input');
    input.type = 'file';
    input.style.display = 'none';

    // 设置多选
    if (options.multiple) {
      input.multiple = true;
    }

    // 设置文件类型过滤器
    if (options.filters && options.filters.length > 0) {
      const accept = options.filters
        .map(filter => filter.extensions.map(ext => `.${ext}`).join(','))
        .join(',');
      input.accept = accept;
    }

    // 监听文件选择
    input.addEventListener('change', event => {
      const files = (event.target as HTMLInputElement).files;

      if (files && files.length > 0) {
        // 浏览器环境只能获取文件名
        const filePaths = Array.from(files).map(file => file.name);
        resolve({
          success: true,
          filePaths,
        });
      } else {
        resolve({
          success: false,
          filePaths: [],
          error: '用户取消了文件选择',
        });
      }

      // 清理
      document.body.removeChild(input);
    });

    // 监听错误
    input.addEventListener('error', () => {
      document.body.removeChild(input);
      resolve({
        success: false,
        filePaths: [],
        error: '文件选择器发生错误',
      });
    });

    // 添加到页面并触发点击
    document.body.appendChild(input);
    input.click();
  });
}

/**
 * 选择单个文件的便捷方法
 */
export async function selectFile(
  options: Omit<FileSelectOptions, 'multiple'> = {}
): Promise<FileSelectResult & { filePath?: string }> {
  const result = await selectFiles({ ...options, multiple: false });
  return {
    ...result,
    filePath: result.filePaths[0],
  };
}

export { FileDialogFilter };
