#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task-retro-confirm 生成器 v2

读取 items.json → 注入 references/skeleton.html 的三个占位符
（__TITLE__ / __LEAD__ / __DATA__），产出自包含、零依赖、可离线的复盘确认页。

v2 新增闸门自检：
  - 有效做法 ≤3、弯路 ≤2、合计 ≤5（超限告警，不阻断）
  - findings / items 缺 evidence 告警
  - confidence=low 的项自动剔除（不渲染进页面）
  - 根因不在四类白名单内告警

用法：
  python gen_retro.py <items.json> <output.html>          # 生成
  python gen_retro.py <items.json> --check                # 只校验不生成
仅依赖标准库。
"""
import json
import os
import sys

VALID_ROOT_CAUSE = ("信息缺失", "判断错误", "执行失误", "工具缺陷")
VALID_TYPE = ("memory", "skill", "prompt", "manual")
VALID_CONF = ("high", "medium", "low")
VALID_SCOPE = ("single", "recurring", "cross")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_gates(data):
    """执行闸门校验，返回 (errors, warnings, filtered_items, dropped_ids)。"""
    errors, warns, dropped = [], [], []
    findings = data.get("findings") or {}
    raw_items = data.get("items") or []

    # ---- 1. 条数闸 ----
    # 口径：firstStep 在成品笔记里本身就是一条（图片 2 模板的第 3 条），必须计入总数
    worked = findings.get("worked") or []
    detours = findings.get("detours") or []
    has_first = bool(str(findings.get("firstStep") or "").strip())
    if len(worked) > 3:
        warns.append("有效做法 %d 条，超过上限 3 条 —— 只留有结果支撑的" % len(worked))
    if len(detours) > 2:
        warns.append("弯路 %d 条，超过上限 2 条 —— 合并同类项或拆成两次复盘" % len(detours))
    body = len(worked) + len(detours)
    total = body + (1 if has_first else 0)
    if total > 5:
        warns.append("笔记合计 %d 条（含「下次第一步」1 条），超过 5 条上限 —— "
                     "做法+弯路合计须 ≤4；装不下说明该拆成两次复盘" % total)

    # ---- 2. 证据闸 ----
    for i, w in enumerate(worked):
        if not (w.get("evidence") or "").strip():
            warns.append("有效做法 #%d 缺 evidence —— 无结果支撑的做法不算发现" % (i + 1))
    if findings.get("firstStep") is not None and not str(findings.get("firstStep") or "").strip():
        warns.append("firstStep 为空 —— 缺迁移层，复盘停在纸面")

    # ---- 3. 根因白名单 ----
    for i, d in enumerate(detours):
        rc = (d.get("rootCause") or "").strip()
        if not rc:
            warns.append("弯路 #%d 未标 rootCause —— 无归因就无法对策" % (i + 1))
        elif rc not in VALID_ROOT_CAUSE:
            warns.append("弯路 #%d 根因「%s」不在四类白名单（%s）—— 换成可对策的归类"
                         % (i + 1, rc, " / ".join(VALID_ROOT_CAUSE)))

    # ---- 4. 候选字段完整性 + 低把握度剔除 ----
    kept = []
    for it in raw_items:
        iid = it.get("id") or "?"
        t = it.get("type")
        conf = it.get("confidence", "high")

        if t not in VALID_TYPE:
            errors.append("候选 %s 的 type「%s」非法（须为 %s）" % (iid, t, " / ".join(VALID_TYPE)))
            continue
        if conf not in VALID_CONF:
            warns.append("候选 %s 的 confidence「%s」非法，按 medium 处理" % (iid, conf))
            conf = "medium"
            it["confidence"] = conf
        if not (it.get("prompt") or "").strip():
            errors.append("候选 %s 缺 prompt —— 无提示词的候选不可执行" % iid)
            continue
        if it.get("scope") and it["scope"] not in VALID_SCOPE:
            warns.append("候选 %s 的 scope「%s」非法（须为 single / recurring / cross）"
                         % (iid, it["scope"]))

        if conf == "low":
            warns.append("候选 %s 把握度 low，已自动剔除（不入页）" % iid)
            dropped.append(iid)
            continue
        if not (it.get("evidence") or "").strip():
            warns.append("候选 %s 缺 evidence —— 页面会显示为无依据项" % iid)
        kept.append(it)

    # ---- 5. 范围闸：single 场景下 limit ----
    if data.get("scope") == "single" and len(kept) > 1:
        non_prompt = [k for k in kept if k["type"] != "prompt"]
        if non_prompt:
            warns.append(
                "scope=single（单次任务）却有 %d 条非提示词类沉淀 —— 单次经验写进长期记忆是污染源"
                % len(non_prompt))

    # ---- 6. variants 完整性 ----
    v = data.get("variants")
    if v:
        if not (v.get("verdict") or "").strip():
            warns.append("差异对比台缺 verdict —— 没有结论的对比等于没做")
        dims = v.get("dims") or []
        for row in (v.get("list") or []):
            sc = row.get("scores") or []
            if dims and len(sc) != len(dims):
                warns.append("对比行「%s」有 %d 个值，但维度有 %d 个 —— 请对齐"
                             % (row.get("name", "?"), len(sc), len(dims)))

    return errors, warns, kept, dropped


def print_report(errors, warns, kept, total_raw):
    print("=" * 62)
    print("闸门自检")
    print("=" * 62)
    if errors:
        for e in errors:
            print("  [ERROR] " + e)
    if warns:
        for w in warns:
            print("  [WARN ] " + w)
    if not errors and not warns:
        print("  全部通过。")
    print("-" * 62)
    print("候选：%d 条入页 / %d 条原始（剔除 %d）"
          % (len(kept), total_raw, total_raw - len(kept)))
    print("=" * 62)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check_only = "--check" in sys.argv

    if not args:
        print("Usage: gen_retro.py <items.json> <output.html>")
        print("       gen_retro.py <items.json> --check")
        sys.exit(1)

    data_path = args[0]
    if not os.path.isfile(data_path):
        print("ERROR: items.json 不存在: %s" % data_path)
        sys.exit(1)

    data = load_json(data_path)
    errors, warns, kept, dropped = run_gates(data)
    print_report(errors, warns, kept, len(data.get("items") or []))

    if errors:
        print("存在 ERROR，未生成页面。请修正后重试。")
        sys.exit(2)

    if check_only:
        print("（--check 模式，未写文件）")
        sys.exit(0)

    if len(args) < 2:
        print("ERROR: 缺少输出路径")
        sys.exit(1)
    out_path = args[1]

    skill_dir = os.path.dirname(os.path.abspath(__file__))
    skeleton_path = os.path.join(skill_dir, "..", "references", "skeleton.html")
    with open(skeleton_path, "r", encoding="utf-8") as f:
        html = f.read()

    title = data.get("title", "任务复盘 · 待确认事项")
    lead = data.get("lead", "")

    # 用剔除 low 之后的 items 渲染
    payload = {
        "title": title,
        "task": data.get("task", ""),
        "scope": data.get("scope", ""),
        "findings": data.get("findings") or {},
        "variants": data.get("variants"),
        "items": kept,
        "droppedIds": dropped,
    }

    # 顺序：先替换文本占位符，最后注入 DATA（避免 JSON 内容被二次替换）
    html = html.replace("__TITLE__", title)
    html = html.replace("__LEAD__", lead)
    html = html.replace("__DATA__", json.dumps(payload, ensure_ascii=False))

    leftover = [t for t in ("__TITLE__", "__LEAD__", "__DATA__") if t in html]
    if leftover:
        print("WARN: 占位符未完全替换: %s" % leftover)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("WROTE %s  size=%d" % (out_path, len(html)))


if __name__ == "__main__":
    main()
