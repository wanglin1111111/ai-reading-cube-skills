#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
knowledge-alchemy 产出校验器。
检查卡片盒产出的结构约束：每张卡是否原子化（标题为命题）、是否有"我的复述"（非照抄）、
是否每张卡至少 1 条带关系类型的链接、是否有标签、是否有主题索引。
用法： python scripts/validate.py <产出文件.md>
退出码 0 = 全部通过；非 0 = 有问题（详见输出）。
"""
import re
import sys
from pathlib import Path


def split_cards(text):
    """按 ### 标题切出卡片块（标题行 + 直到下一个 ##/### 的内容）。"""
    cards = []
    current_title = None
    buf = []
    for line in text.splitlines():
        h3 = re.match(r"^###\s+(.*)$", line)
        h2 = re.match(r"^##\s+(.*)$", line)
        if h3:
            if current_title is not None:
                cards.append((current_title, "\n".join(buf)))
            current_title = h3.group(1).strip()
            buf = []
        elif h2:
            if current_title is not None:
                cards.append((current_title, "\n".join(buf)))
            current_title = None
            buf = []
        else:
            buf.append(line)
    if current_title is not None:
        cards.append((current_title, "\n".join(buf)))
    return cards


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

    cards = split_cards(text)
    # 只看带 [[...]] ID 的卡片块
    card_blocks = [(t, b) for t, b in cards if re.search(r"\[\[.*?\]\]", t)]

    if not card_blocks:
        problems.append("未检测到任何原子卡片（### [[ID]] 标题）")

    bad_titles = []
    no_restate = []
    no_link = []
    no_tag = []
    weak_link = []

    for title, body in card_blocks:
        # 标题应为命题式：去掉 [[ID]] 后应有实质陈述，且非纯主题词
        clean = re.sub(r"\[\[.*?\]\]", "", title).strip()
        if len(clean) < 6 or re.fullmatch(r"[\u4e00-\u9fa5A-Za-z0-9·\s]{1,5}", clean):
            bad_titles.append(title)

        # 必须有"我的复述"
        if "我的复述" not in body and "复述" not in body:
            no_restate.append(title)
        # 复述不能等于照抄（启发式：复述字段后不应直接是"原文"二字的内容）
        rest = re.search(r"我的复述[：:]\s*(.+)", body)
        if rest:
            v = rest.group(1).strip()
            if v.startswith(("待消化", "（待消化")):
                pass  # 允许，但属待办
            elif len(v) < 8:
                no_restate.append(f"{title}（复述过短）")

        # 至少 1 条链接
        links = re.findall(r"→\s*\[\[.*?\]\]", body) + re.findall(r"\[\[.*?\]\].*?(?:关系|支持|反例|上位|下位|导致|应用|张力|关联)", body)
        if not links:
            no_link.append(title)
        else:
            # 链接应带关系说明：检查每条链接后是否有关键词
            bare = re.findall(r"→\s*\[\[.*?\]\]\s*$", body, re.MULTILINE)
            if len(bare) == len(links):
                weak_link.append(title)

        # 标签
        if not re.search(r"#\S", body):
            no_tag.append(title)

    if bad_titles:
        problems.append(f"标题疑似非命题式（过短/纯主题词）：{bad_titles[:3]}")
    if no_restate:
        problems.append(f"缺少有效的'我的复述'（可能照抄或过短）：{no_restate[:3]}")
    if no_link:
        problems.append(f"无任何链接的卡片：{no_link[:3]}")
    if weak_link:
        problems.append(f"链接缺少关系类型说明：{weak_link[:3]}")
    if no_tag:
        problems.append(f"无标签的卡片：{no_tag[:3]}")

    # 主题索引存在性
    if not re.search(r"主题索引|索引[：:]", text):
        problems.append("未检测到主题索引区")

    if problems:
        print("✗ 校验未通过：")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"✓ 通过：原子卡片 {len(card_blocks)} 张，结构完整")
    return 0


if __name__ == "__main__":
    sys.exit(main())
