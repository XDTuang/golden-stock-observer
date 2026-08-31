#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
review/fix_html_comments.py —— HTML 注释闭合修复 + 校验

背景（2026-08-31 事故）：
  段落重写脚本用 replace_between(start_marker, end_marker, ...) 切段时，
  start_marker 只写了 '<!-- 0 结论先行'（不带 ' -->'），而拼接模板为
      repl = start_marker + new_inner + end_marker
  只补了 end_marker，漏了 start_marker 的 ' -->'，导致注释未闭合。
  未闭合的 '<!--' 会把后续内容一路吞到下一个 '-->'，
  表现为「整段在页面上消失」——0/0.5/1/4/5/7.1/7.3 段集体丢失。

本脚本提供：
  1. check()  —— 扫描所有未正确闭合的注释（只报「疑似锚点注释」，跳过合法多行注释）
  2. fix()    —— 给形如 '<!-- N 标题' 且未闭合的锚点注释补上 ' -->'
  3. main()   —— 默认先 check，有病则 fix，修完再 check 复验

用法：
  python3 review/fix_html_comments.py                    # 检查 + 修复（源文件 + deploy 副本）
  python3 review/fix_html_comments.py --check-only       # 只检查，不改文件
  python3 review/fix_html_comments.py -f path/to/a.html  # 指定文件
"""
import argparse
import os
import re
import sys

# 「锚点注释」特征：<!-- 紧跟 数字编号（可含小数点）+ 空格 + 标题文本
ANCHOR_RE = re.compile(r'^(\s*)<!--(\s*[0-9]+(?:\.[0-9]+)?\s+[^\n]*?)(\s*)$')

DEFAULT_FILES = [
    'data/daily_review/analysis.html',
    'deploy/data/daily_review/analysis.html',
]


def scan(path):
    """返回 (issues, total_anchors)
    issues: [(lineno, raw_line, swallow_end_lineno)] 未闭合的锚点注释
    """
    with open(path, encoding='utf-8') as f:
        text = f.read()
    lines = text.split('\n')

    # 预计算每行起始偏移
    offs, acc = [0], 0
    for ln in lines:
        acc += len(ln) + 1
        offs.append(acc)

    issues = []
    total = 0
    for i, ln in enumerate(lines, 1):
        m = ANCHOR_RE.match(ln)
        if not m:
            continue
        total += 1
        if ln.rstrip().endswith('-->'):
            continue
        # 未闭合，找吞噬终点
        pos = text.find('<!--', offs[i - 1])
        end = text.find('-->', pos)
        endline = text[:end].count('\n') + 1 if end != -1 else -1
        issues.append((i, ln.rstrip(), endline))
    return issues, total


def fix(path, dry=False):
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')

    fixed = []
    for i, ln in enumerate(lines, 1):
        m = ANCHOR_RE.match(ln)
        if m and not ln.rstrip().endswith('-->'):
            indent, body, tail = m.group(1), m.group(2), m.group(3)
            new = '%s<!--%s -->' % (indent, body.rstrip())
            fixed.append((i, ln.rstrip(), new))
            lines[i - 1] = new

    if fixed and not dry:
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    return fixed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-f', '--files', nargs='*', default=None,
                    help='指定要处理的文件（默认处理源 + deploy 副本）')
    ap.add_argument('--check-only', action='store_true', help='只检查不修改')
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = args.files or DEFAULT_FILES
    os.chdir(root)

    bad_total = 0
    for p in files:
        if not os.path.exists(p):
            print('⚠️  跳过（不存在）: %s' % p)
            continue
        issues, total = scan(p)
        print('\n── %s  （锚点 %d 个）' % (p, total))
        if not issues:
            print('   ✅ 注释闭合正常')
            continue
        bad_total += len(issues)
        for lineno, raw, endline in issues:
            print('   ❌ 行%-4d %r' % (lineno, raw[:56]))
            if endline != -1:
                print('             → 吞到第 %d 行，共 %d 行被吞掉'
                      % (endline, endline - lineno))
        if args.check_only:
            bad_total += len(issues)
            continue
        fixed = fix(p)
        print('   🔧 已修复 %d 处' % len(fixed))
        for lineno, old, new in fixed:
            print('       行%-4d %r → %r' % (lineno, old[:40], new[:56]))
        # 复验：只统计「修复后仍然残留」的问题
        again, _ = scan(p)
        if again:
            bad_total += len(again)
            print('   ❌ 仍有 %d 处未闭合' % len(again))
        else:
            print('   ✅ 复验通过（0 处残留）')

    print('\n' + '=' * 60)
    if bad_total:
        print('❌ 仍有 %d 处问题未解决' % bad_total)
        return 1
    print('✅ 全部文件的锚点注释均已正确闭合')
    return 0


if __name__ == '__main__':
    sys.exit(main())
