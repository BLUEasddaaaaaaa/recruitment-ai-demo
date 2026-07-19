import importlib.metadata
import tomllib
from pathlib import Path

from packaging.requirements import Requirement


def test_installed_openai_sdk_meets_declared_verified_floor() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    dependency = next(
        Requirement(value) for value in project["dependencies"] if value.startswith("openai")
    )

    assert str(dependency.specifier) == "<2,>=1.109.1"
    assert dependency.specifier.contains(importlib.metadata.version("openai"), prereleases=True)
