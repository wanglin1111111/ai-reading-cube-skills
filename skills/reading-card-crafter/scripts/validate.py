#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reading-card-crafter 产出校验器。
检查小红书读书笔记物料的硬约束：标题字数、金句卡片字数、标签数量与结构、emoji 数量。
用法： python scripts/validate.py <产出文件.md>
退出码 0 = 全部通过；非 0 = 有问题（详见输出）。
"""
import re
import sys
from pathlib import Path

EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "\U0001F900-\U0001F9FF\U0001F000-\U0001F02F]",
)

TITLE_MAX = 20      # 标题 ≤20 字
CARD_MAX = 14       # 金句卡片封面文字 ≤14 字
TAG_MIN, TAG_MAX = 5, 8
EMOJI_MAX = 6       # 全文 emoji 克制（含标题/卡片里零星的，宽松上界）


def parse_sections(text):
    """按 ### / ## 标题切成 section dict。"""
    sections = {}
    current = None
    buf = []
    for line in text.splitlines():
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            if current:
                sections[current] = "\n".join(buf)
            current = m.group(2).strip()
            buf = []
        else:
            buf.append(line)
    if current:
        sections[current] = "\n".join(buf)
    return sections


def collect_titles(text):
    """收集所有形如 「① 标题」「1. 标题」「- 标题」的备选标题行（标题区）。"""
    titles = []
    for line in text.splitlines():
        s = line.strip()
        # 序号式：①②③ 或 1-5，后跟可选标点(.、．:：)) 再跟空白
        m = re.match(r"^([①②③④⑤1-5])[.、．:：)]?\s+(.+)$", s)
        if m:
            titles.append(m.group(2).strip())
        elif s.startswith("- ") and len(s) <= TITLE_MAX + 4:
            titles.append(s[2:].strip())
    return titles


def collect_cards(text):
    """收集「封面文字：xxx」的值。"""
    return [m.strip() for m in re.findall(r"封面文字[：:]\s*(.+)", text)]


def collect_tags(text):
    """收集 # 标签。"""
    return [t for t in re.findall(r"#[^\s#＃]{1,20}", text)]


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/validate.py <产出文件.md>")
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"✗ 文件不存在: {path}")
        return 2
    text = path.read_text(encoding="utf-8")
    problems = []

    # 标题
    titles = collect_titles(text)
    if len(titles) < 3:
        problems.append(f"标题备选不足 3 个（找到 {len(titles)} 个）")
    for t in titles:
        tlen = len(re.sub(r"\s+", "", t))
        if tlen > TITLE_MAX:
            problems.append(f"标题超长（{tlen}>{TITLE_MAX}）：{t}")

    # 金句卡片
    cards = collect_cards(text)
    for c in cards:
        clen = len(re.sub(r"\s+", "", c))
        if clen > CARD_MAX:
            problems.append(f"金句卡片封面文字超长（{clen}>{CARD_MAX}）：{c}")

    # 标签
    tags = collect_tags(text)
    if not (TAG_MIN <= len(tags) <= TAG_MAX):
        problems.append(f"标签数量 {len(tags)} 不在 {TAG_MIN}-{TAG_MAX} 区间")
    # 结构：至少含一个 #读书 类大类 + 一个书名（启发式：标签里至少 2 个非情绪词）
    if tags and len({t for t in tags}) < 3:
        problems.append("标签可能过于单一，检查四层结构是否齐全")

    # emoji
    emoji_count = len(EMOJI_RE.findall(text))
    if emoji_count > EMOJI_MAX:
        problems.append(f"emoji 偏多（{emoji_count}>{EMOJI_MAX}），建议克制")

    # 原文/提炼标注：含「封面文字」时，附近应能找到【原文】或【提炼】
    if cards:
        if "原文" not in text and "提炼" not in text:
            problems.append("金句卡片未标注【原文】/【提炼】")

    if problems:
        print("✗ 校验未通过：")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"✓ 通过：标题 {len(titles)} 个｜卡片 {len(cards)} 张｜标签 {len(tags)} 个｜emoji {emoji_count} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
