import ast
from pathlib import Path

FORBIDDEN_USE_CASES = {"sqlalchemy", "urllib", "infrastructure", "celery"}
FORBIDDEN_INFRASTRUCTURE = {"domain", "application"}
DOMAIN_ALLOWED_PREFIX = Path("src/use_cases/domain")


def _top_level_module(name: str) -> str:
    return name.split(".")[0]


def test_use_cases_have_no_infrastructure_imports() -> None:
    root = Path("src/use_cases")
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert _top_level_module(alias.name) not in FORBIDDEN_USE_CASES, (
                        f"{path}: {alias.name}"
                    )
            if isinstance(node, ast.ImportFrom) and node.module:
                assert _top_level_module(node.module) not in FORBIDDEN_USE_CASES, (
                    f"{path}: {node.module}"
                )


def test_infrastructure_has_no_domain_or_application_imports() -> None:
    root = Path("src/infrastructure")
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert _top_level_module(alias.name) not in FORBIDDEN_INFRASTRUCTURE, (
                        f"{path}: {alias.name}"
                    )
            if isinstance(node, ast.ImportFrom) and node.module:
                assert _top_level_module(node.module) not in FORBIDDEN_INFRASTRUCTURE, (
                    f"{path}: {node.module}"
                )


def test_domain_imports_only_under_use_cases_domain() -> None:
    root = Path("src/use_cases")
    for path in root.rglob("*.py"):
        if path.is_relative_to(DOMAIN_ALLOWED_PREFIX):
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert _top_level_module(alias.name) != "domain", f"{path}: {alias.name}"
            if isinstance(node, ast.ImportFrom) and node.module:
                assert _top_level_module(node.module) != "domain", f"{path}: {node.module}"
