# upload_to_database.py
# -*- coding: utf-8 -*-

# --- 核心依赖 ---
import notion_client
import re
import os
from datetime import datetime, timezone, timedelta
import threading
from pathlib import Path

import sys
import logging

# ==============================================================================
#  --- 从环境变量加载配置 ---
# ==============================================================================
# 1. 从环境变量获取官方机器人“钥匙”
NOTION_TOKEN = os.getenv("NOTION_TOKEN")

# 2. 从环境变量获取数据库ID
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# 3. 数据库中【标题】属性的【准确名称】(大小写敏感)
TITLE_PROPERTY_NAME = "Name" # 例如: "Name" 或 "文章标题"

# 4. 数据库中【日期】属性的【准确名称】(大小写敏感)
DATE_PROPERTY_NAME = "Date" # 例如: "Date" 或 "发布日期"

# ==============================================================================

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==============================================================================
#  上传函数 (新版逻辑)
# ==============================================================================
def upload_reports_to_notion_properties(report_dir_path):
    """
    创建一个Notion页面，并将指定目录下的每个报告内容填充到对应的数据库文本属性中。
    """
    try:
        # --- 1. 检查输入 ---
        logging.info("开始执行上传脚本...")
        if not report_dir_path:
            logging.error("错误：未提供报告目录路径！")
            return

        if not all([NOTION_TOKEN, DATABASE_ID]):
             logging.error("错误：请确保 NOTION_TOKEN 和 NOTION_DATABASE_ID 环境变量已设置。")
             return

        report_dir = Path(report_dir_path)
        if not report_dir.is_dir():
            logging.error(f"错误：路径 '{report_dir_path}' 不是一个有效的目录。")
            return

        # --- 2. 初始化Notion客户端 ---
        try:
            notion = notion_client.Client(auth=NOTION_TOKEN)
            logging.info("Notion客户端初始化成功。")
        except Exception as e:
            logging.error(f"客户端初始化失败: {e}")
            return

        # --- 3. 准备页面属性 ---
        beijing_tz = timezone(timedelta(hours=8))
        now = datetime.now(beijing_tz)
        title = now.strftime("%Y-%m-%d %H:%M:%S") + " Analysis Report"
        
        properties_payload = {
            TITLE_PROPERTY_NAME: {"title": [{"type": "text", "text": {"content": title}}]},
            DATE_PROPERTY_NAME: {"date": {"start": now.isoformat()}}
        }

        # --- 4. 读取报告文件并填充属性 ---
        report_files = list(report_dir.glob("*.md"))
        if not report_files:
            logging.warning("警告：报告目录为空，没有可上传的文件。")
            return

        logging.info(f"找到 {len(report_files)} 个报告文件，准备填充属性...")
        for report_file in report_files:
            property_name = report_file.stem  # e.g., "market_report"
            try:
                content = report_file.read_text(encoding="utf-8")
                # Notion API对文本属性内容有2000字符的限制
                if len(content) > 2000:
                    content = content[:1997] + "..."
                    logging.warning(f"'{property_name}' 的内容超过2000字符，已被截断。")
                
                properties_payload[property_name] = {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                }
                logging.info(f"已准备属性 '{property_name}'。")
            except Exception as e:
                logging.error(f"读取或处理文件 '{report_file.name}' 时出错: {e}")
                continue # 跳过有问题的文件

        # --- 5. 创建页面 ---
        try:
            notion.pages.create(
                parent={"database_id": DATABASE_ID},
                properties=properties_payload,
                children=[] # 页面内容为空，所有信息都在属性中
            )
            logging.info(f"成功在数据库中创建新条目: '{title}'")
            
        except notion_client.errors.APIResponseError as e:
            logging.error(f"创建新页面失败: {e}\n请检查：\n1. Token和Database ID是否正确。\n2. 机器人是否已授权给该数据库。\n3. 数据库是否包含与报告文件名完全匹配的文本属性（例如 'market_report', 'news_report' 等）。")
            return
            
        logging.info("----------------------------------------")
        logging.info("🎉 完结撒花！所有报告已作为属性成功上传。")
        logging.info("----------------------------------------")

    except Exception as e:
        logging.error(f"发生未预料的严重错误: {e}")

# ==============================================================================
#  主执行逻辑
# ==============================================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error("使用方法: python upload_to_notion.py <报告目录路径>")
        sys.exit(1)
    
    report_directory = sys.argv[1]
    upload_reports_to_notion_properties(report_directory)
