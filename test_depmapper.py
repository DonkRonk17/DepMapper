#!/usr/bin/env python3
"""
Comprehensive test suite for DepMapper v1.0.

Tests cover:
- Core scanning and parsing
- Dependency tree generation
- Circular import detection
- Coupling metrics calculation
- Orphan module detection
- Report generation (text, JSON, markdown)
- DOT graph output
- Edge cases and error handling
- CLI interface
- Python API

Run: python test_depmapper.py
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from depmapper import (
    DepMapper,
    ImportInfo,
    ModuleInfo,
    CouplingMetrics,
    ScanResult,
    __version__,
    main,
)


class TestHelpers:
    """Shared test helpers for creating temporary Python projects."""

    @staticmethod
    def create_temp_project(files: dict) -> str:
        """Create a temporary project directory with given files.

        Args:
            files: Dict of relative_path -> file_content

        Returns:
            Path to the temporary directory
        """
        tmpdir = tempfile.mkdtemp(prefix="depmapper_test_")
        for rel_path, content in files.items():
            filepath = Path(tmpdir) / rel_path
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
        return tmpdir


class TestDepMapperCore(unittest.TestCase):
    """Test core scanning and parsing functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.dm = DepMapper()
        self.temp_dirs = []

    def tearDown(self):
        """Clean up temporary directories."""
        for d in self.temp_dirs:
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass

    def _create_project(self, files):
        """Helper to create and track temp project."""
        d = TestHelpers.create_temp_project(files)
        self.temp_dirs.append(d)
        return d

    def test_initialization(self):
        """Test DepMapper initializes with empty state."""
        dm = DepMapper()
        self.assertIsNotNone(dm)
        self.assertIsNone(dm._result)

    def test_scan_single_file(self):
        """Test scanning a single Python file."""
        proj = self._create_project({
            "hello.py": "import os\nimport sys\nprint('hello')\n",
        })
        result = self.dm.scan(os.path.join(proj, "hello.py"))
        self.assertEqual(result.total_files, 1)
        self.assertEqual(len(result.modules), 1)
        self.assertIn("hello", result.modules)

    def test_scan_directory(self):
        """Test scanning a directory with multiple files."""
        proj = self._create_project({
            "main.py": "import os\nfrom utils import helper\n",
            "utils.py": "def helper(): pass\n",
            "config.py": "import json\n",
        })
        result = self.dm.scan(proj)
        self.assertEqual(result.total_files, 3)
        self.assertEqual(len(result.modules), 3)

    def test_scan_with_packages(self):
        """Test scanning a project with package structure."""
        proj = self._create_project({
            "mypackage/__init__.py": "",
            "mypackage/core.py": "from mypackage import utils\n",
            "mypackage/utils.py": "import os\n",
        })
        result = self.dm.scan(proj)
        self.assertEqual(result.total_files, 3)
        # Should have mypackage, mypackage.core, mypackage.utils
        self.assertTrue(any("core" in m for m in result.modules))
        self.assertTrue(any("utils" in m for m in result.modules))

    def test_scan_excludes_directories(self):
        """Test that excluded directories are skipped."""
        proj = self._create_project({
            "main.py": "x = 1\n",
            "__pycache__/cached.py": "x = 2\n",
            "venv/lib/pkg.py": "x = 3\n",
        })
        result = self.dm.scan(proj)
        # Should only find main.py (pycache and venv excluded by default)
        self.assertEqual(result.total_files, 1)

    def test_scan_custom_excludes(self):
        """Test custom exclude patterns."""
        proj = self._create_project({
            "main.py": "x = 1\n",
            "tests/test_main.py": "x = 2\n",
        })
        result = self.dm.scan(proj, exclude=["tests"])
        self.assertEqual(result.total_files, 1)

    def test_scan_nonexistent_path(self):
        """Test scanning a nonexistent path raises error."""
        with self.assertRaises(FileNotFoundError):
            self.dm.scan("/nonexistent/path/to/nothing")

    def test_scan_non_python_file(self):
        """Test scanning a non-Python file raises error."""
        proj = self._create_project({
            "readme.txt": "Hello",
        })
        with self.assertRaises(ValueError):
            self.dm.scan(os.path.join(proj, "readme.txt"))

    def test_scan_handles_syntax_errors(self):
        """Test graceful handling of Python files with syntax errors."""
        proj = self._create_project({
            "good.py": "x = 1\n",
            "bad.py": "def broken(\n",  # Syntax error
        })
        result = self.dm.scan(proj)
        self.assertEqual(result.total_files, 2)
        self.assertEqual(result.parse_errors, 1)
        # The bad file should still be in modules with parse_error set
        bad_mod = None
        for name, info in result.modules.items():
            if "bad" in name:
                bad_mod = info
                break
        self.assertIsNotNone(bad_mod)
        self.assertIsNotNone(bad_mod.parse_error)

    def test_scan_time_recorded(self):
        """Test that scan time is recorded."""
        proj = self._create_project({"a.py": "x = 1\n"})
        result = self.dm.scan(proj)
        self.assertGreaterEqual(result.scan_time, 0)
        self.assertIsInstance(result.scan_time, float)

    def test_import_extraction_basic(self):
        """Test extraction of basic import statements."""
        proj = self._create_project({
            "main.py": "import os\nimport sys\nfrom pathlib import Path\n",
        })
        result = self.dm.scan(proj)
        mod = result.modules["main"]
        self.assertEqual(len(mod.imports), 3)

    def test_local_dependency_detection(self):
        """Test that local imports create edges."""
        proj = self._create_project({
            "app.py": "import utils\nfrom config import settings\n",
            "utils.py": "def helper(): pass\n",
            "config.py": "settings = {}\n",
        })
        result = self.dm.scan(proj)
        app_deps = result.edges.get("app", set())
        self.assertIn("utils", app_deps)
        self.assertIn("config", app_deps)

    def test_stdlib_not_in_edges(self):
        """Test that stdlib imports are not recorded as local edges."""
        proj = self._create_project({
            "main.py": "import os\nimport sys\nimport json\n",
        })
        result = self.dm.scan(proj)
        self.assertEqual(len(result.edges.get("main", set())), 0)


class TestDependencyTree(unittest.TestCase):
    """Test dependency tree generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.dm = DepMapper()
        self.temp_dirs = []

    def tearDown(self):
        """Clean up temporary directories."""
        for d in self.temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _create_project(self, files):
        d = TestHelpers.create_temp_project(files)
        self.temp_dirs.append(d)
        return d

    def test_tree_no_scan_raises(self):
        """Test that get_tree raises without prior scan."""
        dm = DepMapper()
        with self.assertRaises(RuntimeError):
            dm.get_tree()

    def test_tree_simple(self):
        """Test tree output for a simple project."""
        proj = self._create_project({
            "main.py": "import utils\n",
            "utils.py": "x = 1\n",
        })
        self.dm.scan(proj)
        tree = self.dm.get_tree()
        self.assertIn("main", tree)
        self.assertIn("utils", tree)

    def test_tree_specific_module(self):
        """Test tree from a specific module."""
        proj = self._create_project({
            "a.py": "import b\n",
            "b.py": "import c\n",
            "c.py": "x = 1\n",
        })
        self.dm.scan(proj)
        tree = self.dm.get_tree(root_module="a")
        self.assertIn("a", tree)
        self.assertIn("b", tree)
        self.assertIn("c", tree)

    def test_tree_nonexistent_module(self):
        """Test tree for a module that doesn't exist."""
        proj = self._create_project({"a.py": "x = 1\n"})
        self.dm.scan(proj)
        tree = self.dm.get_tree(root_module="nonexistent")
        self.assertIn("[!]", tree)

    def test_tree_marks_circular(self):
        """Test that circular deps are marked in tree."""
        proj = self._create_project({
            "a.py": "import b\n",
            "b.py": "import a\n",
        })
        self.dm.scan(proj)
        tree = self.dm.get_tree()
        self.assertIn("[circular]", tree)


class TestCircularImports(unittest.TestCase):
    """Test circular import detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.dm = DepMapper()
        self.temp_dirs = []

    def tearDown(self):
        """Clean up temporary directories."""
        for d in self.temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _create_project(self, files):
        d = TestHelpers.create_temp_project(files)
        self.temp_dirs.append(d)
        return d

    def test_no_circular_imports(self):
        """Test project with no circular imports."""
        proj = self._create_project({
            "a.py": "import b\n",
            "b.py": "import c\n",
            "c.py": "x = 1\n",
        })
        self.dm.scan(proj)
        cycles = self.dm.find_circular()
        self.assertEqual(len(cycles), 0)

    def test_simple_circular_import(self):
        """Test detection of A -> B -> A cycle."""
        proj = self._create_project({
            "a.py": "import b\n",
            "b.py": "import a\n",
        })
        self.dm.scan(proj)
        cycles = self.dm.find_circular()
        self.assertGreater(len(cycles), 0)
        # Verify the cycle contains both a and b
        cycle_mods = set()
        for cycle in cycles:
            cycle_mods.update(cycle)
        self.assertIn("a", cycle_mods)
        self.assertIn("b", cycle_mods)

    def test_triple_circular_import(self):
        """Test detection of A -> B -> C -> A cycle."""
        proj = self._create_project({
            "a.py": "import b\n",
            "b.py": "import c\n",
            "c.py": "import a\n",
        })
        self.dm.scan(proj)
        cycles = self.dm.find_circular()
        self.assertGreater(len(cycles), 0)

    def test_no_scan_raises(self):
        """Test that find_circular raises without prior scan."""
        dm = DepMapper()
        with self.assertRaises(RuntimeError):
            dm.find_circular()


class TestCouplingMetrics(unittest.TestCase):
    """Test coupling metrics calculation."""

    def setUp(self):
        """Set up test fixtures."""
        self.dm = DepMapper()
        self.temp_dirs = []

    def tearDown(self):
        """Clean up temporary directories."""
        for d in self.temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _create_project(self, files):
        d = TestHelpers.create_temp_project(files)
        self.temp_dirs.append(d)
        return d

    def test_metrics_basic(self):
        """Test basic metrics calculation."""
        proj = self._create_project({
            "core.py": "x = 1\n",
            "utils.py": "import core\n",
            "main.py": "import core\nimport utils\n",
        })
        self.dm.scan(proj)
        metrics = self.dm.get_metrics(sort_by="name")

        # core should have fan_in=2 (utils and main import it)
        core_met = next(m for m in metrics if m.module == "core")
        self.assertEqual(core_met.fan_in, 2)
        self.assertEqual(core_met.fan_out, 0)
        self.assertEqual(core_met.instability, 0.0)  # maximally stable

        # main has fan_in=0, fan_out=2
        main_met = next(m for m in metrics if m.module == "main")
        self.assertEqual(main_met.fan_in, 0)
        self.assertEqual(main_met.fan_out, 2)
        self.assertEqual(main_met.instability, 1.0)  # maximally unstable

    def test_metrics_sort_options(self):
        """Test that all sort options work."""
        proj = self._create_project({
            "a.py": "import b\n",
            "b.py": "x = 1\n",
        })
        self.dm.scan(proj)

        for sort_by in ["instability", "fan_in", "fan_out", "name"]:
            metrics = self.dm.get_metrics(sort_by=sort_by)
            self.assertEqual(len(metrics), 2)

    def test_metrics_invalid_sort(self):
        """Test that invalid sort_by raises ValueError."""
        proj = self._create_project({"a.py": "x = 1\n"})
        self.dm.scan(proj)
        with self.assertRaises(ValueError):
            self.dm.get_metrics(sort_by="invalid")

    def test_metrics_no_scan_raises(self):
        """Test that get_metrics raises without prior scan."""
        dm = DepMapper()
        with self.assertRaises(RuntimeError):
            dm.get_metrics()


class TestOrphanDetection(unittest.TestCase):
    """Test orphan module detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.dm = DepMapper()
        self.temp_dirs = []

    def tearDown(self):
        """Clean up temporary directories."""
        for d in self.temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _create_project(self, files):
        d = TestHelpers.create_temp_project(files)
        self.temp_dirs.append(d)
        return d

    def test_find_orphans(self):
        """Test finding modules with no inbound imports."""
        proj = self._create_project({
            "main.py": "import utils\n",
            "utils.py": "x = 1\n",
            "standalone.py": "print('hello')\n",
        })
        self.dm.scan(proj)
        orphans = self.dm.find_orphans()
        self.assertIn("main", orphans)  # nothing imports main
        self.assertIn("standalone", orphans)
        self.assertNotIn("utils", orphans)  # main imports utils

    def test_no_orphans(self):
        """Test project where all modules are imported."""
        proj = self._create_project({
            "a.py": "import b\n",
            "b.py": "import a\n",
        })
        self.dm.scan(proj)
        orphans = self.dm.find_orphans()
        self.assertEqual(len(orphans), 0)


class TestReportGeneration(unittest.TestCase):
    """Test report generation in all formats."""

    def setUp(self):
        """Set up test fixtures."""
        self.dm = DepMapper()
        self.temp_dirs = []
        # Create a test project
        self.proj = self._create_project({
            "main.py": "import utils\nimport config\n",
            "utils.py": "import config\n",
            "config.py": "settings = {}\n",
        })
        self.dm.scan(self.proj)

    def tearDown(self):
        """Clean up temporary directories."""
        for d in self.temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _create_project(self, files):
        d = TestHelpers.create_temp_project(files)
        self.temp_dirs.append(d)
        return d

    def test_text_report(self):
        """Test text format report."""
        report = self.dm.generate_report(format="text")
        self.assertIn("DEPMAPPER", report)
        self.assertIn("DEPENDENCY TREE", report)
        self.assertIn("CIRCULAR IMPORTS", report)
        self.assertIn("COUPLING METRICS", report)

    def test_json_report(self):
        """Test JSON format report."""
        report = self.dm.generate_report(format="json")
        data = json.loads(report)
        self.assertIn("summary", data)
        self.assertIn("modules", data)
        self.assertIn("dependencies", data)
        self.assertIn("coupling_metrics", data)
        self.assertEqual(data["summary"]["total_files"], 3)

    def test_markdown_report(self):
        """Test Markdown format report."""
        report = self.dm.generate_report(format="markdown")
        self.assertIn("# DepMapper", report)
        self.assertIn("## Summary", report)
        self.assertIn("## Dependency Tree", report)
        self.assertIn("## Coupling Metrics", report)

    def test_invalid_format_raises(self):
        """Test that invalid format raises ValueError."""
        with self.assertRaises(ValueError):
            self.dm.generate_report(format="xml")


class TestDotGraphGeneration(unittest.TestCase):
    """Test Graphviz DOT format generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.dm = DepMapper()
        self.temp_dirs = []

    def tearDown(self):
        """Clean up temporary directories."""
        for d in self.temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _create_project(self, files):
        d = TestHelpers.create_temp_project(files)
        self.temp_dirs.append(d)
        return d

    def test_dot_output(self):
        """Test DOT format graph generation."""
        proj = self._create_project({
            "main.py": "import utils\n",
            "utils.py": "x = 1\n",
        })
        self.dm.scan(proj)
        dot = self.dm.generate_dot()
        self.assertIn("digraph", dot)
        self.assertIn("main", dot)
        self.assertIn("utils", dot)
        self.assertIn("->", dot)

    def test_dot_highlights_cycles(self):
        """Test DOT graph highlights circular imports."""
        proj = self._create_project({
            "a.py": "import b\n",
            "b.py": "import a\n",
        })
        self.dm.scan(proj)
        dot = self.dm.generate_dot(highlight_cycles=True)
        self.assertIn("red", dot)

    def test_dot_no_highlight(self):
        """Test DOT graph without cycle highlighting."""
        proj = self._create_project({
            "a.py": "import b\n",
            "b.py": "import a\n",
        })
        self.dm.scan(proj)
        dot = self.dm.generate_dot(highlight_cycles=False)
        self.assertNotIn("red", dot)


class TestUtilityMethods(unittest.TestCase):
    """Test utility and query methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.dm = DepMapper()
        self.temp_dirs = []
        self.proj = self._create_project({
            "main.py": "import utils\nimport config\n",
            "utils.py": "import config\n",
            "config.py": "import os\nimport json\n",
        })
        self.dm.scan(self.proj)

    def tearDown(self):
        """Clean up temporary directories."""
        for d in self.temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _create_project(self, files):
        d = TestHelpers.create_temp_project(files)
        self.temp_dirs.append(d)
        return d

    def test_get_imports_for(self):
        """Test getting imports for a specific module."""
        imports = self.dm.get_imports_for("main")
        self.assertIn("utils", imports)
        self.assertIn("config", imports)

    def test_get_importers_of(self):
        """Test getting modules that import a given module."""
        importers = self.dm.get_importers_of("config")
        self.assertIn("main", importers)
        self.assertIn("utils", importers)

    def test_get_all_imports_classified(self):
        """Test classified import listing."""
        classified = self.dm.get_all_imports("config")
        self.assertIn("stdlib", classified)
        self.assertIn("os", classified["stdlib"])
        self.assertIn("json", classified["stdlib"])

    def test_get_all_imports_nonexistent(self):
        """Test that nonexistent module raises KeyError."""
        with self.assertRaises(KeyError):
            self.dm.get_all_imports("nonexistent")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and unusual inputs."""

    def setUp(self):
        """Set up test fixtures."""
        self.dm = DepMapper()
        self.temp_dirs = []

    def tearDown(self):
        """Clean up temporary directories."""
        for d in self.temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _create_project(self, files):
        d = TestHelpers.create_temp_project(files)
        self.temp_dirs.append(d)
        return d

    def test_empty_project(self):
        """Test scanning a directory with no Python files."""
        proj = self._create_project({
            "readme.md": "# Hello\n",
            "data.txt": "some data\n",
        })
        result = self.dm.scan(proj)
        self.assertEqual(result.total_files, 0)
        self.assertEqual(len(result.modules), 0)

    def test_empty_python_file(self):
        """Test scanning an empty Python file."""
        proj = self._create_project({
            "empty.py": "",
        })
        result = self.dm.scan(proj)
        self.assertEqual(result.total_files, 1)
        self.assertEqual(len(result.modules), 1)

    def test_file_with_encoding_issues(self):
        """Test handling files with encoding issues."""
        proj = self._create_project({
            "utf8.py": "# -*- coding: utf-8 -*-\nx = 'hello'\n",
        })
        result = self.dm.scan(proj)
        self.assertEqual(result.total_files, 1)
        self.assertEqual(result.parse_errors, 0)

    def test_deeply_nested_packages(self):
        """Test scanning deeply nested package structure."""
        proj = self._create_project({
            "pkg/__init__.py": "",
            "pkg/sub/__init__.py": "",
            "pkg/sub/deep/__init__.py": "",
            "pkg/sub/deep/module.py": "import os\n",
        })
        result = self.dm.scan(proj)
        self.assertGreater(result.total_files, 0)
        # Should find the deeply nested module
        deep_found = any("deep" in m for m in result.modules)
        self.assertTrue(deep_found)

    def test_relative_import_handling(self):
        """Test that relative imports are resolved correctly."""
        proj = self._create_project({
            "pkg/__init__.py": "",
            "pkg/core.py": "from . import utils\n",
            "pkg/utils.py": "def helper(): pass\n",
        })
        result = self.dm.scan(proj)
        # pkg.core should depend on pkg.utils
        core_deps = result.edges.get("pkg.core", set())
        # The relative import should resolve to pkg.utils or pkg
        has_dep = len(core_deps) > 0
        self.assertTrue(has_dep)

    def test_star_import(self):
        """Test handling of 'from X import *'."""
        proj = self._create_project({
            "main.py": "from utils import *\n",
            "utils.py": "x = 1\n",
        })
        result = self.dm.scan(proj)
        main_deps = result.edges.get("main", set())
        self.assertIn("utils", main_deps)

    def test_version_exists(self):
        """Test that version string is set."""
        self.assertEqual(__version__, "1.0.0")

    def test_stdlib_modules_populated(self):
        """Test that stdlib module set is populated."""
        self.assertIn("os", DepMapper.STDLIB_MODULES)
        self.assertIn("sys", DepMapper.STDLIB_MODULES)
        self.assertIn("json", DepMapper.STDLIB_MODULES)
        self.assertIn("pathlib", DepMapper.STDLIB_MODULES)

    def test_scan_result_dataclass(self):
        """Test ScanResult dataclass fields."""
        result = ScanResult(root_path="/test")
        self.assertEqual(result.root_path, "/test")
        self.assertEqual(result.total_files, 0)
        self.assertEqual(result.parse_errors, 0)

    def test_import_info_dataclass(self):
        """Test ImportInfo dataclass fields."""
        imp = ImportInfo(module="os", names=["path"], line=1)
        self.assertEqual(imp.module, "os")
        self.assertFalse(imp.is_relative)

    def test_coupling_metrics_dataclass(self):
        """Test CouplingMetrics dataclass fields."""
        met = CouplingMetrics(module="test", fan_in=5, fan_out=3,
                              instability=0.375)
        self.assertEqual(met.module, "test")
        self.assertEqual(met.fan_in, 5)
        self.assertEqual(met.fan_out, 3)
        self.assertAlmostEqual(met.instability, 0.375)


class TestCLI(unittest.TestCase):
    """Test CLI interface."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dirs = []
        self.orig_argv = sys.argv

    def tearDown(self):
        """Clean up."""
        sys.argv = self.orig_argv
        for d in self.temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _create_project(self, files):
        d = TestHelpers.create_temp_project(files)
        self.temp_dirs.append(d)
        return d

    def test_cli_no_args(self):
        """Test CLI with no arguments shows help."""
        sys.argv = ["depmapper"]
        result = main()
        self.assertEqual(result, 0)

    def test_cli_version(self):
        """Test CLI --version flag."""
        sys.argv = ["depmapper", "--version"]
        with self.assertRaises(SystemExit) as ctx:
            main()
        self.assertEqual(ctx.exception.code, 0)

    def test_cli_scan(self):
        """Test CLI scan command."""
        proj = self._create_project({
            "main.py": "import os\n",
        })
        sys.argv = ["depmapper", "scan", proj]
        result = main()
        self.assertEqual(result, 0)

    def test_cli_circular_clean(self):
        """Test CLI circular command with no cycles."""
        proj = self._create_project({
            "main.py": "import os\n",
        })
        sys.argv = ["depmapper", "circular", proj]
        result = main()
        self.assertEqual(result, 0)

    def test_cli_circular_found(self):
        """Test CLI circular command when cycles exist."""
        proj = self._create_project({
            "a.py": "import b\n",
            "b.py": "import a\n",
        })
        sys.argv = ["depmapper", "circular", proj]
        result = main()
        self.assertEqual(result, 2)  # Exit code 2 = cycles found

    def test_cli_scan_nonexistent(self):
        """Test CLI scan with nonexistent path."""
        sys.argv = ["depmapper", "scan", "/nonexistent/path"]
        result = main()
        self.assertEqual(result, 1)


def run_tests():
    """Run all tests with formatted output."""
    print("=" * 70)
    print("TESTING: DepMapper v" + __version__)
    print("=" * 70)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDepMapperCore))
    suite.addTests(loader.loadTestsFromTestCase(TestDependencyTree))
    suite.addTests(loader.loadTestsFromTestCase(TestCircularImports))
    suite.addTests(loader.loadTestsFromTestCase(TestCouplingMetrics))
    suite.addTests(loader.loadTestsFromTestCase(TestOrphanDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestReportGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestDotGraphGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestUtilityMethods))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestCLI))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 70)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"RESULTS: {result.testsRun} tests run")
    print(f"[OK] Passed: {passed}")
    if result.failures:
        print(f"[X] Failed: {len(result.failures)}")
    if result.errors:
        print(f"[X] Errors: {len(result.errors)}")
    status = "[OK] ALL TESTS PASSED" if result.wasSuccessful() else "[X] SOME TESTS FAILED"
    print(status)
    print("=" * 70)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
