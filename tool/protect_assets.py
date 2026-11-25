#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兜是宝 · 核心资产加密（AES-256-GCM）

作用：把页面实际 fetch 的核心数据加密为 `<原文件名>.enc`，并可移除明文，
      使 GitHub Pages / 公开仓库上只剩密文。前端登录后由浏览器解密。

密钥来源（优先级）：
  1) 环境变量 DDB_DATA_KEY（base64 32B）—— CI 用（GitHub Actions Secret）
  2) .secret/keys.json 的 data_key —— 本地用

用法：
  python tool/protect_assets.py --list              # 打印清单与状态
  python tool/protect_assets.py --encrypt           # 加密（保留明文）
  python tool/protect_assets.py --encrypt --purge   # 加密并删除明文（发布用）
  python tool/protect_assets.py --check             # 校验：清单中每个文件都有 .enc 且无明文
  python tool/protect_assets.py --decrypt DIR        # 应急：把 .enc 解到 DIR（需密钥）

fail-closed：密钥缺失、清单文件既无明文也无密文 → 非 0 退出，阻断发布。
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOY = os.path.join(BASE, "deploy")
KEYS_FILE = os.path.join(BASE, ".secret", "keys.json")
ENC_SUFFIX = ".enc"
MANIFEST = os.path.join(DEPLOY, "auth", "protected.json")

# ── 受保护清单 ──────────────────────────────────────────────
# 判据：index.html 实际 fetch 的路径（含动态拼接的命名规则）
PROTECTED = [
    # 根
    "signals.json",
    "lh_calendar.json",
    "realtime.json",
    # 每日复盘
    "data/daily_review/market.json",
    "data/daily_review/analysis.html",
    # output/ 页面直读
    "output/backtest_daily.json",
    "output/cross_analysis.json",
    "output/daily_macro_latest.json",
    "output/daily_news_latest.json",
    "output/daily_news_window.json",
    "output/feed_review_latest.json",
    "output/gate_data.json",
    "output/gate_data_lite.json",
    "output/golden_diamond_history.json",
    "output/golden_pool_manifest.json",
    "output/golden_pool_meta.json",
    "output/institutional_flow.json",
    "output/market_thermometer.json",
    "output/national_team_etf.json",
    "output/obs_deduce_latest.json",
    "output/observation_pool.json",
    "output/report_analysis.json",
    "output/sector_flow.json",
    "output/sector_golden_diamond_history.json",
    "output/stocks.json",
    "output/top10_history.json",
    "output/valuation_band.json",
    "output/vix_panel.json",
    "output/window_latest.json",
    # output/ 指数K线（_idxKlineFiles 映射）
    "output/sh_index_kline.json",
    "output/sz_index_kline.json",
    "output/cyb_index_kline.json",
    "output/kc50_index_kline.json",
    "output/hs300_index_kline.json",
]

# 通配：金钻分片（golden_pool_0..6）与事件日历（按月）
PATTERNS = ["golden_pool_", "event_calendar_"]


def load_key() -> bytes:
    env = os.environ.get("DDB_DATA_KEY", "").strip()
    if env:
        try:
            k = base64.b64decode(env)
        except Exception:
            sys.exit("✗ DDB_DATA_KEY 不是合法 base64")
        if len(k) != 32:
            sys.exit(f"✗ DDB_DATA_KEY 长度 {len(k)}，须 32 字节")
        return k
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, encoding="utf-8") as f:
            return base64.b64decode(json.load(f)["data_key"])
    sys.exit("✗ 未找到密钥：请设置 DDB_DATA_KEY 或先生成 .secret/keys.json")


def key_fp(key: bytes) -> str:
    """密钥指纹（sha256 前 12 位）——只用来核对「CI 用的是不是同一把钥」，不泄漏密钥"""
    return hashlib.sha256(key).hexdigest()[:12]


# 密钥自检样本：仓库里长期存在、且必然由当前 data_key 加密的密文。
# 只取少数几个，避免大文件拖慢 CI。
VERIFY_SAMPLES = ["signals.json", "output/cross_analysis.json", "realtime.json"]


def _sample_blob(rel: str):
    """找一个可用的密文样本路径（deploy 优先，其次站点根）"""
    for p in (enc_path(rel), os.path.join(BASE, rel + ENC_SUFFIX)):
        if os.path.exists(p):
            return p
    return None


def verify_key(key: bytes) -> tuple[bool, str]:
    """用现成密文验证密钥是否真的匹配。

    要点：AES-GCM **加密**永不失败（错钥也能加出垃圾密文），只有解密会 InvalidTag。
    所以「加密成功」不能证明密钥正确；必须拿历史密文试解一次。
    返回 (ok, 说明)。没有任何样本时返回 ok=True（无从校验，放行）。
    """
    aes = AESGCM(key)
    used = []
    for rel in VERIFY_SAMPLES:
        p = _sample_blob(rel)
        if not p:
            continue
        blob = open(p, "rb").read()
        if len(blob) <= 28:
            continue
        try:
            aes.decrypt(blob[:12], blob[12:], None)
        except Exception:
            return False, (f"{rel}（{os.path.relpath(p, BASE)}）解密失败 InvalidTag → "
                           f"当前密钥与仓库密文不是同一把")
        used.append(rel)
    if not used:
        return True, "无密文样本，跳过密钥比对"
    return True, f"指纹 {key_fp(key)}，已验 {len(used)} 个样本（{', '.join(used)}）"


def cmd_verify_key() -> int:
    key = load_key()
    ok, msg = verify_key(key)
    if not ok:
        print(f"✗ 密钥校验失败：{msg}")
        print("  排查：① GitHub Secret DDB_DATA_KEY 是否为本机 .secret/keys.json 里的 data_key "
              "② 是否带多余空白/换行 ③ 轮换后 Secret 是否已更新")
        return 1
    print(f"✓ 密钥可用：{msg}")
    return 0


def resolve() -> list[str]:
    """返回 deploy 下实际存在的受保护文件（相对路径）"""
    out = []
    for rel in PROTECTED:
        if os.path.exists(os.path.join(DEPLOY, rel)):
            out.append(rel)
    odir = os.path.join(DEPLOY, "output")
    if os.path.isdir(odir):
        for name in sorted(os.listdir(odir)):
            if not name.endswith(".json"):
                continue
            if any(name.startswith(p) for p in PATTERNS):
                rel = f"output/{name}"
                if rel not in out:
                    out.append(rel)
    return out


def enc_path(rel: str) -> str:
    return os.path.join(DEPLOY, rel + ENC_SUFFIX)


def resolve_expected() -> list[str]:
    """应受保护的完整清单：deploy 下存在**明文或密文**即计入。

    与 resolve() 的区别：resolve() 只返回「当前有明文的」（加密源）；
    本函数用于清单与校验，**口径只增不减**——否则一旦明文被 purge，
    清单就会缩水，--check 的检查面静默变小（静默失效家族）。
    """
    out = []
    for rel in PROTECTED:
        if os.path.exists(os.path.join(DEPLOY, rel)) or os.path.exists(enc_path(rel)):
            out.append(rel)
    odir = os.path.join(DEPLOY, "output")
    if os.path.isdir(odir):
        for name in sorted(os.listdir(odir)):
            base = name[:-len(ENC_SUFFIX)] if name.endswith(ENC_SUFFIX) else name
            if not base.endswith(".json"):
                continue
            if any(base.startswith(p) for p in PATTERNS):
                rel = f"output/{base}"
                if rel not in out:
                    out.append(rel)
    return out


def seal(key: bytes, data: bytes) -> bytes:
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, data, None)


def unseal(key: bytes, blob: bytes) -> bytes:
    return AESGCM(key).decrypt(blob[:12], blob[12:], None)


def cmd_list() -> int:
    files = resolve()
    print(f"受保护文件 {len(files)} 个（deploy/ 下实际存在）\n")
    total = 0
    for rel in files:
        p = os.path.join(DEPLOY, rel)
        size = os.path.getsize(p)
        total += size
        has_enc = "✓" if os.path.exists(enc_path(rel)) else "·"
        print(f"  [{has_enc}] {size / 1048576:8.2f} MB  {rel}")
    print(f"\n合计明文 {total / 1048576:.1f} MB")
    return 0


def cmd_encrypt(purge: bool) -> int:
    key = load_key()
    # 🔴 fail-closed：先证明这把钥能解历史密文，再拿它加密。
    #    否则错钥（Secret 粘错/轮换未同步）会把全部数据重新加密成谁也解不开的垃圾，
    #    而且加密过程本身不报错 → 站点静默变空（不报错不空白家族）。
    ok, msg = verify_key(key)
    if not ok:
        print(f"✗ 拒绝加密：{msg}")
        print("  已中止，未改动任何文件。修好密钥后重跑（或改用 tool/protect_assets.py --rotate-key）。")
        return 2
    files = resolve()
    if not files:
        print("⚠️  清单为空（deploy/ 下未找到受保护文件）")
        return 0
    n_enc = 0
    for rel in files:
        p = os.path.join(DEPLOY, rel)
        with open(p, "rb") as f:
            data = f.read()
        blob = seal(key, data)
        with open(enc_path(rel), "wb") as f:
            f.write(blob)
        n_enc += 1
        if purge:
            os.remove(p)
        print(f"  🔒 {rel} → {rel}{ENC_SUFFIX} ({len(blob)} B)"
              + ("  明文已删" if purge else ""))
    # 落清单：既是 --check 的权威依据，也让「今天该有哪些文件」可审计
    # 口径用 resolve_expected()（明文或密文皆计）——只增不减，避免 purge 后清单缩水
    expected = resolve_expected() or files
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump({"v": 1, "count": len(expected), "files": expected}, f,
                  indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"🧾 受保护清单 → {os.path.relpath(MANIFEST, BASE)}（{len(expected)} 条）")
    if len(expected) < len(files):
        print(f"   ⚠️  清单 {len(expected)} 条 < 本次加密 {len(files)} 条，请检查 resolve_expected()")
    print(f"\n✅ 已加密 {n_enc} 个文件" + ("，明文已移除" if purge else "（明文保留）"))
    return 0


def manifest_files() -> list[str]:
    """受保护清单：以 protected.json 为权威，缺失时回退到扫描结果"""
    if os.path.exists(MANIFEST):
        try:
            return json.load(open(MANIFEST, encoding="utf-8"))["files"]
        except Exception:
            pass
    return resolve()


# 发布到站点根时优先采用 deploy 精简版的例外。
# 根目录 signals.json 历史上存在「未 slim 的全量」（18MB），直接加密会把体积带进线上，
# 因此固定取 deploy 侧的精简密文。
PREFER_DEPLOY = {"signals.json"}


def cmd_sync_root() -> int:
    """把密文同步到站点根目录并删除根目录明文。

    背景：GitHub Pages 服务的是 main 分支根目录，deploy/ 只是构建产物，
    发布时必须把 *.enc 与 auth/ 同步上去，否则：
      ① 根目录明文仍可被直取（保护形同虚设）
      ② 根 index.html 的拦截层改写请求为 *.enc 后 404（页面数据全空）
    """
    key = load_key()
    files = manifest_files()
    if not files:
        print("⚠️  受保护清单为空，跳过根目录同步")
        return 1
    n_use = n_re = n_del = 0
    for rel in files:
        rootp = os.path.join(BASE, rel)
        root_enc = rootp + ENC_SUFFIX
        dep_enc = enc_path(rel)
        os.makedirs(os.path.dirname(rootp) or BASE, exist_ok=True)

        use_deploy = rel in PREFER_DEPLOY and os.path.exists(dep_enc)
        if os.path.exists(rootp) and not use_deploy:
            blob = seal(key, open(rootp, "rb").read())
            with open(root_enc, "wb") as f:
                f.write(blob)
            if not os.path.exists(dep_enc):       # deploy 侧缺失则补齐，保持两侧同源
                with open(dep_enc, "wb") as f:
                    f.write(blob)
            n_re += 1
        elif os.path.exists(dep_enc):
            shutil.copy2(dep_enc, root_enc)
            n_use += 1
        else:
            print(f"  ❌ {rel}: 根目录与 deploy 均无源文件，无法发布")
            return 1

        if os.path.exists(rootp):
            os.remove(rootp)
            n_del += 1

    auth_src = os.path.join(DEPLOY, "auth")
    if os.path.isdir(auth_src):
        auth_dst = os.path.join(BASE, "auth")
        os.makedirs(auth_dst, exist_ok=True)
        for name in sorted(os.listdir(auth_src)):
            shutil.copy2(os.path.join(auth_src, name), os.path.join(auth_dst, name))

    print(f"📤 根目录同步完成：沿用 deploy {n_use} · 重加密 {n_re} · 删除明文 {n_del} · auth 已同步")
    remain = [r for r in files if os.path.exists(os.path.join(BASE, r))]
    if remain:
        print(f"❌ 仍有 {len(remain)} 个明文残留：{remain[:5]}")
        return 1
    return 0


def cmd_stage_plain() -> int:
    """为本地门禁临时把受保护文件解密到工作区（跑完必须 --unstage-plain）。

    必要性：14 道门禁直接 open() 根目录文件。明文下线后，部分门禁会因文件缺失
    而**静默跳过**（空转通过）——比报错更危险。此命令让门禁看到与改造前一致的环境。
    """
    key = load_key()
    files = manifest_files()
    n = 0
    for rel in files:
        src = os.path.join(DEPLOY, rel + ENC_SUFFIX)
        if not os.path.exists(src):
            continue
        plain = unseal(key, open(src, "rb").read())
        # 根目录 + deploy 双侧都要还原：门禁多在比对「root ↔ deploy 副本」
        for dst in (os.path.join(BASE, rel), os.path.join(DEPLOY, rel)):
            os.makedirs(os.path.dirname(dst) or BASE, exist_ok=True)
            with open(dst, "wb") as f:
                f.write(plain)
        n += 1
    print(f"🔓 已解密 {n} 个受保护文件到工作区（root + deploy，仅供门禁，勿提交）")
    return 0


def cmd_unstage_plain() -> int:
    """删除上一步解密出来的明文，恢复密文态"""
    files = manifest_files()
    n = 0
    for rel in files:
        for dst in (os.path.join(BASE, rel), os.path.join(DEPLOY, rel)):
            if os.path.exists(dst + ENC_SUFFIX) and os.path.exists(dst):
                os.remove(dst)
                n += 1
    print(f"🔒 已清除 {n} 个临时明文（root + deploy）")
    return 0


def cmd_cat(rel: str) -> int:
    """把单个受保护文件的内容写到 stdout（明文优先，否则解 .enc）。

    用途：门禁 / CI 判断类步骤需要读产物里的字段（如 signals.json 的
    freshness.latest_data_date），而明文已下线。**只读、不落盘**，
    避免为了读一个日期把整份明文重新展开（静默失效面最小化）。
    """
    cand = [os.path.join(DEPLOY, rel), os.path.join(BASE, rel)]
    for p in cand:
        if os.path.exists(p):
            with open(p, "rb") as f:
                sys.stdout.buffer.write(f.read())
            return 0
    for p in [c + ENC_SUFFIX for c in cand]:
        if os.path.exists(p):
            with open(p, "rb") as f:
                sys.stdout.buffer.write(unseal(load_key(), f.read()))
            return 0
    print(f"✗ 找不到 {rel} 的明文或密文", file=sys.stderr)
    return 1


def cmd_check() -> int:
    """校验（不可空转）：
      ① 清单内每个文件必须存在 .enc
      ② deploy 下不得残留任何受保护明文
      校验对象来自上次加密写下的受保护清单（manifest.json）。
    """
    bad = []

    # ① 依据 manifest（加密时落下的权威清单）
    listed = []
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as f:
            listed = json.load(f).get("files", [])
    if not listed:
        bad.append("受保护清单缺失或为空（未执行过 --encrypt，或清单被删）")

    # 清单可能因历史原因缩水 → 与 expected 合并后再校验，保证检查面不被缩小
    listed = sorted(set(listed) | set(resolve_expected()))

    for rel in listed:
        if not os.path.exists(enc_path(rel)):
            bad.append(f"{rel}: 缺少 {rel}{ENC_SUFFIX}")
        if os.path.exists(os.path.join(DEPLOY, rel)):
            bad.append(f"{rel}: 明文仍在")

    # ② 兜底扫描：清单 + 通配范围内的明文一律视为泄漏
    odir = os.path.join(DEPLOY, "output")
    plain_hits = []
    for rel in PROTECTED:
        p = os.path.join(DEPLOY, rel)
        if os.path.exists(p):
            plain_hits.append(rel)
    if os.path.isdir(odir):
        for name in os.listdir(odir):
            if name.endswith(".json") and any(name.startswith(x) for x in PATTERNS):
                plain_hits.append(f"output/{name}")
    for h in sorted(set(plain_hits)):
        msg = f"{h}: 明文残留（未 purge）"
        if msg not in bad:
            bad.append(msg)

    if bad:
        print("❌ 校验未通过：")
        for b in bad:
            print("   ·", b)
        return 1
    print(f"✅ 校验通过：{len(listed)} 个受保护文件均为密文，且 deploy 下无受保护明文")
    return 0


def cmd_decrypt(outdir: str) -> int:
    key = load_key()
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for root, dirs, names in os.walk(DEPLOY):
        # auth/ 下是凭据（accounts.enc 由 DK_ADMIN 加密），不属数据资产
        dirs[:] = [d for d in dirs if os.path.join(root, d) != os.path.join(DEPLOY, "auth")]
        for name in names:
            if not name.endswith(ENC_SUFFIX):
                continue
            src = os.path.join(root, name)
            rel = os.path.relpath(src, DEPLOY)[: -len(ENC_SUFFIX)]
            dst = os.path.join(outdir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, "rb") as f:
                blob = f.read()
            with open(dst, "wb") as f:
                f.write(unseal(key, blob))
            n += 1
    print(f"✅ 已解密 {n} 个文件 → {outdir}")
    return 0


def cmd_rotate_key(admin_pw: str, vip_pw: str) -> int:
    """轮换 data_key：解全部密文 → 换新密钥重加密 → 重包装凭据 → 同步根目录。

    用途：密钥疑似泄露时彻底作废旧加密口令（不是改密码，是换数据密钥）。
    失败安全：先把全部明文落到临时目录，任何一步失败都能据此重建。
    """
    import time
    import tempfile

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ddb_auth as A

    if os.environ.get("DDB_DATA_KEY", "").strip():
        print("❌ 环境变量 DDB_DATA_KEY 非空：rotate 会读错密钥，请先 unset")
        return 1
    if not admin_pw or not vip_pw:
        print("❌ 需同时提供 --admin-password 与 --vip-password（重包装凭据必须解 KEK）")
        return 1

    old = load_key()
    files = resolve_expected()
    if not files:
        print("⚠️  受保护清单为空，中止")
        return 1

    staging = tempfile.mkdtemp(prefix="ddb_rotate_")
    plain: dict[str, bytes] = {}
    for rel in files:
        p = enc_path(rel)
        if not os.path.exists(p):
            print(f"❌ 缺少密文 deploy/{rel}{ENC_SUFFIX}，中止（未做任何修改）")
            return 1
        with open(p, "rb") as f:
            data = unseal(old, f.read())
        plain[rel] = data
        with open(os.path.join(staging, rel.replace("/", "__")), "wb") as f:
            f.write(data)
    print(f"🔓 已解密 {len(plain)} 个文件（暂存 {staging}，失败可据此重建）")

    new = os.urandom(32)
    for rel, data in plain.items():
        with open(enc_path(rel), "wb") as f:
            f.write(seal(new, data))
    print(f"🔐 已用新密钥重加密 {len(plain)} 个文件")

    keys = A.load_keys()
    keys["data_key"] = base64.b64encode(new).decode()
    keys["rotated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    for level, pw in (("admin", admin_pw), ("vip", vip_pw)):
        old_cred = A.read_cred(level)
        cred = A.build_cred(level, pw, keys, old_cred.get("exp"))
        A.write_json(os.path.join(A.AUTH_DIR, f"{level}.json"), cred)
        print(f"🔑 auth/{level}.json 已重包装（salt 重随机）")
    A.write_accounts(keys, vip_exp=A.read_cred("vip").get("exp"),
                     updated=keys["rotated"])
    A.save_keys(keys)

    if cmd_sync_root() != 0:
        print("❌ 根目录同步失败，但 deploy 侧已换新密钥；修复后重跑 --sync-root")
        return 1

    out = os.path.join(BASE, ".secret", "NEW_DATA_KEY.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(base64.b64encode(new).decode() + "\n")
    os.chmod(out, 0o600)
    print(f"\n🆕 新 DDB_DATA_KEY → {os.path.relpath(out, BASE)}（chmod 600）")
    print("   取完填 GitHub Secret 后请删除该文件；旧密钥已完全失效")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="核心资产加密 / 校验")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--encrypt", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--cat", metavar="REL", help="输出单个受保护文件内容（明文优先，否则解 .enc）")
    g.add_argument("--decrypt", metavar="DIR")
    g.add_argument("--sync-root", dest="sync_root", action="store_true")
    g.add_argument("--verify-key", dest="verify_key", action="store_true",
                   help="校验当前密钥能否解密仓库现有密文（不写文件）")
    g.add_argument("--stage-plain", dest="stage_plain", action="store_true")
    g.add_argument("--unstage-plain", dest="unstage_plain", action="store_true")
    g.add_argument("--rotate-key", dest="rotate_key", action="store_true",
                   help="轮换 data_key（需 --admin-password / --vip-password）")
    ap.add_argument("--admin-password", dest="admin_password")
    ap.add_argument("--vip-password", dest="vip_password")
    ap.add_argument("--purge", action="store_true", help="加密后删除明文")
    a = ap.parse_args()

    if a.list:
        sys.exit(cmd_list())
    if a.encrypt:
        sys.exit(cmd_encrypt(a.purge))
    if a.check:
        sys.exit(cmd_check())
    if a.cat:
        sys.exit(cmd_cat(a.cat))
    if a.decrypt:
        sys.exit(cmd_decrypt(a.decrypt))
    if a.sync_root:
        sys.exit(cmd_sync_root())
    if a.verify_key:
        sys.exit(cmd_verify_key())
    if a.stage_plain:
        sys.exit(cmd_stage_plain())
    if a.unstage_plain:
        sys.exit(cmd_unstage_plain())
    if a.rotate_key:
        sys.exit(cmd_rotate_key(a.admin_password, a.vip_password))


if __name__ == "__main__":
    main()
