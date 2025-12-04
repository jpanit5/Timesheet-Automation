
import subprocess, csv, time, os, sys, ast, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path.cwd()
SRC = next((p for p in ROOT.glob("**/src") if p.is_dir()), ROOT)
REPORTS = ROOT / "server/reports"
REPORTS.mkdir(parents=True, exist_ok=True)
REPO_URL = os.environ.get("REPO_URL")
failed = False

if REPO_URL and not SRC.exists():
    subprocess.run(["git", "clone", REPO_URL, str(ROOT / "repo")], check=True)
    SRC = ROOT / "repo"

def run_command(name, cmd):
    start = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = round(time.time() - start, 2)
    status = "PASS" if proc.returncode == 0 else "FAIL"
    details = (proc.stdout + "\n" + proc.stderr).strip()
    return [name, status, elapsed, details], status, proc


checks = [
    ("Type Check", ["mypy", str(SRC)]),
    ("Lint Check", ["flake8", str(SRC)]),
    ("Import Style Check", ["isort", "--check-only", str(SRC)]),
    ("Formatting Check", ["black", "--check", str(SRC)])
]

results = []
for name, cmd in checks:
    row, status, _ = run_command(name, cmd)
    results.append(row)
    if status == "FAIL":
        failed = True

# Save coding checks report
with (REPORTS / "server_checks.csv").open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Check", "Result", "Time(s)", "Details"])
    writer.writerows(results)

# Markdown (partial)
with (REPORTS / "server_pipeline_summary.md").open("w") as f:
    f.write("# Server Pipeline Summary\n\n")
    f.write("## Coding Checks\n")
    for row in results:
        f.write(f"- {row[0]}: {row[1]} ({row[2]}s)\n")

# Gate to next pipeline
if failed:
    print("First pipeline failed — checking stop.")
    sys.exit(1)

doc_rows = []
doc_row, doc_status, doc_proc = run_command("Docstring Style (pydocstyle)", ["pydocstyle", str(SRC)])
doc_rows.append(doc_row)
if doc_status == "FAIL":
    failed = True


violations = []
for py in SRC.rglob("*.py"):
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                doc = ast.get_docstring(node) or ""
                name = getattr(node, 'name', '<module>')
                short_ok = bool(doc.strip()) and len(doc.strip().splitlines()) <= 2
                has_params = "Args:" in doc or "Parameters:" in doc
                has_returns = "Returns:" in doc or "Return:" in doc
                type_ok = True
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for arg in node.args.args:
                        if arg.arg != "self" and arg.annotation is None:
                            type_ok = False
                    if node.name != "__init__" and node.returns is None:
                        type_ok = False

                issues = []
                if not short_ok:
                    issues.append("Short description missing or too long.")
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not has_params:
                    issues.append("Missing Args section.")
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not has_returns:
                    issues.append("Missing Returns section.")
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not type_ok:
                    issues.append("Missing type hints.")

                for issue in issues:
                    violations.append([str(py), name, issue])
    except Exception as e:
        violations.append([str(py), "<parse>", f"Parse error: {e}"])

if violations:
    failed = True

with (REPORTS / "server_docstring_typesafe.csv").open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["File", "Symbol", "Violation"])
    
    if doc_proc.stdout.strip():
        for line in doc_proc.stdout.strip().splitlines():
            writer.writerow(["pydocstyle", "-", line])
    if doc_proc.stderr.strip():
        for line in doc_proc.stderr.strip().splitlines():
            writer.writerow(["pydocstyle", "-", line])
    writer.writerows(violations)

# Dependency tree
dep_tree_path = REPORTS / "dependency_tree.txt"
try:
    _row, _status, dep_proc = run_command("Dependency Tree (pipdeptree)", ["pipdeptree", "--freeze"])
    dep_tree_path.write_text(dep_proc.stdout or dep_proc.stderr)
except FileNotFoundError:
    # Fallback
    _row, _status, dep_proc = run_command("Dependency Tree (pip freeze)", ["pip", "freeze"])
    dep_tree_path.write_text(dep_proc.stdout or dep_proc.stderr)

# Check for redundant packages
freeze = subprocess.run(["pip", "freeze"], capture_output=True, text=True)
pkgs = {line.split("==")[0].lower() for line in freeze.stdout.splitlines() if "==" in line}
redundancies = []
http_clients = {"requests", "httpx", "urllib3"}
rest_frameworks = {"flask", "flask-restful", "fastapi"}

if len(http_clients.intersection(pkgs)) > 1:
    redundancies.append(["HTTP Clients", "-", f"Multiple detected: {sorted(http_clients.intersection(pkgs))}"])
if len(rest_frameworks.intersection(pkgs)) > 1:
    redundancies.append(["REST Frameworks", "-", f"Multiple detected: {sorted(rest_frameworks.intersection(pkgs))}"])

with (REPORTS / "server_dependencies_bloat.csv").open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Area", "Item", "Issue"])
    writer.writerows(redundancies)

if redundancies:
    failed = True

# Update markdown
with (REPORTS / "server_pipeline_summary.md").open("a") as f:
    f.write("\n## Docstrings & TypeSafe\n")
    f.write(f"- pydocstyle: {doc_status}\n")
    f.write(f"- AST violations: {len(violations)}\n")
    f.write("\n## Dependencies\n")
    f.write(f"- Redundancy flags: {len(redundancies)}\n")
    f.write(f"- Tree: written to {dep_tree_path.name}\n")

# Gate to next pipeline
if failed:
    print("Second pipeline failed — checking stop.")
    sys.exit(1)


junit_xml = REPORTS / "junit.xml"
row, status, proc = run_command(
    "Pytest (with coverage + JUnit)",
    ["coverage", "run", "-m", "pytest", "--maxfail=1", "--disable-warnings", f"--junitxml={junit_xml}"]
)
# Raw output log
(REPORTS / "server_pytest_output.log").write_text(proc.stdout + "\n" + proc.stderr)

if status == "FAIL":
    failed = True

# Coverage threshold
row_cov, status_cov, proc_cov = run_command("Coverage Report", ["coverage", "report", "--fail-under=85"])
(REPORTS / "coverage_report.log").write_text(proc_cov.stdout + "\n" + proc_cov.stderr)
if status_cov == "FAIL":
    failed = True

test_csv = REPORTS / "server_test_log.csv"
violations_3s = 0

with test_csv.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["File/Class", "TestName", "ParamsInName", "Result", "Elapsed(s)"])

    try:
        tree = ET.parse(junit_xml)
        root = tree.getroot()
        
        for tc in root.iter("testcase"):
            classname = tc.attrib.get("classname", "")
            name = tc.attrib.get("name", "")
            time_s = float(tc.attrib.get("time", "0") or 0)
            
            params_hint = ""
            if "[" in name and "]" in name:
                params_hint = name[name.find("[")+1:name.rfind("]")]

            result = "PASS"
            if list(tc.findall("failure")) or list(tc.findall("error")):
                result = "FAIL"
            elif list(tc.findall("skipped")):
                result = "SKIP"

            
            if time_s > 3.0 and result != "SKIP":
                result = "FAIL"
                violations_3s += 1

            writer.writerow([classname, name, params_hint, result, round(time_s, 3)])
    except Exception as e:
        
        failed = True
        writer.writerow(["<parse_error>", "<parse_error>", "", "FAIL", 0.0])
        (REPORTS / "junit_parse_error.log").write_text(str(e))

if violations_3s > 0:
    failed = True


with (REPORTS / "server_pipeline_summary.md").open("a") as f:
    f.write("\n## Tests\n")
    f.write(f"- Coverage: {'PASS' if status_cov == 'PASS' else 'FAIL'}\n")
    f.write(f"- Per-test <3s violations: {violations_3s}\n")
    f.write(f"- JUnit: {junit_xml.name}\n")
    f.write(f"- Raw: server_pytest_output.log\n")

print(f"Combined pipeline completed. Reports in {REPORTS}")
sys.exit(1 if failed else 0)
