#!/usr/bin/env python3
"""dsh 插件注册面回归：插件是否真的注册了 skills/ 下**每一个** skill。

为什么需要（而不是只 `node --check`）：语法检查只保证文件能解析，不保证运行时真的注册。
`readSkills()` 对读不到 / frontmatter 不合格的技能目录**只打 warn 并跳过**——某天某个
SKILL.md 的 description 被写坏，宿主就静默少加载一个技能，而仓库侧一切照绿
（同类前科：本地 harness 的技能名单断言未随新 skill 更新，红灯静默 9 天）。

本测试真跑插件入口（node 打桩 ctx），断言：
  1. 注册数 == skills/ 下含 SKILL.md 的目录数
  2. 注册名单 == 目录名单（无遗漏、无多余）
  3. core 作为依赖单元不可调用（modelInvocable / userInvocable 均为 false）
  4. 每个技能 description / body 非空、name 与目录名一致

无 node 时跳过（外部贡献者环境不强制装 Node；CI 侧由 check.sh 的 node --check 兜底）。
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / ".dsh/plugins/qa-skills.js"
SKILLS = REPO / "skills"

HARNESS = r"""
import(process.argv[1]).then(async (m) => {
  const registered = [];
  const ctx = { skills: { register: (s) => registered.push(s) },
                logger: { warn: () => {}, info: () => {} } };
  await m.apply(ctx);
  console.log(JSON.stringify(registered.map((s) => ({
    name: s.name, description: s.description, bodyLen: (s.content || '').length,
    invocation: s.invocation || null,
  }))));
}).catch((e) => { console.error(String(e)); process.exit(1); });
"""


@unittest.skipUnless(shutil.which("node"), "需要 node 运行 dsh 插件注册探针")
class PluginRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        proc = subprocess.run(
            ["node", "--input-type=module", "-e", HARNESS, str(PLUGIN)],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            raise AssertionError(f"插件注册探针失败:\n{proc.stderr[:800]}")
        cls.registered = json.loads(proc.stdout.strip().splitlines()[-1])
        cls.dirs = sorted(d.name for d in SKILLS.iterdir()
                          if d.is_dir() and (d / "SKILL.md").exists())

    def test_registers_every_skill_directory(self):
        """注册数必须等于技能目录数——少一个就是宿主静默丢技能。"""
        self.assertEqual(len(self.registered), len(self.dirs),
                         f"注册 {len(self.registered)} 个，目录 {len(self.dirs)} 个")

    def test_registered_names_match_directories(self):
        names = sorted(r["name"] for r in self.registered)
        self.assertEqual(names, self.dirs)

    def test_core_is_not_invocable(self):
        core = [r for r in self.registered if r["name"] == "core"]
        self.assertEqual(len(core), 1, "core 必须注册且只注册一次")
        self.assertEqual(core[0]["invocation"],
                         {"modelInvocable": False, "userInvocable": False},
                         "core 是依赖单元，不得可调用（否则会参与触发竞争）")

    def test_every_skill_has_description_and_body(self):
        empty = [r["name"] for r in self.registered
                 if not (r["description"] or "").strip() or r["bodyLen"] <= 0]
        self.assertEqual(empty, [], f"这些技能缺 description 或正文：{empty}")


if __name__ == "__main__":
    unittest.main()
