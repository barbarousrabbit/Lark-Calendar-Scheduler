#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日历数据获取器 - 简化版
"""

import encoding_fix
import os
import json
import datetime
import requests
import re
import calendar

from config import API_CONFIG, PATHS
from logger import logger


class CalendarFetcher:
    """日历数据获取器"""
    
    def __init__(self):
        self.token_file = PATHS["token_file"]
        self.personal_calendars_dir = PATHS["personal_calendars"]
        self.history_dir = PATHS["calendar_history"]
        self.result_file = PATHS["result_file"]
        
        # 确保目录存在
        for directory in [self.personal_calendars_dir, self.history_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        logger.info("日历数据获取器初始化完成")
    
    def load_access_token(self):
        """加载访问令牌"""
        try:
            if not os.path.exists(self.token_file):
                return None
            
            with open(self.token_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            token_data = data.get("oauth", {}).get("token", {})
            access_token = token_data.get("access_token")
            
            if access_token:
                logger.success("成功加载访问令牌")
                return access_token
            else:
                logger.warning("未找到有效的访问令牌")
                return None
                
        except Exception as e:
            logger.error(f"加载访问令牌失败: {e}")
            return None
    
    def get_calendar_list(self, access_token):
        """获取日历列表"""
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            response = requests.get(API_CONFIG["calendar_url"], headers=headers, timeout=10)
            
            if response.status_code == 200:
                calendar_data = response.json()
                if calendar_data.get("code") == 0:
                    calendar_list = calendar_data.get("data", {}).get("calendar_list", [])
                    logger.success(f"成功获取 {len(calendar_list)} 个日历")
                    return calendar_data
                else:
                    logger.error(f"API错误: {calendar_data.get('msg', 'Unknown error')}")
            else:
                logger.error(f"HTTP错误: {response.status_code}")
            
            return None
        except Exception as e:
            logger.error(f"获取日历列表失败: {e}")
            return None
    
    def get_calendar_events(self, access_token, calendar_id):
        """获取日历事件（当前月到接下来2个月）"""
        try:
            # 计算时间范围
            current_date = datetime.datetime.now()
            start_date = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # 计算结束时间（2个月后）
            target_month = current_date.month + 2
            target_year = current_date.year
            if target_month > 12:
                target_month -= 12
                target_year += 1
            
            last_day = calendar.monthrange(target_year, target_month)[1]
            end_date = datetime.datetime(target_year, target_month, last_day, 23, 59, 59)
            
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            params = {
                "page_size": 1000,
                "start_time": str(start_timestamp),
                "end_time": str(end_timestamp)
            }
            
            events_url = API_CONFIG["events_url_template"].format(calendar_id)
            response = requests.get(events_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                events_data = response.json()
                if events_data.get("code") != 0:
                    logger.error(f"API错误 [{calendar_id}]: {events_data.get('msg')}")
                    return None
                
                events = events_data.get("data", {}).get("items", [])
                
                # 过滤事件
                filtered_events = []
                cancelled_count = 0
                empty_summary_count = 0
                out_of_range_count = 0
                
                # 计算过滤时间范围（当前月及未来2个月）
                now = datetime.datetime.now()
                filter_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                filter_start_timestamp = int(filter_start.timestamp())
                
                for event in events:
                    if event.get("status") == "cancelled":
                        cancelled_count += 1
                        continue
                    
                    if not event.get("summary", "").strip():
                        empty_summary_count += 1
                        continue
                    
                    # 检查事件开始时间
                    start_time = event.get("start_time", {})
                    if isinstance(start_time, dict):
                        event_start_timestamp = int(start_time.get("timestamp", "0"))
                    else:
                        event_start_timestamp = int(str(start_time))
                    
                    # 过滤掉当前月之前的事件
                    if event_start_timestamp < filter_start_timestamp:
                        out_of_range_count += 1
                        continue
                    
                    filtered_events.append(event)
                
                if cancelled_count > 0:
                    logger.info(f"已过滤 {cancelled_count} 个cancelled事件")
                if empty_summary_count > 0:
                    logger.info(f"已过滤 {empty_summary_count} 个空Summary事件")
                if out_of_range_count > 0:
                    logger.info(f"已过滤 {out_of_range_count} 个当前月之前的事件")
                
                return {
                    "code": 0,
                    "msg": "success",
                    "data": {
                        "items": filtered_events,
                        "total_count": len(filtered_events),
                        "original_count": len(events),
                        "cancelled_count": cancelled_count,
                        "empty_summary_count": empty_summary_count,
                        "out_of_range_count": out_of_range_count,
                        "filter_start_timestamp": filter_start_timestamp,
                        "query_start_time": start_timestamp,
                        "query_end_time": end_timestamp,
                        "retrieved_at": datetime.datetime.now().isoformat()
                    }
                }
            else:
                logger.error(f"HTTP错误 [{calendar_id}]: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"获取日历事件失败 [{calendar_id}]: {e}")
            return None
    
    def sanitize_filename(self, filename):
        """清理文件名"""
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        return filename[:100] if len(filename) > 100 else filename
    
    def save_calendar_results(self, calendar_data, access_token):
        """保存日历结果"""
        try:
            calendar_list = calendar_data.get("data", {}).get("calendar_list", [])
            if not calendar_list:
                logger.error("没有找到日历数据")
                return False
            
            logger.info("开始获取所有日历事件...")
            
            for calendar in calendar_list:
                calendar_id = calendar.get("calendar_id", "")
                summary = calendar.get("summary", "Unknown")
                
                if calendar_id:
                    events_data = self.get_calendar_events(access_token, calendar_id)
                    
                    if events_data:
                        events_count = events_data.get("data", {}).get("total_count", 0)
                        
                        # 保存到文件
                        safe_filename = self.sanitize_filename(f"{summary}.txt")
                        file_path = os.path.join(self.personal_calendars_dir, safe_filename)
                        
                        with open(file_path, "w", encoding="utf-8") as f:
                            json.dump(events_data, f, ensure_ascii=False, indent=2)
                        
                        logger.success(f"{summary}: {events_count} 个事件")
            
            # 保存日历列表
            with open(self.result_file, "w", encoding="utf-8") as f:
                json.dump(calendar_data, f, ensure_ascii=False, indent=2)
            
            logger.success("日历数据保存完成")
            return True
            
        except Exception as e:
            logger.error(f"保存日历结果失败: {e}")
            return False
    
    def fetch_calendar_data(self):
        """获取日历数据的主要流程"""
        try:
            logger.info("开始获取日历数据")
            
            # 1. 加载访问令牌
            access_token = self.load_access_token()
            if not access_token:
                logger.error("无法获取访问令牌")
                return False
            
            # 2. 获取日历列表
            calendar_data = self.get_calendar_list(access_token)
            if not calendar_data:
                logger.error("获取日历列表失败")
                return False
            
            # 3. 保存日历结果
            success = self.save_calendar_results(calendar_data, access_token)
            
            if success:
                logger.success("日历数据获取完成")
            else:
                logger.error("日历数据获取失败")
            
            return success
            
        except Exception as e:
            logger.error(f"获取日历数据异常: {e}")
            return False


def main():
    """主函数"""
    fetcher = CalendarFetcher()
    success = fetcher.fetch_calendar_data()
    
    if not success:
        logger.warning("提示：请先运行OAuth授权获得访问令牌")


if __name__ == "__main__":
    main()