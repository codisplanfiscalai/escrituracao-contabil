"""Entrada gráfica Windows e inicialização do mesmo portal no contêiner."""
from pathlib import Path
import os
import sys
if not getattr(sys,'frozen',False):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--archive-worker":
        from src.archive_worker import main as worker_main
        raise SystemExit(worker_main(sys.argv[2:]))
    from src import local_app
    if getattr(sys,'frozen',False):local_app.PROJECT_ROOT=Path(sys.executable).resolve().parent
    if os.name=='nt':
        from windows_app import main as desktop_main
        desktop_main(sys.argv[1:])
    else:
        from src.server.runtime import main as server_main
        server_main()
if __name__=='__main__':main()
