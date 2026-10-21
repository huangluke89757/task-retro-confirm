#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task-retro-confirm 生成器
读取 items.json（{title, lead, items:[{id,type,title,why,prompt}]}）
注入 references/skeleton.html 的 __TITLE__ / __LEAD__ / __DATA__ 占位符，
产出自包含、零依赖、可离线的「待确认事项」HTML。

用法：
  python gen_retro.py <items.json> <output.html>
仅依赖标准库。
"""
import json
import os
import sys


def main():
    if len(sys.argv) < 3:
        print("Usage: gen_retro.py <items.json> <output.html>")
        sys.exit(1)

    data_path = sys.argv[1]
    out_path = sys.argv[2]
    skill_dir = os.path.dirname(os.path.abspath(__file__))
    skeleton_path = os.path.join(skill_dir, "..", "references", "skeleton.html")

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(skeleton_path, "r", encoding="utf-8") as f:
        html = f.read()

    title = data.get("title", "任务复盘 · 待确认事项")
    lead = data.get("lead", "")
    payload = {"items": data.get("items", [])}

    # 顺序：先替换文本占位符，最后再注入 DATA（避免 JSON 内出现占位符被二次替换）
    html = html.replace("__TITLE__", title)
    html = html.replace("__LEAD__", lead)
    html = html.replace("__DATA__", json.dumps(payload, ensure_ascii=False))

    # 自检：不应残留任何占位符
    leftover = [t for t in ("__TITLE__", "__LEAD__", "__DATA__") if t in html]
    if leftover:
        print("WARN: 占位符未完全替换:", leftover)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("WROTE", out_path, "size=", len(html))


if __name__ == "__main__":
    main()
