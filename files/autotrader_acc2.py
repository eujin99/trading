import pathlib
import subprocess
import sys


if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parents[1]
    cmd = [sys.executable, str(root / "app.py"), "--config-module", "config_acc2"]
    raise SystemExit(subprocess.call(cmd, cwd=str(root)))
