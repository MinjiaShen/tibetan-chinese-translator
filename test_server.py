#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_server.py — Python HTTP 服务器测试"""

import importlib.util
import socket
import socketserver
import threading
import time
import unittest
import unittest.mock
import os

# 动态加载 tibetan-translator.py（文件名含连字符）
def _load_module():
    spec = importlib.util.spec_from_file_location(
        "tibetan_translator",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "tibetan-translator.py"),
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

mod = _load_module()


class TestReusableTCPServer(unittest.TestCase):
    """1. ReusableTCPServer — 类存在且 allow_reuse_address = True"""

    def test_class_exists(self):
        self.assertTrue(hasattr(mod, "ReusableTCPServer"))

    def test_allow_reuse_address(self):
        self.assertTrue(mod.ReusableTCPServer.allow_reuse_address)

    def test_is_tcp_server_subclass(self):
        self.assertTrue(issubclass(mod.ReusableTCPServer, socketserver.TCPServer))


class TestFindPort(unittest.TestCase):
    """2-3. find_port() 端口查找"""

    def test_returns_valid_port_in_range(self):
        port = mod.find_port()
        self.assertGreaterEqual(port, 9090)
        self.assertLessEqual(port, 9109)

    def test_returns_int(self):
        port = mod.find_port()
        self.assertIsInstance(port, int)

    def test_finds_next_port_when_occupied(self):
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            blocker.bind(("127.0.0.1", 9090))
            blocker.listen(1)
            port = mod.find_port(start=9090)
            self.assertNotEqual(port, 9090)
            self.assertGreaterEqual(port, 9091)
            self.assertLessEqual(port, 9109)
        finally:
            blocker.close()


class TestHandlerGET(unittest.TestCase):
    """4-5. Handler.do_GET — / 和 /favicon.ico"""

    @classmethod
    def setUpClass(cls):
        cls.port = mod.find_port()
        cls.server = mod.ReusableTCPServer(("127.0.0.1", cls.port), mod.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        for _ in range(30):
            try:
                with socket.create_connection(("127.0.0.1", cls.port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path):
        import urllib.request
        url = f"http://127.0.0.1:{self.port}{path}"
        return urllib.request.urlopen(url, timeout=5)

    def test_root_returns_200(self):
        resp = self._get("/")
        self.assertEqual(resp.status, 200)

    def test_root_returns_html(self):
        resp = self._get("/")
        body = resp.read()
        self.assertIn(b"<!DOCTYPE html>", body)

    def test_root_content_type_is_html(self):
        resp = self._get("/")
        ct = resp.getheader("Content-Type")
        self.assertIn("text/html", ct)
        self.assertIn("utf-8", ct.lower())

    def test_favicon_returns_200(self):
        resp = self._get("/favicon.ico")
        self.assertEqual(resp.status, 200)

    def test_favicon_content_type(self):
        resp = self._get("/favicon.ico")
        ct = resp.getheader("Content-Type")
        self.assertIn("image/x-icon", ct)

    def test_favicon_has_body(self):
        resp = self._get("/favicon.ico")
        data = resp.read()
        self.assertGreater(len(data), 0)


class TestHandlerHEAD(unittest.TestCase):
    """6. Handler.do_HEAD — 对 / 返回 200 + 正确 Content-Length"""

    @classmethod
    def setUpClass(cls):
        cls.port = mod.find_port()
        cls.server = mod.ReusableTCPServer(("127.0.0.1", cls.port), mod.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        for _ in range(30):
            try:
                with socket.create_connection(("127.0.0.1", cls.port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_head_returns_200(self):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("HEAD", "/")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        conn.close()

    def test_head_has_content_length(self):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("HEAD", "/")
        resp = conn.getresponse()
        cl = resp.getheader("Content-Length")
        self.assertIsNotNone(cl)
        self.assertGreater(int(cl), 0)
        conn.close()

    def test_head_content_length_matches_html(self):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("HEAD", "/")
        resp = conn.getresponse()
        cl = int(resp.getheader("Content-Length"))
        expected = len(mod.HTML.encode("utf-8"))
        self.assertEqual(cl, expected)
        conn.close()


class TestHTMLVariable(unittest.TestCase):
    """7. HTML 变量 — 包含关键 UI 元素"""

    def test_contains_tibetan(self):
        self.assertIn("藏语", mod.HTML)

    def test_contains_chinese(self):
        self.assertIn("中文", mod.HTML)

    def test_contains_voice(self):
        self.assertIn("语音", mod.HTML)

    def test_contains_keyboard(self):
        self.assertIn("键盘", mod.HTML)

    def test_contains_ocr(self):
        self.assertIn("OCR", mod.HTML)

    def test_contains_doctype(self):
        self.assertIn("<!DOCTYPE html>", mod.HTML)

    def test_contains_script_tag(self):
        self.assertIn("<script>", mod.HTML)

    def test_contains_meta_charset(self):
        self.assertIn('charset="UTF-8"', mod.HTML)

    def test_contains_meta_viewport(self):
        self.assertIn('name="viewport"', mod.HTML)


class TestFavicon(unittest.TestCase):
    """8. FAVICON_ICO — 是有效的 ICO 二进制数据"""

    def test_exists(self):
        self.assertTrue(hasattr(mod, "FAVICON_ICO"))

    def test_is_bytes(self):
        self.assertIsInstance(mod.FAVICON_ICO, bytes)

    def test_length_greater_than_zero(self):
        self.assertGreater(len(mod.FAVICON_ICO), 0)

    def test_starts_with_ico_header(self):
        self.assertTrue(mod.FAVICON_ICO.startswith(b"\x00\x00\x01\x00"))


class TestServerStartup(unittest.TestCase):
    """9. 服务器启动和端口绑定"""

    def test_server_starts_and_responds(self):
        port = mod.find_port()
        server = mod.ReusableTCPServer(("127.0.0.1", port), mod.Handler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            for _ in range(30):
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                        break
                except OSError:
                    time.sleep(0.05)
            import urllib.request
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5)
            self.assertEqual(resp.status, 200)
        finally:
            server.shutdown()
            server.server_close()


class TestMainFunction(unittest.TestCase):
    """10. main() 基本执行（mock webbrowser.open）"""

    def test_main_starts_server_and_can_be_stopped(self):
        """验证 main 函数能启动服务器并响应请求"""
        opened_urls = []

        def fake_open(url):
            opened_urls.append(url)
            return True

        def fake_signal(*args, **kwargs):
            pass  # no-op: signal.signal 不能在非主线程调用

        with unittest.mock.patch("webbrowser.open", side_effect=fake_open), \
             unittest.mock.patch("signal.signal", side_effect=fake_signal):
            main_thread = threading.Thread(target=mod.main, daemon=True)
            main_thread.start()
            time.sleep(2)

            self.assertTrue(len(opened_urls) > 0, "webbrowser.open should have been called")
            self.assertIn("127.0.0.1", opened_urls[0])

            import urllib.request
            port = int(opened_urls[0].rsplit(":", 1)[1])
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5)
            self.assertEqual(resp.status, 200)
            resp.close()

    def test_main_function_exists_and_callable(self):
        self.assertTrue(callable(mod.main))


if __name__ == "__main__":
    unittest.main()
