# PC 使用时间监控与健康提醒 - PRD（完整版）

> **版本**：v1.1  
> **最后更新**：2025-02  
> **状态**：草稿 · 待评审

---

## 目录

1. 背景与目标
2. 用户与使用场景
3. 总体方案（高层架构）
4. 功能需求（MVP）
5. 数据与模型
6. 权限与安全/隐私
7. 性能与稳定性要求
8. **技术框架选型**（新增）
9. **模块拆解与接口定义**（新增）
10. **开发计划与里程碑**（新增）
11. 兼容性与打包（Nuitka）
12. 验收标准

---

## 1. 背景与目标

### 1.1 背景
用户希望在 PC 端长期、低打扰地记录"正在使用什么软件/页面、用了多久"，并能把数据转化为直观的统计图表；同时希望具备"健康使用电脑"的强提醒能力（定时全屏遮罩休息提醒），并在日常使用中通过悬浮球/托盘快速感知当前焦点与累计情况。

### 1.2 产品目标
- 自动、连续记录当前焦点软件的使用时长
- 面对浏览器时，能记录到"当前标签页"，并对同一站点的不同 URL 进行智能归类聚合
- 提供可扩展的数据统计体系，MVP 先实现饼图与折线图
- 提供健康提醒：按规则定时弹出覆盖全屏的休息提示
- 提供悬浮球 + 气泡提示当前焦点软件/页面；可隐藏
- 提供托盘图标与常用操作入口
- 提供设置页面：查看统计数据、配置健康提醒、悬浮球等
- 满足 Nuitka 打包为 PC 端应用（优先 Windows）的工程与依赖约束

### 1.3 非目标（本期不做）
- 多设备同步、账号体系、云备份
- 深度内容识别（如识别视频标题、文档标题的全量解析）
- 企业级管控（强制策略下发、远程监控等）

---

## 2. 用户与使用场景

### 2.1 目标用户
- **自我管理型**：希望了解时间花在哪里、提升专注力的个人用户
- **自由职业/学生**：需要统计学习/工作时长与分布
- **电脑重度用户**：需要强制休息提醒预防疲劳

### 2.2 核心场景

| 场景 | 描述 |
|------|------|
| 场景 A | 用户日常使用多软件，系统自动统计各软件时长，并在设置页查看饼图 |
| 场景 B | 用户主要在浏览器里工作/娱乐，系统能按站点聚合时长（哔哩哔哩、知乎、GitHub 等） |
| 场景 C | 到达设定的工作时长后全屏遮罩提醒休息，用户可选择"开始休息/延迟/跳过" |
| 场景 D | 用户不打开主界面，也能通过悬浮球/托盘看到当前焦点与快捷操作 |

---

## 3. 总体方案（高层架构）

### 3.1 模块划分

```
┌─────────────────────────────────────────────────────────┐
│                        UI 层                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ 设置/统计 │  │  悬浮球  │  │  健康遮罩 │  │  托盘  │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
└─────────────────────────────────────────────────────────┘
         ↕ 事件/数据                    ↕ 命令
┌─────────────────────────────────────────────────────────┐
│                      核心服务层                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Tracker  │  │Analytics │  │ Health   │              │
│  │ 数据采集  │  │ 统计引擎  │  │ 健康管理  │              │
│  └────┬─────┘  └────┬─────┘  └──────────┘              │
└───────┼─────────────┼───────────────────────────────────┘
        ↓             ↓
┌─────────────────────────────────────────────────────────┐
│                      存储层 (SQLite)                     │
│   focus_events  │  day_aggregates  │  app_config        │
└─────────────────────────────────────────────────────────┘
        ↑
┌─────────────────────────────────────────────────────────┐
│                      采集适配层                          │
│   Win32 API     │  浏览器扩展 WebSocket  │  URL 归类器   │
└─────────────────────────────────────────────────────────┘
```

### 3.2 数据流

```
1s 定时器
  └→ Tracker.poll()
       ├→ Win32.get_foreground_window()  → (process, title)
       ├→ BrowserBridge.get_active_tab() → (url, domain)  [若焦点为浏览器]
       ├→ Classifier.classify()          → CategoryKey
       └→ Storage.append_slice()         → SQLite 写入
             └→ 每分钟触发 DayAggregate 累加
```

---

## 4. 功能需求（MVP）

### 4.1 使用时间采集

#### 4.1.1 前台应用识别
- 系统应能持续获取当前前台应用（进程名/可读应用名）与窗口标题
- 采样频率可配置（默认 1s，允许 0.5s~5s）
- 需处理边界情况：
  - 电脑锁屏/休眠：不计入使用时长（通过 `WM_WTSSESSION_CHANGE` 或 `win32api.GetLastInputInfo` 检测）
  - 无焦点窗口/桌面：计入"系统/桌面"或忽略（可配置）
  - 短时间切换：按采样累加即可

#### 4.1.2 浏览器标签页识别
- 支持至少 Chrome / Edge（Chromium 内核，扩展兼容）
- URL 获取方案（MVP 选方案 1）：
  - **方案 1（推荐）**：浏览器扩展通过 `chrome.tabs.onActivated` + `chrome.tabs.onUpdated` 监听活动 tab，经 WebSocket/Native Messaging 上报给本地 App
  - **方案 2（备选）**：浏览器远程调试端口（DevTools Protocol），部署复杂，权限风险高
- 当无法获取 URL 时，回退为仅记录"浏览器应用 + 窗口标题"

#### 4.1.3 智能归类聚合（站点级）
- 默认按 eTLD+1（主域名）聚合：`www.bilibili.com` → `bilibili.com`
- 支持站点别名映射（内置常用站点中文名，用户可自定义）
- 自定义规则优先级：精确匹配 > 域名后缀匹配 > 默认主域名聚合
- 对于"同站点不同路径"默认不细分

#### 4.1.4 计时与切片
- 计时口径：按采样时钟累加（每 1s 将 1s 记到当前聚合 key）
- 存储层支持：原始切片（可选）+ 日聚合（必须）
- 锁屏/休眠期间自动暂停计时，恢复时继续

### 4.2 数据统计与可扩展性

#### 4.2.1 统计维度
MVP 必须支持：
- 按时间：今天、昨天、近 7 天、近 30 天、自定义日期范围
- 按主体：应用（exe/进程）与站点（域名聚合后的站点名）

#### 4.2.2 图表
- **饼图**：选定时间范围内各应用/站点用时占比（Top10 + "其他"合并）
- **折线图**：选定时间范围内每日总用时趋势（或某一应用/站点的趋势）

#### 4.2.3 统计扩展机制
- 统计计算与 UI 解耦，UI 仅消费结构化数据对象
- 指标注册通过 `MetricRegistry` 集中管理
- 后续扩展只需实现 `BaseMetric` 接口并注册，无需改主流程

### 4.3 健康使用电脑（强提醒）

#### 4.3.1 规则与策略
| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 工作时长 X | 45 分钟 | 连续使用触发阈值 |
| 休息时长 Y | 5 分钟 | 休息倒计时时长 |
| 延迟时长 | 5 分钟 | 点"延迟"后推迟时长 |
| 每日最多跳过次数 | 2 次 | 0 表示不可跳过 |
| 白名单应用 | 空 | 白名单内应用不触发遮罩 |

#### 4.3.2 全屏遮罩交互
- 弹出覆盖全屏的遮罩窗口，置顶，不可被普通窗口遮挡
- 展示内容：休息提示文案、剩余休息倒计时
- 按钮：**开始休息** / **延迟 N 分钟** / **跳过**（按配置显示）
- 休息结束后自动关闭遮罩，重置计时器

### 4.4 悬浮球
- 默认显示可拖拽悬浮球（贴边吸附）
- 气泡信息：当前焦点应用名/站点名 + 当日已累计时长
- 支持一键隐藏/显示（从托盘与设置页）

### 4.5 托盘图标
- 常驻托盘，菜单提供：打开设置 / 暂停记录 / 暂停健康提醒 / 显示悬浮球 / 退出
- Hover 提示：今日总用时 / 当前焦点

### 4.6 设置页面

| 子页 | 核心功能 |
|------|---------|
| 统计页 | 时间范围选择、应用/站点切换、饼图+折线图、Top 列表 |
| 健康页 | 规则参数配置、白名单管理 |
| 外观与行为 | 悬浮球开关、开机自启、采样频率 |
| 隐私与数据 | 数据范围说明、隐私模式切换、数据清理 |

---

## 5. 数据与模型

### 5.1 核心概念

| 概念 | 描述 |
|------|------|
| FocusEvent | 某个时间片内用户正在使用的"归类项" |
| CategoryKey | 聚合维度的唯一 key（应用或站点） |
| DayAggregate | 按天聚合后的用时统计 |

### 5.2 数据库 Schema（SQLite）

```sql
-- 原始切片（可选，按需开启）
CREATE TABLE focus_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            INTEGER NOT NULL,          -- Unix timestamp (秒)
    date          TEXT    NOT NULL,          -- YYYY-MM-DD
    process_name  TEXT    NOT NULL,
    app_display   TEXT,
    window_title  TEXT,
    browser_name  TEXT,
    domain        TEXT,
    url           TEXT,                      -- 隐私模式下为 NULL
    category_type TEXT    NOT NULL,          -- 'app' | 'site'
    category_key  TEXT    NOT NULL,
    category_name TEXT    NOT NULL,
    duration_sec  INTEGER NOT NULL DEFAULT 1
);

-- 日聚合（必须，统计主表）
CREATE TABLE day_aggregates (
    date          TEXT NOT NULL,
    category_type TEXT NOT NULL,
    category_key  TEXT NOT NULL,
    category_name TEXT NOT NULL,
    duration_sec  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (date, category_key)
);

-- 用户配置
CREATE TABLE app_config (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- 索引
CREATE INDEX idx_events_date ON focus_events(date);
CREATE INDEX idx_agg_date    ON day_aggregates(date);
```

### 5.3 配置键（app_config）

| key | 默认值 | 说明 |
|-----|--------|------|
| `sample_interval_ms` | `1000` | 采样间隔（毫秒） |
| `health_work_min` | `45` | 工作阈值（分钟） |
| `health_rest_min` | `5` | 休息时长（分钟） |
| `health_delay_min` | `5` | 延迟时长（分钟） |
| `health_skip_max` | `2` | 每日最多跳过次数 |
| `health_whitelist` | `[]` | JSON 数组，白名单进程名 |
| `privacy_mode` | `true` | 是否仅存域名不存完整 URL |
| `floating_ball_visible` | `true` | 悬浮球是否可见 |
| `store_raw_events` | `false` | 是否保留原始切片 |
| `autostart` | `false` | 是否开机自启 |

---

## 6. 权限与安全/隐私
- 默认不采集键盘输入、截图、剪贴板等敏感信息
- URL 存储策略可配置：隐私模式（默认）仅存域名；详细模式存完整 URL（本地加密预留点）
- 本地数据库路径：`%APPDATA%\TimeTracker\data.db`
- 浏览器扩展仅申请 `tabs`（只读活动 tab URL）权限

---

## 7. 性能与稳定性要求
- 后台常驻 CPU 占用 < 1%（常态）
- 内存常态占用 < 150MB（含 UI 框架）
- 写库批量/异步（每 10s 批量写一次），避免频繁磁盘 IO
- 崩溃后自动重启不丢失当天聚合数据（允许最后 10s 内数据丢失）
- 日志文件自动滚动，保留最近 7 天

---

## 8. 技术框架选型（新增）

### 8.1 选型原则
1. **Nuitka 可打包**：避免运行时动态加载、避免难以静态分析的依赖
2. **Windows 原生能力可达**：能调用 Win32 API、系统托盘、全屏置顶窗口
3. **UI 框架轻量且稳定**：渲染图表，支持拖拽悬浮、全局置顶

### 8.2 技术栈选型表

| 层次 | 选型 | 备选 | 选型理由 |
|------|------|------|---------|
| **语言** | Python 3.11 | — | 生态丰富，Nuitka 支持最好 |
| **UI 框架** | PySide6（Qt6） | PyQt6 | 官方维护，Nuitka Qt 插件成熟，支持无边框窗口、全屏置顶；LGPL 可商用 |
| **图表** | PyQtGraph | Matplotlib | 原生 Qt，无需 WebEngine，Nuitka 打包体积小，渲染性能高 |
| **数据库** | SQLite（内置） | — | 零依赖，Nuitka 内置支持，无需额外进程 |
| **ORM/查询** | 原生 `sqlite3` + 薄封装 | SQLAlchemy | 避免 SQLAlchemy 动态特性导致打包问题 |
| **Win32 API** | `pywin32`（win32api/gui/con） | ctypes | 覆盖全面；Nuitka 有 pywin32 打包路径 |
| **系统托盘** | `pystray` | Qt QSystemTrayIcon | 轻量；或直接用 Qt（推荐统一用 Qt） |
| **浏览器通信** | WebSocket（`websockets` 库） | Native Messaging | 简单可靠，扩展与 App 双向通信 |
| **URL 解析** | `tldextract` | `urllib.parse` | 准确提取 eTLD+1，含内置 TLD 列表（可离线） |
| **配置序列化** | `json`（内置） | — | 轻量，无额外依赖 |
| **日志** | `logging`（内置）+ `RotatingFileHandler` | — | 无额外依赖 |
| **打包** | Nuitka（standalone 模式） | PyInstaller | 更好性能，生成真正编译产物 |
| **浏览器扩展** | Chrome Extension (Manifest V3) | — | 兼容 Chrome/Edge |

### 8.3 Nuitka 打包注意事项

```bash
# 推荐构建命令（示例）
python -m nuitka \
  --standalone \
  --onefile \
  --windows-disable-console \
  --enable-plugin=pyside6 \
  --include-data-dir=assets=assets \
  --include-package=tldextract \
  --windows-icon-from-ico=assets/icon.ico \
  main.py
```

- `pyside6` 插件由 Nuitka 官方维护，自动处理 Qt 依赖
- `tldextract` 包含 TLD 数据文件，需通过 `--include-data-files` 显式打包
- `pywin32` DLL 需手动指定 `--include-data-files=*.dll`
- 避免使用 `importlib.import_module` 动态导入（改为显式导入）

### 8.4 浏览器扩展技术方案

```
浏览器扩展（MV3）
  background.js
    ├─ chrome.tabs.onActivated  →  当前活动 tab 变化
    ├─ chrome.tabs.onUpdated    →  URL 变化
    └─ WebSocket 连接 ws://127.0.0.1:49152
         └─ 上报 { type: "tab_change", url, title, ts }

本地 App（Python）
  BrowserBridgeServer（asyncio WebSocket Server, 127.0.0.1:49152）
    └─ 接收消息 → 更新内存缓存 current_browser_tab
```

---

## 9. 模块拆解与接口定义（新增）

### 9.1 目录结构

```
timetracker/
├── main.py                    # 入口，初始化各模块，启动 Qt App
├── tracker/
│   ├── __init__.py
│   ├── win_api.py             # Win32 前台窗口获取
│   ├── browser_bridge.py      # WebSocket 服务，接收浏览器扩展消息
│   ├── classifier.py          # URL/进程 → CategoryKey 归类器
│   └── tracker.py             # 主采样定时器，整合各子模块
├── storage/
│   ├── __init__.py
│   ├── db.py                  # SQLite 连接管理，建表，批量写入
│   ├── models.py              # 数据类（dataclass）定义
│   └── repository.py          # CRUD 查询封装
├── analytics/
│   ├── __init__.py
│   ├── base_metric.py         # BaseMetric 抽象类
│   ├── metric_registry.py     # 指标注册中心
│   ├── pie_metric.py          # 饼图数据指标
│   └── trend_metric.py        # 折线图趋势指标
├── health/
│   ├── __init__.py
│   └── health_manager.py      # 健康提醒状态机与规则引擎
├── ui/
│   ├── __init__.py
│   ├── tray.py                # 系统托盘
│   ├── floating_ball.py       # 悬浮球窗口
│   ├── overlay.py             # 全屏遮罩窗口
│   └── settings/
│       ├── main_window.py     # 设置主窗口（Tab 容器）
│       ├── stats_page.py      # 统计页（图表）
│       ├── health_page.py     # 健康配置页
│       ├── general_page.py    # 外观与行为页
│       └── privacy_page.py    # 隐私与数据页
├── config/
│   ├── __init__.py
│   ├── config_manager.py      # 配置读写（SQLite app_config 表）
│   └── site_aliases.py        # 内置站点别名表
├── assets/
│   ├── icon.ico
│   └── icon_tray.png
├── browser_extension/
│   ├── manifest.json
│   ├── background.js
│   └── icon*.png
└── requirements.txt
```

### 9.2 核心接口定义

#### 9.2.1 Tracker 层

```python
# tracker/win_api.py
@dataclass
class WindowInfo:
    process_name: str       # 进程名（如 chrome.exe）
    app_display: str        # 显示名（如 Google Chrome）
    window_title: str       # 窗口标题
    is_fullscreen: bool     # 是否全屏（用于白名单判断）

def get_foreground_window() -> Optional[WindowInfo]: ...
def is_screen_locked() -> bool: ...

# tracker/browser_bridge.py
@dataclass
class TabInfo:
    url: str
    domain: str             # eTLD+1
    title: str
    browser: str            # 'chrome' | 'edge'
    ts: float               # 上报时间戳

class BrowserBridgeServer:
    async def start(self, host="127.0.0.1", port=49152): ...
    def get_current_tab(self) -> Optional[TabInfo]: ...

# tracker/classifier.py
@dataclass
class CategoryResult:
    category_type: str      # 'app' | 'site'
    category_key: str       # 唯一 key（如 bilibili.com 或 chrome.exe）
    category_name: str      # 显示名（如 哔哩哔哩）

class Classifier:
    def classify(
        self,
        window: WindowInfo,
        tab: Optional[TabInfo]
    ) -> CategoryResult: ...

# tracker/tracker.py
class Tracker:
    def start(self): ...
    def stop(self): ...
    def pause(self): ...
    def resume(self): ...
    # 每次采样后发射信号（PySide6 Signal）
    # on_sample: Signal(CategoryResult)
```

#### 9.2.2 Storage 层

```python
# storage/models.py
@dataclass
class FocusSlice:
    ts: int
    date: str
    process_name: str
    category_type: str
    category_key: str
    category_name: str
    duration_sec: int = 1
    domain: Optional[str] = None
    url: Optional[str] = None

@dataclass
class DayAggregate:
    date: str
    category_type: str
    category_key: str
    category_name: str
    duration_sec: int

# storage/repository.py
class Repository:
    def append_slice(self, slice: FocusSlice): ...
    def flush(self): ...  # 批量写入（每 10s 调用）
    def get_aggregates(
        self,
        start_date: str,
        end_date: str,
        category_type: Optional[str] = None
    ) -> List[DayAggregate]: ...
    def get_today_total(self) -> int: ...  # 今日总秒数
    def get_today_current(self, category_key: str) -> int: ...
```

#### 9.2.3 Analytics 层

```python
# analytics/base_metric.py
@dataclass
class MetricQuery:
    start_date: str
    end_date: str
    category_type: str      # 'app' | 'site'
    top_n: int = 10

class BaseMetric(ABC):
    metric_id: str
    display_name: str

    @abstractmethod
    def compute(self, query: MetricQuery, repo: Repository) -> dict: ...

# analytics/pie_metric.py
# compute() 返回：
# {
#   "labels": ["哔哩哔哩", "VSCode", "其他"],
#   "values": [3600, 7200, 1800],   # 秒
#   "total": 12600
# }

# analytics/trend_metric.py
# compute() 返回：
# {
#   "dates": ["2025-01-01", ...],
#   "series": [
#     {"key": "bilibili.com", "name": "哔哩哔哩", "values": [3600, ...]},
#     ...
#   ]
# }
```

#### 9.2.4 Health 层

```python
# health/health_manager.py
class HealthState(Enum):
    WORKING = "working"
    OVERLAY_SHOWN = "overlay_shown"
    RESTING = "resting"
    PAUSED = "paused"

class HealthManager:
    # 信号（PySide6 Signal）
    # on_show_overlay: Signal()
    # on_hide_overlay: Signal()
    # on_rest_tick: Signal(int)   # 剩余秒数

    def start(self): ...
    def stop(self): ...
    def pause(self): ...
    def resume(self): ...
    def notify_working(self, duration_sec: int): ...  # Tracker 每秒调用
    def user_start_rest(self): ...
    def user_delay(self): ...
    def user_skip(self) -> bool: ...   # 返回 False 表示跳过次数已用完
```

#### 9.2.5 UI 层信号总线

```python
# 使用 PySide6 的 Signal/Slot 机制
# 主要信号流：
# Tracker.on_sample       → FloatingBall.update_display()
# Tracker.on_sample       → HealthManager.notify_working()
# HealthManager.on_show   → Overlay.show()
# HealthManager.on_hide   → Overlay.hide()
# HealthManager.on_tick   → Overlay.update_countdown()
# Tray.menu_action        → Tracker/HealthManager/FloatingBall
```

---

## 10. 开发计划与里程碑（新增）

### 10.1 整体节奏

| 阶段 | 时间 | 目标 |
|------|------|------|
| **Phase 0**：环境搭建 | 第 1 周 | 开发环境就绪，Nuitka 打包验证 |
| **Phase 1**：核心采集 | 第 2-3 周 | Tracker + Storage 可用 |
| **Phase 2**：UI 基础 | 第 4-5 周 | 悬浮球 + 托盘 + 设置主窗口 |
| **Phase 3**：浏览器集成 | 第 6 周 | 浏览器扩展 + BrowserBridge |
| **Phase 4**：统计图表 | 第 7-8 周 | Analytics + 饼图 + 折线图 |
| **Phase 5**：健康提醒 | 第 9 周 | 全屏遮罩 + HealthManager |
| **Phase 6**：集成测试 | 第 10 周 | 联调 + Bug 修复 + Nuitka 产物验证 |

**预计 MVP 总工期：10 周（2.5 个月）**

---

### 10.2 详细任务拆解

#### Phase 0：环境搭建（第 1 周）

| Task | 描述 | 估时 |
|------|------|------|
| P0-1 | 配置 Python 3.11 开发环境，安装 PySide6、pywin32、tldextract 等 | 0.5d |
| P0-2 | 验证 Nuitka + PySide6 最小打包 Hello World 可运行 | 1d |
| P0-3 | 初始化项目结构、Git 仓库、CI 脚本（可选） | 0.5d |
| P0-4 | 验证 pywin32 `GetForegroundWindow` 在 Win10/Win11 下基本可用 | 0.5d |

**Phase 0 产出**：可打包的最小 Qt 窗口 Hello World

---

#### Phase 1：核心采集 + 存储（第 2-3 周）

| Task | 描述 | 估时 |
|------|------|------|
| P1-1 | `win_api.py`：实现 `get_foreground_window()` 和 `is_screen_locked()` | 1d |
| P1-2 | `classifier.py`：实现进程 → CategoryKey 归类，内置常用 app 别名 | 1d |
| P1-3 | `db.py`：SQLite 建表、连接管理、批量写入队列 | 1d |
| P1-4 | `repository.py`：实现 `append_slice()`、`flush()`、`get_aggregates()` | 1d |
| P1-5 | `tracker.py`：主采样定时器（QTimer），整合 win_api + classifier + storage | 1.5d |
| P1-6 | `config_manager.py`：配置读写封装，支持默认值 | 0.5d |
| P1-7 | 单元测试：Tracker 采样逻辑、Classifier 归类、Repository 写读 | 1d |

**Phase 1 产出**：无界面情况下后台运行，可在 SQLite 中看到采集记录

---

#### Phase 2：UI 基础（第 4-5 周）

| Task | 描述 | 估时 |
|------|------|------|
| P2-1 | `tray.py`：系统托盘图标，菜单（打开设置/暂停/退出），Hover 提示 | 1d |
| P2-2 | `floating_ball.py`：无边框置顶窗口，可拖拽，气泡文字显示，贴边吸附 | 2d |
| P2-3 | `settings/main_window.py`：Tab 容器主窗口，页面切换框架 | 0.5d |
| P2-4 | `settings/general_page.py`：悬浮球开关、开机自启、采样频率设置 UI | 1d |
| P2-5 | `settings/privacy_page.py`：隐私模式切换、数据清理入口 | 0.5d |
| P2-6 | 托盘与悬浮球的双向联动（隐藏/显示），整合 Tracker 信号 | 0.5d |

**Phase 2 产出**：托盘常驻 + 悬浮球展示当前焦点 + 设置窗口可打开

---

#### Phase 3：浏览器集成（第 6 周）

| Task | 描述 | 估时 |
|------|------|------|
| P3-1 | 浏览器扩展：`manifest.json`（MV3），`background.js` 监听 tab 变化 | 1d |
| P3-2 | 扩展 WebSocket 客户端，连接本地 App，上报 tab 信息，断线重连 | 0.5d |
| P3-3 | `browser_bridge.py`：asyncio WebSocket 服务端，与 Qt 事件循环集成 | 1d |
| P3-4 | `classifier.py`：集成 `tldextract`，实现 URL → eTLD+1 + 别名映射 | 0.5d |
| P3-5 | `site_aliases.py`：内置 50+ 常用中文站点别名，支持用户自定义规则 | 0.5d |
| P3-6 | 端到端测试：Chrome/Edge 切换 Tab，验证域名聚合正确性 | 0.5d |

**Phase 3 产出**：浏览器标签页实时上报，域名聚合正确写入 DB

---

#### Phase 4：统计图表（第 7-8 周）

| Task | 描述 | 估时 |
|------|------|------|
| P4-1 | `base_metric.py` + `metric_registry.py`：指标抽象与注册机制 | 0.5d |
| P4-2 | `pie_metric.py`：饼图数据计算（TopN + 其他合并） | 1d |
| P4-3 | `trend_metric.py`：折线图趋势数据计算（按天聚合） | 1d |
| P4-4 | `settings/stats_page.py`：时间范围选择器 + 应用/站点切换 | 1d |
| P4-5 | PyQtGraph 饼图组件封装（PyQtGraph 无原生饼图，需用 `pg.GraphicsObject` 自绘） | 1.5d |
| P4-6 | PyQtGraph 折线图组件封装（`pg.PlotWidget`） | 1d |
| P4-7 | Top 列表 UI（`QTableWidget`），与图表联动 | 0.5d |

**Phase 4 产出**：统计页完整可用，饼图 + 折线图数据准确

---

#### Phase 5：健康提醒（第 9 周）

| Task | 描述 | 估时 |
|------|------|------|
| P5-1 | `health_manager.py`：状态机实现（Working → Overlay → Resting → Working） | 1.5d |
| P5-2 | 规则引擎：连续工作时长计算、跳过次数统计、每日重置 | 0.5d |
| P5-3 | `overlay.py`：全屏置顶遮罩窗口，倒计时显示，三按钮交互 | 1.5d |
| P5-4 | 白名单检测：全屏窗口检测（自动跳过），进程名白名单 | 0.5d |
| P5-5 | `settings/health_page.py`：规则参数配置 UI + 白名单管理 | 0.5d |
| P5-6 | 健康功能端到端测试（加速时间模拟到点场景） | 0.5d |

**Phase 5 产出**：健康遮罩可靠触发，延迟/跳过按配置正确工作

---

#### Phase 6：集成测试与打包（第 10 周）

| Task | 描述 | 估时 |
|------|------|------|
| P6-1 | 全量联调：Tracker + Storage + Analytics + Health + UI 全链路 | 1.5d |
| P6-2 | 24 小时稳定性测试（监控 CPU/内存，验证不崩溃） | 1d |
| P6-3 | Nuitka standalone 打包，修复打包问题（DLL 缺失、资源路径等） | 1d |
| P6-4 | Windows 10 / Windows 11 双版本验证 | 0.5d |
| P6-5 | 用户文档（安装说明、扩展安装说明、FAQ） | 0.5d |
| P6-6 | Bug 修复 Buffer | 1d |

**Phase 6 产出**：可分发的 MVP 绿色包 + 浏览器扩展安装包

---

### 10.3 MVP 里程碑验收节点

| 里程碑 | 节点 | 核心验收标准 |
|--------|------|-------------|
| M1 | Phase 1 结束 | 后台采集运行 1h，DB 数据可查，CPU < 1% |
| M2 | Phase 2 结束 | 托盘 + 悬浮球可用，设置窗口可打开 |
| M3 | Phase 3 结束 | 浏览器域名聚合准确，同站点不同 URL 归为一项 |
| M4 | Phase 4 结束 | 30 天数据量下，图表加载 < 2s，数据误差 < 2% |
| M5 | Phase 5 结束 | 健康遮罩到点可靠触发，置顶不被遮挡 |
| **MVP** | Phase 6 结束 | 24h 不崩溃，Nuitka 产物可在干净 Win10/11 运行 |

---

### 10.4 风险与应对

| 风险 | 概率 | 影响 | 应对方案 |
|------|------|------|---------|
| Nuitka 打包 PySide6 遇到兼容性问题 | 中 | 高 | Phase 0 提前验证；备选 PyInstaller |
| asyncio WebSocket 与 Qt 事件循环集成复杂 | 中 | 中 | 使用 `qasync` 库桥接；或在独立线程运行 asyncio |
| PyQtGraph 无原生饼图，自绘工作量超预期 | 中 | 中 | 备选 Matplotlib（确认 Nuitka 可打包后使用） |
| Win32 API 在某些 Win11 版本权限变化 | 低 | 中 | 测试覆盖 Win11 22H2+；预留 UIAutomation 备选 |
| 浏览器扩展 MV3 `tabs` 权限审查 | 低 | 低 | 扩展为本地安装（开发者模式），无需商店审核 |

---

## 11. 兼容性与打包（Nuitka）

- **目标平台**：Windows 10 / 11（MVP）
- **运行形态**：后台常驻 + UI（设置页、遮罩、悬浮球）+ 托盘
- **依赖约束**：
  - 避免大量动态加载与不可分析依赖
  - `tldextract` TLD 数据文件需随包分发
  - `pywin32` DLL 需显式包含
- **产物目标**：
  - v0.1：绿色版目录包（可运行）
  - v0.2+：安装包（NSIS / WiX）

---

## 12. 验收标准（MVP）

| 验收项 | 标准 |
|--------|------|
| 稳定性 | 连续运行 24 小时不崩溃 |
| 采集准确性 | 统计结果与实际使用大体一致（误差在采样口径允许范围内，< 2%） |
| 浏览器集成 | 浏览器场景下能稳定记录到站点级，同站点不同 URL 聚合为同一项 |
| 图表性能 | 饼图与折线图在 30 天数据量下加载流畅（< 2s） |
| 健康遮罩 | 到点时可靠置顶覆盖，按配置支持延迟/跳过 |
| 悬浮球/托盘 | 悬浮球可隐藏，托盘可完成核心操作 |
| 打包 | Nuitka 产物可在干净 Windows 10/11 环境运行，无需 Python 环境 |
| 性能 | 后台 CPU < 1%，内存 < 150MB |
