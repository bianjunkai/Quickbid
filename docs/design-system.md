# QuickBid Design System

> 由 UI/UX Pro Max 生成，基于 Data-Dense Dashboard 风格

## Style

**Data-Dense Dashboard** — multiple charts/widgets, data tables, KPI cards, minimal padding, grid layout, space-efficient, maximum data visibility.

最适合：企业级运营面板、数据分析、招投标工具

## Colors

| Role | Hex | Tailwind | Usage |
|------|-----|----------|-------|
| Primary | `#2563EB` | `blue-600` | 主按钮、链接、选中态、品牌色 |
| Secondary | `#3B82F6` | `blue-500` | 次要操作、悬停态 |
| CTA | `#F97316` | `orange-500` | 关键行动按钮 |
| Background | `#F8FAFC` | `slate-50` | 页面背景 |
| Surface | `#FFFFFF` | `white` | 卡片、表格背景 |
| Text Primary | `#1E293B` | `slate-800` | 正文 |
| Text Secondary | `#64748B` | `slate-500` | 辅助文字 |
| Border | `#E2E8F0` | `slate-200` | 边框、分割线 |
| Success | `#16A34A` | `green-600` | 通过/成功 |
| Warning | `#F59E0B` | `amber-500` | 警告 |
| Danger | `#DC2626` | `red-600` | 失败/危险 |

## Typography

| Role | Font | Weight | Size |
|------|------|--------|------|
| Page Heading | Fira Code | 600 | 24px |
| Section Heading | Fira Code | 500 | 18px |
| Body | Fira Sans | 400 | 14px |
| Label | Fira Sans | 500 | 13px |
| Code/Data | Fira Code | 400 | 13px |
| Stats/Numbers | Fira Code | 600 | 28px |

```css
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');
```

## Spacing (4px base)

| Token | Value | Usage |
|-------|-------|-------|
| `xs` | 4px | 紧凑内边距 |
| `sm` | 8px | 元素间隔 |
| `md` | 16px | 组件内边距 |
| `lg` | 24px | 区块间隔 |
| `xl` | 32px | 页面区块 |
| `2xl` | 48px | 大区块分离 |

## Effects

- Hover: 行高亮 (`background-color` 变化 150ms)
- Focus: 2px 蓝色环 (`#2563EB`)
- Loading: 骨架屏 (skeleton)，非空白 spinner
- 过渡: 150-300ms `ease-out`
- 卡片: 1px border，无阴影 (扁平风格)
- 数据强调: 色彩 + 数字加粗

## Anti-Patterns (避免)

- 装饰性设计（无意义的渐变/阴影）
- 缺少筛选/搜索
- Emoji 作为图标
- 静态表格无排序
- 操作无反馈
