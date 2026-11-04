"""Fluxo local main/develop. Alterações remotas exigem --apply explícito."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from github_api import api, repository
from version import bump, read_version, set_version

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def clean():
    if git('status', '--porcelain'): raise ValueError('Há alterações locais. Faça commit ou guarde-as antes de continuar.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    start = sub.add_parser('start'); start.add_argument('branch'); start.add_argument('--apply', action='store_true')
    release = sub.add_parser('prepare-release'); release.add_argument('--bump', choices=['patch', 'minor', 'major'], default='patch'); release.add_argument('--apply', action='store_true')
    sync = sub.add_parser('sync'); sync.add_argument('--apply', action='store_true')
    bootstrap = sub.add_parser('bootstrap'); bootstrap.add_argument('--apply', action='store_true'); bootstrap.add_argument('--protect', action='store_true')
    args = parser.parse_args()
    repo = repository()
    if args.command == 'bootstrap':
        main_ref = api(f'repos/{repo}/git/ref/heads/main')
        if not main_ref: raise ValueError('main não encontrada.')
        develop = api(f'repos/{repo}/git/ref/heads/develop')
        plan = {'create_develop': not bool(develop), 'protect': args.protect, 'apply': args.apply}
        print(json.dumps(plan, indent=2))
        if not args.apply: return
        if not develop: api(f'repos/{repo}/git/refs', 'POST', {'ref': 'refs/heads/develop', 'sha': main_ref['object']['sha']})
        if args.protect:
            for branch in ('main', 'develop'):
                existing = api(f'repos/{repo}/branches/{branch}/protection')
                if existing:
                    print(f'{branch}: proteção existente preservada; revise no GitHub.'); continue
                api(f'repos/{repo}/branches/{branch}/protection', 'PUT', {'required_status_checks': {'strict': True, 'contexts': ['Branch policy', 'Tests Python 3.10', 'Tests Python 3.12', 'Tests Python 3.13', 'Workflow lint', 'Portal browser', 'Build gate']}, 'enforce_admins': True, 'required_pull_request_reviews': {'dismiss_stale_reviews': True, 'require_code_owner_reviews': False, 'required_approving_review_count': 0}, 'restrictions': None, 'required_linear_history': False, 'allow_force_pushes': False, 'allow_deletions': False, 'required_conversation_resolution': True})
        return
    clean()
    if args.command == 'start':
        if not re.fullmatch(r'(feature|feat|fix|ci|chore|docs|test|build|hotfix)/[a-z0-9][a-z0-9._/-]*', args.branch): raise ValueError('Nome de branch inválido.')
        print(f'Criar {args.branch} a partir de origin/develop; apply={args.apply}')
        if args.apply:
            git('fetch', 'origin', 'develop'); git('switch', '-c', args.branch, 'origin/develop')
    elif args.command == 'sync':
        print(f'Integrar origin/main em develop, sem rebase/force; apply={args.apply}')
        if args.apply:
            git('fetch', 'origin'); git('switch', 'develop'); git('pull', '--ff-only', 'origin', 'develop'); git('merge', '--no-edit', 'origin/main'); git('push', 'origin', 'develop')
    else:
        if git('branch', '--show-current') != 'develop': raise ValueError('Prepare a release na branch develop.')
        git('fetch', 'origin', 'main', 'develop', '--tags')
        if git('rev-parse', 'HEAD') != git('rev-parse', 'origin/develop'): raise ValueError('Atualize develop antes de preparar a release.')
        main_version = git('show', 'origin/main:pyproject.toml')
        match = re.search(r'^version = "([^"]+)"$', main_version, re.M)
        if not match: raise ValueError('Versão de main não encontrada.')
        target = bump(match[1], args.bump)
        if read_version() not in (match[1], target): raise ValueError('A versão atual não corresponde ao incremento solicitado. Escolha o bump correto sem rebaixar VERSION.')
        print(json.dumps({'version': target, 'base': 'main', 'head': 'develop', 'apply': args.apply}))
        if not args.apply: return
        if read_version() != target:
            set_version(target)
            git('add', 'VERSION', 'pyproject.toml'); git('commit', '-m', f'chore(release): prepara {target}'); git('push', 'origin', 'develop')
        title = f'release({args.bump}): Escritura {target}'
        body = f'## Descrição\nPromove a revisão de develop como versão {target}.\n\n## Branch\ndevelop → main\n\n## Validação\nCI, Windows gráfico x86/x64 e Docker devem concluir antes do merge. A publicação estável acontece após a integração em main.'
        prs = api(f'repos/{repo}/pulls?state=open&base=main&head={repo.split("/")[0]}:develop')
        if prs: result = api(f'repos/{repo}/pulls/{prs[0]["number"]}', 'PATCH', {'title': title, 'body': body})
        else: result = api(f'repos/{repo}/pulls', 'POST', {'title': title, 'body': body, 'base': 'main', 'head': 'develop'})
        print(result['html_url'])


if __name__ == '__main__': main()
