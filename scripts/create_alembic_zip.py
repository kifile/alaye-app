"""Create ZIP archive of alembic_migrations directory."""

import zipfile
from pathlib import Path


def create_alembic_zip(source_dir: str, output_zip: str):
    """
    Create a ZIP archive of alembic_migrations directory.

    Args:
        source_dir: Path to alembic_migrations directory
        output_zip: Path for output ZIP file

    Returns:
        int: 0 on success, 1 on failure
    """
    source_path = Path(source_dir)

    if not source_path.exists():
        print(f"Error: {source_dir} not found")
        return 1

    # Create output directory if needed
    output_path = Path(output_zip)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Patterns to exclude
    exclude_patterns = [
        "__pycache__",
        ".pyc",
        ".pyo",
        ".DS_Store",
        ".git",
        ".gitignore",
    ]

    def should_exclude(file_path: Path) -> bool:
        """Check if file should be excluded from ZIP."""
        # Check if any part of the path matches exclude patterns
        for part in file_path.parts:
            if part in exclude_patterns:
                return True
        # Check file extensions
        if file_path.suffix in [".pyc", ".pyo"]:
            return True
        return False

    # Create ZIP archive
    file_count = 0
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in source_path.rglob("*"):
            # Skip directories
            if file_path.is_dir():
                continue

            # Skip excluded files
            if should_exclude(file_path):
                continue

            # Calculate relative path
            relative_path = file_path.relative_to(source_path.parent)
            zf.write(file_path, relative_path)
            file_count += 1

    # Print summary
    zip_size = output_path.stat().st_size / 1024  # KB
    print(f"ZIP created: {output_zip}")
    print(f"Files included: {file_count}")
    print(f"Size: {zip_size:.1f} KB")

    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python create_alembic_zip.py <output_zip>")
        print("Example: python create_alembic_zip.py build/alembic_migrations.zip")
        sys.exit(1)

    output_zip = sys.argv[1]
    source_dir = "alembic_migrations"  # Default source directory

    sys.exit(create_alembic_zip(source_dir, output_zip))
