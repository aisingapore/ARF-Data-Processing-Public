import csv
import json

from itemadapter import ItemAdapter


class SaveToCsvPipeline:
    """
    A pipeline that saves items to a CSV file.
    This is good for simple, flat data structures.
    """

    def open_spider(self, spider):
        self.file_path = f"{spider.name}_output.csv"
        self.file = open(self.file_path, "w", newline="", encoding="utf-8")
        self.writer = None
        spider.logger.info(f"CSV file opened at {self.file_path}")

    def close_spider(self, spider):
        self.file.close()
        spider.logger.info(f"CSV file closed. Data saved to {self.file_path}")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        if self.writer is None:
            fieldnames = adapter.field_names()
            self.writer = csv.DictWriter(self.file, fieldnames=fieldnames)
            self.writer.writeheader()

        self.writer.writerow(adapter.asdict())
        return item


class SaveToJsonlPipeline:
    """
    A generic pipeline that saves items to a JSON Lines (.jsonl) file.
    Each item is written as a separate JSON object on its own line.
    This pipeline is highly reusable and works with any item type.
    """

    def open_spider(self, spider):
        self.file_path = f"{spider.name}_output.jsonl"
        self.file = open(self.file_path, "w", encoding="utf-8")
        spider.logger.info(f"JSONL file opened at {self.file_path}")

    def close_spider(self, spider):
        self.file.close()
        spider.logger.info(f"JSONL file closed. Data saved to {self.file_path}")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        line = json.dumps(adapter.asdict(), ensure_ascii=False) + "\n"

        self.file.write(line)

        return item
