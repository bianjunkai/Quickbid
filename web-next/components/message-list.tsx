"use client";

import type { UIMessage } from "ai";
import { cn } from "@/lib/utils";
import { ParseToolResult } from "./tools/parse-tool-result";
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
    <div className="max-w-3xl mx-auto space-y-6">
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
    </div>
  );
}

function MessageBubble({ message }: { message: UIMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex gap-4", isUser ? "flex-row-reverse" : "flex-row")}>
      <div
        className={cn(
          "text-[10px] font-bold uppercase tracking-wider pt-1 w-9 shrink-0",
          isUser ? "text-ink-light text-right" : "text-stone"
        )}
      >
        {isUser ? "你" : "系统"}
      </div>
      <div className="flex-1 min-w-0 space-y-3">
        {message.parts.map((part, i) => {
          if (part.type === "text") {
            return <TextPart key={i} text={part.text} state={(part as any).state} />;
          }
          if (part.type === "reasoning") {
            return null; // 跳过 reasoning
          }
          if (typeof part.type === "string" && part.type.startsWith("tool-")) {
            const toolName = part.type.replace(/^tool-/, "");
            return (
              <ToolPart
                key={i}
                toolName={toolName}
                state={(part as any).state}
                input={(part as any).input}
                output={(part as any).output}
                errorText={(part as any).errorText}
              />
            );
          }
          if (part.type === "dynamic-tool") {
            return (
              <ToolPart
                key={i}
                toolName={(part as any).toolName}
                state={(part as any).state}
                input={(part as any).input}
                output={(part as any).output}
                errorText={(part as any).errorText}
              />
            );
          }
          return null;
        })}
      </div>
    </div>
  );
}

function TextPart({ text, state }: { text: string; state?: string }) {
  if (!text) return null;
  return (
    <div
      className={cn(
        "text-sm leading-7 whitespace-pre-wrap",
        state === "streaming" && "text-ink-light"
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

function EmptyHint() {
  return (
    <div className="max-w-2xl mx-auto py-16 text-center">
      <h2 className="font-display text-3xl text-ink mb-2">QuickBid</h2>
      <p className="text-sm text-stone mb-6">标书智能生成工作流</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-left">
        {[
          { label: "放好了", desc: "开始解析招标文件" },
          { label: "继续", desc: "进入材料匹配" },
          { label: "生成", desc: "生成主标书" },
          { label: "终审", desc: "C01-C10 检查" },
        ].map((q) => (
          <div
            key={q.label}
            className="bg-surface border border-border rounded-sm p-3 hover:border-amber cursor-pointer"
          >
            <div className="text-sm font-medium text-ink">「{q.label}」</div>
            <div className="text-xs text-stone mt-1">{q.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
