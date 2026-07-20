from pathlib import Path
import subprocess


def test_launcher_self_check_succeeds() -> None:
    launcher = Path("scripts/start-demo.command")
    assert launcher.exists()
    result = subprocess.run(
        ["zsh", str(launcher), "--check"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Demo 启动环境检查通过" in result.stdout
    assert "http://127.0.0.1:8501" in result.stdout


def test_launcher_exposes_project_root_to_python_imports() -> None:
    launcher_text = Path("scripts/start-demo.command").read_text()
    assert 'PYTHONPATH="$APP_DIR"' in launcher_text
