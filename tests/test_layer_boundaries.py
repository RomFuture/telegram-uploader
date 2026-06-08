import ast
from pathlib import Path

FORBIDDEN_USE_CASES = {"sqlalchemy", "urllib", "infrastructure", "celery"}
FORBIDDEN_INFRASTRUCTURE = {"domain", "application"}
FORBIDDEN_APPLICATION = {"domain", "use_cases"}


def _top_level_module(name: str) -> str:
    return name.split(".")[0]


def _collect_top_level_domain_imports(path: Path) -> list[str]:
    violations: list[str] = []
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _top_level_module(alias.name) == "domain":
                    violations.append(alias.name)
        if isinstance(node, ast.ImportFrom) and node.module:
            if _top_level_module(node.module) == "domain":
                violations.append(node.module)
    return violations


def _collect_forbidden_imports(path: Path, forbidden: set[str]) -> list[str]:
    violations: list[str] = []
    tree = ast.parse(path.read_text())
    type_checking_nodes: set[int] = set()
    for node in ast.walk(tree):
        is_type_checking = (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Name)
            and node.test.id == "TYPE_CHECKING"
        )
        if is_type_checking:
            for child in ast.walk(node):
                type_checking_nodes.add(id(child))

    for node in ast.walk(tree):
        if id(node) in type_checking_nodes:
            continue
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _top_level_module(alias.name) in forbidden:
                    violations.append(alias.name)
        if isinstance(node, ast.ImportFrom) and node.module:
            if _top_level_module(node.module) in forbidden:
                violations.append(node.module)
    return violations


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
        violations = _collect_forbidden_imports(path, FORBIDDEN_INFRASTRUCTURE)
        assert not violations, f"{path}: {', '.join(violations)}"


def test_application_has_no_domain_or_use_cases_imports() -> None:
    root = Path("src/application")
    if not root.exists():
        return
    for path in root.rglob("*.py"):
        violations = _collect_forbidden_imports(path, FORBIDDEN_APPLICATION)
        assert not violations, f"{path}: {', '.join(violations)}"


FORBIDDEN_DOMAIN_SUBMODULES = {"errors", "models", "factories", "actions", "guards", "scenarios"}


def _collect_domain_submodule_imports(path: Path) -> list[str]:
    violations: list[str] = []
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            if len(parts) >= 2 and parts[0] == "domain":
                submodule = parts[1]
                if submodule in FORBIDDEN_DOMAIN_SUBMODULES:
                    violations.append(node.module)
    return violations


def test_use_case_modules_do_not_import_domain_submodules() -> None:
    roots = (
        Path("src/use_cases/backup"),
        Path("src/use_cases/session"),
        Path("src/use_cases/restore"),
    )
    for root in roots:
        for path in root.rglob("*.py"):
            violations = _collect_domain_submodule_imports(path)
            assert not violations, f"{path}: {', '.join(violations)}"


def test_domain_has_no_outward_layer_imports() -> None:
    forbidden_roots = {"infrastructure", "application", "observation", "use_cases"}
    forbidden_third_party = {"sqlalchemy", "celery", "urllib", "redis", "psycopg"}
    root = Path("src/domain")
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = _top_level_module(alias.name)
                    assert top not in forbidden_roots, f"{path}: {alias.name}"
                    assert top not in forbidden_third_party, f"{path}: {alias.name}"
            if isinstance(node, ast.ImportFrom) and node.module:
                top = _top_level_module(node.module)
                assert top not in forbidden_roots, f"{path}: {node.module}"
                assert top not in forbidden_third_party, f"{path}: {node.module}"


def test_no_empty_init_py_under_src() -> None:
    for path in Path("src").rglob("__init__.py"):
        assert path.stat().st_size > 0, f"empty package entrypoint: {path}"
