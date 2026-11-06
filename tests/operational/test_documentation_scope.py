import importlib.util
from pathlib import Path


def test_documentation_validation_does_not_inspect_installed_dependencies(tmp_path):
    spec = importlib.util.spec_from_file_location("docs_validator", Path("scripts/validate_docs.py"))
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    validator.ROOT = tmp_path
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "reference.md").write_text("Reference", encoding="utf-8")
    (tmp_path / "README.md").write_text("[Reference](docs/reference.md)", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "NOTICE.md").write_text("[License](missing-vendor-license)", encoding="utf-8")
    assert validator.validate_links() == []
