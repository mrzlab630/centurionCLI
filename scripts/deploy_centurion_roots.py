#!/usr/bin/env python3
"""Descriptor-anchored CENTURION skill-surface deployment."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import secrets
import shutil
import stat
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW
RENAME_NOREPLACE = 1
LIBC = ctypes.CDLL(None, use_errno=True)
RENAMEAT2 = LIBC.renameat2
RENAMEAT2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
RENAMEAT2.restype = ctypes.c_int


@dataclass
class Stage:
    parent: Path
    name: str
    parent_fd: int
    live_fd: int
    staging_fd: int
    staging_name: str
    backup_name: str
    before: dict[str, dict[str, object]]
    expected: dict[str, dict[str, object]]
    incoming_count: int
    protected_count: int


def write_file_at(root_fd: int, relative: str, content: bytes, mode: int) -> None:
    parts = relative.split('/')
    current_fd = os.dup(root_fd)
    try:
        for component in parts[:-1]:
            try:
                os.mkdir(component, mode=0o700, dir_fd=current_fd)
            except FileExistsError:
                info = os.stat(component, dir_fd=current_fd, follow_symlinks=False)
                if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
                    raise RuntimeError(f"generated file parent is not a real directory: {relative}")
            next_fd = os.open(component, DIR_FLAGS, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, mode, dir_fd=current_fd)
        try:
            os.write(fd, content)
            os.fchmod(fd, mode)
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        os.close(current_fd)


def rename_noreplace(parent_fd: int, source: str, destination: str) -> None:
    if RENAMEAT2(parent_fd, os.fsencode(source), parent_fd, os.fsencode(destination), RENAME_NOREPLACE) == 0:
        return
    error = ctypes.get_errno()
    raise OSError(error, os.strerror(error), destination)


def digest_fd(fd: int) -> str:
    h = hashlib.sha256()
    while chunk := os.read(fd, 1024 * 1024):
        h.update(chunk)
    return h.hexdigest()


def tree_manifest(root_fd: int) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for current, dirs, files, current_fd in os.fwalk('.', topdown=True, follow_symlinks=False, dir_fd=root_fd):
        for name in list(dirs):
            info = os.stat(name, dir_fd=current_fd, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                relative = os.path.normpath(os.path.join(current, name)).removeprefix('./')
                records[relative] = {"symlink": os.readlink(name, dir_fd=current_fd)}
                dirs.remove(name)
            elif not stat.S_ISDIR(info.st_mode):
                raise RuntimeError(f"non-directory is not allowed: {current}/{name}")
        for name in files:
            relative = os.path.normpath(os.path.join(current, name)).removeprefix('./')
            info = os.stat(name, dir_fd=current_fd, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                records[relative] = {"symlink": os.readlink(name, dir_fd=current_fd)}
                continue
            if not stat.S_ISREG(info.st_mode):
                raise RuntimeError(f"non-regular file is not allowed: {relative}")
            file_fd = os.open(name, FILE_FLAGS, dir_fd=current_fd)
            try:
                records[relative] = {"sha256": digest_fd(file_fd), "mode": stat.S_IMODE(info.st_mode)}
            finally:
                os.close(file_fd)
    return records


def copy_tree(source: str, destination_fd: int, source_fd: int | None = None) -> None:
    inherited = (destination_fd,) if source_fd is None else (source_fd, destination_fd)
    result = subprocess.run(
        ['cp', '-a', '--no-dereference', f'{source}/.', f'/proc/self/fd/{destination_fd}/'],
        pass_fds=inherited, text=True, capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"copy failed from {source}: {result.stderr.strip() or result.stdout.strip()}")


def open_destination_prefix(root_fd: int, prefix: str) -> int:
    current_fd = os.dup(root_fd)
    try:
        for component in [part for part in prefix.split('/') if part]:
            try:
                os.mkdir(component, mode=0o700, dir_fd=current_fd)
            except FileExistsError:
                info = os.stat(component, dir_fd=current_fd, follow_symlinks=False)
                if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
                    raise RuntimeError(f"overlay prefix is not a real directory: {prefix}")
            next_fd = os.open(component, DIR_FLAGS, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def overlay_tree(source: Path, destination_fd: int, destination_prefix: str = '') -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}

    def recurse(source_dir: Path, destination_dir_fd: int, prefix: str) -> None:
        for entry in os.scandir(source_dir):
            if entry.name in {'node_modules', '__pycache__'} or entry.name.endswith('.pyc'):
                continue
            relative = f'{prefix}/{entry.name}'.removeprefix('/')
            info = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                raise RuntimeError(f"repo overlay must not contain symlinks: {entry.path}")
            if stat.S_ISDIR(info.st_mode):
                try:
                    os.mkdir(entry.name, mode=stat.S_IMODE(info.st_mode), dir_fd=destination_dir_fd)
                except FileExistsError:
                    existing = os.stat(entry.name, dir_fd=destination_dir_fd, follow_symlinks=False)
                    if not stat.S_ISDIR(existing.st_mode) or stat.S_ISLNK(existing.st_mode):
                        raise RuntimeError(f"repo overlay parent is not a real directory: {relative}")
                child_fd = os.open(entry.name, DIR_FLAGS, dir_fd=destination_dir_fd)
                try:
                    recurse(Path(entry.path), child_fd, relative)
                finally:
                    os.close(child_fd)
                continue
            if not stat.S_ISREG(info.st_mode):
                raise RuntimeError(f"repo overlay contains non-regular file: {entry.path}")
            source_fd = os.open(entry.path, FILE_FLAGS)
            try:
                target_fd = os.open(entry.name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
                                    stat.S_IMODE(info.st_mode), dir_fd=destination_dir_fd)
                try:
                    while chunk := os.read(source_fd, 1024 * 1024):
                        os.write(target_fd, chunk)
                    os.fchmod(target_fd, stat.S_IMODE(info.st_mode))
                    os.fsync(target_fd)
                finally:
                    os.close(target_fd)
            finally:
                os.close(source_fd)
            records[relative] = {"sha256": hashlib.sha256(Path(entry.path).read_bytes()).hexdigest(),
                                 "mode": stat.S_IMODE(info.st_mode)}

    prefix_fd = open_destination_prefix(destination_fd, destination_prefix)
    try:
        recurse(source, prefix_fd, destination_prefix)
        return records
    finally:
        os.close(prefix_fd)


def open_surface(parent: Path, name: str) -> tuple[int, int]:
    parent_fd = os.open(parent, DIR_FLAGS)
    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        os.close(parent_fd)
        raise RuntimeError(f"deployment surface must be a real directory: {parent / name}")
    return parent_fd, os.open(name, DIR_FLAGS, dir_fd=parent_fd)


def assert_binding(stage: Stage) -> None:
    current_fd = os.open(stage.name, DIR_FLAGS, dir_fd=stage.parent_fd)
    try:
        current = os.fstat(current_fd)
        held = os.fstat(stage.live_fd)
        if (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino):
            raise RuntimeError(f"deployment surface changed during staging: {stage.parent / stage.name}")
    finally:
        os.close(current_fd)


def stage_surface(parent: Path, name: str, overlays: list[tuple[Path, str]], stamp: str,
                  generated: dict[str, tuple[bytes, int]] | None = None) -> Stage:
    parent_fd, live_fd = open_surface(parent, name)
    staging_name = f'.{name}.centurion-stage-{stamp}-{secrets.token_hex(4)}'
    backup_name = f'.{name}.centurion-backup-{stamp}'
    os.mkdir(staging_name, mode=0o700, dir_fd=parent_fd)
    staging_fd = os.open(staging_name, DIR_FLAGS, dir_fd=parent_fd)
    try:
        before = tree_manifest(live_fd)
        copy_tree(f'/proc/self/fd/{live_fd}', staging_fd, live_fd)
        incoming: dict[str, dict[str, object]] = {}
        for overlay, prefix in overlays:
            incoming.update(overlay_tree(overlay, staging_fd, prefix))
        for relative, (content, mode) in (generated or {}).items():
            write_file_at(staging_fd, relative, content, mode)
            incoming[relative] = {"sha256": hashlib.sha256(content).hexdigest(), "mode": mode}
        staged = tree_manifest(staging_fd)
        for relative, expected in incoming.items():
            if staged.get(relative) != expected:
                raise RuntimeError(f"staged repo-wins verification failed: {parent / name / relative}")
        for relative, expected in before.items():
            if relative not in incoming and staged.get(relative) != expected:
                raise RuntimeError(f"staged local-only preservation failed: {parent / name / relative}")
        return Stage(parent, name, parent_fd, live_fd, staging_fd, staging_name, backup_name,
                     before, staged, len(incoming), sum(item not in incoming for item in before))
    except Exception:
        os.close(staging_fd)
        os.close(live_fd)
        shutil.rmtree(staging_name, dir_fd=parent_fd, ignore_errors=True)
        os.close(parent_fd)
        raise


def publish(stages: list[Stage]) -> None:
    published: list[Stage] = []
    try:
        for stage in stages:
            assert_binding(stage)
            rename_noreplace(stage.parent_fd, stage.name, stage.backup_name)
            os.fsync(stage.parent_fd)
            try:
                rename_noreplace(stage.parent_fd, stage.staging_name, stage.name)
                os.fsync(stage.parent_fd)
            except Exception:
                os.rename(stage.backup_name, stage.name, src_dir_fd=stage.parent_fd, dst_dir_fd=stage.parent_fd)
                os.fsync(stage.parent_fd)
                raise
            published.append(stage)
        for stage in stages:
            current_fd = os.open(stage.name, DIR_FLAGS, dir_fd=stage.parent_fd)
            try:
                if tree_manifest(current_fd) != stage.expected:
                    raise RuntimeError(f"published tree verification failed: {stage.parent / stage.name}")
            finally:
                os.close(current_fd)
    except Exception:
        for stage in reversed(published):
            failed = f'.{stage.name}.centurion-failed-{secrets.token_hex(4)}'
            rename_noreplace(stage.parent_fd, stage.name, failed)
            rename_noreplace(stage.parent_fd, stage.backup_name, stage.name)
            os.fsync(stage.parent_fd)
            shutil.rmtree(failed, dir_fd=stage.parent_fd, ignore_errors=True)
        raise


def close_stages(stages: list[Stage]) -> None:
    for stage in stages:
        try:
            shutil.rmtree(stage.staging_name, dir_fd=stage.parent_fd, ignore_errors=True)
        except OSError:
            pass
        for fd in (stage.staging_fd, stage.live_fd, stage.parent_fd):
            try:
                os.close(fd)
            except OSError:
                pass



def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--hermes-home', required=True)
    parser.add_argument('--agents-home', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    hermes = Path(args.hermes_home).resolve()
    agents = Path(args.agents_home).resolve()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    cli_launcher = (
        '#!/bin/sh\n'
        f'exec node {json.dumps(str(repo / "integrations/open-design-bridge/bin/centurion-design.mjs"))} "$@"\n'
    ).encode()
    definitions = [
        (hermes, 'skills', [(repo / 'integrations/hermes-legion-kit/skills', ''), (repo / 'skills/open-design-producer', 'autonomous-ai-agents/open-design-producer')], {}),
        (hermes, 'skill-bundles', [(repo / 'integrations/hermes-legion-kit/skill-bundles', '')], {}),
        (hermes, 'bin', [(repo / 'integrations/hermes-legion-kit/runtime/bin', '')], {'centurion-open-design': (cli_launcher, 0o755)}),
        (agents, 'skills', [(repo / 'skills', '')], {}),
    ]
    stages: list[Stage] = []
    try:
        for parent, name, overlays, generated in definitions:
            stages.append(stage_surface(parent, name, overlays, stamp, generated))
        report = {
            'schema': 'CENTURION_DEPLOYMENT_V2',
            'mode': 'apply' if args.apply else 'plan',
            'policy': 'repo-wins-preserve-complete-local-trees',
            'openDesign': 'cli-only',
            'surfaces': [{
                'path': str(stage.parent / stage.name),
                'incomingFiles': stage.incoming_count,
                'protectedLocalFiles': stage.protected_count,
                'backupPath': str(stage.parent / stage.backup_name) if args.apply else None,
            } for stage in stages],
            'untouchedSurfaces': ['config.yaml', 'SOUL.md', '.env', 'auth.json', 'plugins', 'hooks', 'mcp-servers', 'centurion-config'],
        }
        if args.apply:
            publish(stages)
            report['status'] = 'pass'
        print(json.dumps(report, indent=2))
        return 0
    finally:
        close_stages(stages)


if __name__ == '__main__':
    raise SystemExit(main())
