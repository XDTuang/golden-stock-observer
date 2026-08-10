#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「兜宝金钻」独立版本地预览服务器（供本地预览用）。
与 serve_preview.py 同理：显式 directory 指定 serve 目录，不依赖进程 cwd。
"""
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DEPLOY = "/Users/samt/golden_stock_observer/diamond_site"
PORT = 8090
HOST = "127.0.0.1"

os.chdir("/tmp")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DEPLOY, **kwargs)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"兜宝金钻独立版预览: http://{HOST}:{PORT}/index.html")
    httpd.serve_forever()
