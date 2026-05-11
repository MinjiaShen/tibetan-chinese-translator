#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_html.py — HTML 完整性测试"""

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

# 也读取独立的 index.html
INDEX_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
    INDEX_HTML = f.read()


class TestHTMLIdUniqueness(unittest.TestCase):
    """1. 所有 id 属性唯一"""

    def test_ids_unique_in_embedded_html(self):
        ids = re.findall(r'id="([^"]+)"', HTML)
        duplicates = [x for x in ids if ids.count(x) > 1]
        self.assertEqual(duplicates, [], f"Duplicate IDs found: {set(duplicates)}")

    def test_ids_unique_in_index_html(self):
        ids = re.findall(r'id="([^"]+)"', INDEX_HTML)
        duplicates = [x for x in ids if ids.count(x) > 1]
        self.assertEqual(duplicates, [], f"Duplicate IDs in index.html: {set(duplicates)}")


class TestButtonEventHandlers(unittest.TestCase):
    """2. 所有 <button> 有对应事件处理"""

    def _get_buttons(self):
        return re.findall(r'<button[^>]*>(.*?)</button>', HTML, re.DOTALL)

    def _get_button_attrs(self):
        return re.findall(r'<button([^>]*)>', HTML)

    def test_buttons_have_handlers(self):
        """每个 button 要么有 onclick，要么有 data-t 属性（tab），要么有 id 被 JS 引用"""
        attrs_list = self._get_button_attrs()
        script_block = re.search(r'<script>(.*?)</script>', HTML, re.DOTALL)
        js = script_block.group(1) if script_block else ""

        for attrs in attrs_list:
            has_onclick = "onclick=" in attrs
            has_data_t = "data-t=" in attrs
            has_id = re.search(r'id="([^"]+)"', attrs)
            if has_id:
                btn_id = has_id.group(1)
                # 检查 JS 中是否有该 id 的事件绑定
                has_js_binding = f"$('{btn_id}')" in js or f"$('{btn_id}')" in js
                self.assertTrue(
                    has_onclick or has_data_t or has_js_binding,
                    f"Button with attrs [{attrs}] has no event handler"
                )
            else:
                self.assertTrue(
                    has_onclick or has_data_t,
                    f"Button with attrs [{attrs}] has no event handler and no id"
                )


class TestCSSClassDefinitions(unittest.TestCase):
    """3. CSS 类名在 <style> 中有定义"""

    def _get_style_block(self):
        m = re.search(r'<style>(.*?)</style>', HTML, re.DOTALL)
        return m.group(1) if m else ""

    def _get_html_classes(self):
        classes = set()
        for match in re.findall(r'class="([^"]+)"', HTML):
            for cls in match.split():
                classes.add(cls)
        return classes

    def _get_css_classes(self):
        css = self._get_style_block()
        return set(re.findall(r'\.([\w-]+)', css))

    def test_all_html_classes_defined_in_css(self):
        html_classes = self._get_html_classes()
        css_classes = self._get_css_classes()
        # 有些类可能只用于 JS 动态添加（如 .at, .lv, .sh, .rc, .drag）
        js_dynamic = {"at", "lv", "sh", "rc", "drag", "on", "err"}
        undefined = html_classes - css_classes - js_dynamic
        self.assertEqual(undefined, set(),
                         f"HTML classes not defined in CSS: {undefined}")


class TestScriptTag(unittest.TestCase):
    """4. <script> 标签存在且非空"""

    def test_script_tag_exists(self):
        self.assertIn("<script>", HTML)

    def test_script_not_empty(self):
        scripts = re.findall(r'<script>(.*?)</script>', HTML, re.DOTALL)
        self.assertTrue(len(scripts) > 0, "No <script> tags found")
        for s in scripts:
            self.assertGreater(len(s.strip()), 0, "Empty <script> tag found")

    def test_script_has_meaningful_content(self):
        scripts = re.findall(r'<script>(.*?)</script>', HTML, re.DOTALL)
        combined = "\n".join(scripts)
        # 至少应该有函数定义
        self.assertIn("function", combined)


class TestMetaTags(unittest.TestCase):
    """5-6. meta charset 和 viewport"""

    def test_charset_utf8(self):
        self.assertIn('<meta charset="UTF-8">', HTML)

    def test_viewport_meta(self):
        self.assertIn('name="viewport"', HTML)
        self.assertIn("width=device-width", HTML)


class TestKeyElementCounts(unittest.TestCase):
    """7. 关键元素数量检查"""

    def test_three_tabs(self):
        tabs = re.findall(r'<button class="t[^"]*"[^>]*data-t="[^"]+"', HTML)
        self.assertEqual(len(tabs), 3, f"Expected 3 tabs, found {len(tabs)}")

    def test_three_panels(self):
        panels = re.findall(r'<div class="pn[^"]*"[^>]*id="p[vko]"', HTML)
        self.assertEqual(len(panels), 3, f"Expected 3 panels, found {len(panels)}")

    def test_tab_data_attributes(self):
        tabs = re.findall(r'data-t="([^"]+)"', HTML)
        self.assertEqual(set(tabs), {"v", "k", "o"})

    def test_has_header(self):
        self.assertIn('class="hd"', HTML)

    def test_has_footer(self):
        self.assertIn('class="ft"', HTML)

    def test_has_main_container(self):
        self.assertIn('class="mn"', HTML)


class TestHTMLConsistency(unittest.TestCase):
    """验证 index.html 与内嵌 HTML 的一致性"""

    def test_both_have_doctype(self):
        self.assertIn("<!DOCTYPE html>", HTML)
        self.assertIn("<!DOCTYPE html>", INDEX_HTML)

    def test_both_have_same_title(self):
        title_embedded = re.search(r'<title>(.*?)</title>', HTML)
        title_index = re.search(r'<title>(.*?)</title>', INDEX_HTML)
        self.assertIsNotNone(title_embedded)
        self.assertIsNotNone(title_index)
        self.assertEqual(title_embedded.group(1), title_index.group(1))

    def test_both_have_same_id_count(self):
        ids_embedded = re.findall(r'id="([^"]+)"', HTML)
        ids_index = re.findall(r'id="([^"]+)"', INDEX_HTML)
        self.assertEqual(len(ids_embedded), len(ids_index),
                         "Embedded HTML and index.html have different number of IDs")


if __name__ == "__main__":
    unittest.main()
