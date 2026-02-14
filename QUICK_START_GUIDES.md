# 🗺️ DepMapper - Quick Start Guides

## 📖 ABOUT THESE GUIDES

Each Team Brain agent has a **5-minute quick-start guide** tailored to their role and workflows.

**Choose your guide:**
- [Forge (Orchestrator)](#-forge-quick-start)
- [Atlas (Executor)](#-atlas-quick-start)
- [Clio (Linux Agent)](#-clio-quick-start)
- [Nexus (Multi-Platform)](#-nexus-quick-start)
- [Bolt (Free Executor)](#-bolt-quick-start)
- [IRIS (Desktop Specialist)](#-iris-quick-start)

---

## 🔥 FORGE QUICK START

**Role:** Orchestrator / Reviewer  
**Time:** 5 minutes  
**Goal:** Use DepMapper for architecture review and code quality assessment

### Step 1: Verify Installation

```bash
python depmapper.py --version
# Expected: depmapper 1.0.0
```

### Step 2: Quick Architecture Assessment

```bash
# Scan a tool you're reviewing
python depmapper.py report ./ToolBeingReviewed
```

This gives you:
- Dependency tree (who imports what)
- Circular import status
- Coupling metrics (most depended-on modules)
- Orphan modules (potential dead code)

### Step 3: Critical Quality Gate — Circular Imports

```bash
python depmapper.py circular ./ToolBeingReviewed
# Exit code 0 = clean, 2 = issues found
```

**Review Rule:** If circular imports exist, request fix before approval.

### Step 4: Coupling Health Check

```bash
python depmapper.py metrics ./ToolBeingReviewed --sort fan_in
```

**Red Flags to Watch For:**
- Utility module with instability > 0.8 (too many dependencies)
- Core module with fan-in = 0 (nothing uses it — dead code?)
- Single module with fan-in > 10 (God module — should it be split?)

### Step 5: Integration with Review Workflow

```python
# In your review script
from depmapper import DepMapper

dm = DepMapper()
dm.scan("./tool_under_review")

# Automatic checks
cycles = dm.find_circular()
if cycles:
    print(f"BLOCKER: {len(cycles)} circular imports")

metrics = dm.get_metrics()
risky = [m for m in metrics if m.fan_in > 8]
if risky:
    print(f"NOTE: {len(risky)} heavily-depended modules")
```

### Forge Next Steps
1. Add DepMapper check to your review checklist
2. Try `depmapper report --markdown` for review notes
3. Read [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md) - Forge section

---

## ⚡ ATLAS QUICK START

**Role:** Executor / Builder  
**Time:** 5 minutes  
**Goal:** Use DepMapper as a quality gate during tool builds

### Step 1: Verify Installation

```bash
python -c "from depmapper import DepMapper; print('[OK] DepMapper ready')"
```

### Step 2: Pre-Build Analysis

Before starting a new tool, analyze existing tools for patterns:

```bash
# See how a well-structured tool looks
python depmapper.py tree ./SynapseLink
python depmapper.py metrics ./SynapseLink
```

### Step 3: During Development — Check Your Work

After writing your core code (Phase 2), verify import health:

```bash
# Check for circular imports (should be 0!)
python depmapper.py circular ./MyNewTool

# Check coupling metrics
python depmapper.py metrics ./MyNewTool
```

### Step 4: Phase 8 Quality Gate

Add to your quality audit:

```python
from depmapper import DepMapper

dm = DepMapper()
result = dm.scan("./MyNewTool")

# Quality checks
cycles = dm.find_circular()
assert len(cycles) == 0, f"FAIL: {len(cycles)} circular imports"

orphans = dm.find_orphans()
dead = [o for o in orphans if len(result.edges.get(o, set())) == 0]
print(f"Orphan modules: {len(orphans)} ({len(dead)} potential dead code)")

# Generate dependency report for docs
report = dm.generate_report(format="markdown")
with open("DEPENDENCY_REPORT.md", "w") as f:
    f.write(report)

print("[OK] Dependency analysis passed")
```

### Step 5: Common Atlas Commands

```bash
# Full project scan
python depmapper.py scan ./NewTool

# Quick circular check
python depmapper.py circular ./NewTool

# Full report for documentation
python depmapper.py report ./NewTool --markdown -o DEPENDENCY_REPORT.md

# Visual graph
python depmapper.py graph ./NewTool -o deps.dot
```

### Atlas Next Steps
1. Add circular import check to your Phase 8 quality audit
2. Include dependency report in your build documentation
3. Use `depmapper metrics` to validate clean architecture

---

## 🐧 CLIO QUICK START

**Role:** Linux / Ubuntu Agent  
**Time:** 5 minutes  
**Goal:** Use DepMapper for CI/CD integration and Linux tool analysis

### Step 1: Linux Installation

```bash
# Clone from GitHub
git clone https://github.com/DonkRonk17/DepMapper.git
cd DepMapper

# Verify (no pip install needed!)
python3 depmapper.py --version

# Optional: install Graphviz for visual graphs
sudo apt install graphviz
```

### Step 2: Quick Scan

```bash
python3 depmapper.py scan ./your_project
python3 depmapper.py circular ./your_project
```

### Step 3: CI/CD Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Checking for circular imports..."
python3 depmapper.py circular ./src
if [ $? -eq 2 ]; then
    echo "BLOCKED: Circular imports detected!"
    echo "Fix them before committing."
    exit 1
fi
echo "Import check passed."
```

### Step 4: Generate Visual Graph

```bash
python3 depmapper.py graph ./project -o deps.dot
dot -Tpng deps.dot -o deps.png
dot -Tsvg deps.dot -o deps.svg
# Open in browser or image viewer
```

### Step 5: Batch Analysis

```bash
# Analyze all Python projects in a directory
for dir in */; do
    if ls "$dir"*.py 1>/dev/null 2>&1; then
        echo "=== $dir ==="
        python3 depmapper.py circular "$dir"
        echo ""
    fi
done
```

### Clio Next Steps
1. Add to CI/CD pipeline as quality gate
2. Set up pre-commit hook for active projects
3. Generate dependency graphs for documentation

---

## 🌐 NEXUS QUICK START

**Role:** Multi-Platform Agent  
**Time:** 5 minutes  
**Goal:** Cross-platform dependency analysis

### Step 1: Platform Detection

```python
import platform
from depmapper import DepMapper

dm = DepMapper()
print(f"Platform: {platform.system()}")
print(f"DepMapper ready on {platform.system()}")
```

### Step 2: Cross-Platform Scan

```python
from depmapper import DepMapper
from pathlib import Path

dm = DepMapper()
# Path objects handle platform differences automatically
result = dm.scan(str(Path("./project")))
print(f"Files: {result.total_files}")
print(f"Platform path: {result.root_path}")
```

### Step 3: Verify Consistency

Run the same analysis on different platforms and compare:

```python
from depmapper import DepMapper
import json

dm = DepMapper()
dm.scan("./project")
report = dm.generate_report(format="json")
data = json.loads(report)

# Key metrics that should be identical across platforms
print(f"Modules: {data['summary']['total_modules']}")
print(f"Dependencies: {data['summary']['total_dependencies']}")
print(f"Circular: {data['summary']['circular_import_count']}")
```

### Step 4: Platform-Specific Notes

**Windows:**
- Uses backslash paths internally but accepts forward slashes
- Console encoding auto-configured for UTF-8

**Linux:**
- All features work natively
- Graphviz available via `apt install graphviz`

**macOS:**
- All features work natively
- Graphviz available via `brew install graphviz`

### Nexus Next Steps
1. Test on all 3 platforms to verify consistency
2. Add to cross-platform test suites
3. Report any platform-specific issues

---

## 🆓 BOLT QUICK START

**Role:** Free Executor (Cline + Grok)  
**Time:** 5 minutes  
**Goal:** Use DepMapper for cost-free dependency analysis

### Step 1: Verify Free Access

```bash
# No API key needed! No pip install needed!
python depmapper.py --version
```

### Step 2: Quick Scan — Zero Cost

```bash
# Scan a project (runs locally, no API calls)
python depmapper.py scan ./any_project
python depmapper.py circular ./any_project
```

### Step 3: Batch All Team Brain Tools

```bash
# Analyze entire AutoProjects — costs nothing!
for tool_dir in C:/Users/logan/OneDrive/Documents/AutoProjects/*/; do
    tool_name=$(basename "$tool_dir")
    echo "=== $tool_name ==="
    python depmapper.py circular "$tool_dir" 2>/dev/null
    echo ""
done
```

### Step 4: Generate Reports for Team

```bash
# Generate markdown reports (free, local)
python depmapper.py report ./project --markdown -o report.md

# JSON for processing
python depmapper.py report ./project --json > analysis.json
```

### Step 5: Cost-Free Quality Checks

```bash
# Run as part of your build process
python depmapper.py circular ./src      # 0 tokens
python depmapper.py metrics ./src       # 0 tokens
python depmapper.py orphans ./src       # 0 tokens
# Total API cost: $0.00
```

### Bolt Next Steps
1. Add to your standard build checks
2. Use for bulk project scanning
3. Generate dependency reports for team review

---

## 🖥️ IRIS QUICK START

**Role:** Desktop Development Specialist  
**Time:** 5 minutes  
**Goal:** Analyze desktop application dependency structures

### Step 1: Quick Check

```bash
python depmapper.py --version
```

### Step 2: Analyze Desktop App Structure

```bash
# Desktop apps often have complex import trees
python depmapper.py tree ./desktop_app
python depmapper.py metrics ./desktop_app --sort fan_in
```

### Step 3: Check for Architecture Issues

```python
from depmapper import DepMapper

dm = DepMapper()
dm.scan("./desktop_app")

# Desktop apps should have clear layers
# UI -> Business Logic -> Data
# Check for violations:
metrics = dm.get_metrics()
for m in metrics:
    if "ui" in m.module.lower() and m.fan_in > 0:
        importers = dm.get_importers_of(m.module)
        non_ui = [i for i in importers if "ui" not in i.lower()]
        if non_ui:
            print(f"WARNING: Non-UI module imports UI: {non_ui} -> {m.module}")
```

### IRIS Next Steps
1. Use for VitalHeart architecture analysis
2. Generate dependency graphs for UI/logic/data layers
3. Track coupling trends across development phases

---

## 📚 ADDITIONAL RESOURCES

**For All Agents:**
- Full Documentation: [README.md](README.md)
- Examples: [EXAMPLES.md](EXAMPLES.md)
- Integration Plan: [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md)
- Integration Examples: [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md)
- Cheat Sheet: [CHEAT_SHEET.txt](CHEAT_SHEET.txt)

**Support:**
- GitHub Issues: https://github.com/DonkRonk17/DepMapper/issues
- Synapse: Post in THE_SYNAPSE/active/
- Direct: Message ATLAS

---

**Last Updated:** February 14, 2026  
**Maintained By:** ATLAS (Team Brain)
