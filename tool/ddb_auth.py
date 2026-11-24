#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兜是宝 · 真鉴权密钥体系（AES-GCM + PBKDF2 密钥包装）

设计要点
--------
1. 密码**不入前端**：只公开 salt / iter / verifier / 包装后的密文。
2. **密钥包装**：数据用 DK_DATA 加密；DK_DATA 由各级密码派生的 KEK 包裹。
   → 改密码只重算 wrapped_key（毫秒级），**无需重新加密数据**。
3. 两级密钥：
   - DK_DATA  ：核心数据加密（admin / vip 均可解出）
   - DK_ADMIN ：管理员专属（账号表 accounts.enc）
4. 密码正确性校验 = 用 KEK 解 verifier，明文须等于 `ddb-auth-v1|<level>`。
   不做哈希比对，避免"离线撞库先验"少一层成本。

用法
----
  python tool/ddb_auth.py init                       # 生成密钥 + admin/vip 凭据
  python tool/ddb_auth.py rekey --level vip          # 改 VIP 密码（其它不变）
  python tool/ddb_auth.py set-exp --level vip --exp 2026-12-15
  python tool/ddb_auth.py accounts                   # 重新生成 accounts.enc
  python tool/ddb_auth.py print-env                  # 输出 CI 用 secret 值
  python tool/ddb_auth.py verify                     # 校验凭据自洽性

密钥存放：.secret/keys.json（已 gitignore，**绝不入库**）
"""
import argparse
import base64
import json
import os
import secrets
import sys
from datetime import datetime, timezone, timedelta

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 凭据必须位于站点根（GitHub Pages 根 = deploy/）才能被前端 fetch
AUTH_DIR = os.path.join(BASE, "deploy", "auth")
SECRET_DIR = os.path.join(BASE, ".secret")
KEYS_FILE = os.path.join(SECRET_DIR, "keys.json")

ITER = 310_000
KDF = "PBKDF2-SHA256"
CST = timezone(timedelta(hours=8))

# 弱密码阈值：低于此长度时明确警告（不阻断，用户可自行决定）
WEAK_LEN = 8


# ── 基础工具 ────────────────────────────────────────────────
def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode()


def b64d(s: str) -> bytes:
    return base64.b64decode(s)


def derive_kek(password: str, salt: bytes, iterations: int) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=iterations)
    return kdf.derive(password.encode("utf-8"))


def seal(key: bytes, plaintext: bytes) -> str:
    """AES-GCM 封装，输出 b64(nonce12 || ciphertext||tag)"""
    nonce = secrets.token_bytes(12)
    return b64e(nonce + AESGCM(key).encrypt(nonce, plaintext, None))


def unseal(key: bytes, blob: str) -> bytes:
    raw = b64d(blob)
    return AESGCM(key).decrypt(raw[:12], raw[12:], None)


def load_keys() -> dict:
    if not os.path.exists(KEYS_FILE):
        sys.exit(f"✗ 缺少 {KEYS_FILE}，请先执行: python tool/ddb_auth.py init")
    with open(KEYS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_keys(d: dict) -> None:
    os.makedirs(SECRET_DIR, exist_ok=True)
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    os.chmod(KEYS_FILE, 0o600)


def read_cred(level: str) -> dict:
    p = os.path.join(AUTH_DIR, f"{level}.json")
    if not os.path.exists(p):
        sys.exit(f"✗ 缺少 {p}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def warn_weak(level: str, password: str) -> None:
    if len(password) < WEAK_LEN:
        print(f"  ⚠️  {level} 密码仅 {len(password)} 位（< {WEAK_LEN}）。"
              f"\n      密码强度 = 数据加密强度；短密码可被离线暴力破解，建议 12 位以上。")


# ── 凭据构建 ────────────────────────────────────────────────
def build_cred(level: str, password: str, keys: dict, exp: str | None,
               salt: bytes | None = None, iterations: int = ITER) -> dict:
    salt = salt or secrets.token_bytes(16)
    kek = derive_kek(password, salt, iterations)
    cred = {
        "v": 1,
        "level": level,
        "kdf": KDF,
        "iter": iterations,
        "salt": b64e(salt),
        "verifier": seal(kek, f"ddb-auth-v1|{level}".encode()),
        "wrap_data": seal(kek, b64d(keys["data_key"])),
    }
    if level == "admin":
        cred["wrap_admin"] = seal(kek, b64d(keys["admin_key"]))
    if exp:
        cred["exp"] = exp
    return cred


def norm_exp(s: str | None) -> str | None:
    """把 2026-12-15 规范为 2026-12-15T23:59:59+08:00"""
    if not s:
        return None
    s = s.strip()
    if len(s) == 10:
        return f"{s}T23:59:59+08:00"
    return s


# ── 子命令 ──────────────────────────────────────────────────
def cmd_init(args) -> None:
    if os.path.exists(KEYS_FILE) and not args.force:
        sys.exit(f"✗ {KEYS_FILE} 已存在。重建会令既有密文与凭据全部失效，"
                 f"确需重建请加 --force")

    keys = {
        "v": 1,
        "created": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S"),
        "data_key": b64e(secrets.token_bytes(32)),
        "admin_key": b64e(secrets.token_bytes(32)),
    }
    save_keys(keys)
    print(f"✅ 已生成密钥 → {KEYS_FILE}")
    print(f"   DK_DATA  = {keys['data_key']}")
    print(f"   DK_ADMIN = {keys['admin_key']}")

    admin_pw = args.admin_password or input("管理员密码: ").strip()
    vip_pw = args.vip_password or input("VIP 密码: ").strip()
    if not admin_pw or not vip_pw:
        sys.exit("✗ 密码不能为空")
    warn_weak("管理员", admin_pw)
    warn_weak("VIP", vip_pw)

    admin = build_cred("admin", admin_pw, keys, None)
    vip = build_cred("vip", vip_pw, keys, norm_exp(args.vip_exp))
    write_json(os.path.join(AUTH_DIR, "admin.json"), admin)
    write_json(os.path.join(AUTH_DIR, "vip.json"), vip)
    print(f"✅ 凭据 → auth/admin.json、auth/vip.json（VIP 到期 {vip.get('exp')}）")

    write_accounts(keys, vip_exp=vip.get("exp"), updated=keys["created"])


def cmd_rekey(args) -> None:
    keys = load_keys()
    level = args.level
    old = read_cred(level)
    pw = args.password or input(f"{level} 新密码: ").strip()
    if not pw:
        sys.exit("✗ 密码不能为空")
    warn_weak(level, pw)
    exp = args.exp if args.exp is not None else old.get("exp")
    cred = build_cred(level, pw, keys, norm_exp(exp))
    write_json(os.path.join(AUTH_DIR, f"{level}.json"), cred)
    print(f"✅ 已更新 auth/{level}.json（salt 重新随机，旧密码立即失效；数据密文无需重加密）")
    if level == "vip":
        write_accounts(keys, vip_exp=cred.get("exp"), updated=now_str())


def cmd_set_exp(args) -> None:
    """只改到期日：保持 salt/密码不变，仅重写 exp 字段"""
    level = args.level
    cred = read_cred(level)
    cred["exp"] = norm_exp(args.exp)
    write_json(os.path.join(AUTH_DIR, f"{level}.json"), cred)
    print(f"✅ auth/{level}.json 到期日 → {cred['exp']}")
    if level == "vip":
        keys = load_keys()
        write_accounts(keys, vip_exp=cred["exp"], updated=now_str())


def cmd_accounts(args) -> None:
    keys = load_keys()
    vip = read_cred("vip")
    write_accounts(keys, vip_exp=vip.get("exp"), updated=now_str())


def write_accounts(keys: dict, vip_exp: str | None, updated: str) -> None:
    table = {
        "v": 1,
        "updated": updated,
        "accounts": [
            {"level": "admin", "label": "管理员", "exp": None,
             "note": "全量权限 + 账号管理"},
            {"level": "vip", "label": "VIP", "exp": vip_exp,
             "note": "受限 tab + 投喂锁定"},
        ],
    }
    blob = seal(b64d(keys["admin_key"]), json.dumps(table, ensure_ascii=False).encode())
    write_json(os.path.join(AUTH_DIR, "accounts.enc"), {"v": 1, "blob": blob})
    print(f"✅ auth/accounts.enc（DK_ADMIN 加密 · {len(table['accounts'])} 条）")


def cmd_print_env(args) -> None:
    keys = load_keys()
    print("# 一次性配置到 GitHub → Settings → Secrets and variables → Actions")
    print(f"DDB_DATA_KEY={keys['data_key']}")
    print(f"DDB_ADMIN_KEY={keys['admin_key']}")


def cmd_verify(args) -> None:
    """自洽性校验：各级凭据能否解出与 keys.json 一致的 dataKey"""
    keys = load_keys()
    ok = True
    for level in ("admin", "vip"):
        p = os.path.join(AUTH_DIR, f"{level}.json")
        if not os.path.exists(p):
            print(f"  ⚠️  {level}: 凭据缺失")
            ok = False
            continue
        cred = read_cred(level)
        pw = getattr(args, f"{level}_password", None)
        if not pw:
            print(f"  ⏭️  {level}: 未提供密码，跳过解密校验")
            continue
        kek = derive_kek(pw, b64d(cred["salt"]), cred["iter"])
        try:
            vp = unseal(kek, cred["verifier"])
            assert vp == f"ddb-auth-v1|{level}".encode(), "verifier 明文不匹配"
            dk = unseal(kek, cred["wrap_data"])
            assert b64e(dk) == keys["data_key"], "dataKey 不一致"
            extra = ""
            if level == "admin":
                ak = unseal(kek, cred["wrap_admin"])
                assert b64e(ak) == keys["admin_key"], "adminKey 不一致"
                extra = " + adminKey"
            print(f"  ✅ {level}: verifier / dataKey{extra} 全部匹配 · 到期 {cred.get('exp') or '不限'}")
        except Exception as e:
            print(f"  ❌ {level}: {type(e).__name__} — {e}")
            ok = False
    sys.exit(0 if ok else 1)


def now_str() -> str:
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")


def main() -> None:
    ap = argparse.ArgumentParser(description="兜是宝真鉴权密钥体系")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="生成密钥与凭据")
    p.add_argument("--admin-password")
    p.add_argument("--vip-password")
    p.add_argument("--vip-exp", default="2026-12-15")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("rekey", help="改密码（只重包，不重加密数据）")
    p.add_argument("--level", choices=["admin", "vip"], required=True)
    p.add_argument("--password")
    p.add_argument("--exp", default=None)
    p.set_defaults(func=cmd_rekey)

    p = sub.add_parser("set-exp", help="改到期日")
    p.add_argument("--level", choices=["admin", "vip"], default="vip")
    p.add_argument("--exp", required=True)
    p.set_defaults(func=cmd_set_exp)

    p = sub.add_parser("accounts", help="重建 accounts.enc")
    p.set_defaults(func=cmd_accounts)

    p = sub.add_parser("print-env", help="输出 CI secret")
    p.set_defaults(func=cmd_print_env)

    p = sub.add_parser("verify", help="自洽性校验")
    p.add_argument("--admin-password")
    p.add_argument("--vip-password")
    p.set_defaults(func=cmd_verify)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
