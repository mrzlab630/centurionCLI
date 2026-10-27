import errno
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("centurion_deploy_roots", ROOT / "scripts/deploy_centurion_roots.py")
deploy = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = deploy
SPEC.loader.exec_module(deploy)


class DeploymentTransactionTests(unittest.TestCase):
    def test_missing_retired_parent_is_a_noop(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deploy.remove_relative(root, "centurion-legion/scripts/open-design-mcp.mjs")
            self.assertEqual(list(root.iterdir()), [])

    def test_archived_feature_cannot_be_enabled_by_old_flag(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/deploy_centurion_roots.py"),
                "--repo", str(ROOT), "--hermes-home", str(Path(temporary) / "hermes"),
                "--agents-home", str(Path(temporary) / "agents"), "--with-open-design"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("unrecognized arguments: --with-open-design", result.stderr)
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_cli_deploys_design_skills_without_archived_surfaces(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in ["hermes/skills", "hermes/skill-bundles", "hermes/bin", "agents/skills", "claude/skills"]:
                (root / relative).mkdir(parents=True)
            for relative in ["hermes/skills/autonomous-ai-agents/open-design-producer/SKILL.md",
                    "agents/skills/open-design-producer/SKILL.md", "claude/skills/open-design-producer/SKILL.md",
                    "hermes/skill-bundles/aquila-design-production.yaml", "hermes/bin/centurion-open-design"]:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("historical managed artifact")
            result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/deploy_centurion_roots.py"),
                "--repo", str(ROOT), "--hermes-home", str(root / "hermes"), "--agents-home", str(root / "agents"),
                "--claude-home", str(root / "claude"), "--apply"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            import json
            self.assertEqual(json.loads(result.stdout)["openDesign"], "archived")
            for relative in ["hermes/skills/autonomous-ai-agents/open-design-producer", "agents/skills/open-design-producer",
                    "claude/skills/open-design-producer", "hermes/skill-bundles/aquila-design-production.yaml", "hermes/bin/centurion-open-design"]:
                self.assertFalse((root / relative).exists(), relative)
            for home in ["agents", "claude"]:
                for name in ["aedilis", "pictor", "nomenclator", "orator", "tabularius"]:
                    self.assertEqual((root / home / "skills" / name / "SKILL.md").read_bytes(), (ROOT / "skills" / name / "SKILL.md").read_bytes())

    def test_failed_retirement_rolls_back_published_trees_and_retired_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "skills").mkdir()
            (root / "skills/local.txt").write_text("preserve me")
            (root / "overlay").mkdir()
            (root / "overlay/managed.txt").write_text("new instruction")
            (root / "centurion").mkdir()
            config = root / "centurion/open-design-bridge.json"
            config.write_text("{}\n")
            retirement_inode = (root / "centurion").stat().st_ino
            stage = deploy.stage_surface(root, "skills", [(root / "overlay", "")], "fixture")
            real_fsync = os.fsync
            injected = False

            def fail_retirement_sync(fd):
                nonlocal injected
                if os.fstat(fd).st_ino == retirement_inode and not injected:
                    injected = True
                    raise OSError(errno.EIO, "injected retirement fsync failure")
                return real_fsync(fd)

            try:
                with patch.object(deploy.os, "fsync", fail_retirement_sync):
                    with self.assertRaises(OSError):
                        deploy.publish([stage], (root, "centurion/open-design-bridge.json", "fixture"))
                self.assertTrue(injected)
                self.assertEqual(config.read_text(), "{}\n")
                self.assertEqual((root / "skills/local.txt").read_text(), "preserve me")
                self.assertFalse((root / "skills/managed.txt").exists())
                self.assertFalse(list((root / "centurion").glob("*backup*")))
            finally:
                deploy.close_stages([stage])

    @unittest.skipIf(os.geteuid() == 0, "permission-denial regression requires an unprivileged process")
    def test_cli_permission_denial_restores_every_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            surfaces = ["hermes/skills", "hermes/skill-bundles", "hermes/bin", "agents/skills", "claude/skills"]
            for relative in surfaces:
                (root / relative).mkdir(parents=True)
                (root / relative / "local.txt").write_text(relative)
            config_dir = root / "claude/centurion"
            config_dir.mkdir()
            (config_dir / "open-design-bridge.json").write_text("{}\n")
            config_dir.chmod(0o500)
            try:
                result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/deploy_centurion_roots.py"),
                    "--repo", str(ROOT), "--hermes-home", str(root / "hermes"),
                    "--agents-home", str(root / "agents"), "--claude-home", str(root / "claude"), "--apply"],
                    capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Permission denied", result.stderr)
                for relative in surfaces:
                    self.assertEqual(sorted(p.name for p in (root / relative).iterdir()), ["local.txt"])
                    self.assertEqual((root / relative / "local.txt").read_text(), relative)
                self.assertEqual((config_dir / "open-design-bridge.json").read_text(), "{}\n")
            finally:
                config_dir.chmod(0o700)


if __name__ == "__main__":
    unittest.main()
