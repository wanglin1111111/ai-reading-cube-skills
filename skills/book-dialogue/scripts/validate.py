#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
book-dialogue 对话质量校验器。
检查一段对话记录是否符合本 Skill 的核心约束：
  - 首轮回应含至少一个"有信息量"的追问（启发式：含问号、且非空泛问句）
  - 回应不过载（单轮段落/字数不超阈值）
  - 未触发剧透高危信号（需配合"读者进度"标注判断，见下）
  - 涉及"作者意图"处带揣测口吻
  - 凭理解处留有讨论分寸

用法：
  python scripts/validate.py <对话记录.md> [--reader-progress "第N章"]

退出码 0 = 通过；非 0 = 有问题。
注：这是启发式检查，不能替代语义级人工复核——保真（是否臆造情节/原文）
仍需人工判断，脚本只抓可机检的格式信号。
"""
import argparse
import re
import sys
from pathlib import Path

# 空泛问句黑名单（这类追问被判为"零信息量"）
# 匹配时先去掉问句末尾标点，再判断"整句就是"或"以短语结尾"
VAGUE_PHRASES = ["你指什么", "你觉得呢", "你能详细说说吗", "怎么理解", "你怎么看呢"]

# 剧透高危词（出现时需结合读者进度复核）
SPOILER_HINTS = ["结局", "最后死了", "凶手是", "反转", "真相是", "原来他", "其实她最后"]

# 揣测口吻标志（出现"作者意图"附近应有这些）
HEDGE_MARKERS = ["我猜", "也许", "可能", "倾向于", "我的感觉", "我觉得作者", "或许", "讨论", "不是定论"]


def split_turns(text):
    """把对话记录按「Skill/回应」标记切成单轮。兼容多种分隔写法。"""
    # 用非捕获组，避免 re.split 把分隔内容插进结果
    turns = re.split(r"\n---+\n|\n【[^】]*轮[^】]*】\n|\n#{1,3}\s*(?:第.{1,3}轮|Skill.{0,4}回应)", text)
    out = []
    for t in turns:
        if t is None:
            continue
        s = t.strip()
        if s and len(s) > 20:
            out.append(s)
    return out


def find_questions(turn):
    """提取一个回合里的中文问句（以？/?结尾的句子）。"""
    sentences = re.split(r"[。\n！!？?]", turn)
    qs = []
    # 重新找带问号的片段
    for m in re.finditer(r"([^。！\n？?]{4,80}[？?])", turn):
        qs.append(m.group(1).strip())
    return qs


def is_vague(q):
    """问句去标点后，若整句就是空泛短语、或≤6字、或以空泛短语结尾，判为空泛。"""
    s = re.sub(r"[？?！!。.\s]+$", "", q).strip()
    if len(s) <= 6:
        return True
    return any(s == p or s.endswith(p) for p in VAGUE_PHRASES)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="对话记录 .md 文件")
    ap.add_argument("--reader-progress", default="", help="读者进度，如 '第3章'，用于剧透判断")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"✗ 文件不存在: {path}")
        return 2
    text = path.read_text(encoding="utf-8")
    problems = []

    turns = split_turns(text)
    if not turns:
        problems.append("未识别出任何对话回合（请用 --- 或【第N轮】分隔）")

    # 1. 首轮追问检查
    first = turns[0] if turns else text
    qs = find_questions(first)
    non_vague = [q for q in qs if not is_vague(q)]
    if not qs:
        problems.append("首轮回应未包含任何问句——违反'先问后答'原则")
    elif not non_vague:
        problems.append(f"首轮问句疑似空泛（{qs[:2]}），需带具体指向")

    # 2. 过载检查（逐轮）
    for i, t in enumerate(turns, 1):
        paras = [p for p in t.split("\n") if p.strip()]
        char_len = len(re.sub(r"\s+", "", t))
        if char_len > 600:
            problems.append(f"第{i}轮回应偏长（{char_len}字），可能过载、淹没读者思考")

    # 3. 剧透高危词（仅提示，需人工结合进度判断）
    spoiler_hits = [w for w in SPOILER_HINTS if w in text]
    if spoiler_hits and args.reader_progress:
        problems.append(f"出现剧透高危词 {spoiler_hits}——请人工复核是否超出读者进度({args.reader_progress})")
    elif spoiler_hits:
        problems.append(f"出现剧透高危词 {spoiler_hits}——建议带 --reader-progress 复核是否剧透")

    # 4. 作者意图揣测口吻
    if "作者" in text and "想" in text:
        if not any(h in text for h in HEDGE_MARKERS):
            problems.append("涉及'作者意图'但未见揣测口吻（我猜/也许/可能…），易把猜测说成定论")

    if problems:
        print("✗ 对话质量校验未通过：")
        for p in problems:
            print(f"  - {p}")
        print("\n注：本检查为启发式。语义保真（是否臆造情节/原文）仍需人工复核。")
        return 1
    print(f"✓ 通过：识别 {len(turns)} 轮｜首轮有效追问 {len(non_vague)} 个｜剧透高危词 {len(spoiler_hits)}")
    print("注：启发式通过 ≠ 内容保真，仍建议人工复核语义。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
