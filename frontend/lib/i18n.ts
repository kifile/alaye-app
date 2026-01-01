/**
 * i18n 配置文件
 * 用于 react-i18next 的初始化配置，支持页面级别的翻译文件
 */

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// 支持的语言列表
export const supportedLanguages = {
  en: 'English',
  zh: '中文',
} as const;

export type SupportedLanguage = keyof typeof supportedLanguages;

// 初始化 i18next（空资源，页面会动态加载）
i18n.use(initReactI18next).init({
  resources: {},
  lng: 'en', // 默认语言（会被 loadSettings 覆盖）
  fallbackLng: 'en', // 回退语言
  interpolation: {
    escapeValue: false, // React 已经做了 XSS 防护
  },
  react: {
    useSuspense: false, // 禁用 Suspense，避免闪烁
  },
});

export default i18n;

/**
 * 切换语言
 * @param language 语言代码
 */
export async function changeLanguage(language: SupportedLanguage) {
  await i18n.changeLanguage(language);
}

/**
 * 获取当前语言
 */
export function getCurrentLanguage(): SupportedLanguage {
  return i18n.language as SupportedLanguage;
}

/**
 * 加载页面的翻译文件
 * @param pageName 页面名称（例如：'settings', 'projects'）
 * @param locale 语言代码
 */
export async function loadPageTranslations(
  pageName: string,
  locale: SupportedLanguage
): Promise<void> {
  try {
    // 动态导入页面的翻译文件
    const translations = await import(`../app/${pageName}/locales_${locale}.json`);

    // 将翻译添加到 i18next 资源中
    // 使用页面名称作为命名空间
    i18n.addResourceBundle(locale, pageName, translations.default, true, true);
  } catch (error) {
    console.error(
      `Failed to load translations for page "${pageName}" in locale "${locale}":`,
      error
    );
  }
}

/**
 * 加载页面的所有语言翻译
 * @param pageName 页面名称
 */
export async function loadAllPageTranslations(pageName: string): Promise<void> {
  const promises = Object.keys(supportedLanguages).map(locale =>
    loadPageTranslations(pageName, locale as SupportedLanguage)
  );

  await Promise.all(promises);
}

/**
 * 加载组件的翻译文件
 * @param componentName 组件名称（例如：'sidebar'）
 * @param locale 语言代码
 */
export async function loadComponentTranslations(
  componentName: string,
  locale: SupportedLanguage
): Promise<void> {
  try {
    // 动态导入组件的翻译文件
    const translations = await import(
      `../components/${componentName}/locales_${locale}.json`
    );

    // 将翻译添加到 i18next 资源中
    // 使用组件名称作为命名空间
    i18n.addResourceBundle(locale, componentName, translations.default, true, true);
  } catch (error) {
    console.error(
      `Failed to load translations for component "${componentName}" in locale "${locale}":`,
      error
    );
  }
}

/**
 * 加载组件的所有语言翻译
 * @param componentName 组件名称
 */
export async function loadAllComponentTranslations(
  componentName: string
): Promise<void> {
  const promises = Object.keys(supportedLanguages).map(locale =>
    loadComponentTranslations(componentName, locale as SupportedLanguage)
  );

  await Promise.all(promises);
}
