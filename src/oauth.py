#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的OAuth授权工具
"""

import encoding_fix
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import os
import sys
import json
import datetime
import webbrowser
import requests
import pyperclip
from urllib.parse import urlparse, parse_qs

from config import OAUTH_CONFIG, API_CONFIG, PATHS
from logger import logger

# 隐藏控制台窗口（Windows）
if sys.platform == "win32":
    import ctypes
    try:
        console_window = ctypes.windll.kernel32.GetConsoleWindow()
        if console_window != 0:
            ctypes.windll.user32.ShowWindow(console_window, 0)
    except:
        pass


class OAuthHandler:
    """OAuth处理器"""
    
    def __init__(self):
        self.config = OAUTH_CONFIG
        self.auth_url = self._build_auth_url()
        self.last_clipboard = ""
    
    def _build_auth_url(self):
        """构建授权URL"""
        return (
            f"https://accounts.larksuite.com/open-apis/authen/v1/authorize?"
            f"client_id={self.config['client_id']}&"
            f"redirect_uri={self.config['redirect_uri']}&"
            f"scope={self.config['scope']}&"
            f"state={self.config['state']}"
        )
    
    def open_auth_page(self):
        """打开授权页面"""
        try:
            webbrowser.open(self.auth_url, new=2)
            logger.success("授权页面已在浏览器中打开")
            return True
        except Exception as e:
            logger.error(f"无法打开浏览器: {e}")
            return False
    
    def is_callback_url(self, text):
        """检查是否为回调URL"""
        return (text and isinstance(text, str) and 
                "example.com/oauth2/callback" in text and
                "code=" in text and "state=" in text)
    
    def extract_code_from_url(self, url):
        """从URL中提取授权码"""
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            if 'code' in query_params:
                code = query_params['code'][0]
                logger.success(f"成功提取授权码: {code[:20]}...")
                return code
            else:
                logger.error("URL中未找到授权码")
                return None
        except Exception as e:
            logger.error(f"解析URL失败: {e}")
            return None
    
    def get_user_token(self, code):
        """获取用户访问令牌"""
        try:
            payload = {
                "grant_type": "authorization_code",
                "client_id": self.config["client_id"],
                "client_secret": self.config["client_secret"],
                "redirect_uri": self.config["redirect_uri"],
                "code": code
            }
            
            headers = {"Content-Type": "application/json"}
            
            response = requests.post(API_CONFIG["token_url"], json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                
                if "access_token" in token_data:
                    access_token = token_data["access_token"]
                    logger.success(f"成功获取访问令牌: {access_token[:30]}...")
                    
                    # 添加时间戳
                    token_data['retrieved_at'] = datetime.datetime.now().isoformat()
                    return token_data
                else:
                    logger.error(f"响应中未包含访问令牌: {token_data}")
                    return None
            else:
                logger.error(f"获取令牌失败: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"获取令牌异常: {e}")
            return None
    
    def monitor_clipboard_for_code(self, callback_function=None):
        """监控剪贴板获取授权码"""
        try:
            current_clipboard = pyperclip.paste()
            
            if current_clipboard != self.last_clipboard:
                self.last_clipboard = current_clipboard
                
                if self.is_callback_url(current_clipboard):
                    logger.success("检测到回调URL")
                    
                    code = self.extract_code_from_url(current_clipboard)
                    if code:
                        token_data = self.get_user_token(code)
                        
                        if token_data and callback_function:
                            callback_function(code, current_clipboard, token_data)
                            return True
                        elif token_data:
                            logger.success("OAuth流程完成")
                            return token_data
            
            return False
            
        except Exception as e:
            logger.error(f"剪贴板监控异常: {e}")
            return False


class OAuthGUI:
    """OAuth GUI界面"""
    
    def __init__(self):
        self.oauth_handler = OAuthHandler()
        self.data_file = PATHS["token_file"]
        
        # 设置主题
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # 监控状态
        self.monitoring = True
        self.current_code = self._load_current_code()
        
        # 创建窗口
        self._create_window()
        
        # 立即打开授权页面
        self.oauth_handler.open_auth_page()
        
        # 开始监控
        self._start_monitoring()
    
    def _load_current_code(self):
        """加载当前授权码"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("oauth", {}).get("code", "")
        except:
            pass
        return ""
    
    def _save_oauth_data(self, code, url, token_data):
        """保存OAuth数据"""
        try:
            complete_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "oauth": {
                    "code": code,
                    "url": url,
                    "client_id": self.oauth_handler.config["client_id"],
                    "redirect_uri": self.oauth_handler.config["redirect_uri"],
                    "token_retrieved": bool(token_data),
                    "token": token_data if token_data else None
                },
                "status": {
                    "oauth_complete": bool(token_data),
                    "last_updated": datetime.datetime.now().isoformat()
                }
            }
            
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(complete_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"保存OAuth数据失败: {e}")
            return False
    
    def _create_window(self):
        """创建窗口"""
        self.root = ctk.CTk()
        self.root.title("飞书日历授权")
        self.root.geometry("450x200")
        
        # 设置图标 - 优先使用外部文件
        try:
            # 检查当前目录的ico文件（外部文件优先）
            icon_paths = [
                "Lark_Calendar.ico",  # 当前目录
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Lark_Calendar.ico"),  # 项目根目录
            ]
            
            # 如果是打包环境，也检查打包路径
            import sys
            if hasattr(sys, '_MEIPASS'):
                icon_paths.insert(0, os.path.join(sys._MEIPASS, "Lark_Calendar.ico"))
            
            icon_path = None
            for path in icon_paths:
                if os.path.exists(path):
                    icon_path = path
                    break
            
            if icon_path:
                # 简化的图标设置
                self.root.iconbitmap(icon_path)
                # 确保任务栏图标正确显示
                self.root.wm_iconbitmap(icon_path)
        except Exception as e:
            # 在无控制台模式下，不使用print
            pass
        
        # 居中窗口
        self._center_window()
        
        # 创建UI元素
        self._create_ui()
    
    def _create_ui(self):
        """创建UI元素"""
        # 主容器
        main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # 标题
        title = ctk.CTkLabel(
            main_frame,
            text="🗓️ 飞书日历授权",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=(20, 10))
        
        # 状态信息
        status_text = "授权页面已在浏览器中打开\n完成授权后复制URL即可自动处理"
        if self.current_code:
            status_text += f"\n当前授权码: {self.current_code[:20]}..."
        
        self.status_label = ctk.CTkLabel(
            main_frame,
            text=status_text,
            font=ctk.CTkFont(size=14),
            text_color="lightblue"
        )
        self.status_label.pack(pady=(0, 20))
        
        # 按钮容器
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=10)
        
        # 重新打开按钮
        reopen_btn = ctk.CTkButton(
            button_frame,
            text="🌐 重新打开",
            font=ctk.CTkFont(size=14),
            height=35,
            width=100,
            command=self.oauth_handler.open_auth_page
        )
        reopen_btn.pack(side="left", padx=(0, 10))
        
        # 手动输入按钮
        manual_btn = ctk.CTkButton(
            button_frame,
            text="📝 手动输入",
            font=ctk.CTkFont(size=14),
            height=35,
            width=100,
            command=self._manual_input
        )
        manual_btn.pack(side="left", padx=(0, 10))
        
        # 取消按钮
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="❌ 取消",
            font=ctk.CTkFont(size=14),
            height=35,
            width=80,
            fg_color="gray",
            hover_color="darkgray",
            command=self._cancel
        )
        cancel_btn.pack(side="left")
    
    def _center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        width = 450
        height = 200
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def _start_monitoring(self):
        """开始监控剪贴板"""
        if not self.monitoring:
            return
        
        result = self.oauth_handler.monitor_clipboard_for_code(self._on_oauth_complete)
        
        if not result:
            self.root.after(1000, self._start_monitoring)
    
    def _on_oauth_complete(self, code, url, token_data):
        """OAuth完成回调"""
        try:
            self.monitoring = False
            
            # 检查重复
            if code == self.current_code:
                self.status_label.configure(text="⚠️ 检测到相同的授权码，请获取新的授权码")
                self.monitoring = True
                self._start_monitoring()
                return
            
            # 保存数据
            self.status_label.configure(text="💾 正在保存OAuth数据...")
            self.root.update()
            
            if self._save_oauth_data(code, url, token_data):
                self.current_code = code
                
                # 自动获取日历数据
                self.status_label.configure(text="📅 正在获取日历数据...")
                self.root.update()
                
                from fetcher import CalendarFetcher
                fetcher = CalendarFetcher()
                success = fetcher.fetch_calendar_data()
                
                if success:
                    self.root.destroy()
                else:
                    messagebox.showerror("错误", "日历数据获取失败")
                    self.monitoring = True
                    self._start_monitoring()
            else:
                messagebox.showerror("错误", "保存OAuth数据失败")
                self.monitoring = True
                self._start_monitoring()
                
        except Exception as e:
            messagebox.showerror("错误", f"处理失败: {str(e)}")
            self.monitoring = True
            self._start_monitoring()
    
    def _manual_input(self):
        """手动输入URL"""
        dialog = ctk.CTkInputDialog(
            text="请粘贴重定向后的完整URL:",
            title="手动输入"
        )
        
        url = dialog.get_input()
        
        if url:
            token_data = self.oauth_handler.process_manual_url(url)
            
            if token_data:
                code = self.oauth_handler.extract_code_from_url(url)
                
                if code and code == self.current_code:
                    messagebox.showwarning("重复授权码", "此授权码已存在，请获取新的授权码")
                    return
                
                self._process_manual_auth(code, url, token_data)
            else:
                messagebox.showerror("错误", "URL处理失败")
    
    def _process_manual_auth(self, code, url, token_data):
        """处理手动授权"""
        try:
            if self._save_oauth_data(code, url, token_data):
                self.current_code = code
                
                from fetcher import CalendarFetcher
                fetcher = CalendarFetcher()
                success = fetcher.fetch_calendar_data()
                
                if success:
                    messagebox.showinfo("完成", "OAuth授权和日历获取完成！")
                    self.root.destroy()
                else:
                    raise Exception("日历数据获取失败")
            else:
                raise Exception("保存OAuth数据失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"处理失败: {str(e)}")
            self.monitoring = True
            self._start_monitoring()
    
    def _cancel(self):
        """取消操作"""
        self.monitoring = False
        self.root.destroy()
    
    def run(self):
        """运行GUI"""
        try:
            # 设置窗口属性
            self.root.protocol("WM_DELETE_WINDOW", self._cancel)
            self.root.focus_force()
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.after(100, lambda: self.root.attributes('-topmost', False))
            
            # 启动事件循环
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("用户中断OAuth授权")
            self._cancel()
        except Exception as e:
            logger.error(f"OAuth GUI异常: {e}")
            self._cancel()


def main():
    """主函数"""
    app = OAuthGUI()
    app.run()


if __name__ == "__main__":
    main()