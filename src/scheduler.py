#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的日历调度器
一键启动，自动处理授权、获取、上传和调度
"""

import encoding_fix
import os
import sys
import time
import signal
import schedule
import psutil
from threading import Event

from config import TABLE_CONFIG, SCHEDULE_CONFIG, PATHS, ensure_directories
from logger import logger
from fetcher import CalendarFetcher
from record_tracker import RecordTracker  
from direct_calendar_uploader import DirectCalendarUploader


class CalendarScheduler:
    """日历调度器 - 简化版"""
    
    def __init__(self):
        """初始化调度器"""
        ensure_directories()
        
        # 初始化组件
        self.fetcher = CalendarFetcher()
        self.tracker = RecordTracker()
        self.uploader = DirectCalendarUploader(
            TABLE_CONFIG["app_token"], 
            TABLE_CONFIG["table_id"]
        )
        
        # 状态管理
        self.stop_event = Event()
        self.pid_file = PATHS["pid_file"]
        
        logger.info("调度器初始化完成")
    
    def is_workday(self):
        """检查是否为工作日"""
        import datetime
        return datetime.datetime.now().weekday() < 5
    
    def kill_existing_process(self):
        """杀死已存在的调度器进程"""
        try:
            if not os.path.exists(self.pid_file):
                return True
            
            with open(self.pid_file, 'r') as f:
                old_pid = int(f.read().strip())
            
            if psutil.pid_exists(old_pid):
                try:
                    proc = psutil.Process(old_pid)
                    if 'scheduler.py' in ' '.join(proc.cmdline()):
                        logger.info(f"终止旧进程 PID: {old_pid}")
                        proc.terminate()
                        proc.wait(timeout=10)
                except psutil.TimeoutExpired:
                    proc.kill()
                except Exception as e:
                    logger.warning(f"终止旧进程失败: {e}")
            
            os.remove(self.pid_file)
            return True
        except Exception as e:
            logger.warning(f"处理旧进程失败: {e}")
            return False
    
    def create_pid_file(self):
        """创建PID文件"""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
        except Exception as e:
            logger.error(f"创建PID文件失败: {e}")
    
    def remove_pid_file(self):
        """删除PID文件"""
        try:
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
        except Exception as e:
            logger.warning(f"删除PID文件失败: {e}")
    
    def get_fresh_token(self):
        """每次执行都获取新的访问令牌"""
        try:
            logger.info("开始OAuth授权流程...")
            logger.info("💡 Token会在5分钟内失效，每次执行都需要重新授权")
            
            # 直接启动OAuth授权，不检查现有token
            from oauth import OAuthGUI
            oauth_app = OAuthGUI()
            oauth_app.run()
            
            # 验证授权结果
            access_token = self.fetcher.load_access_token()
            if access_token:
                logger.success("OAuth授权成功，获得新的访问令牌")
                return True
            else:
                logger.error("OAuth授权失败")
                return False
                
        except KeyboardInterrupt:
            logger.info("用户中断OAuth授权流程")
            return False
        except Exception as e:
            logger.error(f"OAuth授权异常: {e}")
            return False
    
    def execute_main_task(self, force_execute=False, skip_auth=False):
        """执行主要任务
        
        Args:
            force_execute: 是否强制执行（忽略工作日检查）
            skip_auth: 是否跳过授权（当外部已经获取过token时）
        """
        try:
            logger.info("开始执行主要任务")
            
            # 工作日检查
            if not force_execute and not self.is_workday():
                logger.info("今天是周末，跳过定时任务")
                return
            
            # 每天任务开始时获取新的访问令牌（除非外部已经获取）
            if not skip_auth:
                if not self.get_fresh_token():
                    logger.error("OAuth授权失败，无法继续")
                    return
            
            # 1. 获取日历数据
            logger.info("获取日历数据...")
            if not self.fetcher.fetch_calendar_data():
                logger.error("获取日历数据失败")
                return
            
            # 2. 加载记录到跟踪器
            logger.info("加载记录到跟踪器...")
            self._load_calendar_records()
            
            # 3. 上传待处理记录
            logger.info("上传待处理记录...")
            self._upload_pending_records()
            
            logger.success("主要任务执行完成")
            
        except Exception as e:
            logger.error(f"执行主要任务失败: {e}")
    
    def _load_calendar_records(self):
        """加载日历记录到跟踪器"""
        try:
            import glob
            import json
            
            calendar_files = glob.glob(os.path.join(PATHS["personal_calendars"], "*.txt"))
            total_added = 0
            
            for file_path in calendar_files:
                person_name = os.path.splitext(os.path.basename(file_path))[0]
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        calendar_data = json.load(f)
                    
                    events = calendar_data.get("data", {}).get("items", [])
                    added_count = 0
                    
                    for event in events:
                        if event.get("status") != "cancelled":
                            if self.tracker.add_or_update_record(event, person_name, file_path):
                                added_count += 1
                    
                    total_added += added_count
                    
                except Exception as e:
                    logger.warning(f"处理文件失败 {file_path}: {e}")
            
            logger.info(f"总计加载 {total_added} 条记录")
            
        except Exception as e:
            logger.error(f"加载日历记录失败: {e}")
    
    def _upload_pending_records(self):
        """上传待处理的记录"""
        try:
            pending_records = self.tracker.get_pending_records()
            
            if not pending_records:
                logger.info("没有待上传的记录")
                return
            
            logger.info(f"找到 {len(pending_records)} 条待上传记录")
            
            uploaded_count = 0
            failed_count = 0
            batch_size = SCHEDULE_CONFIG["batch_size"]
            
            # 分批上传
            for i in range(0, len(pending_records), batch_size):
                batch_records = pending_records[i:i + batch_size]
                
                # 转换为上传格式
                upload_batch = []
                event_ids = []
                
                for record in batch_records:
                    upload_record = {
                        "fields": {
                            "Summary": record["summary"] or "",
                            "Start Time": record["start_time"],
                            "End Time": record["end_time"] or record["start_time"],
                            "Person": record["person_name"]
                        }
                    }
                    upload_batch.append(upload_record)
                    event_ids.append(record["event_id"])
                
                # 执行上传
                result = self.uploader.batch_upload_records(upload_batch)
                
                if result and result.get('code') == 0:
                    # 上传成功
                    for event_id in event_ids:
                        self.tracker.mark_as_uploaded(event_id, "批量上传成功")
                    uploaded_count += len(event_ids)
                else:
                    # 上传失败
                    error_msg = result.get('msg', '未知错误') if result else '网络错误'
                    for event_id in event_ids:
                        self.tracker.mark_as_failed(event_id, error_msg)
                    failed_count += len(event_ids)
            
            logger.success(f"上传完成: 成功 {uploaded_count} 条，失败 {failed_count} 条")
            
        except Exception as e:
            logger.error(f"上传记录失败: {e}")
    
    def daily_scheduled_task(self):
        """定时任务专用方法"""
        logger.info("执行定时任务")
        self.execute_main_task(force_execute=False)
    
    def setup_schedule(self):
        """设置定时任务"""
        work_time = SCHEDULE_CONFIG["work_time"]
        schedule.every().monday.at(work_time).do(self.daily_scheduled_task)
        schedule.every().tuesday.at(work_time).do(self.daily_scheduled_task)
        schedule.every().wednesday.at(work_time).do(self.daily_scheduled_task)
        schedule.every().thursday.at(work_time).do(self.daily_scheduled_task)
        schedule.every().friday.at(work_time).do(self.daily_scheduled_task)
        
        logger.info(f"已设置定时任务: 工作日每天{work_time}执行")
        
        next_run = schedule.next_run()
        if next_run:
            logger.info(f"下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def handle_signal(self, signum, frame):
        """处理系统信号"""
        logger.info(f"收到停止信号 {signum}")
        self.stop_event.set()
    
    def run(self, immediate_execute=False):
        """启动调度器"""
        try:
            logger.info("启动日历调度器")
            
            # 杀死已存在的进程
            self.kill_existing_process()
            
            # 创建PID文件
            self.create_pid_file()
            
            # 设置信号处理
            signal.signal(signal.SIGINT, self.handle_signal)
            signal.signal(signal.SIGTERM, self.handle_signal)
            
            # 立即执行一次（如果需要）
            if immediate_execute:
                logger.info("立即执行一次任务")
                
                # 立即获取新的访问令牌
                if self.get_fresh_token():
                    # 执行任务（不重置已上传记录，跳过重复授权）
                    self.execute_main_task(force_execute=True, skip_auth=True)
                else:
                    logger.error("访问令牌验证失败")
            
            # 设置定时任务
            self.setup_schedule()
            
            logger.success("调度器已启动，按 Ctrl+C 停止")
            
            # 主循环
            check_interval = SCHEDULE_CONFIG["check_interval"]
            while not self.stop_event.is_set():
                try:
                    schedule.run_pending()
                    time.sleep(check_interval)
                except KeyboardInterrupt:
                    logger.info("收到键盘中断信号，停止调度器")
                    self.stop_event.set()
                    break
                except Exception as e:
                    logger.warning(f"调度循环异常: {e}")
                    time.sleep(check_interval)
            
        except KeyboardInterrupt:
            logger.info("用户中断，停止调度器")
            self.stop_event.set()
        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
        finally:
            self.remove_pid_file()
            logger.info("调度器已停止")
    
    def run_once(self):
        """立即执行一次任务"""
        logger.info("立即执行一次任务")
        
        if self.get_fresh_token():
            # 执行任务（不重置已上传记录，跳过重复授权）
            self.execute_main_task(force_execute=True, skip_auth=True)
        else:
            logger.error("访问令牌验证失败")
    
    def show_status(self):
        """显示调度器状态"""
        logger.info("调度器状态信息")
        print("=" * 40)
        
        # 检查运行状态
        if os.path.exists(self.pid_file):
            with open(self.pid_file, 'r') as f:
                pid = f.read().strip()
            print(f"🟢 状态: 运行中 (PID: {pid})")
        else:
            print("🔴 状态: 未运行")
        
        # 显示统计信息
        stats = self.tracker.get_upload_statistics()
        if stats:
            total_stats = stats.get("total_stats", {})
            print(f"\n📊 记录统计:")
            print(f"   总记录数: {total_stats.get('total_records', 0)}")
            print(f"   待上传: {total_stats.get('pending_count', 0)}")
            print(f"   已上传: {total_stats.get('uploaded_count', 0)}")
            print(f"   失败: {total_stats.get('failed_count', 0)}")
        
        print("=" * 40)



def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Calendar Scheduler")
    parser.add_argument("--run", action="store_true", help="Start scheduler (scheduled only)")
    parser.add_argument("--run-immediate", action="store_true", help="Start scheduler and run immediately") 
    parser.add_argument("--run-once", action="store_true", help="Run once only")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--stop", action="store_true", help="Stop scheduler")
    
    args = parser.parse_args()
    
    scheduler = CalendarScheduler()
    
    if args.run:
        scheduler.run(immediate_execute=False)
    elif args.run_immediate:
        scheduler.run(immediate_execute=True)
    elif args.run_once:
        scheduler.run_once()
    elif args.status:
        scheduler.show_status()
    elif args.stop:
        # 停止调度器
        pid_file = PATHS["pid_file"]
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                logger.success(f"已发送停止信号给进程 {pid}")
            except Exception as e:
                logger.error(f"停止调度器失败: {e}")
        else:
            logger.warning("调度器未在运行")
    else:
        # 默认行为：立即执行并启动调度器
        scheduler.run(immediate_execute=True)


if __name__ == "__main__":
    main()