#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地预览服务器（供 launchd com.goldenstock.preview 调用）。
不使用 `python -m http.server` CLI，避免其在 launchd 下：
  1) argparse 阶段调用 os.getcwd() 因 cwd 不可访问而抛 PermissionError；
  2) 进程在 launchd 上下文不稳定。
改为：先 cd 到 launchd 必定可访问的 /tmp，再用 SimpleHTTPRequestHandler
显式 directory= 参数指定 serve 目录（不依赖进程 cwd）。
"""
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DEPLOY = "/Users/samt/golden_stock_observer/deploy"
PORT = 8080
HOST = "127.0.0.1"

# 先切到必定可访问的目录，规避 launchd 下 getcwd 权限问题
os.chdir("/tmp")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DEPLOY, **kwargs)

    def log_message(self, *args):
        pass  # 静默访问日志，避免写满 stderr


if __name__ == "__main__":
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    httpd.serve_forever()
