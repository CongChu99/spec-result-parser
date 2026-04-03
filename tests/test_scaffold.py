"""
Tests for task tools-7yx.1: Project scaffolding & pyproject.toml.
"""
import sys
from pathlib import Path
from click.testing import CliRunner
from spec_result_parser.cli import main

# Project root is parent of tests/
ROOT = Path(__file__).parent.parent


class TestProjectStructure:
    """Check required files and directories exist."""

    def test_pyproject_toml_exists(self):
        assert (ROOT / "pyproject.toml").exists(), "pyproject.toml not found"

    def test_pyproject_has_project_section(self):
        content = (ROOT / "pyproject.toml").read_text()
        assert "[project]" in content, "pyproject.toml missing [project] section"

    def test_pyproject_has_scripts_section(self):
        content = (ROOT / "pyproject.toml").read_text()
        assert "[project.scripts]" in content, "pyproject.toml missing [project.scripts]"

    def test_pyproject_has_build_system(self):
        content = (ROOT / "pyproject.toml").read_text()
        assert "[build-system]" in content, "pyproject.toml missing [build-system]"

    def test_pyproject_declares_python_version(self):
        content = (ROOT / "pyproject.toml").read_text()
        assert "python" in content.lower() and "3.9" in content, \
            "pyproject.toml missing Python 3.9+ version constraint"

    def test_spec_parser_entry_point(self):
        content = (ROOT / "pyproject.toml").read_text()
        assert "spec-parser" in content, \
            "pyproject.toml missing 'spec-parser' entry point"

    def test_src_package_exists(self):
        assert (ROOT / "src" / "spec_result_parser").is_dir(), \
            "src/spec_result_parser/ package directory not found"

    def test_src_init_exists(self):
        assert (ROOT / "src" / "spec_result_parser" / "__init__.py").exists(), \
            "src/spec_result_parser/__init__.py not found"

    def test_cli_module_exists(self):
        assert (ROOT / "src" / "spec_result_parser" / "cli.py").exists(), \
            "src/spec_result_parser/cli.py not found"

    def test_cli_has_click_main_group(self):
        cli_content = (ROOT / "src" / "spec_result_parser" / "cli.py").read_text()
        assert "click" in cli_content, "cli.py must use click"
        assert "main" in cli_content, "cli.py must define 'main' click group"

    def test_cli_has_check_subcommand(self):
        cli_content = (ROOT / "src" / "spec_result_parser" / "cli.py").read_text()
        assert "check" in cli_content, "cli.py must define 'check' subcommand"

    def test_cli_has_aggregate_subcommand(self):
        cli_content = (ROOT / "src" / "spec_result_parser" / "cli.py").read_text()
        assert "aggregate" in cli_content, "cli.py must define 'aggregate' subcommand"

    def test_tests_init_exists(self):
        assert (ROOT / "tests" / "__init__.py").exists(), \
            "tests/__init__.py not found"

    def test_license_exists(self):
        assert (ROOT / "LICENSE").exists(), "LICENSE file not found"

    def test_license_is_mit(self):
        content = (ROOT / "LICENSE").read_text()
        assert "MIT" in content, "LICENSE must contain 'MIT'"

    def test_readme_exists(self):
        assert (ROOT / "README.md").exists(), "README.md not found"

    def test_gitignore_exists(self):
        assert (ROOT / ".gitignore").exists(), ".gitignore not found"


class TestDependenciesDeclaration:
    """Verify pyproject.toml declares all required runtime deps."""

    def test_click_dependency(self):
        content = (ROOT / "pyproject.toml").read_text()
        assert "click" in content, "pyproject.toml missing 'click' dependency"

    def test_rich_dependency(self):
        content = (ROOT / "pyproject.toml").read_text()
        assert "rich" in content, "pyproject.toml missing 'rich' dependency"

    def test_pyyaml_dependency(self):
        content = (ROOT / "pyproject.toml").read_text()
        assert "PyYAML" in content or "pyyaml" in content.lower(), \
            "pyproject.toml missing 'PyYAML' dependency"

    def test_pandas_dependency(self):
        content = (ROOT / "pyproject.toml").read_text()
        assert "pandas" in content, "pyproject.toml missing 'pandas' dependency"

    def test_hatchling_build_backend(self):
        content = (ROOT / "pyproject.toml").read_text()
        assert "hatchling" in content, "pyproject.toml must use hatchling build backend"

    def test_dev_extras_pytest(self):
        content = (ROOT / "pyproject.toml").read_text()
        assert "pytest" in content, \
            "pyproject.toml missing pytest in dev/test extras"


class TestCliEntryPoints:
    """Verify the CLI entry points work via click.testing.CliRunner."""

    def setup_method(self):
        self.runner = CliRunner()

    def test_main_help(self):
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "spec-parser" in result.output.lower() or "Commands" in result.output

    def test_main_version(self):
        result = self.runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.2.0" in result.output

    def test_check_help(self):
        result = self.runner.invoke(main, ["check", "--help"])
        assert result.exit_code == 0
        assert "--spec" in result.output

    def test_aggregate_help(self):
        result = self.runner.invoke(main, ["aggregate", "--help"])
        assert result.exit_code == 0
        assert "--spec" in result.output

    def test_check_requires_spec_option(self):
        """check command must require --spec flag."""
        with self.runner.isolated_filesystem():
            # Create a dummy result file
            Path("dummy.psf").write_text("dummy content")
            result = self.runner.invoke(main, ["check", "dummy.psf"])
            # Should fail because --spec is required
            assert result.exit_code != 0

    def test_aggregate_requires_spec_option(self):
        """aggregate command must require --spec flag."""
        with self.runner.isolated_filesystem():
            import os
            os.makedirs("corners")
            result = self.runner.invoke(main, ["aggregate", "corners"])
            assert result.exit_code != 0
