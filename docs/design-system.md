# QuickBid Design System — Document Studio

> 策略来源：Scanner & Document Manager + Legal Services + Warm Notes Palette + Swiss Modernism
> 核心原则：看起来像高端文档工具，不像 AI 聊天机器人

## 反 AI 设计原则

| AI 产品特征（避免） | QuickBid 替代方案（采用） |
|---------------------|--------------------------|
| 紫/粉/蓝紫渐变色 | 暖石色 + 奶油底 + 琥珀强调 |
| 聊天气泡 (左蓝右白) | 清晰排版层级 + 左侧标签卡片 |
| 打字机闪烁动画 | 静默的内容更新 + 小幅过渡 |
| "AI 正在思考..." 文案 | 无文案，或"处理中" / 不强调 AI |
| emoji 头像 / 机器人图标 | 纯文字标签 + 文件图标 |
| 圆角过度的输入框 | 方角或小圆角功能输入区 |
| 渐变背景 | 纯色暖奶油底 `#FFFBEB` |

## 色彩 — 暖调文书

| Token | Hex | Usage |
|-------|-----|-------|
| Paper | `#FFFBEB` | 页面底色 — 暖奶油纸 |
| Ink | `#44403C` | 正文 — 深石色 |
| Ink Light | `#78716C` | 次要文字 — 暖灰 |
| Stone | `#A8A29E` | 禁用/占位 |
| Surface | `#FFFFFF` | 卡片/面板 |
| Border | `#E7E5E4` | 分割线 |
| Amber | `#D97706` | 强调/CTA/激活态 |
| Amber Light | `#FEF3C7` | 强调背景 |
| Success | `#15803D` | 通过 |
| Warning | `#B45309` | 警告 |
| Danger | `#B91C1C` | 危险 |

## 字体 — 编辑级质感

| Role | Font | Weight | Size | Notes |
|------|------|--------|------|-------|
| 页面大标题 | Cormorant Garamond | 600 | 28px | 编辑级衬线，权威感 |
| 面板标题 | Cormorant Garamond | 500 | 18px | |
| 正文 | Public Sans | 400 | 15px | 功能性无衬线，可读 |
| 标签/提示 | Public Sans | 500 | 12px | |
| 数据/代码 | JetBrains Mono | 400 | 13px | |

```css
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Public+Sans:wght@300;400;500;600;700&display=swap');
```

## 空间 — Swiss Grid

- 基础单位: 8px
- 卡片间距: 16px
- 区块间距: 24px
- 页面边距: 32px
- 圆角: 4px (直角为主)
- 阴影: 无或极轻 (0 1px 3px rgba(0,0,0,0.04))

## 组件改造

### 消息 → 文档条目
- ~~聊天气泡~~ → 左侧彩色标签 + 卡片式内容
- AI 消息: 左侧石色细线 + 干净排版
- 用户消息: 右侧暖灰色背景卡片
- 无头像、无圆形气泡

### 输入区 → 功能栏
- 底部固定功能条
- 方形输入框，小圆角
- 发送按钮：文字 + 图标，非圆形

### 侧边栏 → 项目浏览器
- 干净文件树
- 项目名用衬线体
- 无多余装饰
