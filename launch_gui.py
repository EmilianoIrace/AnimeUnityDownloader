#!/usr/bin/env python3
"""Launcher script for AnimeUnityDownloader GUI.

This script checks for required dependencies and launches the GUI.
"""

import importlib.util
import os
import subprocess
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=Warning, module="urllib3")


PROJECT_ROOT = Path(__file__).resolve().parent
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
REQUIRED_MODULES = {
    "requests": "requests",
    "beautifulsoup4": "bs4",
    "rich": "rich",
    "httpx": "httpx",
    "cloudscraper": "cloudscraper",
}
REQUIRED_MODULES_WEB = {
    **REQUIRED_MODULES,
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
}


def ensure_project_environment() -> None:
    """Re-run the launcher inside the project virtual environment when available."""
    if not VENV_PYTHON.exists():
        return

    if Path(sys.executable).resolve() == VENV_PYTHON.resolve():
        return

    print(f"Re-launching with project virtual environment: {VENV_PYTHON}")
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), __file__])


def ensure_tkinter_available() -> None:
    """Fail fast with a useful message when the current Python lacks tkinter."""
    tk_spec = importlib.util.find_spec("tkinter")
    _tk_spec = importlib.util.find_spec("_tkinter")
    if tk_spec is not None and _tk_spec is not None:
        return

    print("ERROR: The current Python interpreter does not include tkinter.")
    print(f"  Python: {sys.executable}")
    print()
    print("Fix: recreate the virtual environment using the system Python (which ships with tkinter):")
    print()
    print("  rm -rf .venv")
    print("  /usr/bin/python3 -m venv .venv")
    print("  source .venv/bin/activate")
    print("  pip install -r requirements.txt")
    print()
    print("Then launch with:  ./start.sh")
    sys.exit(1)


def check_and_install_dependencies(web: bool = False) -> None:
    """Check if required packages are installed, and install them only inside .venv."""
    print("Checking dependencies...")
    modules = REQUIRED_MODULES_WEB if web else REQUIRED_MODULES
    missing_packages = []

    for package, module_name in modules.items():
        if importlib.util.find_spec(module_name) is None:
            missing_packages.append(package)

    if missing_packages:
        print(f"Missing packages: {', '.join(missing_packages)}")

        if Path(sys.executable).resolve() != VENV_PYTHON.resolve():
            print("Activate the project virtual environment and install dependencies with:")
            print("source .venv/bin/activate")
            print(f"python -m pip install -r {REQUIREMENTS_FILE.name}")
            sys.exit(1)

        print("Installing missing packages into .venv...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
                cwd=PROJECT_ROOT,
            )
            print("Dependencies installed successfully!")
        except subprocess.CalledProcessError:
            print("Failed to install dependencies into the project virtual environment.")
            print("Please run:")
            print(f"{sys.executable} -m pip install -r {REQUIREMENTS_FILE}")
            sys.exit(1)
    else:
        print("All dependencies are installed!")


def main() -> None:
    """Launch the GUI application (desktop or web based on --web flag)."""
    web_mode = True

    ensure_project_environment()
    check_and_install_dependencies(web=web_mode)

    if web_mode:
        print("\nLaunching AnimeUnity Downloader (web GUI)...")
        try:
            from web_gui import main as web_main
            web_main()
        except Exception as e:
            print(f"Error launching web GUI: {e}")
            sys.exit(1)
    else:
        ensure_tkinter_available()
        os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")
        print("\nLaunching AnimeUnity Downloader GUI...")
        try:
            from gui import main as gui_main
            gui_main()
        except Exception as e:
            print(f"Error launching GUI: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
