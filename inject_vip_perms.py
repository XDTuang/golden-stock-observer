#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜来米金融 · VIP 权限区隔注入（幂等 v1）
=========================================
1. VIP 密码有效期：2027-08-09 → 2026-09-30（密码不变）
2. 注入 VIP 权限控制：
   - VIP 仅可见 tab：总览(overview) + 每日复盘(dailyreview)
   - VIP 锁定投喂功能（投喂按钮隐藏）
   - nav 点击守卫（VIP 切到禁止 tab 直接忽略）
   - 登录成功 / 页面加载 / 刷新恢复登录时应用权限
3. 主站三份（index/index_template/deploy）与副站（diamond_site/index.html）同步

用法:
  python inject_vip_perms.py                 # 全部
  python inject_vip_perms.py deploy/index.html
"""
import os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGETS = ["index.html", "index_template.html", os.path.join("deploy", "index.html"),
           os.path.join("diamond_site", "index.html")]
if len(sys.argv) > 1:
    TARGETS = [sys.argv[1]]

MARK = "// ===== VIP 权限区隔"
MARK_V2 = "// ===== VIP 权限区隔 v2 ====="

PERM_JS = r"""
// ===== VIP 权限区隔 v2 =====
var _VIP_ALLOW = {overview:1, dailyreview:1, realtime:1, diamond:1, calendar:1, eventcal:1};  // VIP 可见 tab：总览/每日复盘(锁投喂)/实时盯盘/兜宝金钻/机游共振日历/重要事件日历
function _authLevel(){
  try { var a = JSON.parse(localStorage.getItem('doudou_auth')); return a && a.level ? a.level : null; }
  catch(e){ return null; }
}
function _setLock(btn, lock){
  if (lock) {
    btn.style.opacity = '0.5'; btn.style.cursor = 'not-allowed'; btn.style.pointerEvents = 'none';
    if (btn.dataset.locked !== '1') { btn.dataset.locked = '1'; btn.innerHTML = '🔒 ' + btn.innerHTML; }
  } else {
    btn.style.opacity = ''; btn.style.cursor = ''; btn.style.pointerEvents = '';
    if (btn.dataset.locked === '1') { btn.dataset.locked = ''; btn.innerHTML = btn.innerHTML.replace(/^🔒 /, ''); }
  }
}
function _applyAuthPerms(){
  var lv = _authLevel();
  if (!lv) return;
  var isVip = lv === 'vip';
  // tab 加锁不隐藏：VIP 可见全部 tab 名称，禁止的加 🔒 不可点击
  document.querySelectorAll('.nav-btn[data-tab]').forEach(function(btn){
    var t = btn.getAttribute('data-tab');
    _setLock(btn, isVip && !_VIP_ALLOW[t]);
  });
  // VIP 锁定投喂功能（加锁不隐藏）
  var fb = document.getElementById('drFeedBtn');
  if (fb) _setLock(fb, isVip);
  // 当前激活 tab 被禁 → 强制回总览
  var cur = document.querySelector('.nav-btn.active');
  if (cur) {
    var t = cur.getAttribute('data-tab');
    if (isVip && !_VIP_ALLOW[t]) {
      var ob = document.querySelector('.nav-btn[data-tab="overview"]');
      if (ob) ob.click();
    }
  }
}
"""

# loginGo 成功分支挂钩
LOGIN_HOOK = "  localStorage.setItem(_AUTH_KEY, JSON.stringify(d));"
LOGIN_HOOK_NEW = LOGIN_HOOK + "\n  _applyAuthPerms();"

# nav 绑定处：加载应用 + 点击守卫
NAV_ANCHOR = "document.querySelectorAll('.nav-btn').forEach(btn => {\n  btn.addEventListener('click', () => {"
NAV_NEW = ("if (typeof _applyAuthPerms === 'function') _applyAuthPerms();\n"
           "document.querySelectorAll('.nav-btn').forEach(btn => {\n"
           "  btn.addEventListener('click', () => {\n"
           "    var _pt = btn.getAttribute('data-tab');\n"
           "    if (_authLevel && _authLevel() === 'vip' && !_VIP_ALLOW[_pt]) return;")


def inject(path):
    with open(path, encoding="utf-8") as f:
        idx = f.read()
    changed = False

    # ① VIP 有效期 2026-09-30（幂等）
    if "2026-09-30T23:59:59" not in idx:
        if "2027-08-09T23:59:59" in idx:
            idx = idx.replace("2027-08-09T23:59:59", "2026-09-30T23:59:59")
            changed = True
            print(f"✅ {path}: VIP 有效期 → 2026-09-30")
        else:
            print(f"⚠️ {path}: 未找到原有效期，跳过")
    else:
        print(f"⏭️ {path}: 有效期已是 2026-09-30")

    # ② 权限 JS（v1 → v2 整体替换；无则插入到登录逻辑标记后）
    if MARK_V2 not in idx:
        anchor = "// ===== 登录逻辑 ====="
        if MARK in idx:
            # v1 块位于登录注释与 _AUTH_KEY 之间 → 整体替换
            s = idx.index(MARK)
            e = idx.index("var _AUTH_KEY = 'doudou_auth';", s)
            idx = idx[:s] + PERM_JS + "\n" + idx[e:]
            changed = True
            print(f"✅ {path}: 已升级 VIP 权限 JS（v2 加锁不隐藏）")
        elif anchor in idx:
            idx = idx.replace(anchor, anchor + "\n" + PERM_JS, 1)
            changed = True
            print(f"✅ {path}: 已注入 VIP 权限 JS")
        else:
            print(f"⚠️ {path}: 未找到登录逻辑锚点")
    else:
        print(f"⏭️ {path}: 权限 JS 已是 v2")

    # ③ loginGo 成功挂钩
    if LOGIN_HOOK in idx and "_applyAuthPerms();" not in idx.split(LOGIN_HOOK, 1)[1][:200]:
        idx = idx.replace(LOGIN_HOOK, LOGIN_HOOK_NEW, 1)
        changed = True
        print(f"✅ {path}: loginGo 已挂钩权限应用")
    # ④ nav 加载应用 + 点击守卫
    if NAV_ANCHOR in idx and "var _pt = btn.getAttribute" not in idx:
        idx = idx.replace(NAV_ANCHOR, NAV_NEW, 1)
        changed = True
        print(f"✅ {path}: nav 守卫 + 加载应用已注入")

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write(idx)
        print(f"💾 {path}: 已写入")


if __name__ == "__main__":
    for t in TARGETS:
        p = os.path.join(BASE, t)
        if os.path.exists(p):
            inject(p)
        else:
            print(f"⚠️ 跳过（不存在）: {p}")
