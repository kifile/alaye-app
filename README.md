# Alaye App

**English** | [**简体中文**](README_zh.md)

Alaye App is a desktop management assistant for AI tools, designed to provide developers with a unified and convenient experience for configuring and managing AI tools.

## Project Overview

Alaye App integrates a modern user interface with powerful backend services, helping developers manage multiple AI tools in one application.

**Phase 1 Features (Current Version)**:

- **Claude AI Project Management**: Easily scan, configure, and manage multiple Claude AI projects
- **Plugin & Extension Support**: Support for Claude plugin marketplace, MCP server configuration, and Hooks management
- **Cross-Platform**: Support for Windows, macOS, and Linux operating systems

**Future Plans**: Continuously expanding support for more AI tools and advanced capabilities

## Tech Stack

- **Frontend**: Next.js 16 + React 19 + TypeScript + Tailwind CSS
- **Backend**: Python 3.12 + PyWebView
- **Cross-Platform Terminal**: pexpect (Unix) / pywinpty (Windows)

## Requirements

- **Python**: 3.12 or higher
- **Node.js**: Recommended 18 or higher
- **Operating System**: Windows 10/11, macOS 10.15+, or major Linux distributions

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd alaye-release
```

### 2. Install Dependencies

Recommended to use `uv` for fast installation (automatically installs all Python dependencies, including PyQt6 on Linux):

```bash
# Install uv (if not already installed)
pip install uv

# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Main configuration items in `.env` file:
- `APP_ENV`: Runtime mode (`development`/`export`/`browser`)
- `PORT`: Development server port (default 3000)

### 4. Run the Application

**Development Mode** (with frontend hot reload):

```bash
# Terminal 1: Start frontend
cd frontend && npm run dev

# Terminal 2: Start backend (make sure APP_ENV=development in .env)
python main.py
```

**Production Mode** (desktop application):

```bash
# 1. Build frontend
cd frontend && npm run build && cd ..

# 2. Start application
uv run python main.py
```

**Browser Mode** (for web testing):

```bash
# Set APP_ENV=browser in .env, then start
uv run python main.py

# Visit http://127.0.0.1:8000
```

## Build Standalone Executable

Package the application as a standalone executable without requiring Python environment:

```bash
# 1. Build frontend
cd frontend && npm run build && cd ..

# 2. Execute build (choose the script for your platform)
./scripts/build.sh          # Linux/macOS
scripts\build.bat            # Windows (CMD)
scripts\build.ps1            # Windows (PowerShell)
```

After building, the executable file is located in the `dist/` directory.

## Roadmap

### ✅ v0.1 - Claude Configuration Management (Current Version)
- [x] Claude project scanning and management
- [x] Claude settings configuration
- [x] MCP server management
- [x] Hooks configuration management
- [x] Plugin marketplace support
- [x] Multi-project support
- [x] Cross-platform desktop application

### 🔮 v1.0 - Multi AI Tool Support (Planned)
- [ ] Tool Extensions: CodeX, Gemini
- [ ] Feature Extensions: Analytics dashboard, advanced AI capabilities

## License

This project is open-sourced under the MIT License. For details, please see the [LICENSE](LICENSE) file in the project root directory.

## Contributing

Issues and Pull Requests are welcome!

## Support

For questions or suggestions, please contact us through GitHub Issues.
