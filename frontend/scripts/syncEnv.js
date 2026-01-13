/**
 * 从根目录同步环境变量到 frontend/.env.local
 * 用于构建和开发时共享环境变量配置
 */

const fs = require('fs');
const path = require('path');

// 路径配置
const rootEnvPath = path.resolve(__dirname, '../../.env');
const rootEnvExamplePath = path.resolve(__dirname, '../../.env.example');
const frontendEnvPath = path.resolve(__dirname, '../.env.local');

/**
 * 读取 .env 文件并解析为对象
 */
function parseEnvFile(filePath) {
  if (!fs.existsSync(filePath)) {
    return {};
  }

  const content = fs.readFileSync(filePath, 'utf-8');
  const env = {};

  content.split('\n').forEach(line => {
    // 跳过注释和空行
    const trimmedLine = line.trim();
    if (!trimmedLine || trimmedLine.startsWith('#')) {
      return;
    }

    // 解析 KEY=VALUE
    const match = trimmedLine.match(/^([^=]+)=(.*)$/);
    if (match) {
      const [, key, value] = match;
      env[key.trim()] = value.trim();
    }
  });

  return env;
}

/**
 * 将对象转换为 .env 文件内容
 */
function stringifyEnv(env) {
  return Object.entries(env)
    .map(([key, value]) => `${key}=${value}`)
    .join('\n');
}

/**
 * 主函数
 */
function syncEnv() {
  try {
    // 读取根目录的 .env 和 .env.example
    const rootEnv = parseEnvFile(rootEnvPath);
    const rootEnvExample = parseEnvFile(rootEnvExamplePath);

    // 合并环境变量（.env 优先级更高）
    const mergedEnv = { ...rootEnvExample, ...rootEnv };

    // 读取现有的 frontend/.env.local
    const frontendEnv = parseEnvFile(frontendEnvPath);

    // 合并时保留 frontend/.env.local 中独有的变量（如前端特定配置）
    const finalEnv = { ...mergedEnv, ...frontendEnv };

    // 生成 .env.local 内容
    let content = '# 环境配置文件\n';
    content += '# 此文件由 scripts/syncEnv.js 自动生成\n';
    content += '# 请在根目录的 .env 文件中修改配置\n';
    content += '# 最后更新时间: ' + new Date().toISOString() + '\n\n';
    content += stringifyEnv(finalEnv);

    // 写入 frontend/.env.local
    fs.writeFileSync(frontendEnvPath, content);

    console.log('[syncEnv] 环境变量已同步到 frontend/.env.local');
    console.log(`[syncEnv] 同步了 ${Object.keys(mergedEnv).length} 个变量`);
  } catch (error) {
    console.error('[syncEnv] 同步失败:', error.message);
    process.exit(1);
  }
}

// 运行同步
syncEnv();
