#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录跟踪系统
基于event_id追踪日历记录的上传状态，防止重复上传
"""

# 编码修复
import encoding_fix

import os
import json
import datetime
import sqlite3
from typing import List, Dict, Any, Optional, Set
from contextlib import contextmanager


class RecordTracker:
    """记录跟踪器 - 追踪日历记录的上传状态"""
    
    def __init__(self, db_path: str = "record_tracking/upload_tracker.db"):
        """
        初始化记录跟踪器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        self.db_dir = os.path.dirname(db_path)
        
        # 确保数据库目录存在
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)
            print(f"📁 已创建数据库目录: {self.db_dir}")
        
        # 初始化数据库
        self._init_database()
        
        print("📊 记录跟踪器初始化完成")
    
    def _init_database(self):
        """初始化数据库表结构"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 创建记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calendar_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    person_name TEXT NOT NULL,
                    summary TEXT,
                    start_time INTEGER,
                    end_time INTEGER,
                    calendar_file TEXT,
                    record_hash TEXT,
                    upload_status TEXT DEFAULT 'pending',
                    upload_time TIMESTAMP,
                    upload_result TEXT,
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建上传日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS upload_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    upload_status TEXT NOT NULL,
                    upload_result TEXT,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_id ON calendar_records(event_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_upload_status ON calendar_records(upload_status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_person_name ON calendar_records(person_name)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_db_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 允许按列名访问
        try:
            yield conn
        finally:
            conn.close()
    
    def add_or_update_record(self, event_data: Dict, person_name: str, calendar_file: str) -> bool:
        """
        添加或更新记录
        
        Args:
            event_data: 事件数据
            person_name: 人员姓名
            calendar_file: 日历文件路径
            
        Returns:
            bool: 操作是否成功
        """
        try:
            event_id = event_data.get("event_id")
            if not event_id:
                print(f"⚠️ 记录缺少event_id，跳过：{event_data.get('summary', 'Unknown')}")
                return False
            
            # 提取时间戳
            start_time = self._extract_timestamp(event_data.get("start_time", {}))
            end_time = self._extract_timestamp(event_data.get("end_time", {}))
            
            # 生成记录哈希（用于检测记录内容变化）
            record_hash = self._generate_record_hash(event_data)
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 检查记录是否已存在
                cursor.execute("""
                    SELECT id, record_hash, upload_status FROM calendar_records 
                    WHERE event_id = ?
                """, (event_id,))
                
                existing_record = cursor.fetchone()
                
                if existing_record:
                    # 如果记录内容有变化，更新记录并重置上传状态
                    if existing_record['record_hash'] != record_hash:
                        cursor.execute("""
                            UPDATE calendar_records SET
                                summary = ?, start_time = ?, end_time = ?, 
                                calendar_file = ?, record_hash = ?,
                                upload_status = 'pending', upload_time = NULL, upload_result = NULL,
                                updated_time = CURRENT_TIMESTAMP
                            WHERE event_id = ?
                        """, (
                            event_data.get("summary", ""),
                            start_time, end_time, calendar_file, record_hash, event_id
                        ))
                        print(f"🔄 更新记录: {event_id} ({event_data.get('summary', 'Unknown')})")
                        conn.commit()
                        return True
                    # 如果内容没变化，不做任何操作（记录已存在，不需要重新处理）
                    return False
                else:
                    # 插入新记录
                    cursor.execute("""
                        INSERT INTO calendar_records 
                        (event_id, person_name, summary, start_time, end_time, 
                         calendar_file, record_hash, upload_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
                    """, (
                        event_id, person_name, event_data.get("summary", ""),
                        start_time, end_time, calendar_file, record_hash
                    ))
                    print(f"➕ 新增记录: {event_id} ({event_data.get('summary', 'Unknown')})")
                    conn.commit()
                    return True
                
        except Exception as e:
            print(f"❌ 添加/更新记录失败: {str(e)}")
            return False
    
    def _extract_timestamp(self, time_data: Dict) -> Optional[int]:
        """从时间数据中提取时间戳（毫秒）"""
        try:
            if "timestamp" in time_data:
                return int(time_data["timestamp"]) * 1000
            elif "date" in time_data:
                date_str = time_data["date"]
                dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                return int(dt.timestamp() * 1000)
            return None
        except:
            return None
    
    def _generate_record_hash(self, event_data: Dict) -> str:
        """生成记录哈希值，用于检测内容变化"""
        import hashlib
        
        # 提取关键字段来生成哈希
        key_fields = {
            "summary": event_data.get("summary", ""),
            "start_time": event_data.get("start_time", {}),
            "end_time": event_data.get("end_time", {}),
            "status": event_data.get("status", ""),
            "description": event_data.get("description", "")
        }
        
        content = json.dumps(key_fields, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_pending_records(self, person_name: str = None, limit: int = None) -> List[Dict]:
        """
        获取待上传的记录
        
        Args:
            person_name: 可选，指定人员姓名
            limit: 可选，限制返回数量
            
        Returns:
            list: 待上传的记录列表
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                sql = """
                    SELECT * FROM calendar_records 
                    WHERE upload_status = 'pending'
                """
                params = []
                
                if person_name:
                    sql += " AND person_name = ?"
                    params.append(person_name)
                
                sql += " ORDER BY created_time ASC"
                
                if limit:
                    sql += " LIMIT ?"
                    params.append(limit)
                
                cursor.execute(sql, params)
                records = cursor.fetchall()
                
                # 转换为字典列表
                result = []
                for record in records:
                    result.append(dict(record))
                
                return result
                
        except Exception as e:
            print(f"❌ 获取待上传记录失败: {str(e)}")
            return []
    
    def mark_as_uploaded(self, event_id: str, upload_result: str = "success") -> bool:
        """
        标记记录为已上传
        
        Args:
            event_id: 事件ID
            upload_result: 上传结果
            
        Returns:
            bool: 操作是否成功
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE calendar_records SET
                        upload_status = 'uploaded',
                        upload_time = CURRENT_TIMESTAMP,
                        upload_result = ?,
                        updated_time = CURRENT_TIMESTAMP
                    WHERE event_id = ?
                """, (upload_result, event_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    return True
                else:
                    print(f"⚠️ 未找到要标记的记录: {event_id}")
                    return False
                        
        except Exception as e:
            print(f"❌ 标记记录失败: {str(e)}")
            return False
    
    def mark_as_failed(self, event_id: str, error_message: str) -> bool:
        """
        标记记录上传失败
        
        Args:
            event_id: 事件ID
            error_message: 错误信息
            
        Returns:
            bool: 操作是否成功
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE calendar_records SET
                        upload_status = 'failed',
                        upload_time = CURRENT_TIMESTAMP,
                        upload_result = ?,
                        updated_time = CURRENT_TIMESTAMP
                    WHERE event_id = ?
                """, (f"FAILED: {error_message}", event_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"❌ 标记失败记录失败: {str(e)}")
            return False
    
    def log_upload_batch(self, batch_id: str, upload_results: List[Dict]) -> bool:
        """
        记录批量上传日志
        
        Args:
            batch_id: 批次ID
            upload_results: 上传结果列表
            
        Returns:
            bool: 操作是否成功
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                for result in upload_results:
                    cursor.execute("""
                        INSERT INTO upload_logs 
                        (batch_id, event_id, upload_status, upload_result, error_message)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        batch_id,
                        result.get("event_id"),
                        result.get("status"),
                        result.get("result"),
                        result.get("error")
                    ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"❌ 记录上传日志失败: {str(e)}")
            return False
    
    def get_upload_statistics(self) -> Dict[str, Any]:
        """获取上传统计信息"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 总体统计
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_records,
                        SUM(CASE WHEN upload_status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                        SUM(CASE WHEN upload_status = 'uploaded' THEN 1 ELSE 0 END) as uploaded_count,
                        SUM(CASE WHEN upload_status = 'failed' THEN 1 ELSE 0 END) as failed_count
                    FROM calendar_records
                """)
                
                total_stats = dict(cursor.fetchone())
                
                # 按人员统计
                cursor.execute("""
                    SELECT 
                        person_name,
                        COUNT(*) as total,
                        SUM(CASE WHEN upload_status = 'pending' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN upload_status = 'uploaded' THEN 1 ELSE 0 END) as uploaded,
                        SUM(CASE WHEN upload_status = 'failed' THEN 1 ELSE 0 END) as failed
                    FROM calendar_records
                    GROUP BY person_name
                    ORDER BY total DESC
                """)
                
                person_stats = [dict(row) for row in cursor.fetchall()]
                
                return {
                    "total_stats": total_stats,
                    "person_stats": person_stats,
                    "generated_at": datetime.datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"❌ 获取统计信息失败: {str(e)}")
            return {}
    
    def reset_failed_records(self) -> int:
        """重置失败的记录为待上传状态"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE calendar_records SET
                        upload_status = 'pending',
                        upload_time = NULL,
                        upload_result = NULL,
                        updated_time = CURRENT_TIMESTAMP
                    WHERE upload_status = 'failed'
                """)
                
                reset_count = cursor.rowcount
                conn.commit()
                
                print(f"🔄 已重置 {reset_count} 条失败记录为待上传状态")
                return reset_count
                
        except Exception as e:
            print(f"❌ 重置失败记录失败: {str(e)}")
            return 0
    
    def reset_all_records_to_pending(self) -> int:
        """重置所有记录为待上传状态"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE calendar_records SET
                        upload_status = 'pending',
                        upload_time = NULL,
                        upload_result = NULL,
                        updated_time = CURRENT_TIMESTAMP
                    WHERE upload_status IN ('uploaded', 'failed')
                """)
                
                reset_count = cursor.rowcount
                conn.commit()
                
                print(f"🔄 已重置 {reset_count} 条记录为待上传状态")
                return reset_count
                
        except Exception as e:
            print(f"❌ 重置所有记录失败: {str(e)}")
            return 0
    
    def clear_all_records(self) -> int:
        """清空所有记录（危险操作，谨慎使用）"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 删除所有记录
                cursor.execute("DELETE FROM calendar_records")
                cursor.execute("DELETE FROM upload_logs")
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                print(f"🗑️ 已清空 {deleted_count} 条记录")
                return deleted_count
                
        except Exception as e:
            print(f"❌ 清空记录失败: {str(e)}")
            return 0


def test_record_tracker():
    """测试记录跟踪器"""
    print("=== 测试记录跟踪器 ===\n")
    
    # 创建跟踪器
    tracker = RecordTracker()
    
    # 模拟一些测试数据
    test_events = [
        {
            "event_id": "test_event_1",
            "summary": "测试会议1",
            "start_time": {"timestamp": "1755563202"},
            "end_time": {"timestamp": "1755566802"},
            "status": "confirmed"
        },
        {
            "event_id": "test_event_2", 
            "summary": "测试会议2",
            "start_time": {"date": "2025-01-20"},
            "end_time": {"date": "2025-01-20"},
            "status": "confirmed"
        }
    ]
    
    # 添加测试记录
    print("📝 添加测试记录...")
    for event in test_events:
        tracker.add_or_update_record(event, "测试用户", "test_calendar.txt")
    
    # 获取待上传记录
    print("\n📋 获取待上传记录...")
    pending_records = tracker.get_pending_records()
    print(f"找到 {len(pending_records)} 条待上传记录")
    
    for record in pending_records:
        print(f"   - {record['event_id']}: {record['summary']}")
    
    # 标记一条记录为已上传
    if pending_records:
        event_id = pending_records[0]['event_id']
        print(f"\n✅ 标记记录 {event_id} 为已上传...")
        tracker.mark_as_uploaded(event_id, "测试上传成功")
    
    # 获取统计信息
    print("\n📊 统计信息:")
    stats = tracker.get_upload_statistics()
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    test_record_tracker()