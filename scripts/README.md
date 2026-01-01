# Build Scripts

This directory contains build scripts for packaging the pywebview application into standalone executables using Nuitka.

## Available Scripts

### Windows

- **`build.bat`** - Windows batch script
  ```cmd
  .\scripts\build.bat
  ```

- **`build.ps1`** - PowerShell script (recommended for Windows)
  ```powershell
  .\scripts\build.ps1
  ```

### Linux/macOS

- **`build.sh`** - Unix shell script
  ```bash
  ./scripts/build.sh
  ```

## Requirements

Before running any build script, make sure you have:

1. Python 3.12+ installed
2. Nuitka installed:
   ```bash
   pip install nuitka
   ```

## Output

All build scripts will:
- Create a `build/` directory in the project root
- Compile `main.py` into a standalone executable
- Place the final executable in `build/main.exe` (Windows) or `build/main` (Linux/macOS)
- Clean up intermediate build files

## Build Options

All scripts use the following Nuitka options:

- `--onefile`: Create a single executable file
- `--windows-disable-console` (Windows only): Hide the console window
- `--output-dir=../build`: Output files to the build directory
- `--remove-output`: Clean up intermediate build files
- `--assume-yes-for-downloads`: Auto-confirm any required downloads
- `--enable-plugin=pywebview`: Enable pywebview plugin support
- `--include-data-dir=frontend/out=frontend/out`: Include frontend static files

## Usage

1. Navigate to the project root directory
2. Build the frontend first (if not already done):
   ```bash
   cd frontend
   npm run build
   cd ..
   ```
3. Run the appropriate script for your platform
4. The executable will be created in the `build/` directory
5. Run the executable to test your application

## Important Notes

- **Frontend Build Required**: The build scripts expect `frontend/out/index.html` to exist. If it doesn't exist, run `npm run build` in the frontend directory first.
- **Resource Handling**: The build scripts automatically include the frontend static files in the executable using Nuitka's data inclusion feature.
- **Environment Configuration**: The `.env.example` file is included in the build as a reference for environment variables.

## Troubleshooting

- **Nuitka not found**: Install it with `pip install nuitka`
- **Build fails**: Check that all dependencies are installed in your virtual environment
- **Permission denied** (Linux/macOS): Make sure `build.sh` is executable: `chmod +x scripts/build.sh`