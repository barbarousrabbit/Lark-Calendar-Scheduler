#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书多维表格记录上传模块
"""

import requests
import json
from typing import List, Dict, Optional, Any
from lark_token import get_lark_token

class LarkBitableUploader:
    """飞书多维表格上传类"""
    
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
    
    def batch_create_records(self, records: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        批量创建记录
        
        Args:
            records: 记录列表，每个记录包含fields字段
            
        Returns:
            dict: API返回结果，失败时返回None
        """
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
            print(f"请求URL: {url}")
            print(f"App Token: {self.app_token}")
            print(f"Table ID: {self.table_id}")
            print(f"记录数量: {len(records)}")
            
            response = requests.post(url, headers=headers, json=data)
            
            print(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"API响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
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
                try:
                    error_result = response.json()
                    return error_result
                except:
                    return None
                    
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求异常: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ 未知错误: {str(e)}")
            return None

def create_test_records(count: int = 10) -> List[Dict[str, Any]]:
    """
    创建测试记录
    
    Args:
        count: 记录数量
        
    Returns:
        list: 测试记录列表
    """
    records = []
    for i in range(1, count + 1):
        record = {
            "fields": {
                "Summary": f"测试日历记录 {i} - 这是第{i}条测试记录的内容"
            }
        }
        records.append(record)
    
    return records

def test_upload():
    """测试上传功能"""
    print("=== 飞书多维表格记录上传测试 ===\n")
    
    # 使用之前获取的obj_token作为app_token
    app_token = "YqkXbLfb8a0VYGsInq4uTAjpsUb"
    table_id = "tbl9yjYfvEzsQ2No"
    
    print(f"📋 配置信息:")
    print(f"   App Token: {app_token}")
    print(f"   Table ID: {table_id}")
    print("-" * 50)
    
    # 创建上传器
    uploader = LarkBitableUploader(app_token, table_id)
    
    # 创建测试记录
    print("📝 创建测试记录...")
    test_records = create_test_records(10)
    
    print(f"生成了 {len(test_records)} 条测试记录:")
    for i, record in enumerate(test_records[:3], 1):  # 只显示前3条
        print(f"   {i}. {record['fields']['Summary']}")
    if len(test_records) > 3:
        print(f"   ... 还有 {len(test_records) - 3} 条记录")
    
    print("\n" + "-" * 50)
    
    # 执行上传
    result = uploader.batch_create_records(test_records)
    
    if result and result.get('code') == 0:
        print(f"\n🎉 上传成功！")
        records_data = result.get('data', {}).get('records', [])
        print(f"✅ 成功创建 {len(records_data)} 条记录")
        
        if records_data:
            print("📊 创建的记录信息:")
            for i, record in enumerate(records_data[:3], 1):  # 只显示前3条
                record_id = record.get('record_id', 'Unknown')
                print(f"   {i}. Record ID: {record_id}")
            if len(records_data) > 3:
                print(f"   ... 还有 {len(records_data) - 3} 条记录")
    else:
        print(f"\n💥 上传失败！")
        if result:
            print(f"错误信息: {result.get('msg', 'Unknown error')}")
    
    return result

if __name__ == "__main__":
    result = test_upload()
    
    print(f"\n📝 使用示例:")
    print("   from lark_bitable_upload import LarkBitableUploader, create_test_records")
    print("   ")
    print("   uploader = LarkBitableUploader('your_app_token', 'your_table_id')")
    print("   records = create_test_records(5)")
    print("   result = uploader.batch_create_records(records)")
