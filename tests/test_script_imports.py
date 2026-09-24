import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    ROOT / "skills" / "velites" / "scripts" / "recon.py",
    ROOT / "skills" / "haruspex" / "scripts" / "scan_code.py",
    ROOT / "skills" / "orchestrator" / "scripts" / "mission_control.py",
    ROOT / "skills" / "sicarius" / "scripts" / "exploit_verify.py",
)


class ScriptImportTests(unittest.TestCase):
    def test_direct_scripts_prefer_adjacent_core_over_pythonpath(self):
        with tempfile.TemporaryDirectory() as temporary:
            foreign_root = Path(temporary) / "foreign"
            (foreign_root / "libs").mkdir(parents=True)
            (foreign_root / "libs" / "__init__.py").write_text("")
            (foreign_root / "libs" / "legion_core.py").write_text(
                'raise RuntimeError("foreign core imported")\n'
            )
            (foreign_root / "legion_core.py").write_text(
                'raise RuntimeError("foreign core imported")\n'
            )
            (foreign_root / "playwright").mkdir()
            (foreign_root / "playwright" / "__init__.py").write_text("")
            (foreign_root / "playwright" / "sync_api.py").write_text(
                "sync_playwright = None\n"
            )
            environment = dict(os.environ, PYTHONPATH=str(foreign_root))

            for script in SCRIPTS:
                with self.subTest(script=script.name):
                    result = subprocess.run(
                        [sys.executable, str(script), "--help"],
                        cwd=temporary,
                        env=environment,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("usage:", result.stdout.lower())

            installed_root = Path(temporary) / "installed"
            installed_script = installed_root / "skills" / "velites" / "scripts" / "recon.py"
            installed_script.parent.mkdir(parents=True)
            (installed_root / "libs").mkdir()
            shutil.copy2(SCRIPTS[0], installed_script)
            shutil.copy2(ROOT / "libs" / "legion_core.py", installed_root / "libs")
            result = subprocess.run(
                [sys.executable, str(installed_script), "--help"],
                cwd=temporary,
                env=environment,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
