import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // 启用静态导出
  output: 'export',

  // 静态导出的基础路径（可选）
  // basePath: '/app',

  // 图片优化配置（静态导出时需要）
  images: {
    unoptimized: true,
  },

  // 资源前缀（如果部署到子路径）
  // assetPrefix: '/app/',

  // 严格模式
  reactStrictMode: true,

  // 导出配置 - 输出到项目根目录的 out 文件夹
  distDir: './out',

  // 尾随斜杠 - 设为 false 避免自动添加尾部斜杠
  trailingSlash: false,

  // TypeScript 配置
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
