"use client";

import type { UIMessage } from "ai";
import { Sparkles, User, ChevronRight, Copy, Maximize2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { ParseToolResult } from "./tools/parse-tool-result";
import { OutlineToolResult } from "./tools/outline-tool-result";
import { MatchToolResult } from "./tools/match-tool-result";
import { GeneratorToolResult } from "./tools/generator-tool-result";
import { ExportToolResult } from "./tools/export-tool-result";
import { ToolFallback } from "./tools/tool-fallback";

export function MessageList({
  messages,
  isStreaming,
}: {
  messages: UIMessage[];
  isStreaming: boolean;
}) {
  if (messages.length === 0) {
    return <EmptyHint />;
  }
  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-32">
      {messages.map((m, idx) => (
        <MessageBubble key={m.id} message={m} index={idx} />
      ))}
      {isStreaming && <StreamingIndicator />}
    </div>
  );
}

function MessageBubble({ message, index }: { message: UIMessage; index: number }) {
  const isUser = message.role === "user";
  return (
    <div
      className={cn(
        "slide-up flex gap-3 items-start",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-semibold shadow-sm",
          isUser
            ? "bg-[var(--color-ink-soft)]"
            : "bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-deep)]"
        )}
        aria-hidden
      >
        {isUser ? <User className="w-3.5 h-3.5" /> : <Sparkles className="w-3.5 h-3.5" />}
      </div>

      {/* Content */}
      <div className={cn("flex-1 min-w-0 space-y-2", isUser && "max-w-[80%]")}>
        {/* Meta line */}
        <div
          className={cn(
            "flex items-center gap-2 text-[11px] text-[var(--color-ink-mute)]",
            isUser && "justify-end"
          )}
        >
          <span className="font-medium text-[var(--color-ink-soft)]">
            {isUser ? "你" : "QuickBid"}
          </span>
          <span>·</span>
          <span>消息 #{index + 1}</span>
        </div>

        {/* Bubble or card */}
        {isUser ? (
          <div className="inline-block bg-[var(--color-primary-bg)] border border-[var(--color-primary-tint)] text-[var(--color-ink)] px-4 py-2.5 rounded-2xl rounded-tr-md text-[14px] leading-[1.6] max-w-full">
            {message.parts.map((p: any, i: number) =>
              p.type === "text" ? <span key={i}>{p.text}</span> : null
            )}
          </div>
        ) : (
          <div className="ai-card space-y-3">
            {message.parts.map((part: any, i: number) => {
              if (part.type === "text") {
                return <TextPart key={i} text={part.text} state={part.state} />;
              }
              if (part.type === "reasoning") return null;
              if (typeof part.type === "string" && part.type.startsWith("tool-")) {
                const toolName = part.type.replace(/^tool-/, "");
                return (
                  <ToolPart
                    key={i}
                    toolName={toolName}
                    state={part.state}
                    input={part.input}
                    output={part.output}
                    errorText={part.errorText}
                  />
                );
              }
              if (part.type === "dynamic-tool") {
                return (
                  <ToolPart
                    key={i}
                    toolName={part.toolName}
                    state={part.state}
                    input={part.input}
                    output={part.output}
                    errorText={part.errorText}
                  />
                );
              }
              return null;
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function TextPart({ text, state }: { text: string; state?: string }) {
  if (!text) return null;
  return (
    <div
      className={cn(
        "text-[14.5px] leading-[1.7] text-[var(--color-ink-soft)] whitespace-pre-wrap",
        state === "streaming" && "text-[var(--color-ink-mute)]"
      )}
    >
      {text}
    </div>
  );
}

function ToolPart({
  toolName,
  state,
  input,
  output,
  errorText,
}: {
  toolName: string;
  state: string;
  input?: any;
  output?: any;
  errorText?: string;
}) {
  if (toolName === "parseTender") {
    return <ParseToolResult state={state} input={input} output={output} errorText={errorText} />;
  }
  if (toolName === "outlineDesign") {
    return <OutlineToolResult state={state} input={input} output={output} errorText={errorText} />;
  }
  if (toolName === "matchMaterials") {
    return <MatchToolResult state={state} input={input} output={output} errorText={errorText} />;
  }
  if (toolName === "generateTender") {
    return <GeneratorToolResult state={state} input={input} output={output} errorText={errorText} />;
  }
  if (toolName === "exportTender") {
    return <ExportToolResult state={state} input={input} output={output} errorText={errorText} />;
  }
  return (
    <ToolFallback
      toolName={toolName}
      state={state}
      input={input}
      output={output}
      errorText={errorText}
    />
  );
}

function StreamingIndicator() {
  return (
    <div className="flex gap-3 items-start max-w-3xl mx-auto">
      <div className="shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-deep)] flex items-center justify-center text-white shadow-sm">
        <Sparkles className="w-3.5 h-3.5" />
      </div>
      <div className="flex items-center gap-1.5 pt-2">
        <span className="w-1.5 h-1.5 bg-[var(--color-primary)] rounded-full pulse-warm" />
        <span className="w-1.5 h-1.5 bg-[var(--color-primary)] rounded-full pulse-warm" style={{ animationDelay: "200ms" }} />
        <span className="w-1.5 h-1.5 bg-[var(--color-primary)] rounded-full pulse-warm" style={{ animationDelay: "400ms" }} />
      </div>
    </div>
  );
}

function EmptyHint() {
  const commands = [
    { cmd: "放好了", desc: "开始解析招标文件", n: "01" },
    { cmd: "继续", desc: "进入材料匹配", n: "02" },
    { cmd: "生成", desc: "生成主标书", n: "03" },
    { cmd: "终审", desc: "C01-C10 合规检查", n: "04" },
  ];
  return (
    <div className="max-w-2xl mx-auto py-8">
      {/* Hero */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)] text-[11px] font-medium mb-5">
          <Sparkles className="w-3 h-3" />
          QuickBid · 标书智能工作台
        </div>
        <h2 className="text-[40px] font-semibold text-[var(--color-ink)] leading-[1.05] tracking-tight">
          你好，<br />
          <span className="text-[var(--color-primary)]">开始今天的投标</span>
        </h2>
        <p className="mt-4 text-[14px] text-[var(--color-ink-mute)] max-w-md mx-auto leading-relaxed">
          确认驱动对话。AI 做一步 → 你确认/纠正 → 继续。
        </p>
      </div>

      {/* Commands card */}
      <div className="card-soft overflow-hidden">
        <div className="px-5 py-3 border-b border-[var(--color-border)] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-[var(--color-primary)]" />
            <span className="text-[12px] font-semibold text-[var(--color-ink)]">快捷指令</span>
          </div>
          <span className="text-[10px] text-[var(--color-ink-mute)] font-mono">04 / 04</span>
        </div>
        <ul>
          {commands.map((c, i) => (
            <li
              key={c.cmd}
              className={cn(
                "group flex items-center gap-4 px-5 py-3.5 cursor-pointer hover:bg-[var(--color-primary-bg)] transition-colors",
                i < commands.length - 1 && "border-b border-[var(--color-border)]"
              )}
            >
              <span className="text-[11px] text-[var(--color-ink-mute)] font-mono tabular-nums w-6">
                {c.n}
              </span>
              <span className="text-[14px] font-semibold text-[var(--color-ink)] group-hover:text-[var(--color-primary-deep)] min-w-[64px]">
                「{c.cmd}」
              </span>
              <span className="flex-1 text-[13px] text-[var(--color-ink-mute)]">
                {c.desc}
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-[var(--color-ink-mute)] group-hover:text-[var(--color-primary)] group-hover:translate-x-0.5 transition-transform" />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
