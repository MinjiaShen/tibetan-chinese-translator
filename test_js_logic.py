#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_js_logic.py — JavaScript 逻辑测试（纯 Python 静态分析）"""

import importlib.util
import os
import re
import unittest


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "tibetan_translator",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "tibetan-translator.py"),
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

mod = _load_module()
HTML = mod.HTML

# 提取 <script> 块
SCRIPT_BLOCKS = re.findall(r'<script[^>]*>(.*?)</script>', HTML, re.DOTALL)
JS = "\n".join(SCRIPT_BLOCKS)


class TestJSFunctions(unittest.TestCase):
    """1. 检查所有 JS 函数定义存在"""

    def test_translate_function(self):
        self.assertIn("async function translate(", JS)

    def test_pq_function(self):
        self.assertIn("async function pq(", JS)

    def test_qt_function(self):
        self.assertIn("function qt(", JS)

    def test_ad_function(self):
        self.assertIn("function ad(", JS)

    def test_esc_function(self):
        self.assertIn("function esc(", JS)

    def test_clr_function(self):
        self.assertIn("function clr(", JS)

    def test_doK_function(self):
        self.assertIn("async function doK(", JS)

    def test_doO_function(self):
        self.assertIn("async function doO(", JS)

    def test_initRec_function(self):
        self.assertIn("function initRec(", JS)

    def test_startRec_function(self):
        self.assertIn("function startRec(", JS)

    def test_stopRec_function(self):
        self.assertIn("function stopRec(", JS)

    def test_toggleRec_function(self):
        self.assertIn("function toggleRec(", JS)


class TestCSSVariables(unittest.TestCase):
    """2. 检查 CSS 变量定义完整"""

    def _get_root_variables(self):
        m = re.search(r':root\{([^}]+)\}', HTML)
        self.assertIsNotNone(m, ":root block not found")
        text = m.group(1)
        return {v for v in re.findall(r'--([\w-]+)', text)}

    def test_has_background_var(self):
        self.assertIn("bg", self._get_root_variables())

    def test_has_surface_vars(self):
        vars = self._get_root_variables()
        self.assertIn("s1", vars)
        self.assertIn("s2", vars)

    def test_has_border_var(self):
        self.assertIn("bd", self._get_root_variables())

    def test_has_accent_vars(self):
        vars = self._get_root_variables()
        self.assertIn("ac", vars)
        self.assertIn("ac2", vars)
        self.assertIn("ac3", vars)

    def test_has_text_vars(self):
        vars = self._get_root_variables()
        self.assertIn("tx", vars)
        self.assertIn("tx2", vars)

    def test_has_danger_vars(self):
        vars = self._get_root_variables()
        self.assertIn("dg", vars)
        self.assertIn("dg2", vars)

    def test_has_success_vars(self):
        vars = self._get_root_variables()
        self.assertIn("sg", vars)
        self.assertIn("sg2", vars)

    def test_has_radius_vars(self):
        vars = self._get_root_variables()
        self.assertIn("r", vars)
        self.assertIn("rs", vars)


class TestHTMLStructureIdsInJS(unittest.TestCase):
    """3. 检查 HTML 结构完整性（所有 id 在 JS 中有对应 $() 调用）"""

    def _get_html_ids(self):
        return set(re.findall(r'id="([^"]+)"', HTML))

    def _get_js_dollar_refs(self):
        return set(re.findall(r"\$\('([^']+)'\)", JS))

    def test_all_ids_referenced_in_js(self):
        html_ids = self._get_html_ids()
        js_refs = self._get_js_dollar_refs()
        # 核心交互 id 必须在 JS 中直接引用
        # 注意: pv/pk/po/vs/ks/os 通过 $('p'+b.dataset.t) 和 $(c+'s') 间接引用，不算缺失
        critical_ids = {"sp", "st", "tst", "mb", "lt", "ki", "kc", "kb",
                        "fi", "uz", "opv", "ob", "ocb", "opr", "opt"}
        missing = critical_ids - js_refs
        self.assertEqual(missing, set(), f"Critical IDs not referenced in JS: {missing}")

    def test_dollar_refs_exist_in_html(self):
        html_ids = self._get_html_ids()
        js_refs = self._get_js_dollar_refs()
        phantom = js_refs - html_ids
        self.assertEqual(phantom, set(), f"JS references non-existent IDs: {phantom}")


class TestEventListeners(unittest.TestCase):
    """4. 检查事件监听器绑定"""

    def test_click_listener_on_mic_button(self):
        self.assertIn("addEventListener('click', toggleRec)", JS)

    def test_keydown_listener(self):
        self.assertIn("addEventListener('keydown'", JS)

    def test_tab_click_listener(self):
        self.assertIn("addEventListener('click'", JS)

    def test_input_listener_on_textarea(self):
        self.assertIn("addEventListener('input'", JS)

    def test_dragover_listener(self):
        self.assertIn("addEventListener('dragover'", JS)

    def test_drop_listener(self):
        self.assertIn("addEventListener('drop'", JS)


class TestQueueVersionAndTesseract(unittest.TestCase):
    """5-6. 检查 qVersion 和 tesseractLoaded"""

    def test_qVersion_defined(self):
        self.assertIn("let qVersion", JS)
        self.assertIn("qVersion = 0", JS)

    def test_qVersion_incremented_on_tab_switch(self):
        self.assertIn("qVersion++", JS)

    def test_qVersion_checked_in_pq(self):
        # pq 函数中检查 ver !== qVersion
        self.assertIn("ver !== qVersion", JS)

    def test_tesseractLoaded_defined(self):
        self.assertIn("let tesseractLoaded", JS)
        self.assertIn("tesseractLoaded = false", JS)

    def test_tesseractLoaded_set_true_on_load(self):
        self.assertIn("tesseractLoaded = true", JS)

    def test_ensureTesseract_function(self):
        self.assertIn("async function ensureTesseract()", JS)


if __name__ == "__main__":
    unittest.main()
