# 🗺️ DepMapper - Integration Examples

## 🎯 INTEGRATION PHILOSOPHY

DepMapper is designed to work seamlessly with other Team Brain tools. This document provides **copy-paste-ready code examples** for common integration patterns.

---

## 📚 TABLE OF CONTENTS

1. [Pattern 1: DepMapper + AgentHealth](#pattern-1-depmapper--agenthealth)
2. [Pattern 2: DepMapper + SynapseLink](#pattern-2-depmapper--synapselink)
3. [Pattern 3: DepMapper + TaskQueuePro](#pattern-3-depmapper--taskqueuepro)
4. [Pattern 4: DepMapper + MemoryBridge](#pattern-4-depmapper--memorybridge)
5. [Pattern 5: DepMapper + SessionReplay](#pattern-5-depmapper--sessionreplay)
6. [Pattern 6: DepMapper + ContextCompressor](#pattern-6-depmapper--contextcompressor)
7. [Pattern 7: DepMapper + ConfigManager](#pattern-7-depmapper--configmanager)
8. [Pattern 8: DepMapper + CodeMetrics](#pattern-8-depmapper--codemetrics)
9. [Pattern 9: Multi-Tool Workflow](#pattern-9-multi-tool-workflow)
10. [Pattern 10: Full Team Brain Stack](#pattern-10-full-team-brain-stack)

---

## Pattern 1: DepMapper + AgentHealth

**Use Case:** Track dependency health as an agent performance metric.

**Why:** Understanding how dependency complexity correlates with build success helps predict issues.

**Code:**

```python
from depmapper import DepMapper

# Initialize
dm = DepMapper()

# Scan project
result = dm.scan("./project")
cycles = dm.find_circular()
metrics = dm.get_metrics()

# Calculate health score
total_modules = len(result.modules)
cycle_count = len(cycles)
avg_instability = (sum(m.instability for m in metrics) / max(len(metrics), 1))

health_score = {
    "agent": "ATLAS",
    "tool": "DepMapper",
    "project": result.root_path,
    "metrics": {
        "total_modules": total_modules,
        "total_dependencies": sum(len(t) for t in result.edges.values()),
        "circular_imports": cycle_count,
        "avg_instability": round(avg_instability, 3),
        "parse_errors": result.parse_errors,
        "scan_time": round(result.scan_time, 3),
    },
    "health": "GREEN" if cycle_count == 0 else "RED",
}

# Log to AgentHealth
# health.log_metric("dependency_health", health_score)
print(f"Health: {health_score['health']}")
print(f"Modules: {total_modules}, Cycles: {cycle_count}")
```

**Result:** Dependency health tracked alongside other agent metrics.

---

## Pattern 2: DepMapper + SynapseLink

**Use Case:** Automatically notify Team Brain when dependency issues are found.

**Why:** Early detection of circular imports prevents runtime errors.

**Code:**

```python
from depmapper import DepMapper
# from synapselink import quick_send

dm = DepMapper()
dm.scan("./project")
cycles = dm.find_circular()
metrics = dm.get_metrics(sort_by="fan_in")

if cycles:
    # Alert team to circular imports
    cycle_details = "\n".join(
        f"  Cycle {i}: {' -> '.join(c)}"
        for i, c in enumerate(cycles, 1)
    )
    message = (
        f"Project: ./project\n"
        f"Circular imports found: {len(cycles)}\n\n"
        f"{cycle_details}\n\n"
        f"Action: Fix before merging!"
    )
    # quick_send("FORGE,LOGAN", "[DepMapper] Circular Import Alert", message, priority="HIGH")
    print(f"[ALERT] {message}")
else:
    # Optional: report healthy status
    top_modules = "\n".join(
        f"  {m.module}: fan_in={m.fan_in}"
        for m in metrics[:3]
    )
    message = (
        f"Project: ./project\n"
        f"Status: CLEAN - No circular imports\n"
        f"Top depended-on modules:\n{top_modules}"
    )
    # quick_send("TEAM", "[DepMapper] Dependency Check Passed", message, priority="LOW")
    print(f"[OK] {message}")
```

**Result:** Team stays informed of dependency health automatically.

---

## Pattern 3: DepMapper + TaskQueuePro

**Use Case:** Queue dependency analysis as part of automated build pipelines.

**Why:** Ensures every build includes dependency verification.

**Code:**

```python
from depmapper import DepMapper
import json

def dependency_check_task(task_data: dict) -> dict:
    """Task handler for dependency analysis in TaskQueuePro."""
    path = task_data.get("project_path", ".")
    thresholds = task_data.get("thresholds", {
        "max_cycles": 0,
        "max_instability": 0.9,
        "max_fan_in": 15,
    })
    
    dm = DepMapper()
    result = dm.scan(path)
    cycles = dm.find_circular()
    metrics = dm.get_metrics()
    
    # Check thresholds
    violations = []
    if len(cycles) > thresholds["max_cycles"]:
        violations.append(f"Circular imports: {len(cycles)} (max: {thresholds['max_cycles']})")
    
    for m in metrics:
        if m.instability > thresholds["max_instability"] and m.fan_in > 0:
            violations.append(f"{m.module}: instability={m.instability}")
        if m.fan_in > thresholds["max_fan_in"]:
            violations.append(f"{m.module}: fan_in={m.fan_in} (max: {thresholds['max_fan_in']})")
    
    return {
        "status": "FAILED" if violations else "PASSED",
        "files_scanned": result.total_files,
        "modules": len(result.modules),
        "cycles": len(cycles),
        "violations": violations,
        "scan_time": round(result.scan_time, 3),
    }

# Example usage
result = dependency_check_task({
    "project_path": "./my_project",
    "thresholds": {"max_cycles": 0, "max_instability": 0.9, "max_fan_in": 15}
})
print(json.dumps(result, indent=2))
```

**Result:** Dependency checks as automated, trackable tasks.

---

## Pattern 4: DepMapper + MemoryBridge

**Use Case:** Persist dependency scan results for historical trend analysis.

**Why:** Track how dependency health changes over time.

**Code:**

```python
import json
from datetime import datetime
from depmapper import DepMapper

dm = DepMapper()
result = dm.scan("./project")
cycles = dm.find_circular()
metrics = dm.get_metrics()

# Create snapshot for memory
snapshot = {
    "timestamp": datetime.now().isoformat(),
    "project": result.root_path,
    "total_files": result.total_files,
    "total_modules": len(result.modules),
    "total_deps": sum(len(t) for t in result.edges.values()),
    "circular_imports": len(cycles),
    "avg_instability": round(
        sum(m.instability for m in metrics) / max(len(metrics), 1), 3
    ),
    "max_fan_in": max((m.fan_in for m in metrics), default=0),
    "parse_errors": result.parse_errors,
}

# Save to memory
# history = memory.get("depmapper_history", [])
# history.append(snapshot)
# memory.set("depmapper_history", history)
# memory.sync()

print(f"Snapshot saved: {json.dumps(snapshot, indent=2)}")

# Trend analysis
# history = memory.get("depmapper_history", [])
# if len(history) > 1:
#     prev = history[-2]
#     curr = history[-1]
#     delta_deps = curr["total_deps"] - prev["total_deps"]
#     delta_cycles = curr["circular_imports"] - prev["circular_imports"]
#     print(f"Dependencies: {'+' if delta_deps >= 0 else ''}{delta_deps}")
#     print(f"Cycles: {'+' if delta_cycles >= 0 else ''}{delta_cycles}")
```

**Result:** Historical dependency data for trend analysis.

---

## Pattern 5: DepMapper + SessionReplay

**Use Case:** Record dependency analysis events during build sessions for debugging.

**Why:** When a build fails due to import issues, replay shows what DepMapper found.

**Code:**

```python
from depmapper import DepMapper

# Start recording
# session_id = replay.start_session("ATLAS", task="Tool build with dep check")

dm = DepMapper()

# Log scan start
# replay.log_event(session_id, "depmapper_scan_start", {"path": "./project"})

result = dm.scan("./project")

# Log scan result
# replay.log_event(session_id, "depmapper_scan_complete", {
#     "files": result.total_files,
#     "modules": len(result.modules),
#     "time": result.scan_time,
# })

cycles = dm.find_circular()

if cycles:
    # Log warning
    # replay.log_event(session_id, "depmapper_cycles_found", {
    #     "count": len(cycles),
    #     "cycles": [" -> ".join(c) for c in cycles],
    # })
    print(f"[!] Logged {len(cycles)} cycles to session replay")
else:
    # replay.log_event(session_id, "depmapper_clean", {})
    print("[OK] Clean dependency check logged to session")

# replay.end_session(session_id)
```

**Result:** Full dependency analysis history in session replay for debugging.

---

## Pattern 6: DepMapper + ContextCompressor

**Use Case:** Compress large dependency reports before sharing via Synapse.

**Why:** Full reports for large projects can be 1000+ tokens — compression saves API costs.

**Code:**

```python
from depmapper import DepMapper

dm = DepMapper()
dm.scan("./large_project")

# Generate full report
full_report = dm.generate_report(format="text")
report_size = len(full_report)

# Compress before sharing
# compressed = compressor.compress_text(
#     full_report,
#     query="circular imports and high-risk modules",
#     method="summary"
# )

# Share compressed version via Synapse
# quick_send("TEAM", "Dep Analysis Summary", compressed.compressed_text)

print(f"Full report: {report_size} chars")
# print(f"Compressed: {compressed.compressed_size} chars")
# print(f"Savings: {compressed.estimated_token_savings} tokens")

# Alternative: Use JSON format and extract key data
json_report = dm.generate_report(format="json")
import json
data = json.loads(json_report)

# Create minimal summary
summary = (
    f"Files: {data['summary']['total_files']}, "
    f"Deps: {data['summary']['total_dependencies']}, "
    f"Cycles: {data['summary']['circular_import_count']}, "
    f"Orphans: {data['summary']['orphan_count']}"
)
print(f"Compact summary: {summary}")
```

**Result:** Token-efficient dependency reports for team sharing.

---

## Pattern 7: DepMapper + ConfigManager

**Use Case:** Centralized DepMapper configuration shared across agents.

**Why:** Consistent analysis settings for all agents.

**Code:**

```python
from depmapper import DepMapper

# Load shared config
# config = ConfigManager()
# dm_settings = config.get("depmapper", default_settings)

default_settings = {
    "exclude_dirs": ["tests", "docs", "__pycache__", "venv", "build"],
    "max_cycle_length": 20,
    "instability_warning_threshold": 0.8,
    "fan_in_warning_threshold": 10,
    "report_format": "text",
}

dm = DepMapper()
result = dm.scan("./project", exclude=default_settings["exclude_dirs"])

# Apply configured thresholds
cycles = dm.find_circular(max_cycle_length=default_settings["max_cycle_length"])
metrics = dm.get_metrics()

warnings = []
for m in metrics:
    if m.instability > default_settings["instability_warning_threshold"] and m.fan_in > 0:
        warnings.append(f"High instability: {m.module} ({m.instability:.3f})")
    if m.fan_in > default_settings["fan_in_warning_threshold"]:
        warnings.append(f"High fan-in: {m.module} (fan_in={m.fan_in})")

if warnings:
    print("Configuration warnings:")
    for w in warnings:
        print(f"  [!] {w}")
else:
    print("[OK] All modules within configured thresholds")
```

**Result:** Consistent, configurable dependency analysis across the team.

---

## Pattern 8: DepMapper + CodeMetrics

**Use Case:** Combined dependency + code quality analysis for comprehensive health scoring.

**Why:** A module that's both heavily depended-on (high fan-in) AND highly complex is the highest risk module in your codebase.

**Code:**

```python
from depmapper import DepMapper
import json

dm = DepMapper()
result = dm.scan("./project")
dep_metrics = dm.get_metrics(sort_by="name")

# Simulate CodeMetrics data (replace with actual CodeMetrics integration)
# from codemetrics import CodeMetrics
# cm = CodeMetrics()
# cm_result = cm.analyze("./project")

# Combined risk scoring
risk_scores = []
for m in dep_metrics:
    # Dependency risk factors
    dep_risk = 0
    if m.fan_in > 5:
        dep_risk += 2  # Heavily depended on
    if m.instability < 0.2 and m.fan_in > 3:
        dep_risk += 1  # Stable core - changes are risky
    
    # Code complexity risk (from CodeMetrics)
    # code_risk = cm_result.get_complexity(m.module)
    code_risk = 0  # Placeholder
    
    total_risk = dep_risk + code_risk
    risk_scores.append({
        "module": m.module,
        "fan_in": m.fan_in,
        "fan_out": m.fan_out,
        "instability": m.instability,
        "dep_risk": dep_risk,
        "code_risk": code_risk,
        "total_risk": total_risk,
    })

# Sort by total risk
risk_scores.sort(key=lambda x: -x["total_risk"])

print("COMBINED RISK ANALYSIS")
print("-" * 60)
print(f"{'Module':<30} {'Fan-In':>7} {'Instab':>7} {'Risk':>5}")
print("-" * 60)
for r in risk_scores[:10]:
    marker = " [!]" if r["total_risk"] >= 3 else ""
    print(f"{r['module']:<30} {r['fan_in']:>7} {r['instability']:>7.3f} {r['total_risk']:>5}{marker}")
```

**Result:** Combined dependency + complexity risk scoring for prioritized refactoring.

---

## Pattern 9: Multi-Tool Workflow

**Use Case:** Complete build verification workflow using multiple Team Brain tools.

**Why:** Demonstrates real production scenario with coordinated tool usage.

**Code:**

```python
from depmapper import DepMapper
import json
from pathlib import Path
from datetime import datetime

def build_verification_workflow(project_path: str, agent: str = "ATLAS") -> dict:
    """Complete build verification using multiple tools.
    
    Steps:
    1. Scan dependencies with DepMapper
    2. Check for circular imports
    3. Analyze coupling metrics
    4. Generate report
    5. Notify team if issues found
    """
    results = {"agent": agent, "project": project_path, "timestamp": datetime.now().isoformat()}
    
    # Step 1: Scan
    dm = DepMapper()
    scan_result = dm.scan(project_path)
    results["scan"] = {
        "files": scan_result.total_files,
        "modules": len(scan_result.modules),
        "deps": sum(len(t) for t in scan_result.edges.values()),
        "parse_errors": scan_result.parse_errors,
        "time": round(scan_result.scan_time, 3),
    }
    
    # Step 2: Circular imports
    cycles = dm.find_circular()
    results["circular"] = {
        "count": len(cycles),
        "cycles": [" -> ".join(c) for c in cycles],
    }
    
    # Step 3: Coupling metrics
    metrics = dm.get_metrics(sort_by="fan_in")
    results["coupling"] = {
        "total_modules": len(metrics),
        "avg_instability": round(
            sum(m.instability for m in metrics) / max(len(metrics), 1), 3
        ),
        "max_fan_in": max((m.fan_in for m in metrics), default=0),
        "high_risk": [m.module for m in metrics if m.fan_in > 8],
    }
    
    # Step 4: Orphans
    orphans = dm.find_orphans()
    dead_code = [o for o in orphans if len(scan_result.edges.get(o, set())) == 0]
    results["orphans"] = {
        "total": len(orphans),
        "potential_dead_code": dead_code,
    }
    
    # Step 5: Overall status
    issues = []
    if cycles:
        issues.append(f"{len(cycles)} circular imports")
    if dead_code:
        issues.append(f"{len(dead_code)} potential dead code modules")
    
    results["status"] = "FAILED" if cycles else "PASSED"
    results["issues"] = issues
    
    # Step 6: Generate report
    report = dm.generate_report(format="markdown")
    report_path = Path(project_path) / "DEPENDENCY_REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    results["report_path"] = str(report_path)
    
    # Step 7: Notify team if issues
    if issues:
        print(f"[!] Build verification issues: {', '.join(issues)}")
        # quick_send("FORGE", f"Build issues in {project_path}", "\n".join(issues))
    else:
        print(f"[OK] Build verification passed for {project_path}")
    
    return results

# Run the workflow
result = build_verification_workflow("./my_project", agent="ATLAS")
print(json.dumps(result, indent=2))
```

**Result:** Fully automated, multi-step build verification with team notification.

---

## Pattern 10: Full Team Brain Stack

**Use Case:** Ultimate integration — all tools working together for comprehensive project analysis.

**Why:** Production-grade agent operation with full observability.

**Code:**

```python
"""
Full Team Brain Stack Integration Example

This demonstrates the ideal workflow where all tools work together:
1. TaskQueuePro creates and tracks the analysis task
2. SessionReplay records the entire process
3. AgentHealth monitors agent performance
4. DepMapper performs the analysis
5. CodeMetrics provides code quality data
6. MemoryBridge persists results
7. ContextCompressor optimizes the output
8. SynapseLink notifies the team
9. ConfigManager provides consistent settings
"""

from depmapper import DepMapper
import json
from datetime import datetime

def full_stack_analysis(project_path: str) -> dict:
    """Complete analysis using the full Team Brain stack."""
    
    # 1. Create task (TaskQueuePro)
    # task_id = queue.create_task("Dependency analysis", agent="ATLAS")
    
    # 2. Start recording (SessionReplay)
    # session_id = replay.start_session("ATLAS", task="Full stack analysis")
    
    # 3. Start health monitoring (AgentHealth)
    # health.start_session("ATLAS", session_id=session_id)
    
    # 4. Load config (ConfigManager)
    # config = config_manager.get("depmapper", {...})
    
    # 5. Run DepMapper analysis
    dm = DepMapper()
    result = dm.scan(project_path)
    cycles = dm.find_circular()
    metrics = dm.get_metrics()
    orphans = dm.find_orphans()
    
    # 6. Run CodeMetrics analysis
    # cm = CodeMetrics()
    # code_health = cm.analyze(project_path)
    
    # 7. Combine results
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "project": project_path,
        "dependency_health": {
            "modules": len(result.modules),
            "dependencies": sum(len(t) for t in result.edges.values()),
            "circular_imports": len(cycles),
            "orphans": len(orphans),
            "avg_instability": round(
                sum(m.instability for m in metrics) / max(len(metrics), 1), 3
            ),
        },
        # "code_health": code_health.summary(),
        "status": "CLEAN" if not cycles else "ISSUES_FOUND",
    }
    
    # 8. Persist to memory (MemoryBridge)
    # memory.append("project_analyses", analysis)
    # memory.sync()
    
    # 9. Compress report for sharing (ContextCompressor)
    report = dm.generate_report(format="text")
    # compressed = compressor.compress(report, query="key findings")
    
    # 10. Notify team (SynapseLink)
    status = analysis["status"]
    # quick_send("TEAM", f"Analysis: {project_path} [{status}]", compressed.text)
    
    # 11. Complete task (TaskQueuePro)
    # queue.complete_task(task_id, result=analysis)
    
    # 12. End session (SessionReplay + AgentHealth)
    # replay.end_session(session_id, status="COMPLETED")
    # health.end_session("ATLAS", session_id=session_id)
    
    print(f"[OK] Full stack analysis complete: {status}")
    return analysis

# Execute
result = full_stack_analysis("./my_project")
print(json.dumps(result, indent=2))
```

**Result:** Production-grade analysis workflow with full Team Brain integration.

---

## 📊 RECOMMENDED INTEGRATION PRIORITY

**Week 1 (Essential):**
1. SynapseLink — Alert team to circular imports
2. AgentHealth — Track dependency health metrics
3. CodeMetrics — Combined health scoring

**Week 2 (Productivity):**
4. TaskQueuePro — Automated analysis tasks
5. MemoryBridge — Historical trend tracking
6. ConfigManager — Consistent settings

**Week 3 (Advanced):**
7. SessionReplay — Build session debugging
8. ContextCompressor — Token-efficient reports
9. Full stack integration

---

## 🔧 TROUBLESHOOTING INTEGRATIONS

**Import Errors:**
```python
# Ensure DepMapper is in Python path
import sys
from pathlib import Path
sys.path.append(str(Path.home() / "OneDrive/Documents/AutoProjects/DepMapper"))
from depmapper import DepMapper
```

**Version Conflicts:**
```bash
# Check version
python depmapper.py --version

# Update from GitHub
cd AutoProjects/DepMapper
git pull origin main
```

**Configuration Issues:**
```python
# Test with defaults first
dm = DepMapper()
result = dm.scan("./project")  # No custom config
# If this works, the issue is in your config
```

**Performance Issues:**
```python
# For large projects, use exclusions
dm = DepMapper()
result = dm.scan("./large_project", exclude=[
    "tests", "docs", "migrations", "vendor",
    "node_modules", "venv", "build"
])
```

---

**Last Updated:** February 14, 2026  
**Maintained By:** ATLAS (Team Brain)
