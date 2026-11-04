"""Build and verify an onedir Windows distribution for the active interpreter."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arch", choices=("x86", "x64"), required=True)
    args = parser.parse_args()
    expected_bits = {"x86": 32, "x64": 64}[args.arch]
    if sys.platform != "win32" or struct.calcsize("P") * 8 != expected_bits:
        parser.error("Build on Windows with an interpreter of the requested architecture")
    version = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M).group(1)
    name = f"escrituracao-contabil-{version}-windows-{args.arch}"
    out = ROOT / "dist" / args.arch
    if out.exists():
        parser.error(f"Output already exists; remove only the previous build directory: {out}")
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--console",
        "--name", "EscrituracaoContabil", "--noupx", "--paths", str(ROOT),
        "--add-data", f"{ROOT / 'src' / 'web' / 'index.html'}:src/web",
        "--add-data", f"{ROOT / 'src' / 'web' / 'app.js'}:src/web",
        "--add-data", f"{ROOT / 'src' / 'web' / 'style.css'}:src/web",
        "--collect-submodules", "src",
        "--distpath", str(out), "--workpath", str(ROOT / "build" / args.arch),
        "--specpath", str(ROOT / "build" / args.arch), str(ROOT / "packaging" / "launcher.py"),
    ], cwd=ROOT, check=True)
    bundle = out / "EscrituracaoContabil"
    exe = bundle / "EscrituracaoContabil.exe"
    with exe.open("rb") as file:
        file.seek(0x3C)
        offset = struct.unpack("<I", file.read(4))[0]
        file.seek(offset)
        assert file.read(4) == b"PE\0\0"
        assert struct.unpack("<H", file.read(2))[0] == {"x86": 0x14C, "x64": 0x8664}[args.arch]
    subprocess.run([sys.executable, str(ROOT / "packaging" / "smoke_test.py"), "--executable", str(exe)], check=True)
    shutil.copy2(ROOT / "docs" / "distribuicao.md", bundle / "DISTRIBUICAO.md")
    files = []
    for file in sorted(bundle.rglob("*")):
        if file.is_file():
            files.append({"path": file.relative_to(bundle).as_posix(), "size": file.stat().st_size,
                          "sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
    source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    manifest = {"name": name, "version": version, "architecture": args.arch, "source_sha": source_sha,
                "python": platform.python_version(), "pyinstaller": importlib.metadata.version("pyinstaller"),
                "status": "prototype-not-homologated", "smoke_test": "passed", "files": files}
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    archive = Path(shutil.make_archive(str(artifacts / name), "zip", root_dir=out, base_dir=bundle.name))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (artifacts / f"{name}.sha256").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    shutil.copy2(bundle / "manifest.json", artifacts / f"{name}.manifest.json")
    print(f"Verified {args.arch} PE and HTTP smoke test; artifact: {archive.name}; sha256:{digest}")


if __name__ == "__main__":
    main()
