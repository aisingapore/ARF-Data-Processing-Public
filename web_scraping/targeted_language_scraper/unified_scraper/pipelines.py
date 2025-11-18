import json
import os

from itemadapter import ItemAdapter
from scrapy.exporters import JsonLinesItemExporter

from .items import ArticleItem, PdfItem, SearchResultItem


class PerSiteJsonLinePipeline:
    """
    This pipeline is from 'multi_site_crawler'.
    It saves ArticleItems to different JSONL files based on 'site_name'.

    """

    def open_spider(self, spider):
        self.files = {}
        self.exporters = {}
        self.output_dir = "output"
        os.makedirs(self.output_dir, exist_ok=True)

    def close_spider(self, spider):
        for exporter in self.exporters.values():
            exporter.finish_exporting()
        for file in self.files.values():
            file.close()

    def process_item(self, item, spider):
        if not isinstance(item, ArticleItem):
            return item
        # ------------------------------------

        site_name = item.get("site_name")
        if not site_name:
            site_name = "uncategorized"

        if site_name not in self.exporters:
            folder_name = f"TL_{site_name.capitalize()}"
            filename = f"{site_name}_output.jsonl"
            file_path = os.path.join(self.output_dir, folder_name, filename)
            directory = os.path.dirname(file_path)
            os.makedirs(directory, exist_ok=True)

            self.files[site_name] = open(file_path, "ab")
            self.exporters[site_name] = JsonLinesItemExporter(self.files[site_name])
            self.exporters[site_name].start_exporting()

        self.exporters[site_name].export_item(item)
        return item


class SaveToJsonlPipeline:
    """
    This pipeline is from 'scraping_framework copy'.
    It saves all items from a spider into a single, generic JSONL file.

    """

    def open_spider(self, spider):
        self.spider_name = spider.name
        self.output_dir = "output"
        os.makedirs(self.output_dir, exist_ok=True)

        self.file_path = os.path.join(self.output_dir, f"{spider.name}_output.jsonl")
        self.file = open(self.file_path, "w", encoding="utf-8")
        spider.logger.info(f"JSONL file opened at {self.file_path}")

    def close_spider(self, spider):
        self.file.close()
        spider.logger.info(f"JSONL file closed. Data saved to {self.file_path}")

    def process_item(self, item, spider):
        if not isinstance(item, (PdfItem, SearchResultItem)):
            return item
        # ------------------------------------

        adapter = ItemAdapter(item)
        line = json.dumps(adapter.asdict(), ensure_ascii=False) + "\n"
        self.file.write(line)
        return item
