"""已知缺陷注入回归集（eval/regression_fixtures/）的入口测试。

eval/ 为本地链路（不随公开仓分发），公开侧无该目录时跳过；
本地全量口径（python3 -m pytest tests/ -q）必须绿。
"""
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO / "eval" / "regression_fixtures"


@unittest.skipUnless(FIXTURE_DIR.exists(), "eval/regression_fixtures 为本地链路，公开侧跳过")
class TestDefectInjectionFixtures(unittest.TestCase):
    def test_all_fixtures_behave_as_registered(self):
        import subprocess
        import sys
        runner = FIXTURE_DIR / "run_fixtures.py"
        r = subprocess.run([sys.executable, str(runner)], capture_output=True, text=True, cwd=REPO)
        self.assertEqual(r.returncode, 0,
                         f"缺陷注入回归集未全过：\n{r.stdout[-1500:]}\n{r.stderr[-500:]}")


if __name__ == "__main__":
    unittest.main()
