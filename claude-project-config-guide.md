# Claude Code 项目级配置完整指南

## 概述

Claude Code 使用分层的配置系统，支持项目级和用户级的配置管理。本文档详细介绍了项目级支持的各类配置项、存储位置和管理方式。

## 1. 配置文件结构

### 项目根目录结构

```
项目根目录/
├── .claude/                    # Claude 配置目录
│   ├── settings.json          # 项目共享配置（受版本控制）
│   ├── settings.local.json    # 项目本地配置（不受版本控制）
│   ├── commands/              # 自定义 Slash Commands
│   │   └── *.md              # 命令定义文件
│   ├── agents/                # 自定义 Subagents
│   │   └── *.md              # Agent 定义文件
│   ├── hooks/                 # 自定义 Hooks 脚本
│   │   └── *.sh/*.py         # Hook 脚本文件
│   ├── skills/                # 自定义 Skills
│   │   └── skill-name/        # Skill 目录
│   │       ├── SKILL.md       # Skill 定义文件
│   │       ├── scripts/       # 可选脚本目录
│   │       ├── templates/     # 可选模板目录
│   │       └── utils/         # 可选工具目录
│   └── CLAUDE.md              # 项目上下文和指导文档（也可以放在项目根目录）
├── CLAUDE.local.md            # 项目本地记忆文件（不受版本控制）
├── CLAUDE.md                  # 项目上下文和指导文档（可选，也可放在 .claude/ 目录下）
├── .mcp.json                  # 项目级 MCP 服务器配置
└── .gitignore                 # Git 忽略文件
```

### 自动 Git 忽略规则

Claude Code 会自动配置 Git 忽略以下文件：
```
.claude/settings.local.json
.claude/.env*
.claude/cache/
.claude/logs/
.claude/session-archives/
CLAUDE.local.md
```

## 2. Settings 配置 (`.claude/settings.json`)

### 基础配置

```json
{
  // 模型和输出配置
  "model": "claude-sonnet-4-5-20250929",
  "outputStyle": "Explanatory",
  "includeCoAuthoredBy": false,
  "cleanupPeriodDays": 20,

  // 环境变量
  "env": {
    "NODE_ENV": "development",
    "DEBUG": "true"
  },

  // 公司公告
  "companyAnnouncements": [
    "Welcome to our project! Please review the coding guidelines."
  ],

  // API 密钥助手脚本
  "apiKeyHelper": "/bin/generate_temp_api_key.sh",

  // 状态栏配置
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh"
  }
}
```

### 权限配置

```json
{
  "permissions": {
    // 允许的工具调用
    "allow": [
      "Bash(npm run lint)",
      "Bash(npm run test:*)",
      "Bash(git status)",
      "Bash(git add:*)",
      "Read(~/.zshrc)",
      "Read(./package.json)",
      "Glob(**/*.{js,ts,jsx,tsx})"
    ],

    // 需要询问的工具调用
    "ask": [
      "Bash(git push:*)",
      "Bash(git commit:*)",
      "Bash(docker:*)",
      "Edit(./config/*.json)"
    ],

    // 禁止的工具调用
    "deny": [
      "Bash(curl:*)",
      "Bash(wget:*)",
      "Bash(rm -rf:*)",
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)",
      "Read(./config/credentials.json)",
      "Read(./build)",
      "Write(./.env*)"
    ],

    // 额外允许访问的目录
    "additionalDirectories": [
      "../docs/",
      "../shared-components/"
    ],

    // 默认权限模式
    "defaultMode": "acceptEdits",

    // 禁用绕过权限模式
    "disableBypassPermissionsMode": "disable"
  }
}
```

### 沙盒配置

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "excludedCommands": ["docker", "kubectl", "sudo"],
    "allowUnsandboxedCommands": false,
    "enableWeakerNestedSandbox": true,
    "network": {
      "allowUnixSockets": [
        "~/.ssh/agent-socket"
      ],
      "allowLocalBinding": true,
      "httpProxyPort": 8080,
      "socksProxyPort": 8081
    }
  }
}
```

### 插件配置

```json
{
  "enabledPlugins": {
    "formatter@company-tools": true,
    "deployer@company-tools": true,
    "analyzer@security-plugins": false,
    "linter@custom-tools": true
  },

  "extraKnownMarketplaces": {
    "company-tools": {
      "source": {
        "source": "github",
        "repo": "company/claude-plugins"
      }
    },
    "community-plugins": {
      "source": {
        "source": "github",
        "repo": "claude-code-community/plugins"
      }
    }
  }
}
```

### MCP 服务器自动批准配置

```json
{
  // 批准所有项目级 MCP 服务器
  "enableAllProjectMcpServers": true,

  // 批准特定服务器
  "enabledMcpjsonServers": ["memory", "github", "filesystem"],

  // 拒绝特定服务器
  "disabledMcpjsonServers": ["filesystem", "database"]
}
```

### Hooks 配置

```json
{
  "hooks": {
    // 工具执行前 Hook
    "PreToolUse": {
      "Bash": "echo 'Executing command...'",
      "Edit": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre-edit-check.sh",
      "Write": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/validate-write.sh"
    },

    // 工具执行后 Hook
    "PostToolUse": {
      "Edit": "npm run format",
      "Write": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/post-process.sh"
    },

    // 会话开始 Hook
    "SessionStart": [{
      "matcher": "startup",
      "hooks": [{
        "type": "command",
        "command": "echo 'source venv/bin/activate' >> \"$CLAUDE_ENV_FILE\""
      }]
    }],

    // 用户提示提交 Hook
    "UserPromptSubmit": [{
      "matcher": "*",
      "hooks": [{
        "type": "prompt",
        "prompt": "Check if prompt contains sensitive information: $ARGUMENTS"
      }]
    }]
  },

  // 禁用所有 Hooks
  "disableAllHooks": false
}
```

## 3. MCP 服务器配置 (`.mcp.json`)

### 基本结构

```json
{
  "servers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"],
      "disabled": false,
      "description": "File system access for project files"
    },

    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      },
      "description": "GitHub repository access and operations"
    },

    "memory": {
      "command": "uvx",
      "args": ["mcp-server-memory"],
      "env": {
        "MEMORY_SIZE": "1000",
        "MEMORY_FILE": "$CLAUDE_PROJECT_DIR/.claude/memory.json"
      },
      "description": "Persistent memory for conversations"
    },

    "database": {
      "command": "python",
      "args": ["-m", "my_database_server"],
      "cwd": "$CLAUDE_PROJECT_DIR/scripts/mcp-servers",
      "env": {
        "DB_URL": "postgresql://user:pass@localhost/db",
        "DB_TYPE": "postgres"
      },
      "description": "Database query and management"
    },

    "web-search": {
      "command": "node",
      "args": ["./dist/mcp-server.js"],
      "cwd": "$CLAUDE_PROJECT_DIR/tools/web-search-mcp",
      "env": {
        "SEARCH_API_KEY": "${SEARCH_API_KEY}",
        "SEARCH_ENGINE": "google"
      }
    }
  },

  // 全局默认配置
  "defaults": {
    "timeout": 30000,
    "retries": 3,
    "disabled": false
  }
}
```

### 环境变量支持

MCP 配置支持环境变量替换：
- `${VAR_NAME}` - 从系统环境变量获取
- `$CLAUDE_PROJECT_DIR` - 项目根目录路径
- `$HOME` - 用户主目录

## 4. Hooks 配置详解

### Hook 事件类型

| 事件名称 | 触发时机 | 常用匹配器 |
|---------|---------|-----------|
| `PreToolUse` | 工具执行前 | `Bash`, `Read`, `Edit`, `Write`, `Grep`, `Glob` |
| `PostToolUse` | 工具执行后 | 同上 |
| `PermissionRequest` | 权限请求时 | 特定工具模式 |
| `UserPromptSubmit` | 用户提交提示时 | `*`, 特定内容模式 |
| `Stop` | Claude 停止响应时 | N/A |
| `SubagentStop` | 子代理停止时 | N/A |
| `SessionStart` | 会话开始时 | `startup`, `resume`, `clear`, `compact` |
| `SessionEnd` | 会话结束时 | N/A |
| `Notification` | 通知发送时 | `permission_prompt`, `idle_prompt` |
| `PreCompact` | 压缩操作前 | `manual`, `auto` |

### Hook 脚本示例

#### Git 操作验证 (`.claude/hooks/validate-git.sh`)

```bash
#!/bin/bash

# 读取 JSON 输入
input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name // empty')
command=$(echo "$input" | jq -r '.tool_input.command // empty')

# 只处理 Bash 工具中的 git 命令
if [[ "$tool_name" != "Bash" ]] || [[ ! "$command" =~ ^git ]]; then
    exit 0
fi

# 检查危险操作
if [[ "$command" =~ "git push.*--force" ]]; then
    echo "❌ Dangerous operation: force push detected" >&2
    echo "Please use 'git push --force-with-lease' instead" >&2
    exit 2
fi

if [[ "$command" =~ "git reset.*--hard" ]]; then
    echo "⚠️  Warning: Hard reset will lose commits" >&2
    read -p "Continue? (y/n): " confirm < /dev/tty
    if [[ "$confirm" != "y" ]]; then
        exit 2
    fi
fi

exit 0
```

#### 代码格式化 (`.claude/hooks/format-code.py`)

```python
#!/usr/bin/env python3

import json
import sys
import subprocess
import os
from pathlib import Path

def main():
    # 读取 hook 输入
    input_data = json.load(sys.stdin)

    # 获取修改的文件
    if input_data.get("tool_name") == "Edit":
        file_path = input_data["tool_input"].get("file_path")
    elif input_data.get("tool_name") == "Write":
        file_path = input_data["tool_input"].get("file_path")
    else:
        sys.exit(0)

    if not file_path:
        sys.exit(0)

    # 根据文件扩展名进行格式化
    path = Path(file_path)

    try:
        if path.suffix in {".js", ".jsx", ".ts", ".tsx"}:
            # JavaScript/TypeScript 格式化
            subprocess.run(["npx", "prettier", "--write", file_path], check=True)
            subprocess.run(["npx", "eslint", "--fix", file_path], check=False)

        elif path.suffix == ".py":
            # Python 格式化
            subprocess.run(["black", file_path], check=True)
            subprocess.run(["isort", file_path], check=True)

        elif path.suffix in {".json", ".yaml", ".yml"}:
            # JSON/YAML 格式化
            subprocess.run(["npx", "prettier", "--write", file_path], check=True)

    except subprocess.CalledProcessError as e:
        print(f"Formatting failed for {file_path}: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
```

#### 会话初始化 (`.claude/hooks/session-start.sh`)

```bash
#!/bin/bash

# 获取会话信息
input=$(cat)
session_type=$(echo "$input" | jq -r '.session_type // "startup"')
project_dir=$(echo "$input" | jq -r '.cwd // empty')

case "$session_type" in
    "startup")
        # 启动时加载项目环境
        if [[ -f "$project_dir/.venv/bin/activate" ]]; then
            echo "source \"$project_dir/.venv/bin/activate\"" >> "$CLAUDE_ENV_FILE"
        fi

        # 加载项目特定的环境变量
        if [[ -f "$project_dir/.claude/.env" ]]; then
            cat "$project_dir/.claude/.env" >> "$CLAUDE_ENV_FILE"
        fi

        # 显示项目信息
        echo "🚀 Project: $(basename "$project_dir")"
        echo "📁 Directory: $project_dir"
        ;;

    "resume")
        echo "🔄 Session resumed"
        ;;

    "clear")
        echo "🧹 Session cleared"
        ;;
esac

exit 0
```

## 5. Slash Commands 配置

### 基本命令结构

每个 Slash Command 是一个 Markdown 文件，包含 YAML 前置元数据和命令内容。

#### 简单命令 (`.claude/commands/review.md`)

```markdown
---
description: Review code for security vulnerabilities and best practices
argument-hint: [file_pattern]
model: claude-3-5-sonnet-20241022
---

Please review this code for security vulnerabilities and best practices: $ARGUMENTS

Focus on:
- Security issues
- Code quality
- Performance concerns
- Testing coverage
```

#### 高级命令 (`.claude/commands/commit.md`)

```markdown
---
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*), Bash(git diff:*)
argument-hint: [message]
description: Create a git commit with proper formatting and validation
---

## Context

Current git status:
\`\`\`bash
!git status
\`\`\`

Staged changes:
\`\`\`bash
!git diff --cached
\`\`\`

Unstaged changes:
\`\`\`bash
!git diff
\`\`\`

## Your task

Create a git commit with message: $ARGUMENTS

Steps:
1. Analyze the current changes
2. Stage relevant files if needed
3. Create a well-formatted commit message
4. Make the commit

Commit message should follow conventional commits format:
- feat: new feature
- fix: bug fix
- docs: documentation
- style: formatting
- refactor: code refactoring
- test: tests
- chore: maintenance
```

#### 组件生成命令 (`.claude/commands/react-component.md`)

```markdown
---
description: Generate a React component with TypeScript and Tailwind CSS
argument-hint: ComponentName props
model: claude-3-5-haiku-20241022
---

Create a React component named $ARGUMENTS with the following structure:
- TypeScript interfaces for props
- Tailwind CSS for styling
- Proper accessibility attributes
- JSDoc comments
- Basic error handling

The component should be production-ready and follow our project's coding standards.
```

#### 数据库操作命令 (`.claude/commands/db-migrate.md`)

```markdown
---
allowed-tools: Bash(prisma migrate:*), Bash(npm run db:*), Read(prisma/*)
description: Run database migrations and verify schema
argument-hint: [migration_name]
---

## Database Migration

Current migrations status:
\`\`\`bash
!npx prisma migrate status
\`\`\`

Proposed migration: $ARGUMENTS

Steps:
1. Create new migration if needed
2. Review generated SQL
3. Apply migration
4. Verify schema
5. Generate client if needed

⚠️ Always backup database before running migrations!
```

#### 命令命名空间

创建子目录来组织命令：

```
.claude/commands/
├── frontend/
│   ├── component.md      # /component (project:frontend)
│   ├── page.md          # /page (project:frontend)
│   └── hook.md          # /hook (project:frontend)
├── backend/
│   ├── api.md           # /api (project:backend)
│   ├── model.md         # /model (project:backend)
│   └── migrate.md       # /migrate (project:backend)
└── ops/
    ├── deploy.md        # /deploy (project:ops)
    └── test.md          # /test (project:ops)
```

## 6. Agents/Subagents 配置

### Agent 配置结构

每个 Agent 是一个 Markdown 文件，包含 YAML 前置元数据和系统提示。

#### 代码审查 Agent (`.claude/agents/code-reviewer.md`)

```markdown
---
name: code-reviewer
description: Expert code reviewer. Use proactively after code changes to ensure quality, security, and maintainability.
tools: Read, Grep, Glob, Bash
model: sonnet
permissionMode: default
---

You are a senior code reviewer ensuring high standards of code quality, security, and maintainability.

**When invoked:**
1. Run `git diff` to see recent changes
2. Focus on modified and new files
3. Begin comprehensive review immediately

**Review Checklist:**

**Security**
- No exposed secrets, API keys, or sensitive data
- Proper input validation and sanitization
- Authentication and authorization checks
- SQL injection and XSS prevention
- Secure file handling

**Code Quality**
- Code is simple, readable, and follows DRY principles
- Functions and variables have clear, descriptive names
- Proper error handling and logging
- No hardcoded values or magic numbers
- Consistent code style and formatting

**Performance**
- Efficient algorithms and data structures
- No obvious performance bottlenecks
- Proper caching strategies
- Resource management (memory, connections)

**Testing**
- Adequate test coverage for new code
- Tests cover edge cases and error conditions
- Integration tests where appropriate

**Documentation**
- Clear comments for complex logic
- Updated API documentation
- README changes if needed

Provide specific, actionable feedback with code examples when suggesting improvements.
```

#### 测试专家 Agent (`.claude/agents/test-expert.md`)

```markdown
---
name: test-expert
description: Testing specialist. Use proactively to write tests, improve coverage, and fix test failures.
tools: Read, Edit, Write, Bash, Grep, Glob
model: sonnet
permissionMode: acceptEdits
skills: testing
---

You are a testing expert specializing in test strategy, test automation, and quality assurance.

**When invoked:**
1. Analyze the code changes to understand testing needs
2. Identify existing test structure and frameworks
3. Determine appropriate test types for the changes

**Testing Strategy:**

**Unit Tests**
- Test individual functions and methods in isolation
- Mock external dependencies
- Cover happy path, edge cases, and error conditions
- Aim for high code coverage

**Integration Tests**
- Test component interactions
- Test API endpoints
- Test database operations
- Use test containers when needed

**End-to-End Tests**
- Test critical user workflows
- Use Playwright or Cypress for web apps
- Include accessibility testing

**Test Organization:**
- Follow AAA pattern (Arrange, Act, Assert)
- Use descriptive test names
- Group related tests in suites
- Use test helpers and fixtures

**Best Practices:**
- Write tests before or alongside code (TDD/BDD)
- Keep tests simple and focused
- Regularly refactor test code
- Use continuous integration for automated testing

Always ensure tests provide meaningful feedback and help maintain code quality.
```

#### 调试专家 Agent (`.claude/agents/debugger.md`)

```markdown
---
name: debugger
description: Debugging specialist for errors, test failures, and unexpected behavior. Use proactively when encountering issues.
tools: Read, Edit, Bash, Grep, Glob, mcp__memory__*
model: sonnet
permissionMode: acceptEdits
---

You are an expert debugger specializing in systematic root cause analysis and problem resolution.

**Debugging Process:**

1. **Understand the Problem**
   - Capture exact error messages and stack traces
   - Identify reproduction steps
   - Gather context about when and how the issue occurs

2. **Form Hypotheses**
   - List potential root causes
   - Prioritize most likely causes
   - Consider recent changes that might be related

3. **Isolate the Issue**
   - Use binary search to locate problematic code
   - Create minimal reproductions
   - Add strategic logging and breakpoints

4. **Investigate Root Cause**
   - Analyze code flow and data flow
   - Check dependencies and environment
   - Review logs and metrics

5. **Implement Fix**
   - Apply minimal, targeted changes
   - Ensure fix doesn't break other functionality
   - Add tests to prevent regression

6. **Verify Solution**
   - Test fix thoroughly
   - Check for side effects
   - Monitor after deployment

**Debugging Tools:**
- Use `git bisect` for finding when issues were introduced
- Leverage memory MCP server for context retention
- Use logging and tracing for insight
- Apply divide-and-conquer strategies

Document findings and share knowledge to prevent similar issues.
```

#### 性能优化 Agent (`.claude/agents/performance-optimizer.md`)

```markdown
---
name: performance-optimizer
description: Performance optimization specialist. Use proactively to identify and fix performance bottlenecks.
tools: Read, Edit, Bash, Grep, Glob
model: opus
permissionMode: acceptEdits
---

You are a performance optimization expert focused on making applications fast, efficient, and scalable.

**Optimization Areas:**

**Frontend Performance**
- Bundle size analysis and code splitting
- Lazy loading and dynamic imports
- Image optimization and compression
- Caching strategies
- Rendering performance
- Network request optimization

**Backend Performance**
- Database query optimization
- API response times
- Caching layers (Redis, CDN)
- Async processing
- Memory management
- CPU usage optimization

**Algorithm Optimization**
- Time complexity analysis
- Space complexity optimization
- Data structure selection
- Caching computed results
- Parallel processing

**Monitoring and Measurement**
- Performance metrics collection
- Profiling and benchmarking
- Real User Monitoring (RUM)
- Application Performance Monitoring (APM)

**Optimization Workflow:**
1. Measure current performance
2. Identify bottlenecks
3. Prioritize optimizations by impact
4. Implement changes
5. Verify improvements
6. Monitor regressions

Always measure before and after optimizations to ensure improvements are realized.
```

### CLI 动态 Agent 配置

```bash
# 使用 --agents 参数动态定义
claude --agents '{
  "security-analyzer": {
    "description": "Security expert for vulnerability analysis and secure coding practices",
    "prompt": "You are a cybersecurity expert specializing in application security...",
    "tools": ["Read", "Grep", "Bash"],
    "model": "sonnet"
  },
  "api-designer": {
    "description": "API design specialist for RESTful and GraphQL APIs",
    "prompt": "You are an API design expert focused on creating scalable, maintainable APIs...",
    "tools": ["Read", "Write", "Edit"],
    "model": "sonnet"
  }
}'
```

## 7. 配置优先级

配置的优先级顺序（从高到低）：

1. **企业托管策略** (`managed-settings.json`)
2. **命令行参数** (临时覆盖)
3. **项目本地设置** (`.claude/settings.local.json`)
4. **项目共享设置** (`.claude/settings.json`)
5. **用户设置** (`~/.claude/settings.json`)

## 8. 环境变量支持

### 常用环境变量

```bash
# API 配置
export ANTHROPIC_API_KEY="your-api-key"
export ANTHROPIC_MODEL="claude-sonnet-4-5-20250929"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="claude-3-5-haiku-20241022"

# 配置目录
export CLAUDE_CONFIG_DIR="/custom/claude/config"

# MCP 配置
export MCP_TIMEOUT=30000
export MCP_TOOL_TIMEOUT=60000
export MAX_MCP_OUTPUT_TOKENS=100000

# 功能开关
export DISABLE_TELEMETRY=1
export DISABLE_AUTOUPDATER=1
export CLAUDE_CODE_USE_BEDROCK=1

# 代理配置
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1,.local"
```

## 9. 最佳实践

### 版本控制

```bash
# 推荐的 .gitignore 配置
echo "# Claude local settings" >> .gitignore
echo ".claude/settings.local.json" >> .gitignore
echo ".claude/.env*" >> .gitignore
echo ".claude/cache/" >> .gitignore
echo ".claude/logs/" >> .gitignore
echo ".claude/session-archives/" >> .gitignore

# 但应该纳入版本控制
git add .claude/settings.json
git add .claude/commands/
git add .claude/agents/
git add .claude/hooks/
git add .mcp.json
```

### 安全性配置

```json
{
  "permissions": {
    "deny": [
      // 绝对禁止的操作
      "Bash(rm -rf:/*)",
      "Bash(chmod +s:*)",
      "Bash(curl:*api_key=*"),

      // 敏感文件访问
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)",
      "Read(./**/*.key)",
      "Read(./**/*.pem"),
      "Read(./**/*.p12)",

      // 构建输出目录
      "Read(./dist/**)",
      "Read(./build/**)",
      "Write(./node_modules/**)"
    ]
  },

  "sandbox": {
    "enabled": true,
    "excludedCommands": [
      "sudo",
      "su",
      "chmod",
      "chown",
      "dd",
      "mkfs",
      "fdisk"
    ]
  }
}
```

### 团队协作

1. **共享配置**：
   - 使用 `.claude/settings.json` 存储团队通用配置
   - 包括代码风格、测试框架、部署流程等

2. **个人配置**：
   - 使用 `.claude/settings.local.json` 存储个人偏好
   - 包括 API 密钥、编辑器设置等

3. **文档化**：
   - 在 CLAUDE.md 中记录项目特定信息
   - 说明配置原因和使用方法

### 性能优化

```json
{
  "cleanupPeriodDays": 7,
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true
  },
  "enableAllProjectMcpServers": false,
  "enabledMcpjsonServers": ["essential-server"]
}
```

## 10. 故障排除

### 常见问题

1. **MCP 服务器无法启动**：
   - 检查命令路径和参数
   - 验证环境变量配置
   - 查看服务器日志

2. **Hooks 不执行**：
   - 检查脚本权限 (`chmod +x`)
   - 验证 JSON 配置格式
   - 查看 Hook 输出

3. **Commands 不可见**：
   - 确保文件在正确目录
   - 检查 Markdown 格式
   - 验证 YAML 前置元数据

### 调试技巧

```bash
# 检查配置
claude config list

# 测试 MCP 连接
claude mcp test

# 查看 Hook 执行
export CLAUDE_DEBUG_HOOKS=1

# 检查权限
claude permissions list
```

## 11. CLAUDE.md 配置

### 记忆系统层级结构

Claude Code 提供分层的记忆系统，优先级从高到低：

1. **企业策略** (`/Library/Application Support/ClaudeCode/CLAUDE.md`)
2. **项目记忆** (`./CLAUDE.md` 或 `./.claude/CLAUDE.md`)
3. **用户记忆** (`~/.claude/CLAUDE.md`)
4. **项目本地记忆** (`./CLAUDE.local.md`)

### CLAUDE.md 文件结构

#### 基本结构 (`./.claude/CLAUDE.md`)

```markdown
# 项目概述

本项目是一个使用 React + Next.js + TypeScript 的全栈 Web 应用程序。

## 技术栈

- **前端**: React 18, Next.js 14, TypeScript 5
- **样式**: Tailwind CSS, shadcn/ui
- **状态管理**: Zustand
- **API**: Next.js API Routes, Prisma ORM
- **数据库**: PostgreSQL
- **部署**: Vercel

## 项目结构

```
src/
├── app/              # Next.js App Router
├── components/       # React 组件
├── lib/             # 工具函数和配置
├── hooks/           # 自定义 React Hooks
├── types/           # TypeScript 类型定义
└── styles/          # 全局样式
```

## 开发规范

### 代码风格
- 使用 2 空格缩进
- 组件使用 PascalCase 命名
- 变量和函数使用 camelCase
- 常量使用 UPPER_SNAKE_CASE

### Git 工作流
- 主分支: `main`
- 开发分支: `develop`
- 功能分支: `feature/功能名称`
- 使用 Conventional Commits 格式

### 测试要求
- 单元测试覆盖率 > 80%
- 使用 Jest + React Testing Library
- API 测试使用 Supertest

## 常用命令

### 开发命令
```bash
npm run dev          # 启动开发服务器
npm run build        # 构建生产版本
npm run test         # 运行测试
npm run lint         # 代码检查
npm run type-check   # 类型检查
```

### 数据库命令
```bash
npm run db:migrate   # 运行数据库迁移
npm run db:seed      # 数据库种子数据
npm run db:studio    # 打开 Prisma Studio
```

## 重要提醒

- 所有 API 路由都需要错误处理
- 不要在前端暴露敏感信息
- 使用环境变量管理配置
- 组件必须有适当的类型定义
```

#### 导入其他文件

CLAUDE.md 支持使用 `@path/to/file` 语法导入其他文件：

```markdown
# 项目配置

## 项目概述
@README.md

## 包管理信息
@package.json

## 开发指南
@docs/development-guide.md

## Git 工作流
@docs/git-workflow.md

## 部署指南
@docs/deployment.md
```

#### 支持的导入特性

- 相对路径和绝对路径
- 用户主目录路径（如 `@~/.claude/common-instructions.md`）
- 递归导入（最大深度 5 层）
- 不会在 Markdown 代码块内执行导入

### CLAUDE.local.md 配置

#### 个人项目偏好 (`./CLAUDE.local.md`)

```markdown
# 个人开发偏好

## 本地环境配置

- 使用 VS Code 作为主要编辑器
- 偏好使用 pnpm 而不是 npm
- 本地数据库运行在 Docker 容器中
- 使用 Firefox 进行开发调试

## 个人工作流

1. 总是先运行类型检查再提交
2. 使用 Git hooks 自动格式化代码
3. 优先修复高优先级的 Jira 票据
4. 每天结束前提交代码并推送

## 本地测试数据

- 测试用户: test@example.com
- 测试密码: test123456
- 本地 API 地址: http://localhost:3000

## 注意事项

- 我更喜欢 TypeScript 严格模式
- 注意不要提交包含真实数据的测试文件
- 我的开发时间通常是上午 9 点到下午 6 点
```

### 记忆管理命令

#### 快速添加记忆

在对话中使用 `#` 开头：

```
# 总是使用描述性的变量名
# 组件必须包含 JSDoc 注释
```

系统会提示选择记忆文件进行存储。

#### 直接编辑记忆

使用 `/memory` 命令在编辑器中打开记忆文件：

```bash
/memory  # 打开记忆文件选择界面
```

#### 项目初始化

使用 `/init` 命令为项目生成基础的 CLAUDE.md：

```bash
/init  # 自动分析项目并创建 CLAUDE.md
```

## 12. Claude Skills 配置

### Skill 基本结构

每个 Skill 是一个文件夹，至少包含 `SKILL.md` 文件：

```
.claude/skills/my-skill/
├── SKILL.md           # 必需：Skill 定义文件
├── scripts/           # 可选：辅助脚本
│   ├── setup.sh
│   └── validate.py
├── templates/         # 可选：代码模板
│   ├── component.js
│   └── test.js
└── utils/             # 可选：工具函数
    └── helpers.js
```

### SKILL.md 配置

#### 基本格式

```markdown
---
name: react-component
description: 创建 React 组件的专业助手，包含 TypeScript、测试和样式
model: sonnet
allowed-tools: Read, Write, Edit, Glob, Grep
---

# React 组件生成器

你是一个专业的 React 组件开发专家，专门创建高质量、可维护的 React 组件。

## 功能能力

- 创建 TypeScript React 组件
- 生成对应的测试文件
- 添加 Tailwind CSS 样式
- 包含完整的组件文档
- 确保可访问性最佳实践

## 组件生成规范

### 组件结构
```typescript
interface ComponentProps {
  // 定义 props 类型
}

export function Component({ prop }: ComponentProps) {
  return (
    // JSX 实现
  );
}
```

### 必需元素
- TypeScript 接口定义
- JSDoc 注释
- 可访问性属性
- 错误边界处理
- 适当的样式类名

## 使用示例

**用户请求**: "创建一个带验证的表单组件"
**你的响应**: 生成完整的表单组件，包含输入验证、错误提示和提交处理。

**用户请求**: "创建一个数据表格组件"
**你的响应**: 生成可排序、可筛选的表格组件，支持分页和数据加载。

## 注意事项

- 总是使用函数组件和 Hooks
- 确保组件是可测试的
- 遵循项目的命名约定
- 包含适当的错误处理
- 考虑性能优化（React.memo, useMemo 等）
```

#### 高级配置

```markdown
---
name: api-designer
description: API 设计专家，创建 RESTful API 和 OpenAPI 规范
model: opus
allowed-tools: Read, Write, Edit, Bash, mcp__swagger__*
skills: documentation, testing
env:
  API_VERSION: "v1"
  FRAMEWORK: "express"
---

# API 设计专家

你是一个资深的 API 设计师，专门创建可扩展、文档完善的 RESTful API。

## 设计原则

1. **RESTful 设计**: 遵循 REST 架构原则
2. **版本控制**: 使用 URL 版本控制 (/api/v1/)
3. **错误处理**: 标准化的错误响应格式
4. **文档化**: 完整的 OpenAPI 3.0 规范
5. **安全性**: 适当的认证和授权机制

## API 端点设计

### 标准 CRUD 操作

```
GET    /api/v1/resources     # 获取资源列表
POST   /api/v1/resources     # 创建新资源
GET    /api/v1/resources/:id # 获取特定资源
PUT    /api/v1/resources/:id # 更新资源
DELETE /api/v1/resources/:id # 删除资源
```

### 响应格式

```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 工作流程

1. **需求分析**: 理解业务需求和数据模型
2. **资源设计**: 定义 API 资源和关系
3. **端点创建**: 设计具体的 API 端点
4. **文档编写**: 生成 OpenAPI 规范
5. **测试创建**: 编写 API 测试用例
6. **安全审核**: 检查安全性和最佳实践

## 最佳实践

- 使用名词而不是动词（/users 而不是 /getUsers）
- 实现适当的 HTTP 状态码
- 提供清晰的错误消息
- 包含 API 版本信息
- 实现速率限制
- 使用适当的缓存策略
```

### Skill 目录组织

#### 按功能分类

```
.claude/skills/
├── frontend/
│   ├── react-component/
│   ├── vue-component/
│   └── styling/
├── backend/
│   ├── api-designer/
│   ├── database-schema/
│   └── authentication/
├── devops/
│   ├── docker-generator/
│   ├── ci-cd-pipeline/
│   └── monitoring/
└── testing/
    ├── unit-tests/
    ├── integration-tests/
    └── e2e-tests/
```

#### 技能命名规范

- 使用小写字母和连字符：`react-component`、`api-designer`
- 名称应该描述技能的核心功能
- 避免使用过于宽泛的名称

### Skill 使用方式

#### 自动激活

Claude 会根据请求内容自动选择合适的 Skill：

```
用户: "帮我创建一个用户登录表单组件"
Claude: 自动使用 react-component Skill
```

#### 手动指定

用户可以明确要求使用特定 Skill：

```
用户: "使用 api-designer 技能设计一个博客 API"
Claude: 加载并使用 api-designer Skill
```

#### Skill 链式调用

可以组合多个技能完成复杂任务：

```
用户: "先使用 api-designer 设计 API，然后用 database-schema 设计数据模型"
Claude: 依次调用两个技能完成任务
```

### Skills 与其他配置的区别

| 特性 | Skills | Slash Commands | Agents |
|------|--------|---------------|--------|
| 复杂度 | 高（多文件、脚本） | 低（单文件） | 中等（单文件） |
| 执行方式 | 按需加载 | 命令调用 | 主动委派 |
| 文件结构 | 文件夹 | 单文件 | 单文件 |
| 脚本支持 | 是 | 否 | 否 |
| 模板支持 | 是 | 有限 | 否 |

## 13. 配置优先级总结

### 完整的配置优先级

1. **企业托管策略** (最高优先级)
2. **命令行参数** (临时覆盖)
3. **项目本地设置** (`.claude/settings.local.json`)
4. **项目共享设置** (`.claude/settings.json`)
5. **项目记忆** (`./CLAUDE.md`)
6. **用户记忆** (`~/.claude/CLAUDE.md`)
7. **项目本地记忆** (`./CLAUDE.local.md`) (最低优先级)

### 配置文件相互作用

- **Settings** 控制 Claude 的行为和权限
- **Memory** 提供项目上下文和指导原则
- **Skills** 提供专门的任务执行能力
- **Commands** 提供快捷的操作方式
- **Agents** 提供专业的子代理服务
- **Hooks** 在关键时机执行自定义逻辑
- **MCP** 扩展可用的工具和服务

## 总结

Claude Code 的项目级配置系统提供了强大而灵活的自定义能力，通过合理配置可以显著提升开发效率和代码质量。关键是要：

1. **分层管理**：区分项目共享配置和个人本地配置
2. **安全第一**：合理设置权限和沙盒限制
3. **团队协作**：通过版本控制共享最佳实践
4. **持续优化**：根据项目需求调整配置

正确使用这些配置功能，可以让 Claude Code更好地理解和适应你的项目，提供更精准的辅助。