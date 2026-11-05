"""Verify the actual Docker context filter with harmless, temporary probe files."""

import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {
    "src/persistence.py",
    "src/work_domain.py",
    "src/server/app.py",
    "src/web/index.html",
    "src/web/workbench.js",
    "src/web/workbench_render.js",
    "src/web/workbench.css",
    "src/web/posting_math.js",
    "src/web/assets/icon.svg",
    "src/web/assets/icon-32.png",
    "src/portal/index.html",
    "src/portal/app.js",
    "src/portal/app.css",
    "src/portal/render.js",
    "src/portal/vendor/vue.js",
    "src/portal/public.html",
    "src/portal/workspace.css",
    "config/scenario.synthetic.json",
    "tests/test_work_application.py",
    "tests/server/test_accounting_http.py",
    "packaging/launcher.py",
    "packaging/smoke_test.py",
    "requirements-server.txt",
    "pyproject.toml",
    "VERSION",
}
FORBIDDEN = {
    ".git/config",
    "private/original.xml",
    "artifacts/container.tar.gz",
    "state/accounting.sqlite3",
    "src/web/unexpected.txt",
    "src/web/setup.token",
    "src/web/agent.token",
    "src/web/private-config.json",
    "src/web/assets/unexpected.txt",
    "src/portal/private.json",
    "src/portal/vendor/unapproved.js",
    "src/portal/unapproved.js",
    "src/portal/private.html",
    "src/portal/secret.token",
    "src/server/setup.token",
    "src/server/master.key",
    "src/server/.env",
    "config/production.json",
    "packaging/unexpected.py",
    "tests/server/original.xml",
}


def verify_context():
    image = "escritura-context-check:" + uuid.uuid4().hex
    container = None
    try:
        with tempfile.TemporaryDirectory(prefix="escritura-context-") as folder:
            context = Path(folder)
            (context / ".dockerignore").write_bytes(
                (ROOT / ".dockerignore").read_bytes()
            )
            for name in ALLOWED | FORBIDDEN:
                path = context / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("SYNTHETIC CONTEXT PROBE\n")
            (context / "Dockerfile").write_text("FROM scratch\nCOPY . /included/\n")
            subprocess.run(
                ["docker", "build", "--network=none", "--tag", image, str(context)],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            container = subprocess.check_output(
                ["docker", "create", image, "/no-execution"], text=True
            ).strip()
            exported = subprocess.check_output(["docker", "export", container])
            with tarfile.open(fileobj=io.BytesIO(exported)) as archive:
                names = {
                    m.name.removeprefix("included/")
                    for m in archive.getmembers()
                    if m.isfile()
                }
            missing = sorted(ALLOWED - names)
            leaked = sorted(FORBIDDEN & names)
            if missing or leaked:
                raise RuntimeError(
                    f"Contexto Docker inválido: obrigatórios ausentes={missing}; sondas proibidas incluídas={leaked}"
                )
            print(
                f"PASS: contexto Docker inclui {len(ALLOWED)} recursos aprovados e exclui {len(FORBIDDEN)} sondas privadas/não aprovadas; nenhum contêiner executado"
            )
    finally:
        if container:
            subprocess.run(
                ["docker", "rm", container],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        subprocess.run(
            ["docker", "image", "rm", image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


if __name__ == "__main__":
    verify_context()
