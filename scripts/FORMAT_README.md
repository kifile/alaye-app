# 代码格式化脚本

本目录包含了用于格式化和检查代码的各种脚本，支持 Python 和前端代码。

## 脚本列表

### Python 代码格式化

- **`format-python.sh`** - Linux/macOS 系统使用
- **`format-python.bat`** - Windows 系统使用

功能：
- 使用 `isort` 整理导入语句
- 使用 `black` 格式化 Python 代码
- 使用 `flake8` 进行代码质量检查

### 前端代码格式化

- **`format-frontend.sh`** - Linux/macOS 系统使用
- **`format-frontend.bat`** - Windows 系统使用

功能：
- 使用 `Prettier` 格式化前端代码
- 使用 `ESLint` 进行代码质量检查和自动修复

### 统一代码格式化

- **`format-all.sh`** - Linux/macOS 系统使用
- **`format-all.bat`** - Windows 系统使用

功能：
- 同时格式化 Python 和前端代码
- 支持分别处理不同语言的代码

## 使用方法

### 基本用法

```bash
# Linux/macOS
./scripts/format-all.sh              # 格式化所有代码
./scripts/format-python.sh           # 仅格式化 Python 代码
./scripts/format-frontend.sh         # 仅格式化前端代码

# Windows
scripts\format-all.bat               # 格式化所有代码
scripts\format-python.bat            # 仅格式化 Python 代码
scripts\format-frontend.bat          # 仅格式化前端代码
```

### 参数选项

所有脚本都支持以下参数：

- `--check` - 仅检查代码格式，不修改文件
- `--verbose` - 显示详细的执行过程
- `--help` - 显示帮助信息

`format-all` 脚本额外支持：
- `--python-only` - 仅处理 Python 代码
- `--frontend-only` - 仅处理前端代码

### 示例

```bash
# 检查所有代码格式但不修改
./scripts/format-all.sh --check

# 详细显示格式化过程
./scripts/format-python.sh --verbose

# 仅检查前端代码
./scripts/format-all.sh --frontend-only --check

# Windows 示例
scripts\format-all.bat --check --verbose
```

## 工具配置

### Python 工具配置

项目使用以下 Python 格式化工具，配置在 `pyproject.toml` 中：

- **Black**: 代码格式化，行长度 88 字符
- **isort**: 导入语句排序，兼容 Black 配置
- **flake8**: 代码质量检查，忽略部分常见问题

### 前端工具配置

前端项目使用以下工具，配置在 `frontend/` 目录下：

- **Prettier**: 代码格式化
  - 配置文件：`.prettierrc`
  - 忽略文件：`.prettierignore`
- **ESLint**: 代码质量检查
  - 配置文件：`eslint.config.mjs`

## IDE 集成

### VS Code

项目已配置 VS Code 设置（`.vscode/settings.json`），支持：

- 保存时自动格式化代码
- 配置不同文件类型的默认格式化工具
- 集成 Black、Prettier、ESLint

推荐安装的扩展列表在 `.vscode/extensions.json` 中。

### EditorConfig

项目根目录的 `.editorconfig` 文件确保不同编辑器使用一致的编码风格。

## 自动化建议

### Git Hooks

虽然项目不使用 pre-commit，但建议配置 Git hooks：

```bash
# 添加 pre-commit hook (示例)
echo '#!/bin/bash
./scripts/format-all.sh --check || exit 1' > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### CI/CD 集成

在 CI/CD 流水线中添加代码格式检查：

```yaml
# GitHub Actions 示例
- name: Check code format
  run: ./scripts/format-all.sh --check
```

## 故障排除

### 常见问题

1. **工具未安装**
   ```bash
   # Python 工具
   uv sync --group dev

   # 前端工具
   cd frontend && npm install
   ```

2. **权限错误**
   ```bash
   # Linux/macOS
   chmod +x scripts/*.sh
   ```

3. **格式化失败**
   - 使用 `--verbose` 参数查看详细错误信息
   - 检查工具版本是否兼容
   - 确保在项目根目录运行脚本

### 手动安装工具

如果脚本无法自动安装工具，可以手动安装：

```bash
# Python 格式化工具
pip install black isort flake8 flake8-docstrings flake8-import-order

# 前端格式化工具
cd frontend
npm install -D prettier eslint eslint-config-prettier eslint-plugin-prettier
```

## 贡献指南

1. 在提交代码前运行格式化脚本
2. 确保所有代码格式检查通过
3. 遵循项目既定的代码风格规范

如需修改格式化配置，请：

1. 更新相应的配置文件（`pyproject.toml`、`.prettierrc` 等）
2. 测试配置变更的效果
3. 更新此文档以反映变更