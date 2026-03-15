"""OPML导入工具 - 将OPML格式的RSS订阅列表导入到config.json"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TypedDict


class RSSSource(TypedDict):
    """RSS源的数据结构"""
    name: str
    url: str
    enabled: bool
    category: str


class OPMLImporter:
    """OPML导入器 - 解析OPML文件并转换为RSS源列表"""

    OPML_NAMESPACES = {"opml": "http://www.opml.org/spec2"}

    @classmethod
    def parse_opml(cls, opml_path: str | Path) -> list[RSSSource]:
        """解析OPML文件并返回RSS源列表

        Args:
            opml_path: OPML文件路径

        Returns:
            RSS源列表
        """
        tree = ET.parse(opml_path)
        root = tree.getroot()

        rss_sources: list[RSSSource] = []

        # 查找body元素
        body = root.find("body")
        if body is None:
            return rss_sources

        # 递归解析outline元素
        cls._parse_outline(body, rss_sources, category=None)

        return rss_sources

    @classmethod
    def _parse_outline(
        cls,
        element: ET.Element,
        rss_sources: list[RSSSource],
        category: str | None
    ) -> None:
        """递归解析outline元素

        Args:
            element: XML元素
            rss_sources: RSS源列表（就地修改）
            category: 当前分类名称
        """
        for outline in element.findall("outline"):
            # 检查是否为RSS源（有xmlUrl属性）
            xml_url = outline.get("xmlUrl")
            text = outline.get("text") or outline.get("title", "")

            if xml_url:
                # 这是一个RSS源
                rss_source: RSSSource = {
                    "name": text,
                    "url": xml_url,
                    "enabled": True,
                    "category": category or "imported"
                }
                rss_sources.append(rss_source)
            else:
                # 这是一个分类文件夹
                new_category = outline.get("text") or outline.get("title", category)
                cls._parse_outline(outline, rss_sources, category=new_category)

    @classmethod
    def import_to_config(
        cls,
        opml_path: str | Path,
        config_path: str | Path,
        merge: bool = True
    ) -> list[RSSSource]:
        """将OPML文件导入到config.json的rss部分

        Args:
            opml_path: OPML文件路径
            config_path: config.json文件路径
            merge: 是否合并到现有RSS源（True）或替换（False）

        Returns:
            导入的RSS源列表
        """
        # 解析OPML文件
        new_sources = cls.parse_opml(opml_path)

        if not new_sources:
            return []

        # 读取config文件
        config_file = Path(config_path)
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 确保sources.rss存在
        if "sources" not in config:
            config["sources"] = {}
        if "rss" not in config["sources"]:
            config["sources"]["rss"] = []

        existing_sources = config["sources"]["rss"]

        if merge:
            # 合并：追加新源，去重（按URL）
            existing_urls = {src["url"] for src in existing_sources}
            for source in new_sources:
                if source["url"] not in existing_urls:
                    existing_sources.append(source)
        else:
            # 替换：直接使用新源
            config["sources"]["rss"] = new_sources

        # 写回config文件
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return new_sources


def import_opml(opml_path: str, config_path: str, merge: bool = True) -> list[dict]:
    """便捷函数：导入OPML文件到config.json

    Args:
        opml_path: OPML文件路径
        config_path: config.json文件路径
        merge: 是否合并到现有RSS源

    Returns:
        导入的RSS源列表
    """
    return OPMLImporter.import_to_config(opml_path, config_path, merge)


def main():
    """命令行入口"""
    import argparse

    # 默认config路径
    default_config = Path(__file__).parent.parent / "data" / "config.json"

    parser = argparse.ArgumentParser(description="导入OPML RSS订阅到config.json")
    parser.add_argument("opml_file", help="OPML文件路径")
    parser.add_argument(
        "-c", "--config",
        default=str(default_config),
        help=f"config.json路径 (默认: {default_config})"
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="替换现有RSS源（默认是合并）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅解析不写入，显示导入结果"
    )

    args = parser.parse_args()

    # 解析OPML
    sources = OPMLImporter.parse_opml(args.opml_file)

    if not sources:
        print(f"未在 {args.opml_file} 中找到RSS源")
        return

    print(f"解析到 {len(sources)} 个RSS源:")
    for s in sources:
        print(f"  - {s['name']} ({s['category']})")
        print(f"    URL: {s['url']}")

    if args.dry_run:
        print("\n[dry-run] 未写入config文件")
        return

    # 导入
    imported = import_opml(args.opml_file, args.config, merge=not args.replace)
    print(f"\n成功导入 {len(imported)} 个RSS源到 {args.config}")


if __name__ == "__main__":
    main()
