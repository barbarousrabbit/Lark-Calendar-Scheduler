# 飞书日历自动同步工具 - CalendarScheduler

## 项目简介

CalendarScheduler 是一个自动化的日历同步工具，可以从飞书日历获取数据并上传到飞书表格。支持OAuth授权、自动筛选、定时任务等功能。

## 功能特性

- 🔐 **OAuth授权**：安全的飞书API授权流程
- 📅 **智能筛选**：自动获取当前月及未来2个月的日历事件
- 🤖 **自动同步**：定时获取日历数据并上传到飞书表格
- 📊 **记录跟踪**：避免重复上传，维护同步状态
- 🖥️ **图形界面**：友好的OAuth授权窗口
- ⏰ **定时任务**：工作日自动执行同步任务

## 快速开始

### 使用预编译版本（推荐）

1. 下载 `CalendarScheduler.zip` 文件
2. 解压到任意目录
3. 双击 `CalendarScheduler.exe` 启动程序
4. 按照提示完成OAuth授权
5. 程序将自动开始同步日历数据

### 从源码运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序
python run.py
```

## 命令行参数

```bash
# 立即执行一次任务
python run.py --run-once
# 或
CalendarScheduler.exe --run-once

# 启动调度器并立即执行
python run.py --run-immediate
# 或
CalendarScheduler.exe --run-immediate

# 启动定时调度器
python run.py --run
# 或
CalendarScheduler.exe --run

# 显示状态
python run.py --status
# 或
CalendarScheduler.exe --status

# 停止调度器
python run.py --stop
# 或
CalendarScheduler.exe --stop
```

## 配置说明

程序的配置信息在 `src/config.py` 中：

- **OAUTH_CONFIG**：OAuth授权配置
- **API_CONFIG**：飞书API地址配置
- **TABLE_CONFIG**：目标表格配置
- **SCHEDULE_CONFIG**：定时任务配置（默认工作日10:00执行）
- **PATHS**：数据存储路径配置

## 目录结构

```
Calendar/
├── CalendarScheduler.zip    # 最终打包文件
├── src/                     # 源代码目录
│   ├── config.py           # 配置文件
│   ├── logger.py           # 日志模块
│   ├── oauth.py            # OAuth授权模块
│   ├── fetcher.py          # 日历数据获取模块
│   ├── scheduler.py        # 调度器模块
│   ├── record_tracker.py   # 记录跟踪模块
│   └── direct_calendar_uploader.py  # 上传模块
├── data/                   # 配置数据目录
├── calendar_history/       # 日历历史记录
├── personal_calendars/     # 个人日历数据
├── record_tracking/        # 记录跟踪数据库
├── scheduler_logs/         # 程序运行日志
├── Lark_Calendar.ico      # 程序图标
├── run.py                 # 主运行脚本
└── requirements.txt       # 依赖文件
```

## 工作流程

1. **OAuth授权**：首次运行时弹出授权窗口，用户完成授权后获取访问令牌
2. **获取日历**：调用飞书API获取当前月及未来2个月的日历事件
3. **数据筛选**：过滤掉已取消、空标题、过期的事件
4. **记录跟踪**：检查哪些事件已经上传过，避免重复处理
5. **批量上传**：将新事件批量上传到飞书表格
6. **定时执行**：工作日自动执行上述流程

## 日期筛选逻辑

程序会获取以下时间范围的日历事件：
- **当前月**：从当月1号开始
- **未来2个月**：连续3个月的事件
- **示例**：如果当前是2025年9月，则获取9月、10月、11月的事件

## 注意事项

- ⚠️ **访问令牌**：飞书API访问令牌会在5分钟内失效，每次执行都需要重新授权
- 📁 **文件位置**：`Lark_Calendar.ico` 文件必须与exe在同一目录
- 🖥️ **无控制台**：exe版本运行时不会显示命令行窗口
- 🔄 **重复检查**：程序会自动避免上传重复的日历事件
- 📝 **日志记录**：所有操作都会记录在 `scheduler_logs/` 目录中

## 常见问题

### Q: OAuth授权窗口没有显示？
A: 检查是否有安全软件阻止，或尝试以管理员身份运行。

### Q: 提示"No module named xxx"错误？
A: 使用预编译的exe版本，或确保已安装所有依赖：`pip install -r requirements.txt`

### Q: 日历数据没有同步？
A: 检查 `scheduler_logs/` 目录中的日志文件，查看具体错误信息。

### Q: 如何修改同步时间？
A: 修改 `src/config.py` 中的 `SCHEDULE_CONFIG["work_time"]` 配置。

## 技术栈

- **Python 3.7+**
- **CustomTkinter**：现代化GUI界面
- **Requests**：HTTP请求处理
- **Schedule**：定时任务调度
- **SQLite**：本地数据存储
- **PyInstaller**：打包为exe文件

## 版本历史

- **v2025.09.09.2**：优化日期筛选功能，修复模块引用问题
- **v2025.09.09.1**：初始版本，实现基本同步功能

## 开发团队

如有问题或建议，请联系开发团队。

## 许可证

本项目仅供内部使用。