"""(f531) The testers' installer downloads the model files itself, each checked against its sha256: this writes installer/models.iss, a
[Code] include for installer/meravia.iss, from data/runtime/server.yaml (one download a model file: its public source, its name, its
checksum, which Inno Setup verifies before it keeps the file; then the copy into {app}\\models). The model files are never among the
game's own files (build_exe.bat ships runtime/, never models/): on Steam they are a depot of their own, and the installer fetches the
same files by the same checksums. build_installer.bat runs this before Inno Setup, so the include always says what server.yaml says.

    python tools/installer_files.py              # writes installer/models.iss
    python tools/installer_files.py --check      # exit 1 when installer/models.iss is not what server.yaml gives now"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from llm import runtime

OUT = ROOT / "installer" / "models.iss"


def models(cfg: dict | None = None) -> list[dict]:
    """The model files in the order server.yaml names them: {file, sha256, size, source}."""
    cfg = runtime.settings() if cfg is None else cfg
    out = []
    for key, m in (cfg.get("models") or {}).items():
        for k in ("file", "sha256", "source"):
            if not m.get(k):
                raise SystemExit(f"data/runtime/server.yaml models.{key}: needs {k}")
        out.append({"file": str(m["file"]), "sha256": str(m["sha256"]), "size": int(m.get("size") or 0), "source": str(m["source"])})
    return out


def pascal(cfg: dict | None = None) -> str:
    """The include's text: the downloads, the copy into {app}\\models, and whether the files are already there."""
    ms = models(cfg)
    gb = sum(m["size"] for m in ms) / 1e9
    lines = ["{ Written by tools/installer_files.py from data/runtime/server.yaml: do not edit, run the tool. }",
             f"{{ The model files, about {gb:.1f} GB, each checked against its sha256 before it is kept. }}", "",
             "procedure AddModelDownloads(Page: TDownloadWizardPage);", "begin"]
    for m in ms:
        lines.append(f"  Page.Add('{m['source']}', '{m['file']}', '{m['sha256']}');")
    lines += ["end;", "", "function ModelsPresent: Boolean;", "begin",
              "  Result := " + " and ".join(f"FileExists(ExpandConstant('{{app}}\\models\\{m['file']}'))" for m in ms) + ";",
              "end;", "", "procedure InstallModels;", "var", "  Dir: String;", "begin",
              "  Dir := ExpandConstant('{app}\\models');", "  ForceDirectories(Dir);"]
    for m in ms:
        lines.append(f"  if FileExists(ExpandConstant('{{tmp}}\\{m['file']}')) then")
        lines.append(f"    FileCopy(ExpandConstant('{{tmp}}\\{m['file']}'), Dir + '\\{m['file']}', False);")
    lines += ["end;", ""]
    return "\n".join(lines)


def write(path: Path | None = None, cfg: dict | None = None) -> Path:
    path = Path(path or OUT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pascal(cfg), encoding="utf-8", newline="\r\n")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="say whether installer/models.iss is what server.yaml gives now; write nothing")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    if a.check:
        have = Path(a.out).read_text(encoding="utf-8") if Path(a.out).exists() else ""
        if have.replace("\r\n", "\n") != pascal():
            print(f"{a.out} is not what data/runtime/server.yaml gives: run python tools/installer_files.py")
            return 1
        print(f"{a.out} matches data/runtime/server.yaml")
        return 0
    p = write(Path(a.out))
    print(f"wrote {p} ({len(models())} model files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
