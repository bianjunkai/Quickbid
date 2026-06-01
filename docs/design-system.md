# QuickBid Design System

> AI-Native UI — Chatbot, conversational, ambient, minimal chrome

## Style: AI-Native UI

Chatbot-first conversation interface. AI做一步 → 用户确认/纠正 → 继续。每条消息就是一个工作流步骤，用户通过自然对话完成标书制作。

**Key Effects**: Typing indicators (3-dot pulse), streaming text, smooth message reveals, context cards
**Anti-patterns**: Heavy chrome, wizard steps, slow response, spinner for >3s

## Layout

```
┌──────────┬─────────────────────────────────────┐
│ Sidebar  │  Chat Messages                       │
│ 220px    │                                      │
│          │  [AI] 你好！我是标书制作助手...        │
│ Projects │  [User] 新建项目：xx医院HIS投标        │
│ Materials│  [AI] ✅ 项目已创建，请上传招标文件...  │
│          │  [User] 放好了                        │
│          │  [AI] 📋 解析完成！K01-K14...          │
│          │  [Quick Replies] [继续] [修改预算]     │
│          ├──────────────────────────────────────│
│          │  [Input_____________________] [Send]  │
└──────────┴─────────────────────────────────────┘
```

## Colors — Blue + White Messenger Style

| Role | Hex | Usage |
|------|-----|-------|
| Primary | `#2563EB` | AI message accent, links, send button |
| Primary Light | `#EFF6FF` | AI message bubble background |
| User Bubble | `#2563EB` | User message bubble (filled) |
| User Text | `#FFFFFF` | Text on user bubble |
| Background | `#FFFFFF` | Main chat background |
| Sidebar | `#F8FAFC` | Sidebar background |
| Border | `#E2E8F0` | Dividers |
| Text Primary | `#1E293B` | Message text |
| Text Secondary | `#64748B` | Timestamps, hints |
| Success | `#16A34A` | Confirmation |
| Warning | `#F59E0B` | Warnings |

## Typography

| Role | Font | Weight | Size |
|------|------|--------|------|
| Heading | Outfit | 600 | 20px |
| Body | Work Sans | 400 | 15px |
| Code/Data | JetBrains Mono | 400 | 13px |

```css
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Work+Sans:wght@300;400;500;600&display=swap');
```

## Effects

- Message reveal: fadeInUp 200ms ease-out
- Typing indicator: 3-dot pulse (scale 0→1→0, staggered)
- Send button: subtle scale on press
- Quick replies: chip buttons, hover bg shift 150ms
- Streaming: typewriter effect for AI responses (Phase 6)
- Cards in messages: 1px border, 8px radius, subtle shadow on hover

## Anti-Patterns

- Wizard step indicators
- Heavy navigation chrome
- Spinners for >3s (use typing indicator instead)
- Decorations that distract from conversation
- Non-streaming static AI text
