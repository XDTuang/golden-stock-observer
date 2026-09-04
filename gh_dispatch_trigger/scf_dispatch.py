# -*- coding: utf-8 -*-
"""
GitHub Actions workflow_dispatch 定时触发器（腾讯云 SCF / 云函数版）
═══════════════════════════════════════════════════════════════════
用途：绕过 GitHub Actions schedule 的队列积压延迟（实测 9/1-9/4 延迟 20~314 分钟，
      盘中档几乎全部延迟到收盘后），用外部定时器准时触发 realtime-monitor.yml。

用法：把本文件内容粘贴到腾讯云 SCF 新建函数（运行环境 Python 3.9+，无需额外依赖，
      纯标准库 urllib），配置一条定时触发器即可，无需改任何仓库代码。

环境变量：
  GITHUB_TOKEN   fine-grained PAT，仓库 XDTuang/golden-stock-observer，
                 权限 Actions: Read and write（触发 workflow_dispatch 必须）。
                 ▸ 在函数「配置 → 环境变量」中添加，切勿写死在代码里。

定时触发器 cron（腾讯云 7 段制，北京时间，见 README.md）：
  建议宽松版一条搞定（多触发的 9:15 / 11:45 会被 fetch_realtime.py 状态机拦截，无副作用）：
    0 15,45 9,10,11,13,14 * * * *
  等价精确 8 档（需建 8 条触发器，不推荐）：
    北京 09:45 → 0 45 9 * * * *   北京 10:15 → 0 15 10 * * * *
    北京 10:45 → 0 45 10 * * * *  北京 11:15 → 0 15 11 * * * *
    北京 13:15 → 0 15 13 * * * *  北京 13:45 → 0 45 13 * * * *
    北京 14:15 → 0 15 14 * * * *  北京 14:45 → 0 45 14 * * * *

返回：{"code": 204, "msg": "dispatch 已触发"} 表示成功。
"""
import json
import os
import urllib.request
import urllib.error

REPO = "XDTuang/golden-stock-observer"
WORKFLOW = "realtime-monitor.yml"          # 实验期 4 档 schedule；本触发器为 8 档主力
REF = "main"


def main_handler(event, context):
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        return {"code": 1, "msg": "GITHUB_TOKEN 未配置（云函数环境变量）"}

    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches"
    body = json.dumps({"ref": REF}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {"code": resp.status, "msg": f"HTTP {resp.status} dispatch 已触发 {WORKFLOW}"}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        return {"code": e.code, "msg": f"HTTP {e.code}: {detail}"}
    except Exception as e:
        return {"code": -1, "msg": f"异常: {e}"}


# 本地自测（不含 SCF 时）：python3 scf_dispatch.py
if __name__ == "__main__":
    print(json.dumps(main_handler({}, {}), ensure_ascii=False))
