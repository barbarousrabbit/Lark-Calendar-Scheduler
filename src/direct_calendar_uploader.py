#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接从日历JSON数据上传到飞书多维表格
直接从JSON文件读取，每条记录直接上传
"""

import os
import json
import datetime
import requests
import glob
from typing import List, Dict, Any, Optional
from lark_token import get_lark_token


class DirectCalendarUploader:
    """直接日历上传器"""
    
    def __init__(self, app_token: str, table_id: str):
        """
        初始化上传器
        
        Args:
            app_token: 应用token（obj_token）
            table_id: 表格ID
        """
        self.app_token = app_token
        self.table_id = table_id
        self.base_url = "https://open.larksuite.com/open-apis"
        self.personal_calendars_dir = "personal_calendars"
        
        print("📋 直接日历上传器初始化完成")
    
    def parse_timestamp_to_ms(self, time_data: Dict) -> Optional[int]:
        """
        将时间数据转换为毫秒时间戳
        
        Args:
            time_data: 时间数据，可能包含timestamp或date字段
            
        Returns:
            int: 毫秒时间戳，失败时返回None
        """
        try:
            # 如果有timestamp字段，直接转换
            if "timestamp" in time_data:
                timestamp = int(time_data["timestamp"])
                return timestamp * 1000  # 转换为毫秒
            
            # 如果有date字段，解析日期
            elif "date" in time_data:
                date_str = time_data["date"]
                timezone = time_data.get("timezone", "UTC")
                
                # 解析日期字符串 (格式如 "2024-11-07")
                dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                
                # 转换为时间戳（毫秒）
                return int(dt.timestamp() * 1000)
            
            return None
            
        except Exception as e:
            print(f"⚠️ 时间解析失败: {time_data}, 错误: {str(e)}")
            return None
    
    def convert_event_to_record(self, event: Dict, person_name: str) -> Optional[Dict]:
        """
        将单个事件转换为飞书多维表格记录格式
        
        Args:
            event: 日历事件数据
            person_name: 人员姓名
            
        Returns:
            dict: 多维表格记录格式，失败时返回None
        """
        try:
            # 获取基本信息
            summary = event.get("summary", "")
            status = event.get("status", "")
            
            # 跳过cancelled状态的事件
            if status == "cancelled":
                return None
            
            # 跳过空Summary的事件
            if not summary.strip():
                return None
            
            # 解析时间
            start_time_data = event.get("start_time", {})
            end_time_data = event.get("end_time", {})
            
            start_timestamp_ms = self.parse_timestamp_to_ms(start_time_data)
            end_timestamp_ms = self.parse_timestamp_to_ms(end_time_data)
            
            # 如果开始时间无效，跳过此事件
            if start_timestamp_ms is None:
                print(f"⚠️ 跳过无效时间事件: {summary}")
                return None
            
            # 构建记录
            record = {
                "fields": {
                    "Summary": summary,
                    "Start Time": start_timestamp_ms,
                    "End Time": end_timestamp_ms or start_timestamp_ms,  # 如果结束时间为空，使用开始时间
                    "Person": person_name
                }
            }
            
            return record
            
        except Exception as e:
            print(f"❌ 转换事件失败: {str(e)}")
            return None
    
    def read_calendar_json(self, file_path: str) -> List[Dict]:
        """
        读取日历JSON文件
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            list: 事件列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                calendar_data = json.load(f)
            
            events = calendar_data.get("data", {}).get("items", [])
            print(f"📖 从 {os.path.basename(file_path)} 读取到 {len(events)} 个事件")
            
            return events
            
        except Exception as e:
            print(f"❌ 读取日历文件失败 {file_path}: {str(e)}")
            return []
    
    def batch_upload_records(self, records: List[Dict]) -> Optional[Dict]:
        """
        批量上传记录到飞书多维表格
        
        Args:
            records: 记录列表
            
        Returns:
            dict: API返回结果，失败时返回None
        """
        if not records:
            print("⚠️ 没有记录需要上传")
            return None
        
        # 获取tenant_access_token
        tenant_token = get_lark_token()
        if not tenant_token:
            print("❌ 无法获取tenant_access_token")
            return None
        
        # 构造请求URL
        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/batch_create"
        
        # 构造请求头
        headers = {
            'Authorization': f'Bearer {tenant_token}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        
        # 构造请求数据
        data = {"records": records}
        
        try:
            print(f"📤 正在上传 {len(records)} 条记录到飞书多维表格...")
            
            response = requests.post(url, headers=headers, json=data)
            
            print(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') == 0:
                    print("✅ 记录上传成功！")
                    return result
                else:
                    print(f"❌ API返回错误: {result.get('msg', '未知错误')}")
                    print(f"错误代码: {result.get('code')}")
                    return result
            else:
                print(f"❌ HTTP请求失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                return None
                    
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求异常: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ 未知错误: {str(e)}")
            return None
    
    def upload_calendar_file(self, file_path: str, person_name: str = None, limit: int = None) -> bool:
        """
        上传单个日历文件的所有记录
        
        Args:
            file_path: 日历文件路径
            person_name: 人员姓名，如果为None则从文件名提取
            limit: 限制上传的记录数量
            
        Returns:
            bool: 上传是否成功
        """
        try:
            # 从文件名提取人员姓名（如果未提供）
            if person_name is None:
                person_name = os.path.splitext(os.path.basename(file_path))[0]
            
            print(f"\n📋 开始处理 {person_name} 的日历记录...")
            
            # 读取日历数据
            events = self.read_calendar_json(file_path)
            if not events:
                print(f"⚠️ {person_name} 没有有效事件")
                return False
            
            # 转换为记录格式
            records = []
            skipped_count = 0
            
            for i, event in enumerate(events):
                if limit and i >= limit:
                    break
                
                record = self.convert_event_to_record(event, person_name)
                if record:
                    records.append(record)
                else:
                    skipped_count += 1
            
            if not records:
                print(f"⚠️ {person_name} 没有有效记录需要上传")
                return False
            
            print(f"📊 {person_name}: 有效记录 {len(records)} 个，跳过 {skipped_count} 个")
            
            # 上传记录
            result = self.batch_upload_records(records)
            
            if result and result.get('code') == 0:
                uploaded_count = len(result.get('data', {}).get('records', []))
                print(f"🎉 {person_name} 上传成功：{uploaded_count} 条记录")
                return True
            else:
                print(f"💥 {person_name} 上传失败")
                return False
                
        except Exception as e:
            print(f"❌ 处理 {person_name} 的日历时发生错误: {str(e)}")
            return False
    
    def upload_all_calendars(self, limit_per_calendar: int = None) -> Dict[str, bool]:
        """
        上传所有日历文件
        
        Args:
            limit_per_calendar: 每个日历限制上传的记录数量
            
        Returns:
            dict: 每个日历的上传结果
        """
        print("🚀 开始上传所有日历记录...")
        print("=" * 60)
        
        # 检查目录
        if not os.path.exists(self.personal_calendars_dir):
            print(f"❌ 目录不存在: {self.personal_calendars_dir}")
            return {}
        
        # 获取所有日历文件
        calendar_files = glob.glob(os.path.join(self.personal_calendars_dir, "*.txt"))
        
        if not calendar_files:
            print(f"❌ 在 {self.personal_calendars_dir} 中未找到日历文件")
            return {}
        
        print(f"📁 找到 {len(calendar_files)} 个日历文件")
        
        # 上传结果
        results = {}
        
        for file_path in calendar_files:
            person_name = os.path.splitext(os.path.basename(file_path))[0]
            success = self.upload_calendar_file(file_path, person_name, limit_per_calendar)
            results[person_name] = success
        
        print("\n" + "=" * 60)
        print("📊 上传结果统计:")
        success_count = sum(1 for success in results.values() if success)
        for person, success in results.items():
            status = "✅ 成功" if success else "❌ 失败"
            print(f"   {person}: {status}")
        
        print(f"\n🎯 总计: {success_count}/{len(results)} 个日历上传成功")
        print("=" * 60)
        
        return results


def test_upload_single_calendar():
    """测试上传单个日历"""
    print("=== 测试上传单个日历记录 ===\n")
    
    # 配置信息（使用用户提供的示例配置）
    app_token = "YqkXbLfb8a0VYGsInq4uTAjpsUb"
    table_id = "tbl9yjYfvEzsQ2No"
    
    # 创建上传器
    uploader = DirectCalendarUploader(app_token, table_id)
    
    # 测试上传Amelia Leavey的日历（限制5条记录）
    test_file = "personal_calendars/Amelia Leavey.txt"
    if os.path.exists(test_file):
        success = uploader.upload_calendar_file(test_file, "Amelia Leavey", limit=5)
        if success:
            print("\n🎉 单个日历测试上传成功！")
        else:
            print("\n💥 单个日历测试上传失败！")
    else:
        print(f"❌ 测试文件不存在: {test_file}")


def upload_all_calendars_limited():
    """上传所有日历（每个限制10条记录）"""
    print("=== 上传所有日历记录（限制版） ===\n")
    
    # 配置信息
    app_token = "YqkXbLfb8a0VYGsInq4uTAjpsUb"
    table_id = "tbl9yjYfvEzsQ2No"
    
    # 创建上传器
    uploader = DirectCalendarUploader(app_token, table_id)
    
    # 上传所有日历（每个限制10条记录）
    results = uploader.upload_all_calendars(limit_per_calendar=10)
    
    return results


if __name__ == "__main__":
    import sys
    
    print("📅 直接日历上传工具")
    print("=" * 60)
    print("功能说明:")
    print("   1. 直接从personal_calendars中的JSON文件读取事件")
    print("   2. 直接从JSON文件读取数据")
    print("   3. 将每条记录直接上传到飞书多维表格")
    print("   4. 自动过滤cancelled状态的事件")
    print("   5. 自动过滤空Summary的事件")
    print("   6. 支持时间戳和日期格式自动转换")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 测试模式：只上传一个日历的少量记录
        test_upload_single_calendar()
    else:
        # 默认模式：上传所有日历的有限记录
        upload_all_calendars_limited()
    
    print(f"\n📝 使用示例:")
    print("   # 测试单个日历")
    print("   python direct_calendar_uploader.py test")
    print("   ")
    print("   # 上传所有日历（限制版）")
    print("   python direct_calendar_uploader.py")
    print("   ")
    print("   # 程序化使用")
    print("   from direct_calendar_uploader import DirectCalendarUploader")
    print("   uploader = DirectCalendarUploader('app_token', 'table_id')")
    print("   uploader.upload_calendar_file('path/to/calendar.txt', 'Person Name')")
