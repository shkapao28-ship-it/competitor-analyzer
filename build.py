import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_FILE = ROOT / "competitionmonitor.spec"


def remove_if_exists(path: Path):
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink()


def main():
    print(">>> Подготовка к сборке EXE...")

    remove_if_exists(DIST_DIR)
    remove_if_exists(BUILD_DIR)
    remove_if_exists(SPEC_FILE)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "competitionmonitor",
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=requests",
        "competitionmonitor.py",
    ]

    print(">>> Запуск PyInstaller...")
    print(" ".join(cmd))

    result = subprocess.run(cmd, cwd=ROOT)

    if result.returncode != 0:
        print(">>> Сборка завершилась с ошибкой")
        sys.exit(result.returncode)

    exe_path = DIST_DIR / "competitionmonitor.exe"

    if exe_path.exists():
        print(f">>> Готово: {exe_path}")
    else:
        print(">>> EXE не найден после сборки")
        sys.exit(1)


if __name__ == "__main__":
    main()