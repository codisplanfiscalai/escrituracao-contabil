"""Smoke do servidor real, sem rede e com dados sintéticos descartáveis."""
import subprocess


def smoke(image):
    subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--read-only',
                    '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                    '--tmpfs', '/tmp:rw,nosuid,nodev,mode=1777',
                    '--tmpfs', '/data:rw,nosuid,nodev,uid=10001,gid=10001,mode=0700',
                    '--entrypoint', 'python', image, 'packaging/smoke_test.py', '--server'], check=True)


def published_smoke(image, expected_id):
    # Executa o digest que veio do registro, antes de promover aliases ou release.
    subprocess.run(['docker', 'pull', image], check=True)
    actual = subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', image], text=True).strip()
    if actual != expected_id:
        raise ValueError('Imagem remota difere da imagem testada antes da publicação.')
    smoke(image)
