"""Create ZIP package for Windows distribution."""
import sys
import zipfile
from pathlib import Path
from datetime import datetime

def create_zip(exe_path: str, zip_dir: str):
    """Create a ZIP archive containing the executable."""
    exe_file = Path(exe_path)

    if not exe_file.exists():
        print(f"Error: {exe_path} not found")
        return 1

    # Generate timestamp for ZIP filename
    timestamp = datetime.now().strftime("%Y%m%d")
    zip_filename = f"alaye-windows-{timestamp}.zip"
    zip_file = Path(zip_dir) / zip_filename

    # Create parent directory if needed
    zip_file.parent.mkdir(parents=True, exist_ok=True)

    # Create ZIP archive
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_file, 'alaye.exe')

    print(f"ZIP created: {zip_file}")
    print(f"Size: {zip_file.stat().st_size / 1024 / 1024:.1f} MB")
    return 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python create_zip.py <exe_path> [zip_dir]")
        sys.exit(1)

    exe_path = sys.argv[1]
    zip_dir = sys.argv[2] if len(sys.argv) > 2 else "build"
    sys.exit(create_zip(exe_path, zip_dir))
