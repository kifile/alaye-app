/**
 * 环境检测工具
 */

/**
 * 检查当前是否运行在 pywebview 环境中
 * @returns {boolean} 如果在 pywebview 环境中返回 true，否则返回 false
 */
export function is_pywebview(): boolean {
  // 检查是否在浏览器环境中
  if (typeof window === 'undefined') {
    return false;
  }

  // 检查是否存在 pywebview 对象
  if (!('pywebview' in window)) {
    return false;
  }

  // 检查 pywebview.api 是否存在
  const pywebview = (window as any).pywebview;
  if (!pywebview || !pywebview.api) {
    return false;
  }

  return true;
}

/**
 * 获取 pywebview API 对象
 * @returns {any} pywebview API 对象，如果不存在则返回 null
 */
export function get_pywebview_api(): any {
  if (!is_pywebview()) {
    return null;
  }

  return (window as any).pywebview.api;
}
