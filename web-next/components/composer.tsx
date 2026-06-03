"use client";

import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";

const QUICK_REPLIES: Record<string, string[]> = {
  parsing: ["放好了"],
  parsed: ["继续"],
  materials_preparing: ["继续"],
  draft_ready: ["终审", "导出"],
  reviewing: ["导出"],
  done: ["导出"],
};

export function Composer({
  onSend,
  onStop,
  isStreaming,
  status,
}: {
  onSend: (text: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  status: string;
}) {
  const [input, setInput] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  // 自动调整高度
  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = "auto";
      ref.current.style.height = ref.current.scrollHeight + "px";
    }
  }, [input]);

  const send = () => {
    const t = input.trim();
    if (!t || isStreaming) return;
    onSend(t);
    setInput("");
  };

  const replies = QUICK_REPLIES[status] || ["放好了", "继续", "生成", "终审", "导出"];

  return (
    <div className="border-t border-border bg-surface px-8 py-4">
      {/* Quick replies */}
      <div className="flex gap-2 mb-3 flex-wrap">
        {replies.map((r) => (
          <button
            key={r}
            onClick={() => onSend(r)}
            disabled={isStreaming}
            className="text-[11px] px-2.5 py-1 bg-paper text-ink-light border border-border rounded-sm hover:border-amber hover:text-ink disabled:opacity-50"
          >
            {r}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="flex items-end gap-2">
        <textarea
          ref={ref}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder="输入消息… (Enter 发送，Shift+Enter 换行)"
          rows={1}
          className={cn(
            "flex-1 px-3 py-2 text-sm bg-paper border border-border rounded-sm resize-none",
            "focus:outline-none focus:border-amber max-h-32"
          )}
        />
        {isStreaming ? (
          <button
            onClick={onStop}
            className="px-4 py-2 text-sm bg-ink-light text-paper rounded-sm hover:bg-ink"
          >
            停止
          </button>
        ) : (
          <button
            onClick={send}
            disabled={!input.trim()}
            className="px-4 py-2 text-sm bg-ink text-paper rounded-sm disabled:opacity-50 hover:bg-ink-light"
          >
            发送
          </button>
        )}
      </div>
    </div>
  );
}
