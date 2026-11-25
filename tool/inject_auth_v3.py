#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把主站的 DDB-AUTH-V1 / DDB-ADMIN-V1 块 + V3 登录门（DDB-GATE-V1）注入 V3 独立版（幂等）。

🔴 为什么需要解密层（2026-11-25 上午）：
   真鉴权上线后，受保护产物只剩 *.enc。主站 index.html 里有 window.fetch 拦截器
   （把 /output/*.json 改写为 .json.enc 再前端解密），但 V3 独立版
   （review_v3/index.html）没有这个块 —— 它直接 fetch ../output/*.json，
   加密后 17 个依赖里 13 个 404，页面大面积空白。

🔴 为什么还要登录门（2026-11-25 下午 · 补）：
   只注入解密层是不够的 —— 主站的**登录浮层与 loginGo()** 并不在那两块里。
   密钥只写 sessionStorage（按标签页隔离），新开 V3 标签页必然无钥：
   `DDB.restore()` 返回 null → `fetch` 拦截器 reject `LOCKED` → `main()` 第一行
   取 `market.json` 拿不到就 `return` ⇒ **整页所有板块恒停在「加载中… / 加载失败」**。
   线上实测（真实浏览器）：`hdDate === "market.json 加载失败"`、`DDB.keys()` 为空、
   页面里连一个密码输入框都没有 —— 用户根本无法解锁。
   ⇒ 本节注入登录门：无钥则浮层，登录成功 `persist()` 后 `location.reload()`，
     同一标签页 sessionStorage 仍在，`main()` 即正常。

设计：
   · 解密层唯一来源 = index.html 里已维护的那块（不复制代码，避免两处漂移）
   · 登录门 = 本文件内的常量（V3 专用，主站有自己的浮层）
   · 目标 = review_v3/index.html + review_v3/index_hide89.html + deploy 两份
   · 🔴 幂等按「比对后替换」，不按「存在即跳过」（铁律 27）：
     内容不一致 → 先删旧块，再插新块。
   · 插入位置 = </head> 之前（与主站一致，注入器触碰不到）；顺序 = 解密层 → 登录门

用法：
   python3 tool/inject_auth_v3.py            # 注入/更新（写盘）
   python3 tool/inject_auth_v3.py --check    # 只校验（两块均存在、与主站一致、顺序正确）
"""
from __future__ import annotations

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "index.html")
TARGETS = [
    os.path.join("review_v3", "index.html"),
    # 🔴 V3 四副本（铁律 7）：index_hide89 经核实与 index 无差异，
    #    但门禁要求四者 md5 一致 —— 漏注入会让 check_v3_style[8/10] 直接红。
    os.path.join("review_v3", "index_hide89.html"),
    os.path.join("deploy", "review_v3", "index.html"),
    os.path.join("deploy", "review_v3", "index_hide89.html"),
]

# 🔴 V3 在子目录 /review_v3/，块里的相对路径 'auth/xxx.json' 会被解析成
#    /review_v3/auth/xxx.json → 404 → 登录报 CRED_MISSING。
#    注入时做一处定向替换（主站块不动，保持唯一来源）。
V3_PATCHES = [
    ("_nativeFetch('auth/' + level + '.json",
     "_nativeFetch('../auth/' + level + '.json"),
]

AUTH_START = "/* ===== DDB-AUTH-V1 START"
AUTH_END = "/* ===== DDB-ADMIN-V1 END ===== */"

GATE_START = "/* ===== DDB-GATE-V1 START"
GATE_END = "/* ===== DDB-GATE-V1 END ===== */"

HEAD_END = "</head>"

GATE_HTML = r"""<script>
/* ===== DDB-GATE-V1 START · V3 独立版登录门（缺此块 = 全板块恒空白）
   实测 2026-11-25 线上：hdDate = "market.json 加载失败"、DDB.keys() 为空、页面无输入框。
   根因：解密层有了，但主站登录浮层不在注入范围内，且密钥只存 sessionStorage（按标签页隔离）。
   做法：DOMContentLoaded → DDB.restore()；无钥则浮层 → unlock 成功 → location.reload()。
   ========================================================================== */
(function(){
  var LV = 'admin', busy = false;
  function msg(e){
    var m = (e && e.message) || String(e);
    if (/BAD_PASSWORD/.test(m)) return '密码错误';
    if (/EXPIRED/.test(m)) return '该账号已过期';
    if (/CRED_MISSING/.test(m)) return '凭据文件缺失（auth/*.json 未部署或路径不对）';
    if (/NO_WEBCRYPTO/.test(m)) return '浏览器不支持 WebCrypto（需 https 环境）';
    return '登录失败：' + m;
  }
  function paint(){
    var bs = document.querySelectorAll('#v3Gate [data-lv]');
    for (var i = 0; i < bs.length; i++){
      var on = bs[i].getAttribute('data-lv') === LV;
      bs[i].style.cssText = 'flex:1;padding:7px 0;border-radius:8px;border:1px solid ' +
        (on ? '#4c8bf5' : '#d7dce6') + ';background:' + (on ? '#eef4ff' : '#fff') +
        ';color:' + (on ? '#1b64d8' : '#6b7280') + ';font-size:13px;font-weight:600;cursor:pointer';
    }
  }
  function go(){
    if (busy) return;
    var pw = (document.getElementById('v3Pw') || {}).value || '';
    var em = document.getElementById('v3Em');
    if (!pw){ if (em) em.textContent = '请输入密码'; return; }
    busy = true;
    if (em){ em.textContent = '正在解密…'; em.style.color = '#6b7280'; }
    DDB.unlock(LV, pw).then(function(){
      location.reload();
    }).catch(function(e){
      busy = false;
      if (em){ em.textContent = msg(e); em.style.color = '#e74c3c'; }
    });
  }
  function show(){
    if (document.getElementById('v3Gate')) return;
    var w = document.createElement('div');
    w.id = 'v3Gate';
    w.style.cssText = 'position:fixed;inset:0;z-index:2147483000;background:rgba(6,10,20,.82);' +
      'display:flex;align-items:center;justify-content:center;padding:16px;' +
      'font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif';
    w.innerHTML =
      '<div style="width:100%;max-width:330px;background:#fff;border-radius:14px;padding:22px 20px 18px;' +
        'box-shadow:0 20px 60px rgba(0,0,0,.45);color:#1a1f2e">' +
        '<div style="font-size:16px;font-weight:700;margin-bottom:6px">每日复盘 V3 · 独立版</div>' +
        '<div style="font-size:12px;color:#6b7280;line-height:1.65;margin-bottom:14px">' +
          '数据已加密，登录后在本机解密。与主站同一套密码。</div>' +
        '<div style="display:flex;gap:8px;margin-bottom:12px">' +
          '<button data-lv="admin">管理员</button><button data-lv="vip">VIP</button></div>' +
        '<input id="v3Pw" type="password" placeholder="请输入密码" autocomplete="current-password" ' +
          'style="width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid #d7dce6;' +
          'border-radius:8px;font-size:14px;outline:none">' +
        '<div id="v3Em" style="min-height:18px;font-size:12px;color:#e74c3c;margin:6px 0 4px"></div>' +
        '<button id="v3Go" style="width:100%;padding:11px 0;border:0;border-radius:9px;background:#4c8bf5;' +
          'color:#fff;font-size:14px;font-weight:600;cursor:pointer">登 录</button>' +
        '<div style="font-size:11px;color:#9ca3af;margin-top:10px;line-height:1.6">' +
          '若已登录但仍空白，刷新本页即可。</div>' +
      '</div>';
    document.body.appendChild(w);
    var bs = w.querySelectorAll('[data-lv]');
    for (var i = 0; i < bs.length; i++){
      bs[i].onclick = function(){ LV = this.getAttribute('data-lv'); paint(); };
    }
    paint();
    w.querySelector('#v3Go').onclick = go;
    w.querySelector('#v3Pw').addEventListener('keydown', function(ev){
      if (ev.key === 'Enter') go();
    });
    setTimeout(function(){ var p = document.getElementById('v3Pw'); if (p) p.focus(); }, 60);
  }
  function init(){
    if (!window.DDB || !DDB.restore){ show(); return; }
    DDB.restore().then(function(k){ if (!k) show(); }).catch(function(){ show(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
/* ===== DDB-GATE-V1 END ===== */
</script>"""


def extract_script_block(html: str, start_mark: str, end_mark: str) -> str | None:
    """返回以 start_mark 开头、end_mark 所在那个 <script> 的整段（含标签）。"""
    if start_mark not in html or end_mark not in html:
        return None
    inner_s = html.index(start_mark)
    s = html.rfind("<script", 0, inner_s)
    if s == -1:
        return None
    e = html.index(end_mark) + len(end_mark)
    tail = html.find("</script>", e)
    if tail == -1:
        return None
    return html[s:tail + len("</script>")]


def extract_block(html: str) -> str | None:
    return extract_script_block(html, AUTH_START, AUTH_END)


def extract_gate(html: str) -> str | None:
    return extract_script_block(html, GATE_START, GATE_END)


def strip_block(html: str, start_mark: str, end_mark: str) -> tuple[str, bool]:
    """删掉指定标记块（若有），返回 (新文本, 是否删过)。"""
    blk = extract_script_block(html, start_mark, end_mark)
    if blk is None:
        return html, False
    i = html.index(blk)
    start = i
    while start > 0 and html[start - 1] in "\n \t":
        start -= 1
    return html[:start] + html[i + len(blk):], True


def inject_one(path: str, auth_block: str, write: bool) -> tuple[bool, str]:
    """注入两块：先解密层，再登录门（顺序必须如此，登录门依赖 DDB）。"""
    if not os.path.exists(path):
        return False, "文件不存在"
    html = open(path, encoding="utf-8").read()

    if HEAD_END not in html:
        return False, "未找到 </head>"

    if extract_block(html) == auth_block and extract_gate(html) == GATE_HTML:
        return True, "已是最新（免改）"

    had_auth = extract_block(html) is not None
    had_gate = extract_gate(html) is not None

    cur, _ = strip_block(html, AUTH_START, AUTH_END)
    cur, _ = strip_block(cur, GATE_START, GATE_END)
    he = cur.index(HEAD_END)
    out = cur[:he].rstrip("\n") + "\n" + auth_block + "\n" + GATE_HTML + "\n" + cur[he:]

    if not write:
        return True, ("需更新（旧块不同）" if (had_auth or had_gate) else "可注入（原先无块）")

    open(path, "w", encoding="utf-8").write(out)
    return True, ("已更新旧块" if (had_auth or had_gate) else "已注入")


def main() -> int:
    check = "--check" in sys.argv
    if not os.path.exists(SRC):
        print("❌ 找不到 index.html（鉴权块唯一来源）")
        return 1
    block = extract_block(open(SRC, encoding="utf-8").read())
    if not block:
        print("❌ index.html 里找不到 DDB-AUTH/ADMIN 块")
        return 1
    for a, b in V3_PATCHES:
        if a not in block:
            print(f"❌ 适配失败：块内找不到 {a[:40]!r}（主站块结构变了？）")
            return 1
        block = block.replace(a, b)

    ok_all = True
    for t in TARGETS:
        ok, msg = inject_one(os.path.join(BASE, t), block, write=not check)
        print(f"  {'✅' if ok else '❌'} {t}: {msg}")
        ok_all = ok_all and ok

    if check:
        # 额外断言：① 两块都在 </head> 之前（否则注入器整段替换会吞掉）；
        #           ② 登录门必须在解密层**之后**（它调用 DDB.unlock）
        for t in TARGETS:
            p = os.path.join(BASE, t)
            if not os.path.exists(p):
                continue
            html = open(p, encoding="utf-8").read()
            blk, gate = extract_block(html), extract_gate(html)
            if not blk:
                print(f"  ❌ {t}: 无解密块")
                ok_all = False
                continue
            if not gate:
                print(f"  ❌ {t}: 无登录门（DDB-GATE-V1）→ 无钥时全页空白")
                ok_all = False
                continue
            head = html.index(HEAD_END)
            if html.index(blk) > head or html.index(gate) > head:
                print(f"  ❌ {t}: 有块在 </head> 之后 → 有被整段替换吞掉的风险")
                ok_all = False
            if html.index(gate) < html.index(blk):
                print(f"  ❌ {t}: 登录门在解密层之前 → DDB 未定义")
                ok_all = False
        print("✅ V3 解密层 + 登录门均在 <head> 内，顺序与主站一致" if ok_all else "❌ 校验未通过")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
