# 🗺️ DepMapper - Integration Plan

## 🎯 INTEGRATION GOALS

This document outlines how DepMapper integrates with:
1. Team Brain agents (Forge, Atlas, Clio, Nexus, Bolt)
2. Existing Team Brain tools (72+ in ecosystem)
3. BCH (Beacon Command Hub)
4. Logan's workflows and CI/CD pipelines

---

## 📦 BCH INTEGRATION

### Overview

DepMapper is a **read-only analysis tool** — it does not modify files, making it safe to integrate into BCH as a diagnostic command. BCH integration enables any agent to request dependency analysis via chat.

### BCH Commands

```
@depmapper scan <path>              Scan project and show summary
@depmapper circular <path>          Check for circular imports
@depmapper metrics <path>           Show coupling metrics
@depmapper report <path>            Full analysis report
@depmapper health <path>            Quick health check (cycles + top metrics)
```

### Implementation Steps

1. **Add to BCH imports:**
   ```python
   sys.path.append(str(Path.home() / "OneDrive/Documents/AutoProjects/DepMapper"))
   from depmapper import DepMapper
   ```

2. **Create command handler:**
   ```python
   async def handle_depmapper(args: list, context: dict) -> str:
       dm = DepMapper()
       command = args[0] if args else "help"
       path = args[1] if len(args) > 1 else "."
       
       if command == "scan":
           result = dm.scan(path)
           return format_scan_summary(result)
       elif command == "circular":
           dm.scan(path)
           cycles = dm.find_circular()
           if cycles:
               return f"[!] {len(cycles)} circular imports found:\n" + \
                      "\n".join(f"  {' -> '.join(c)}" for c in cycles)
           return "[OK] No circular imports!"
       elif command == "metrics":
           dm.scan(path)
           return dm.generate_report(format="text")
       elif command == "report":
           dm.scan(path)
           return dm.generate_report(format="markdown")
       elif command == "health":
           dm.scan(path)
           cycles = dm.find_circular()
           metrics = dm.get_metrics(sort_by="fan_in")[:5]
           health = "[OK] Clean" if not cycles else f"[!] {len(cycles)} cycles"
           top = "\n".join(f"  {m.module}: fan_in={m.fan_in}" for m in metrics)
           return f"Health: {health}\nTop modules:\n{top}"
       return "Commands: scan, circular, metrics, report, health"
   ```

3. **Register in BCH routing:**
   ```python
   commands["depmapper"] = handle_depmapper
   ```

4. **Test integration:**
   ```
   @depmapper scan ./SynapseLink
   @depmapper circular ./AgentHealth
   ```

---

## 🤖 AI AGENT INTEGRATION

### Integration Matrix

| Agent | Primary Use Case | Integration Method | Priority |
|-------|-----------------|-------------------|----------|
| **Forge** | Code review, architecture assessment | Python API | HIGH |
| **Atlas** | Pre-build analysis, quality gates | CLI + Python API | HIGH |
| **Clio** | Linux tool analysis, CI/CD integration | CLI | MEDIUM |
| **Nexus** | Cross-platform verification | Python API | MEDIUM |
| **Bolt** | Bulk project scanning | CLI | LOW |
| **IRIS** | Desktop tool dependency mapping | Python API | LOW |
| **PORTER** | Mobile toolkit analysis | CLI | LOW |

### Agent-Specific Workflows

---

#### Forge (Orchestrator / Reviewer)

**Primary Use Case:** Architecture review during code review and tool assessment.

**Integration Steps:**
1. Forge scans the tool being reviewed with DepMapper
2. Checks for circular imports (automatic quality gate)
3. Reviews coupling metrics for architectural concerns
4. Includes dependency analysis in review notes

**Example Workflow:**
```python
# Forge reviewing a tool submission
from depmapper import DepMapper

dm = DepMapper()
result = dm.scan("./submitted_tool")

# Check quality gates
cycles = dm.find_circular()
if cycles:
    review_notes.append(f"BLOCKER: {len(cycles)} circular imports found")
    for cycle in cycles:
        review_notes.append(f"  Cycle: {' -> '.join(cycle)}")

# Check coupling health
metrics = dm.get_metrics(sort_by="instability")
unstable_utils = [m for m in metrics 
                  if m.instability > 0.8 and m.fan_in > 0]
if unstable_utils:
    review_notes.append("WARNING: Unstable utility modules detected")
    for m in unstable_utils:
        review_notes.append(f"  {m.module}: instability={m.instability}")

# Check for dead code
orphans = dm.find_orphans()
dead_code = [o for o in orphans 
             if len(result.edges.get(o, set())) == 0]
if dead_code:
    review_notes.append(f"INFO: {len(dead_code)} potential dead code modules")
```

---

#### Atlas (Executor / Builder)

**Primary Use Case:** Pre-build analysis and quality verification during tool creation.

**Integration Steps:**
1. Run DepMapper before starting new tool builds
2. Verify no circular imports after Phase 2 (development)
3. Include dependency report in Phase 8 (quality audit)
4. Generate dependency graph for documentation

**Example Workflow:**
```python
# Atlas tool build quality gate
from depmapper import DepMapper

dm = DepMapper()

# Phase 2: After writing code
dm.scan("./NewTool")
cycles = dm.find_circular()
assert len(cycles) == 0, f"Circular imports detected: {cycles}"

# Phase 8: Quality audit
report = dm.generate_report(format="markdown")
Path("DEPENDENCY_REPORT.md").write_text(report)

# Generate graph for docs
dot = dm.generate_dot()
Path("docs/dependencies.dot").write_text(dot)

print("[OK] Dependency analysis passed quality gate")
```

---

#### Clio (Linux / Ubuntu Agent)

**Primary Use Case:** CI/CD integration and Linux tool analysis.

**Platform Considerations:**
- All features work on Linux without modification
- Graphviz is easily installed: `sudo apt install graphviz`
- Can be added to CI pipelines

**Example:**
```bash
# Clio CI/CD integration
#!/bin/bash

# Pre-commit check
python3 depmapper.py circular ./src
if [ $? -eq 2 ]; then
    echo "BLOCKED: Fix circular imports before committing"
    exit 1
fi

# Generate dependency report
python3 depmapper.py report ./src --markdown -o docs/DEPENDENCIES.md

# Render dependency graph
python3 depmapper.py graph ./src -o deps.dot
dot -Tsvg deps.dot -o docs/dependencies.svg
```

---

#### Nexus (Multi-Platform Agent)

**Primary Use Case:** Cross-platform dependency verification.

**Cross-Platform Notes:**
- DepMapper uses `pathlib.Path` throughout — works on all platforms
- No platform-specific features or dependencies
- Same results regardless of OS

**Example:**
```python
# Nexus cross-platform verification
import platform
from depmapper import DepMapper

dm = DepMapper()
result = dm.scan("./cross_platform_tool")

print(f"Platform: {platform.system()}")
print(f"Modules: {len(result.modules)}")
print(f"Dependencies: {sum(len(t) for t in result.edges.values())}")

# Verify same results across platforms
report_json = dm.generate_report(format="json")
# Compare with report from other platform
```

---

#### Bolt (Free Executor)

**Primary Use Case:** Bulk project scanning without API costs.

**Cost Considerations:**
- DepMapper is 100% local — zero API costs
- Can analyze all 72+ Team Brain tools in one batch
- Perfect for repetitive quality checks

**Example:**
```bash
# Bolt batch scanning all tools
cd AutoProjects
for dir in */; do
    if [ -f "$dir/setup.py" ] || [ -f "$dir/*.py" ]; then
        echo "=== $dir ==="
        python3 DepMapper/depmapper.py circular "$dir" 2>/dev/null
    fi
done
```

---

## 🔗 INTEGRATION WITH OTHER TEAM BRAIN TOOLS

### With CodeMetrics

**Correlation Use Case:** Combine dependency coupling with code complexity for comprehensive health scoring.

**Integration Pattern:**
```python
from depmapper import DepMapper
# Assume CodeMetrics is importable
# from codemetrics import CodeMetrics

dm = DepMapper()
dm.scan("./project")
dep_metrics = dm.get_metrics(sort_by="name")

# Cross-reference: modules with high coupling AND high complexity
# are the highest-risk modules for refactoring
for m in dep_metrics:
    if m.fan_in > 5 and m.instability < 0.2:
        print(f"HIGH RISK: {m.module} - heavily depended on (fan_in={m.fan_in})")
        # Check CodeMetrics complexity for this file
```

### With SynapseLink

**Notification Use Case:** Alert team when circular imports are detected.

**Integration Pattern:**
```python
from synapselink import quick_send
from depmapper import DepMapper

dm = DepMapper()
dm.scan("./project")
cycles = dm.find_circular()

if cycles:
    cycle_text = "\n".join(f"  {' -> '.join(c)}" for c in cycles)
    quick_send(
        "FORGE,LOGAN",
        "[DepMapper] Circular Imports Detected!",
        f"Project: ./project\n"
        f"Cycles found: {len(cycles)}\n\n"
        f"{cycle_text}\n\n"
        f"Action required: Fix circular imports before merge.",
        priority="HIGH"
    )
```

### With AgentHealth

**Monitoring Use Case:** Track dependency health metrics over time.

**Integration Pattern:**
```python
from depmapper import DepMapper

dm = DepMapper()
dm.scan("./project")
metrics = dm.get_metrics()
cycles = dm.find_circular()

# Log to AgentHealth
health_data = {
    "tool": "DepMapper",
    "project": "./project",
    "total_modules": len(dm._result.modules),
    "total_deps": sum(len(t) for t in dm._result.edges.values()),
    "circular_imports": len(cycles),
    "avg_instability": sum(m.instability for m in metrics) / max(len(metrics), 1),
    "max_fan_in": max((m.fan_in for m in metrics), default=0),
}
# health.log_metric("dependency_health", health_data)
```

### With TaskQueuePro

**Task Management Use Case:** Queue dependency analysis as part of build tasks.

**Integration Pattern:**
```python
from depmapper import DepMapper

dm = DepMapper()

def analyze_dependencies(task_data: dict) -> dict:
    """Task handler for dependency analysis."""
    path = task_data.get("project_path", ".")
    result = dm.scan(path)
    cycles = dm.find_circular()
    metrics = dm.get_metrics()
    
    return {
        "status": "warning" if cycles else "clean",
        "files": result.total_files,
        "modules": len(result.modules),
        "cycles": len(cycles),
        "cycle_details": [" -> ".join(c) for c in cycles],
        "top_dependencies": [
            {"module": m.module, "fan_in": m.fan_in}
            for m in sorted(metrics, key=lambda x: -x.fan_in)[:5]
        ],
    }
```

### With MemoryBridge

**Context Persistence Use Case:** Save dependency scan results for trend analysis.

**Integration Pattern:**
```python
import json
from datetime import datetime
from depmapper import DepMapper

dm = DepMapper()
dm.scan("./project")
report = dm.generate_report(format="json")

# Save to memory for historical comparison
snapshot = {
    "timestamp": datetime.now().isoformat(),
    "project": "./project",
    "report": json.loads(report),
}
# memory.append("depmapper_history", snapshot)
# memory.sync()
```

### With SessionReplay

**Debugging Use Case:** Record dependency analysis during build sessions.

**Integration Pattern:**
```python
from depmapper import DepMapper

dm = DepMapper()

# Log analysis as session event
# replay.log_event("dependency_scan_start", {"path": "./project"})

result = dm.scan("./project")
cycles = dm.find_circular()

# replay.log_event("dependency_scan_complete", {
#     "files": result.total_files,
#     "cycles": len(cycles),
#     "time": result.scan_time,
# })
```

### With ContextCompressor

**Token Optimization Use Case:** Compress large dependency reports before sharing.

**Integration Pattern:**
```python
from depmapper import DepMapper

dm = DepMapper()
dm.scan("./large_project")
full_report = dm.generate_report(format="text")

# Compress before sharing via Synapse
# compressed = compressor.compress_text(
#     full_report,
#     query="circular imports and high coupling modules",
#     method="summary"
# )
# quick_send("TEAM", "Dep Analysis", compressed.compressed_text)
```

### With ConfigManager

**Configuration Use Case:** Store default DepMapper settings centrally.

**Integration Pattern:**
```python
from depmapper import DepMapper

# Load shared config
# config = ConfigManager()
# dm_config = config.get("depmapper", {
#     "default_excludes": ["tests", "docs", "__pycache__"],
#     "max_cycle_length": 20,
#     "instability_threshold": 0.8,
# })

dm = DepMapper()
# dm.scan("./project", exclude=dm_config["default_excludes"])
```

---

## 🚀 ADOPTION ROADMAP

### Phase 1: Core Adoption (Week 1)

**Goal:** All agents aware and can use basic features.

**Steps:**
1. [x] Tool deployed to GitHub
2. [ ] Quick-start guides sent via Synapse
3. [ ] Each agent tests: `depmapper scan` and `depmapper circular`
4. [ ] Feedback collected

**Success Criteria:**
- All 5+ agents have used tool at least once
- No blocking issues reported
- Basic commands work on all platforms

### Phase 2: Workflow Integration (Week 2-3)

**Goal:** Integrated into daily workflows.

**Steps:**
1. [ ] Add circular import check to Atlas build pipeline
2. [ ] Add dependency report to Forge review workflow
3. [ ] Create CI/CD integration for active projects
4. [ ] Monitor usage patterns

**Success Criteria:**
- Used in every tool build by Atlas
- Used in every code review by Forge
- CI/CD integration active for 3+ projects

### Phase 3: Deep Integration (Week 4+)

**Goal:** Full ecosystem integration.

**Steps:**
1. [ ] BCH command handler implemented
2. [ ] Integration with CodeMetrics for combined health scoring
3. [ ] Historical trend tracking via MemoryBridge
4. [ ] Automated alerts via SynapseLink

**Success Criteria:**
- BCH `@depmapper` commands working
- Historical data being collected
- Automated circular import alerts active

---

## 📊 SUCCESS METRICS

**Adoption Metrics:**
- Number of agents using tool: Target 5+
- Weekly usage count: Target 10+ scans/week
- Projects analyzed: Target all 72+ Team Brain tools

**Efficiency Metrics:**
- Time saved per circular import debug: 30+ minutes
- Time saved per architecture review: 1-2 hours
- Dead code modules discovered: Track cumulative

**Quality Metrics:**
- Circular imports caught before merge: Track count
- Coupling issues identified early: Track count
- Bug reports: Target 0 (tool is read-only and safe)

---

## 🛠️ TECHNICAL INTEGRATION DETAILS

### Import Paths

```python
# Standard import (when in same directory)
from depmapper import DepMapper

# Import from AutoProjects
import sys
from pathlib import Path
sys.path.append(str(Path.home() / "OneDrive/Documents/AutoProjects/DepMapper"))
from depmapper import DepMapper

# Import specific components
from depmapper import DepMapper, ScanResult, CouplingMetrics, ImportInfo
```

### Error Handling Integration

**Standardized Exit Codes:**
- 0: Success
- 1: General error (bad path, invalid options)
- 2: Circular imports found (circular command only)

### Logging Integration

DepMapper does not produce log files (it's a read-only analyzer). All output goes to stdout/stderr.

For logging integration, wrap DepMapper calls:
```python
import logging
logger = logging.getLogger("depmapper")

dm = DepMapper()
result = dm.scan("./project")
logger.info(f"Scanned {result.total_files} files in {result.scan_time:.3f}s")
```

---

## 🔧 MAINTENANCE & SUPPORT

### Update Strategy
- Minor updates (v1.x): As needed for bug fixes
- Major updates (v2.0+): Planned for multi-language support
- Security patches: Not applicable (read-only, no network, no file writes)

### Support Channels
- GitHub Issues: Bug reports and feature requests
- Synapse: Team Brain discussions
- Direct to ATLAS: Complex issues

### Known Limitations
- Only analyzes Python files (.py)
- Dynamic imports (`importlib.import_module()`) not detected
- Conditional imports inside if/try blocks are still counted
- Very large projects (1000+ files) may take 2-3 seconds

### Planned Improvements (v1.1)
- [ ] Multi-project comparison mode
- [ ] Dependency diff (before/after refactoring)
- [ ] Interactive TUI mode
- [ ] Auto-fix suggestions for circular imports

---

## 📚 ADDITIONAL RESOURCES

- Main Documentation: [README.md](README.md)
- Examples: [EXAMPLES.md](EXAMPLES.md)
- Quick Start Guides: [QUICK_START_GUIDES.md](QUICK_START_GUIDES.md)
- Integration Examples: [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md)
- Cheat Sheet: [CHEAT_SHEET.txt](CHEAT_SHEET.txt)
- GitHub: https://github.com/DonkRonk17/DepMapper

---

**Last Updated:** February 14, 2026  
**Maintained By:** ATLAS (Team Brain)
