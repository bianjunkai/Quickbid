# QuickBid 实现日志

## 2026-05-30：Phase 1 — 冗余代码清理

### 已移除

| 文件/目录 | 说明 | 决策依据 |
|-----------|------|----------|
| `Design.md` | 编码损坏（`\&\#34;`、`\n` 字面量），与 `docs/technical-design.md` 重复 | 保留 `docs/` 中版本为唯一真相源 |
| `ui/` 全部 5 个文件 | PyQt5 桌面 GUI（basic_info_page.py, info_page.py, OutlinePage.py, quick_bid.ui, __init__.py） | 与确认驱动对话理念矛盾，数据模型（QObject+dataclass）与 SQLAlchemy 不兼容，零代码共享 |
| `ui_main.py` | pyuic5 从 .ui 自动生成的 UI 代码 | 依赖已删除的 ui/ 包 |
| `core/data_model.py` | PyQt5 QObject+pyqtSignal 数据模型 | 仅被 PyQt5 UI 引用，与 SQLAlchemy models.py 并行且不兼容 |
| ` resources/styles/styles.qss` | Qt 样式表（目录名带前导空格） | 仅 PyQt5 UI 使用，无其他引用 |
| `web/src/components/HelloWorld.vue` | Vite 脚手架默认组件 | 未被任何路由或组件引用 |
| `web/src/assets/vite.svg` | Vite 脚手架资源 | 仅被 HelloWorld.vue 引用 |
| `web/src/assets/vue.svg` | Vite 脚手架资源 | 仅被 HelloWorld.vue 引用 |
| `web/src/assets/hero.png` | Vite 脚手架资源 | 仅被 HelloWorld.vue 引用 |

### 清理后文件结构

```
Quickbid/
├── .gitignore
├── README.md
├── cli.py
├── config.yaml
├── main.py
├── models.py
├── docs/
│   ├── multi-agent-architecture.md   ← v3 架构设计（新增）
│   └── technical-design.md
└── web/                              ← Vue.js 前端（已清理）
```

### 后续待处理

- Phase 2：关键 Bug 修复


## 2026-05-30：Phase 2 — 关键 Bug 修复 + 基础设施

### 修复清单

| Bug | 文件 | 修复内容 |
|-----|------|---------|
| 导入崩溃 | `main.py:14` | 移除 `TenderType, ProjectStatus` 导入（不存在），所有枚举引用替换为字符串字面量 |
| 缺少导入 | `main.py:5` | 添加 `import json` 和 `from datetime import datetime` |
| JSON 序列化 | `main.py:209` | `str(parsed)` → `json.dumps(parsed, ensure_ascii=False)` |
| 枚举属性访问 | `main.py:133,150,264` | `p.status.value if hasattr(...)` → `p.status`（状态是纯字符串） |
| 配置路径硬编码 | `cli.py:14`, `main.py:17` | 优先项目本地 `config.yaml`，回退 `~/.tender-tool/` |
| 数据库路径硬编码 | `models.py:98` | 优先项目本地 `tender.db`，支持 `TENDER_DB_PATH` 环境变量 |
| 配置路径 | `config.yaml` | `~/tender-tool/` → `./` 相对路径 |
| .gitignore 拼写 | `.gitignore` | `.sesion.json` → `.session.json`，添加 `node_modules/` |
| 缺少依赖文件 | — | 创建 `requirements.txt` |
| 缺少运行时目录 | — | 创建 `materials/` (6 分类)、`projects/`、`exports/`、`scripts/` + `.gitkeep` |
| createMaterial 缺失 | `web/src/api/index.ts` | 添加 `createMaterial` 导出 |
| Pinia store 损坏 | `web/src/store/project.ts` | `createProject` 改为调用正确 API，添加缺失的 API imports |
| CSS 冲突 | `web/src/style.css` | Vite scaffold CSS → 最小化 Element Plus 兼容重置 |
| API 参数不匹配 | `main.py:275` | `create_material` 从查询参数改为 Pydantic `CreateMaterialRequest` body |

### 更新后文件结构

```
Quickbid/
├── config.yaml              ← 已更新（相对路径）
├── requirements.txt         ← 新增
├── .gitignore               ← 已修正
├── README.md
├── cli.py                   ← 已修复（配置路径）
├── main.py                  ← 已修复（导入/序列化/API 参数）
├── models.py                ← 已修复（DB 路径 + os import）
├── docs/
│   ├── technical-design.md  ← 已重写（反映当前实际）
│   ├── multi-agent-architecture.md
│   └── implementation-log.md
├── materials/               ← 新增（6 分类 + .gitkeep）
├── projects/                ← 新增（.gitkeep）
├── exports/                 ← 新增（.gitkeep）
├── scripts/                 ← 新增（空目录）
└── web/                     ← 已修复（api/store/style）
```

### 后续待处理

- Phase 3：多 Agent 框架搭建（agents/ + orchestrator.py）
