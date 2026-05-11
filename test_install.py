#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_install.py — install.sh 安装脚本测试"""

import os
import subprocess
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "install.sh")


class TestInstallSyntax(unittest.TestCase):
    """1. Shell 语法检查"""

    def test_bash_n_syntax(self):
        result = subprocess.run(
            ["bash", "-n", SCRIPT],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0,
                         f"Syntax error in install.sh:\n{result.stderr}")


class TestInstallContent(unittest.TestCase):
    """2-3. 检查脚本内容"""

    @classmethod
    def setUpClass(cls):
        with open(SCRIPT, "r", encoding="utf-8") as f:
            cls.content = f.read()

    def test_uses_set_e(self):
        self.assertIn("set -e", self.content)

    def test_checks_python3(self):
        self.assertIn("python3", self.content)

    def test_checks_python_version(self):
        self.assertIn("version_info", self.content)

    def test_has_download_logic(self):
        # 应该有 curl 或 wget 下载逻辑
        has_curl = "curl" in self.content
        has_wget = "wget" in self.content
        self.assertTrue(has_curl or has_wget, "Script should use curl or wget for download")

    def test_has_error_handling(self):
        # 应该有 exit 1 之类的错误退出
        self.assertIn("exit 1", self.content)

    def test_has_install_dir(self):
        self.assertIn("INSTALL_DIR", self.content)

    def test_has_repo_url(self):
        # install.sh 使用 raw.githubusercontent.com（通过 REPO 变量拼接）
        self.assertTrue(
            "githubusercontent.com" in self.content or "github.com" in self.content,
            "Script should reference a GitHub URL"
        )

    def test_checks_file_integrity(self):
        self.assertIn("ReusableTCPServer", self.content)
        self.assertIn("find_port", self.content)

    def test_has_usage_instructions(self):
        self.assertIn("启动", self.content)

    def test_script_is_executable_or_has_shebang(self):
        self.assertTrue(self.content.startswith("#!/bin/bash"),
                        "Script should start with #!/bin/bash shebang")


if __name__ == "__main__":
    unittest.main()
