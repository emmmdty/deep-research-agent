"""提示词资产回归测试。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


class TestProjectAuditPrompt(unittest.TestCase):
    """验证 v1 项目现状审计提示词。"""

    def test_build_prompt_contains_required_audit_contract(self) -> None:
        """提示词应包含角色、流程、结论分档和报告结构要求。"""
        from prompts.project_audit import build_v1_project_audit_prompt

        prompt = build_v1_project_audit_prompt(Path("/tmp/deep-research-agent"))

        self.assertIn("开源项目技术审计员", prompt)
        self.assertIn("先读仓库事实，再看 GitHub 公共面，最后用联网搜索补证", prompt)
        self.assertIn("已实现", prompt)
        self.assertIn("已声明但依赖配置/外部环境", prompt)
        self.assertIn("占位或未接线", prompt)
        self.assertIn("项目定位结论", prompt)
        self.assertIn("当前 v1 已实现能力", prompt)
        self.assertIn("“是否存在混乱”结论", prompt)
        self.assertIn("与“企业级”定位的差距", prompt)
        self.assertIn("目录结构", prompt)
        self.assertIn("文件放置位置", prompt)
        self.assertIn("不混乱", prompt)
        self.assertIn("部分混乱", prompt)
        self.assertIn("明显混乱", prompt)
        self.assertIn("静态检查结论", prompt)
        self.assertIn("已实际运行验证", prompt)

    def test_build_prompt_embeds_repo_boundaries_as_absolute_paths(self) -> None:
        """提示词应嵌入关键边界文件的绝对路径，避免误判。"""
        from prompts.project_audit import build_v1_project_audit_prompt

        root = Path("/repo/example").resolve()
        prompt = build_v1_project_audit_prompt(root)

        self.assertIn(str(root / "README.zh-CN.md"), prompt)
        self.assertIn(str(root / "workflows" / "graph.py"), prompt)
        self.assertIn(str(root / "evaluation" / "comparators.py"), prompt)
        self.assertIn(str(root / "tests" / "test_public_repo_standards.py"), prompt)

    def test_default_prompt_uses_current_repo_root(self) -> None:
        """默认导出的提示词应指向当前仓库。"""
        from prompts.project_audit import V1_PROJECT_AUDIT_PROMPT

        self.assertIn(str(PROJECT_ROOT / "README.zh-CN.md"), V1_PROJECT_AUDIT_PROMPT)
        self.assertIn(str(PROJECT_ROOT / "workflows" / "graph.py"), V1_PROJECT_AUDIT_PROMPT)


if __name__ == "__main__":
    unittest.main()
