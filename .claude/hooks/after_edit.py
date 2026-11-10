"""PostToolUse: after Claude edits a file, catch the cheap mistakes at once (fed back to Claude on exit 2)."""
import json, subprocess, sys
ev = json.load(sys.stdin)
path = (ev.get("tool_input") or {}).get("file_path", "")
problems = []
if path.endswith(".py"):
    r = subprocess.run([sys.executable, "-m", "py_compile", path], capture_output=True, text=True)
    if r.returncode:
        problems.append(r.stderr.strip())
elif path.endswith((".yaml", ".yml")) and "/data/" in path.replace("\\", "/"):
    r = subprocess.run([sys.executable, "-c", "import engine.data_check as d; p=d.check(); print('\\n'.join(map(str,p))); raise SystemExit(1 if p else 0)"],
                       capture_output=True, text=True)
    if r.returncode:
        problems.append("data_check: " + (r.stdout or r.stderr).strip()[-2000:])
if problems:
    print("\n".join(problems), file=sys.stderr)
    sys.exit(2)
