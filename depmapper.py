#!/usr/bin/env python3
"""
DepMapper - Python Dependency Mapper & Circular Import Detector

Scans Python projects to map import dependencies, detect circular imports,
measure coupling metrics, and generate dependency tree visualizations.
Understanding import relationships is critical for maintaining clean
architecture - DepMapper makes this instant and automatic.

Author: ATLAS (Team Brain)
For: Logan Smith / Metaphy LLC
Version: 1.0
Date: February 14, 2026
License: MIT
"""

# Standard library imports (alphabetical)
import argparse
import ast
import json
import os
import sys
import textwrap
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# =============================================================================
# VERSION
# =============================================================================

__version__ = "1.0.0"
__author__ = "ATLAS (Team Brain)"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ImportInfo:
    """Represents a single import statement found in a Python file.

    Attributes:
        module: The module being imported (e.g., 'os.path')
        names: Specific names imported (e.g., ['join', 'exists'])
        line: Line number where the import appears
        is_from: Whether this is a 'from X import Y' style import
        is_relative: Whether this is a relative import (starts with .)
        level: Number of dots in relative import (0 = absolute)
    """
    module: str
    names: List[str] = field(default_factory=list)
    line: int = 0
    is_from: bool = False
    is_relative: bool = False
    level: int = 0


@dataclass
class ModuleInfo:
    """Information about a single Python module (file) in the project.

    Attributes:
        name: Module name (dotted path, e.g., 'mypackage.utils')
        filepath: Absolute path to the .py file
        imports: List of ImportInfo objects found in this module
        is_package: Whether this is an __init__.py (package marker)
        line_count: Number of lines in the file
        parse_error: If not None, the error that prevented parsing
    """
    name: str
    filepath: str
    imports: List[ImportInfo] = field(default_factory=list)
    is_package: bool = False
    line_count: int = 0
    parse_error: Optional[str] = None


@dataclass
class CouplingMetrics:
    """Coupling metrics for a single module.

    Attributes:
        module: Module name
        fan_in: Number of modules that import this module
        fan_out: Number of modules this module imports
        instability: fan_out / (fan_in + fan_out), range 0.0 to 1.0
                     0.0 = maximally stable (everyone depends on it)
                     1.0 = maximally unstable (depends on everything)
    """
    module: str
    fan_in: int = 0
    fan_out: int = 0
    instability: float = 0.0


@dataclass
class ScanResult:
    """Complete result of a project scan.

    Attributes:
        root_path: The project root that was scanned
        modules: Dict of module_name -> ModuleInfo
        edges: Dict of module_name -> set of imported module names
        scan_time: Time taken for the scan in seconds
        total_files: Number of Python files found
        parse_errors: Number of files that failed to parse
    """
    root_path: str
    modules: Dict[str, ModuleInfo] = field(default_factory=dict)
    edges: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    scan_time: float = 0.0
    total_files: int = 0
    parse_errors: int = 0


# =============================================================================
# CORE ENGINE
# =============================================================================

class DepMapper:
    """
    Python Dependency Mapper - the core analysis engine.

    Scans Python projects to build a dependency graph, then provides
    various analysis methods: tree visualization, circular import
    detection, coupling metrics, and more.

    Example:
        >>> dm = DepMapper()
        >>> result = dm.scan("./my_project")
        >>> print(f"Found {result.total_files} files")
        >>> cycles = dm.find_circular()
        >>> if cycles:
        ...     print(f"WARNING: {len(cycles)} circular imports found!")
    """

    # Known Python standard library top-level modules (Python 3.8+)
    STDLIB_MODULES: Set[str] = {
        "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
        "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
        "binhex", "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb",
        "chunk", "cmath", "cmd", "code", "codecs", "codeop", "collections",
        "colorsys", "compileall", "concurrent", "configparser", "contextlib",
        "contextvars", "copy", "copyreg", "cProfile", "crypt", "csv",
        "ctypes", "curses", "dataclasses", "datetime", "dbm", "decimal",
        "difflib", "dis", "distutils", "doctest", "email", "encodings",
        "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput",
        "fnmatch", "fractions", "ftplib", "functools", "gc", "getopt",
        "getpass", "gettext", "glob", "grp", "gzip", "hashlib", "heapq",
        "hmac", "html", "http", "idlelib", "imaplib", "imghdr", "imp",
        "importlib", "inspect", "io", "ipaddress", "itertools", "json",
        "keyword", "lib2to3", "linecache", "locale", "logging", "lzma",
        "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap",
        "modulefinder", "multiprocessing", "netrc", "nis", "nntplib",
        "numbers", "operator", "optparse", "os", "ossaudiodev", "pathlib",
        "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform",
        "plistlib", "poplib", "posix", "posixpath", "pprint", "profile",
        "pstats", "pty", "pwd", "py_compile", "pyclbr", "pydoc",
        "queue", "quopri", "random", "re", "readline", "reprlib",
        "resource", "rlcompleter", "runpy", "sched", "secrets", "select",
        "selectors", "shelve", "shlex", "shutil", "signal", "site",
        "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd",
        "sqlite3", "sre_compile", "sre_constants", "sre_parse", "ssl",
        "stat", "statistics", "string", "stringprep", "struct", "subprocess",
        "sunau", "symtable", "sys", "sysconfig", "syslog", "tabnanny",
        "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap",
        "threading", "time", "timeit", "tkinter", "token", "tokenize",
        "tomllib", "trace", "traceback", "tracemalloc", "tty", "turtle",
        "turtledemo", "types", "typing", "unicodedata", "unittest", "urllib",
        "uu", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
        "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc",
        "zipapp", "zipfile", "zipimport", "zlib", "_thread",
    }

    def __init__(self) -> None:
        """Initialize DepMapper with empty state."""
        self._result: Optional[ScanResult] = None
        self._reverse_edges: Dict[str, Set[str]] = defaultdict(set)

    # -------------------------------------------------------------------------
    # SCANNING
    # -------------------------------------------------------------------------

    def scan(self, path: str, exclude: Optional[List[str]] = None) -> ScanResult:
        """
        Scan a Python project directory and build the dependency graph.

        Args:
            path: Path to the project root directory or a single .py file
            exclude: List of directory/file patterns to exclude
                     (e.g., ['__pycache__', '.git', 'venv'])

        Returns:
            ScanResult with all discovered modules and dependencies

        Raises:
            FileNotFoundError: If path does not exist
            ValueError: If path is not a directory or .py file
        """
        target = Path(path).resolve()

        if not target.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        if target.is_file() and not target.suffix == ".py":
            raise ValueError(f"Not a Python file: {path}")

        if exclude is None:
            exclude = ["__pycache__", ".git", ".venv", "venv", "env",
                        "node_modules", ".tox", ".eggs", "build", "dist",
                        ".pytest_cache", ".mypy_cache"]

        start_time = time.time()

        result = ScanResult(root_path=str(target))

        if target.is_file():
            # Single file scan
            module_name = target.stem
            module_info = self._parse_file(target, module_name)
            result.modules[module_name] = module_info
            result.total_files = 1
            if module_info.parse_error:
                result.parse_errors = 1
        else:
            # Directory scan
            py_files = self._find_python_files(target, exclude)
            result.total_files = len(py_files)

            for py_file in py_files:
                module_name = self._path_to_module(py_file, target)
                module_info = self._parse_file(py_file, module_name)
                result.modules[module_name] = module_info
                if module_info.parse_error:
                    result.parse_errors += 1

        # Build dependency edges (only for local modules)
        local_modules = set(result.modules.keys())
        local_top_levels = {m.split(".")[0] for m in local_modules}

        for mod_name, mod_info in result.modules.items():
            for imp in mod_info.imports:
                resolved = self._resolve_import(imp, mod_name, local_modules,
                                                local_top_levels)
                if resolved:
                    result.edges[mod_name].add(resolved)

        result.scan_time = time.time() - start_time

        # Store result and build reverse edges
        self._result = result
        self._reverse_edges = defaultdict(set)
        for src, targets in result.edges.items():
            for tgt in targets:
                self._reverse_edges[tgt].add(src)

        return result

    def _find_python_files(self, root: Path,
                           exclude: List[str]) -> List[Path]:
        """Find all .py files in directory tree, respecting exclusions.

        Args:
            root: Root directory to search
            exclude: Directory/file name patterns to skip

        Returns:
            Sorted list of Path objects for Python files
        """
        py_files = []
        exclude_set = set(exclude)

        for dirpath, dirnames, filenames in os.walk(root):
            # Filter out excluded directories (modify in-place to skip)
            dirnames[:] = [d for d in dirnames if d not in exclude_set]

            for filename in filenames:
                if filename.endswith(".py"):
                    py_files.append(Path(dirpath) / filename)

        return sorted(py_files)

    def _path_to_module(self, filepath: Path, root: Path) -> str:
        """Convert a file path to a Python module name.

        Args:
            filepath: Absolute path to .py file
            root: Project root directory

        Returns:
            Dotted module name (e.g., 'mypackage.submod.utils')
        """
        relative = filepath.relative_to(root)
        parts = list(relative.parts)

        # Remove .py extension from last part
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]

        # Handle __init__.py -> package name (drop __init__)
        if parts[-1] == "__init__":
            parts = parts[:-1]

        if not parts:
            # Root __init__.py
            return root.name

        return ".".join(parts)

    def _parse_file(self, filepath: Path, module_name: str) -> ModuleInfo:
        """Parse a Python file and extract import information.

        Args:
            filepath: Path to the .py file
            module_name: The module's dotted name

        Returns:
            ModuleInfo with extracted imports
        """
        info = ModuleInfo(
            name=module_name,
            filepath=str(filepath),
            is_package=filepath.name == "__init__.py",
        )

        try:
            source = filepath.read_text(encoding="utf-8", errors="replace")
            info.line_count = source.count("\n") + 1
        except (OSError, PermissionError) as e:
            info.parse_error = f"Read error: {e}"
            return info

        try:
            tree = ast.parse(source, filename=str(filepath))
        except SyntaxError as e:
            info.parse_error = f"Syntax error: line {e.lineno}: {e.msg}"
            return info

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    info.imports.append(ImportInfo(
                        module=alias.name,
                        names=[alias.asname or alias.name],
                        line=node.lineno,
                        is_from=False,
                        is_relative=False,
                        level=0,
                    ))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [a.name for a in (node.names or [])]
                info.imports.append(ImportInfo(
                    module=module,
                    names=names,
                    line=node.lineno,
                    is_from=True,
                    is_relative=node.level > 0,
                    level=node.level or 0,
                ))

        return info

    def _resolve_import(self, imp: ImportInfo, current_module: str,
                        local_modules: Set[str],
                        local_top_levels: Set[str]) -> Optional[str]:
        """Resolve an import to a local module name, if applicable.

        Args:
            imp: The ImportInfo to resolve
            current_module: The module where this import appears
            local_modules: Set of all known local module names
            local_top_levels: Set of top-level package/module names

        Returns:
            Resolved local module name, or None if external/stdlib
        """
        if imp.is_relative:
            # Resolve relative imports
            parts = current_module.split(".")
            # Go up 'level' packages
            if imp.level <= len(parts):
                base_parts = parts[:len(parts) - imp.level]
            else:
                base_parts = []

            if imp.module:
                candidate = ".".join(base_parts + [imp.module]) if base_parts else imp.module
            else:
                candidate = ".".join(base_parts) if base_parts else ""

            if candidate in local_modules:
                return candidate
            # Try parent package
            parent = candidate.rsplit(".", 1)[0] if "." in candidate else candidate
            if parent in local_modules:
                return parent
            return None

        # Absolute import
        module_name = imp.module

        # Check if it's a standard library module
        top_level = module_name.split(".")[0]
        if top_level in self.STDLIB_MODULES:
            return None

        # Check if it matches a local module exactly
        if module_name in local_modules:
            return module_name

        # Check if top-level matches a local package
        if top_level in local_top_levels:
            # Find the best matching local module
            if module_name in local_modules:
                return module_name
            # Try progressively shorter prefixes
            parts = module_name.split(".")
            for i in range(len(parts), 0, -1):
                candidate = ".".join(parts[:i])
                if candidate in local_modules:
                    return candidate
            return top_level if top_level in local_modules else None

        # Not a local import (third-party)
        return None

    # -------------------------------------------------------------------------
    # ANALYSIS: DEPENDENCY TREE
    # -------------------------------------------------------------------------

    def get_tree(self, root_module: Optional[str] = None,
                 max_depth: int = 10) -> str:
        """
        Generate a text-based dependency tree.

        Args:
            root_module: Start from this module (None = show all roots)
            max_depth: Maximum depth to traverse (prevents infinite recursion)

        Returns:
            String containing the formatted dependency tree

        Raises:
            RuntimeError: If no scan has been performed yet
        """
        self._ensure_scanned()
        result = self._result

        lines: List[str] = []

        if root_module:
            if root_module not in result.modules:
                return f"[!] Module not found: {root_module}"
            lines.append(root_module)
            visited: Set[str] = set()
            self._build_tree(root_module, "", True, lines, visited,
                             0, max_depth)
        else:
            # Find root modules (those with no inbound local edges)
            all_targets = set()
            for targets in result.edges.values():
                all_targets.update(targets)

            roots = sorted(set(result.modules.keys()) - all_targets)

            if not roots:
                # All modules are in cycles; show all
                roots = sorted(result.modules.keys())

            for i, mod in enumerate(roots):
                is_last = (i == len(roots) - 1)
                lines.append(mod)
                visited = set()
                self._build_tree(mod, "", is_last, lines, visited,
                                 0, max_depth)
                if not is_last:
                    lines.append("")

        return "\n".join(lines)

    def _build_tree(self, module: str, prefix: str, is_last: bool,
                    lines: List[str], visited: Set[str],
                    depth: int, max_depth: int) -> None:
        """Recursively build tree lines.

        Args:
            module: Current module name
            prefix: Line prefix for indentation
            is_last: Whether this is the last child at current level
            lines: Accumulating output lines
            visited: Set of already-visited modules (cycle prevention)
            depth: Current depth
            max_depth: Maximum allowed depth
        """
        if depth >= max_depth:
            return

        visited.add(module)
        deps = sorted(self._result.edges.get(module, set()))

        for i, dep in enumerate(deps):
            dep_is_last = (i == len(deps) - 1)
            connector = "`-- " if dep_is_last else "|-- "
            extension = "    " if dep_is_last else "|   "

            if dep in visited:
                lines.append(f"{prefix}{connector}{dep} [circular]")
            else:
                lines.append(f"{prefix}{connector}{dep}")
                self._build_tree(dep, prefix + extension, dep_is_last,
                                 lines, visited.copy(), depth + 1, max_depth)

    # -------------------------------------------------------------------------
    # ANALYSIS: CIRCULAR IMPORTS
    # -------------------------------------------------------------------------

    def find_circular(self, max_cycle_length: int = 20) -> List[List[str]]:
        """
        Find all circular import chains in the dependency graph.

        Uses depth-first search with path tracking to find cycles.

        Args:
            max_cycle_length: Maximum cycle length to report (prevents
                              reporting very long chains that are less useful)

        Returns:
            List of cycles, where each cycle is a list of module names
            forming the circular dependency chain.

        Raises:
            RuntimeError: If no scan has been performed yet

        Example:
            >>> cycles = dm.find_circular()
            >>> for cycle in cycles:
            ...     print(" -> ".join(cycle))
            module_a -> module_b -> module_a
        """
        self._ensure_scanned()
        result = self._result

        cycles: List[List[str]] = []
        visited: Set[str] = set()
        path: List[str] = []
        path_set: Set[str] = set()

        def dfs(node: str) -> None:
            """DFS with path tracking for cycle detection."""
            if node in path_set:
                # Found a cycle - extract it
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                if len(cycle) <= max_cycle_length + 1:
                    # Normalize: start from the lexicographically smallest
                    min_idx = cycle[:-1].index(min(cycle[:-1]))
                    normalized = cycle[min_idx:-1] + cycle[min_idx:min_idx + 1]
                    if normalized not in cycles:
                        cycles.append(normalized)
                return

            if node in visited:
                return

            visited.add(node)
            path.append(node)
            path_set.add(node)

            for dep in sorted(result.edges.get(node, set())):
                dfs(dep)

            path.pop()
            path_set.discard(node)

        for module in sorted(result.modules.keys()):
            if module not in visited:
                visited.clear()
                dfs(module)

        return sorted(cycles, key=lambda c: (len(c), c))

    # -------------------------------------------------------------------------
    # ANALYSIS: COUPLING METRICS
    # -------------------------------------------------------------------------

    def get_metrics(self, sort_by: str = "instability") -> List[CouplingMetrics]:
        """
        Calculate coupling metrics for all modules.

        Metrics:
        - Fan-In: How many modules import this module (afferent coupling)
        - Fan-Out: How many modules this module imports (efferent coupling)
        - Instability: fan_out / (fan_in + fan_out)
          * 0.0 = maximally stable (everything depends on it)
          * 1.0 = maximally unstable (depends on everything, nothing depends on it)

        Args:
            sort_by: Sort results by 'instability', 'fan_in', 'fan_out',
                     or 'name'

        Returns:
            List of CouplingMetrics, sorted as requested

        Raises:
            RuntimeError: If no scan has been performed yet
            ValueError: If sort_by is not a valid field
        """
        self._ensure_scanned()
        result = self._result

        valid_sorts = {"instability", "fan_in", "fan_out", "name"}
        if sort_by not in valid_sorts:
            raise ValueError(
                f"Invalid sort_by: {sort_by}. Valid: {', '.join(sorted(valid_sorts))}"
            )

        metrics_list: List[CouplingMetrics] = []

        for mod_name in result.modules:
            fan_out = len(result.edges.get(mod_name, set()))
            fan_in = len(self._reverse_edges.get(mod_name, set()))
            total = fan_in + fan_out

            instability = fan_out / total if total > 0 else 0.0

            metrics_list.append(CouplingMetrics(
                module=mod_name,
                fan_in=fan_in,
                fan_out=fan_out,
                instability=round(instability, 3),
            ))

        if sort_by == "name":
            metrics_list.sort(key=lambda m: m.module)
        elif sort_by == "fan_in":
            metrics_list.sort(key=lambda m: (-m.fan_in, m.module))
        elif sort_by == "fan_out":
            metrics_list.sort(key=lambda m: (-m.fan_out, m.module))
        else:  # instability
            metrics_list.sort(key=lambda m: (-m.instability, m.module))

        return metrics_list

    # -------------------------------------------------------------------------
    # ANALYSIS: ORPHAN MODULES
    # -------------------------------------------------------------------------

    def find_orphans(self) -> List[str]:
        """
        Find modules that no other local module imports.

        These are potential entry points, standalone scripts, or dead code.
        Modules that both have no fan-in AND no fan-out are most likely
        standalone scripts. Modules with no fan-in but some fan-out are
        entry points or orchestrators.

        Returns:
            List of module names with zero fan-in, sorted alphabetically

        Raises:
            RuntimeError: If no scan has been performed yet
        """
        self._ensure_scanned()
        result = self._result

        all_imported = set()
        for targets in result.edges.values():
            all_imported.update(targets)

        orphans = []
        for mod_name in sorted(result.modules.keys()):
            if mod_name not in all_imported:
                orphans.append(mod_name)

        return orphans

    # -------------------------------------------------------------------------
    # ANALYSIS: FULL REPORT
    # -------------------------------------------------------------------------

    def generate_report(self, format: str = "text") -> str:
        """
        Generate a comprehensive dependency analysis report.

        Combines scan summary, dependency tree, circular imports,
        coupling metrics, and orphan detection into one report.

        Args:
            format: Output format - 'text', 'json', or 'markdown'

        Returns:
            Formatted report string

        Raises:
            RuntimeError: If no scan has been performed yet
            ValueError: If format is not valid
        """
        self._ensure_scanned()

        valid_formats = {"text", "json", "markdown"}
        if format not in valid_formats:
            raise ValueError(
                f"Invalid format: {format}. Valid: {', '.join(sorted(valid_formats))}"
            )

        if format == "json":
            return self._report_json()
        elif format == "markdown":
            return self._report_markdown()
        else:
            return self._report_text()

    def _report_text(self) -> str:
        """Generate plain text report."""
        result = self._result
        lines: List[str] = []
        sep = "=" * 70

        # Header
        lines.append(sep)
        lines.append("DEPMAPPER - DEPENDENCY ANALYSIS REPORT")
        lines.append(sep)
        lines.append(f"Project: {result.root_path}")
        lines.append(f"Scanned: {result.total_files} Python files")
        lines.append(f"Parse errors: {result.parse_errors}")
        lines.append(f"Scan time: {result.scan_time:.3f}s")
        lines.append(f"Modules: {len(result.modules)}")
        total_edges = sum(len(t) for t in result.edges.values())
        lines.append(f"Dependencies: {total_edges}")
        lines.append("")

        # Dependency Tree
        lines.append(sep)
        lines.append("DEPENDENCY TREE")
        lines.append("-" * 70)
        tree = self.get_tree()
        if tree.strip():
            lines.append(tree)
        else:
            lines.append("(no local dependencies found)")
        lines.append("")

        # Circular Imports
        cycles = self.find_circular()
        lines.append(sep)
        lines.append("CIRCULAR IMPORTS")
        lines.append("-" * 70)
        if cycles:
            lines.append(f"[!] Found {len(cycles)} circular import chain(s):")
            lines.append("")
            for i, cycle in enumerate(cycles, 1):
                chain = " -> ".join(cycle)
                lines.append(f"  Cycle {i}: {chain}")
        else:
            lines.append("[OK] No circular imports detected!")
        lines.append("")

        # Coupling Metrics
        metrics = self.get_metrics(sort_by="instability")
        lines.append(sep)
        lines.append("COUPLING METRICS")
        lines.append("-" * 70)
        if metrics:
            header = f"{'Module':<40} {'Fan-In':>7} {'Fan-Out':>8} {'Instab.':>8}"
            lines.append(header)
            lines.append("-" * 70)
            for m in metrics:
                lines.append(
                    f"{m.module:<40} {m.fan_in:>7} {m.fan_out:>8} "
                    f"{m.instability:>8.3f}"
                )
        else:
            lines.append("(no modules to analyze)")
        lines.append("")

        # Orphan Modules
        orphans = self.find_orphans()
        lines.append(sep)
        lines.append("ORPHAN MODULES (no inbound imports)")
        lines.append("-" * 70)
        if orphans:
            for orph in orphans:
                fan_out = len(result.edges.get(orph, set()))
                if fan_out > 0:
                    label = "entry point / orchestrator"
                else:
                    label = "standalone / potential dead code"
                lines.append(f"  {orph} ({label})")
        else:
            lines.append("(all modules are imported by at least one other)")
        lines.append("")

        # Parse Errors
        if result.parse_errors > 0:
            lines.append(sep)
            lines.append("PARSE ERRORS")
            lines.append("-" * 70)
            for mod_name, mod_info in sorted(result.modules.items()):
                if mod_info.parse_error:
                    lines.append(f"  {mod_name}: {mod_info.parse_error}")
            lines.append("")

        lines.append(sep)
        lines.append("Report generated by DepMapper v" + __version__)
        lines.append(sep)

        return "\n".join(lines)

    def _report_json(self) -> str:
        """Generate JSON report."""
        result = self._result
        cycles = self.find_circular()
        metrics = self.get_metrics(sort_by="name")
        orphans = self.find_orphans()

        report = {
            "depmapper_version": __version__,
            "project": result.root_path,
            "summary": {
                "total_files": result.total_files,
                "total_modules": len(result.modules),
                "total_dependencies": sum(len(t) for t in result.edges.values()),
                "parse_errors": result.parse_errors,
                "scan_time_seconds": round(result.scan_time, 3),
                "circular_import_count": len(cycles),
                "orphan_count": len(orphans),
            },
            "modules": {},
            "dependencies": {},
            "circular_imports": [
                {"cycle": cycle, "length": len(cycle)} for cycle in cycles
            ],
            "coupling_metrics": [asdict(m) for m in metrics],
            "orphans": orphans,
        }

        for mod_name, mod_info in sorted(result.modules.items()):
            report["modules"][mod_name] = {
                "filepath": mod_info.filepath,
                "line_count": mod_info.line_count,
                "is_package": mod_info.is_package,
                "import_count": len(mod_info.imports),
                "parse_error": mod_info.parse_error,
            }

        for mod_name, deps in sorted(result.edges.items()):
            if deps:
                report["dependencies"][mod_name] = sorted(deps)

        return json.dumps(report, indent=2)

    def _report_markdown(self) -> str:
        """Generate Markdown report."""
        result = self._result
        cycles = self.find_circular()
        metrics = self.get_metrics(sort_by="instability")
        orphans = self.find_orphans()
        total_edges = sum(len(t) for t in result.edges.values())

        lines: List[str] = []

        lines.append("# DepMapper - Dependency Analysis Report")
        lines.append("")
        lines.append(f"**Project:** `{result.root_path}`  ")
        lines.append(f"**Files Scanned:** {result.total_files}  ")
        lines.append(f"**Modules Found:** {len(result.modules)}  ")
        lines.append(f"**Dependencies:** {total_edges}  ")
        lines.append(f"**Parse Errors:** {result.parse_errors}  ")
        lines.append(f"**Scan Time:** {result.scan_time:.3f}s  ")
        lines.append("")

        # Summary Table
        lines.append("## Summary")
        lines.append("")
        status_circ = "[!] FOUND" if cycles else "[OK]"
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Python Files | {result.total_files} |")
        lines.append(f"| Local Modules | {len(result.modules)} |")
        lines.append(f"| Dependencies | {total_edges} |")
        lines.append(f"| Circular Imports | {len(cycles)} {status_circ} |")
        lines.append(f"| Orphan Modules | {len(orphans)} |")
        lines.append(f"| Parse Errors | {result.parse_errors} |")
        lines.append("")

        # Dependency Tree
        lines.append("## Dependency Tree")
        lines.append("")
        lines.append("```")
        tree = self.get_tree()
        lines.append(tree if tree.strip() else "(no local dependencies)")
        lines.append("```")
        lines.append("")

        # Circular Imports
        lines.append("## Circular Imports")
        lines.append("")
        if cycles:
            lines.append(
                f"**[!] {len(cycles)} circular import chain(s) detected:**"
            )
            lines.append("")
            for i, cycle in enumerate(cycles, 1):
                chain = " -> ".join(cycle)
                lines.append(f"{i}. `{chain}`")
        else:
            lines.append("**[OK] No circular imports detected!**")
        lines.append("")

        # Coupling Metrics
        lines.append("## Coupling Metrics")
        lines.append("")
        if metrics:
            lines.append("| Module | Fan-In | Fan-Out | Instability |")
            lines.append("|--------|--------|---------|-------------|")
            for m in metrics:
                lines.append(
                    f"| {m.module} | {m.fan_in} | {m.fan_out} | "
                    f"{m.instability:.3f} |"
                )
        else:
            lines.append("(no modules to analyze)")
        lines.append("")

        # Orphans
        lines.append("## Orphan Modules")
        lines.append("")
        if orphans:
            lines.append(
                "These modules are not imported by any other local module:"
            )
            lines.append("")
            for orph in orphans:
                fan_out = len(result.edges.get(orph, set()))
                label = ("entry point" if fan_out > 0
                         else "standalone / dead code")
                lines.append(f"- `{orph}` ({label})")
        else:
            lines.append("All modules are imported by at least one other.")
        lines.append("")

        lines.append("---")
        lines.append(f"*Generated by DepMapper v{__version__}*")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # ANALYSIS: DOT GRAPH
    # -------------------------------------------------------------------------

    def generate_dot(self, highlight_cycles: bool = True) -> str:
        """
        Generate a Graphviz DOT format dependency graph.

        The output can be rendered with Graphviz:
            dot -Tpng graph.dot -o graph.png

        Args:
            highlight_cycles: If True, edges in circular imports
                              are highlighted in red

        Returns:
            String containing the DOT format graph

        Raises:
            RuntimeError: If no scan has been performed yet
        """
        self._ensure_scanned()
        result = self._result

        cycle_edges: Set[Tuple[str, str]] = set()
        if highlight_cycles:
            cycles = self.find_circular()
            for cycle in cycles:
                for i in range(len(cycle) - 1):
                    cycle_edges.add((cycle[i], cycle[i + 1]))

        lines: List[str] = []
        lines.append("digraph dependencies {")
        lines.append('    rankdir=LR;')
        lines.append('    node [shape=box, style=filled, '
                      'fillcolor="#e8f4fd", fontname="Arial"];')
        lines.append('    edge [fontname="Arial", fontsize=10];')
        lines.append("")

        # Nodes
        for mod_name in sorted(result.modules.keys()):
            mod = result.modules[mod_name]
            label = mod_name.replace(".", "\\n")
            safe_id = mod_name.replace(".", "_")

            if mod.is_package:
                lines.append(
                    f'    {safe_id} [label="{label}", '
                    f'fillcolor="#d4edda"];'
                )
            else:
                lines.append(f'    {safe_id} [label="{label}"];')

        lines.append("")

        # Edges
        for src, targets in sorted(result.edges.items()):
            safe_src = src.replace(".", "_")
            for tgt in sorted(targets):
                safe_tgt = tgt.replace(".", "_")
                if (src, tgt) in cycle_edges:
                    lines.append(
                        f'    {safe_src} -> {safe_tgt} '
                        f'[color="red", penwidth=2.0];'
                    )
                else:
                    lines.append(f'    {safe_src} -> {safe_tgt};')

        lines.append("}")
        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # UTILITY / QUERY
    # -------------------------------------------------------------------------

    def get_imports_for(self, module: str) -> List[str]:
        """
        Get the list of local modules that a given module imports.

        Args:
            module: Module name to query

        Returns:
            Sorted list of module names imported by the given module

        Raises:
            RuntimeError: If no scan has been performed yet
        """
        self._ensure_scanned()
        return sorted(self._result.edges.get(module, set()))

    def get_importers_of(self, module: str) -> List[str]:
        """
        Get the list of local modules that import a given module.

        Args:
            module: Module name to query

        Returns:
            Sorted list of module names that import the given module

        Raises:
            RuntimeError: If no scan has been performed yet
        """
        self._ensure_scanned()
        return sorted(self._reverse_edges.get(module, set()))

    def get_all_imports(self, module: str,
                        classify: bool = False) -> Dict[str, List[str]]:
        """
        Get all imports for a module, classified by type.

        Args:
            module: Module name to query
            classify: If True, returns classified dict; otherwise flat list

        Returns:
            Dict with keys: 'stdlib', 'local', 'third_party', 'relative'
            Each maps to a list of module names.

        Raises:
            RuntimeError: If no scan has been performed yet
            KeyError: If module not found
        """
        self._ensure_scanned()
        result = self._result

        if module not in result.modules:
            raise KeyError(f"Module not found: {module}")

        mod_info = result.modules[module]
        classified = {
            "stdlib": [],
            "local": [],
            "third_party": [],
            "relative": [],
        }

        local_top_levels = {m.split(".")[0] for m in result.modules}

        for imp in mod_info.imports:
            if imp.is_relative:
                classified["relative"].append(imp.module or ".")
            elif imp.module.split(".")[0] in self.STDLIB_MODULES:
                classified["stdlib"].append(imp.module)
            elif imp.module.split(".")[0] in local_top_levels:
                classified["local"].append(imp.module)
            else:
                classified["third_party"].append(imp.module)

        # Sort each category
        for key in classified:
            classified[key] = sorted(set(classified[key]))

        return classified

    def _ensure_scanned(self) -> None:
        """Verify that a scan has been performed.

        Raises:
            RuntimeError: If no scan result is available
        """
        if self._result is None:
            raise RuntimeError(
                "No scan performed yet. Call scan() first."
            )


# =============================================================================
# CLI INTERFACE
# =============================================================================

def format_scan_summary(result: ScanResult) -> str:
    """Format a brief scan summary for CLI output.

    Args:
        result: The scan result to summarize

    Returns:
        Formatted summary string
    """
    total_edges = sum(len(t) for t in result.edges.values())
    lines = [
        f"[OK] Scan complete: {result.root_path}",
        f"     Files: {result.total_files} | "
        f"Modules: {len(result.modules)} | "
        f"Dependencies: {total_edges} | "
        f"Time: {result.scan_time:.3f}s",
    ]
    if result.parse_errors > 0:
        lines.append(
            f"     [!] {result.parse_errors} file(s) had parse errors"
        )
    return "\n".join(lines)


def cmd_scan(args: argparse.Namespace) -> int:
    """Handle the 'scan' command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    dm = DepMapper()
    exclude = args.exclude.split(",") if args.exclude else None

    try:
        result = dm.scan(args.path, exclude=exclude)
    except (FileNotFoundError, ValueError) as e:
        print(f"[X] Error: {e}")
        return 1

    print(format_scan_summary(result))

    if args.json:
        print(dm.generate_report(format="json"))
    elif args.markdown:
        print(dm.generate_report(format="markdown"))

    return 0


def cmd_tree(args: argparse.Namespace) -> int:
    """Handle the 'tree' command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    dm = DepMapper()
    exclude = args.exclude.split(",") if args.exclude else None

    try:
        result = dm.scan(args.path, exclude=exclude)
    except (FileNotFoundError, ValueError) as e:
        print(f"[X] Error: {e}")
        return 1

    print(format_scan_summary(result))
    print()
    print("DEPENDENCY TREE")
    print("-" * 50)

    tree = dm.get_tree(root_module=args.module, max_depth=args.depth)
    print(tree if tree.strip() else "(no local dependencies found)")

    return 0


def cmd_circular(args: argparse.Namespace) -> int:
    """Handle the 'circular' command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 2 if cycles found)
    """
    dm = DepMapper()
    exclude = args.exclude.split(",") if args.exclude else None

    try:
        result = dm.scan(args.path, exclude=exclude)
    except (FileNotFoundError, ValueError) as e:
        print(f"[X] Error: {e}")
        return 1

    print(format_scan_summary(result))
    print()

    cycles = dm.find_circular(max_cycle_length=args.max_length)

    if cycles:
        print(f"[!] Found {len(cycles)} circular import chain(s):")
        print()
        for i, cycle in enumerate(cycles, 1):
            chain = " -> ".join(cycle)
            print(f"  Cycle {i}: {chain}")
        return 2
    else:
        print("[OK] No circular imports detected!")
        return 0


def cmd_metrics(args: argparse.Namespace) -> int:
    """Handle the 'metrics' command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    dm = DepMapper()
    exclude = args.exclude.split(",") if args.exclude else None

    try:
        result = dm.scan(args.path, exclude=exclude)
    except (FileNotFoundError, ValueError) as e:
        print(f"[X] Error: {e}")
        return 1

    print(format_scan_summary(result))
    print()

    try:
        metrics = dm.get_metrics(sort_by=args.sort)
    except ValueError as e:
        print(f"[X] Error: {e}")
        return 1

    if args.json:
        data = [asdict(m) for m in metrics]
        print(json.dumps(data, indent=2))
        return 0

    print("COUPLING METRICS")
    print("-" * 70)
    header = f"{'Module':<40} {'Fan-In':>7} {'Fan-Out':>8} {'Instab.':>8}"
    print(header)
    print("-" * 70)

    for m in metrics:
        # Mark extreme values
        marker = ""
        if m.instability >= 0.8:
            marker = " [!]"
        elif m.instability <= 0.2 and m.fan_in > 0:
            marker = " [stable]"

        print(
            f"{m.module:<40} {m.fan_in:>7} {m.fan_out:>8} "
            f"{m.instability:>8.3f}{marker}"
        )

    return 0


def cmd_orphans(args: argparse.Namespace) -> int:
    """Handle the 'orphans' command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    dm = DepMapper()
    exclude = args.exclude.split(",") if args.exclude else None

    try:
        result = dm.scan(args.path, exclude=exclude)
    except (FileNotFoundError, ValueError) as e:
        print(f"[X] Error: {e}")
        return 1

    print(format_scan_summary(result))
    print()

    orphans = dm.find_orphans()

    if orphans:
        print(f"ORPHAN MODULES ({len(orphans)} found)")
        print("-" * 50)
        for orph in orphans:
            fan_out = len(result.edges.get(orph, set()))
            if fan_out > 0:
                label = "entry point / orchestrator"
            else:
                label = "standalone / potential dead code"
            print(f"  {orph} ({label})")
    else:
        print("[OK] All modules are imported by at least one other module.")

    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Handle the 'report' command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    dm = DepMapper()
    exclude = args.exclude.split(",") if args.exclude else None

    try:
        dm.scan(args.path, exclude=exclude)
    except (FileNotFoundError, ValueError) as e:
        print(f"[X] Error: {e}")
        return 1

    fmt = "text"
    if args.json:
        fmt = "json"
    elif args.markdown:
        fmt = "markdown"

    report = dm.generate_report(format=fmt)

    if args.output:
        try:
            Path(args.output).write_text(report, encoding="utf-8")
            print(f"[OK] Report saved to: {args.output}")
        except OSError as e:
            print(f"[X] Error saving report: {e}")
            return 1
    else:
        print(report)

    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    """Handle the 'graph' command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    dm = DepMapper()
    exclude = args.exclude.split(",") if args.exclude else None

    try:
        dm.scan(args.path, exclude=exclude)
    except (FileNotFoundError, ValueError) as e:
        print(f"[X] Error: {e}")
        return 1

    dot = dm.generate_dot(highlight_cycles=not args.no_highlight)

    if args.output:
        try:
            Path(args.output).write_text(dot, encoding="utf-8")
            print(f"[OK] DOT graph saved to: {args.output}")
            print(
                f"     Render with: dot -Tpng {args.output} "
                f"-o {Path(args.output).stem}.png"
            )
        except OSError as e:
            print(f"[X] Error saving graph: {e}")
            return 1
    else:
        print(dot)

    return 0


def main() -> int:
    """CLI entry point for DepMapper.

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    # Windows console encoding fix
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    parser = argparse.ArgumentParser(
        prog="depmapper",
        description="DepMapper - Python Dependency Mapper & Circular Import Detector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              %(prog)s scan ./my_project          Scan and show summary
              %(prog)s tree ./my_project          Show dependency tree
              %(prog)s circular ./src             Check for circular imports
              %(prog)s metrics ./src --sort fan-in Show coupling metrics
              %(prog)s orphans ./src              Find orphan modules
              %(prog)s report ./src --markdown    Full report in Markdown
              %(prog)s graph ./src -o deps.dot    Generate Graphviz DOT graph

            For more info: https://github.com/DonkRonk17/DepMapper
        """),
    )

    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Command to execute"
    )

    # --- scan ---
    p_scan = subparsers.add_parser(
        "scan", help="Scan a project and show summary"
    )
    p_scan.add_argument("path", help="Path to Python project or file")
    p_scan.add_argument("--exclude", help="Comma-separated dirs to exclude")
    p_scan.add_argument("--json", action="store_true",
                        help="Output full scan as JSON")
    p_scan.add_argument("--markdown", action="store_true",
                        help="Output full scan as Markdown")

    # --- tree ---
    p_tree = subparsers.add_parser(
        "tree", help="Show dependency tree"
    )
    p_tree.add_argument("path", help="Path to Python project or file")
    p_tree.add_argument("--module", "-m", help="Start tree from this module")
    p_tree.add_argument("--depth", "-d", type=int, default=10,
                        help="Max tree depth (default: 10)")
    p_tree.add_argument("--exclude", help="Comma-separated dirs to exclude")

    # --- circular ---
    p_circ = subparsers.add_parser(
        "circular", help="Find circular imports"
    )
    p_circ.add_argument("path", help="Path to Python project or file")
    p_circ.add_argument("--max-length", type=int, default=20,
                        help="Max cycle length to report (default: 20)")
    p_circ.add_argument("--exclude", help="Comma-separated dirs to exclude")

    # --- metrics ---
    p_met = subparsers.add_parser(
        "metrics", help="Show coupling metrics"
    )
    p_met.add_argument("path", help="Path to Python project or file")
    p_met.add_argument("--sort", "-s", default="instability",
                       choices=["instability", "fan_in", "fan_out", "name"],
                       help="Sort by field (default: instability)")
    p_met.add_argument("--json", action="store_true",
                       help="Output as JSON")
    p_met.add_argument("--exclude", help="Comma-separated dirs to exclude")

    # --- orphans ---
    p_orph = subparsers.add_parser(
        "orphans", help="Find modules with no inbound imports"
    )
    p_orph.add_argument("path", help="Path to Python project or file")
    p_orph.add_argument("--exclude", help="Comma-separated dirs to exclude")

    # --- report ---
    p_rep = subparsers.add_parser(
        "report", help="Generate full analysis report"
    )
    p_rep.add_argument("path", help="Path to Python project or file")
    p_rep.add_argument("--json", action="store_true",
                       help="Output as JSON")
    p_rep.add_argument("--markdown", action="store_true",
                       help="Output as Markdown")
    p_rep.add_argument("--output", "-o", help="Save report to file")
    p_rep.add_argument("--exclude", help="Comma-separated dirs to exclude")

    # --- graph ---
    p_graph = subparsers.add_parser(
        "graph", help="Generate Graphviz DOT graph"
    )
    p_graph.add_argument("path", help="Path to Python project or file")
    p_graph.add_argument("--output", "-o", help="Save DOT to file")
    p_graph.add_argument("--no-highlight", action="store_true",
                         help="Don't highlight circular import edges")
    p_graph.add_argument("--exclude", help="Comma-separated dirs to exclude")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "scan": cmd_scan,
        "tree": cmd_tree,
        "circular": cmd_circular,
        "metrics": cmd_metrics,
        "orphans": cmd_orphans,
        "report": cmd_report,
        "graph": cmd_graph,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
