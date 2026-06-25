"use client";

import { useState, useRef, useEffect } from "react";
import { Paperclip, Send, Square, Plus, AtSign } from "lucide-react";
import { cn } from "@/lib/utils";

const QUICK_REPLIES: Record<string, string[]> = {
  parsing: ["文件已上传，请开始解析"],
  parsed: ["继续", "价格测算"],
  outline_generating: ["继续", "价格测算"],
  materials_preparing: ["生成"],
  deviation_preparing: ["确认", "补充技术偏离："],
  generated: ["价格测算", "终审", "生成陪标", "导出Word"],
  reviewing: ["导出Word"],
  reviewed: ["生成陪标", "导出Word"],
  review_failed: ["终审"],
  done: ["生成陪标", "导出Word"],
};

const QUICK_REPLY_DESC: Record<string, string> = {
  "文件已上传，请开始解析": "读取并分析已上传的招标文件",
  继续: "确认当前结果并进入下一步",
  确认: "确认当前结果并继续",
  生成: "生成主标书",
  价格测算: "计算报价得分并检查异常低价风险",
  生成陪标: "生成陪标并自动终审",
  终审: "C01-C10 合规检查",
  导出: "导出最终版本",
  导出Word: "导出 Word 文件",
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

  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = "auto";
      ref.current.style.height = Math.min(ref.current.scrollHeight, 140) + "px";
    }
  }, [input]);

  const send = () => {
    const t = input.trim();
    if (!t || isStreaming) return;
    onSend(t);
    setInput("");
  };

  const replies = QUICK_REPLIES[status] || ["文件已上传，请开始解析", "继续", "生成", "终审", "导出"];

  return (
    <div className="absolute bottom-0 left-0 right-0 z-10 pointer-events-none">
      {/* Floating pill input */}
      <div className="px-6 pb-5 pointer-events-auto">
        <div className="max-w-3xl mx-auto">
          {/* Quick replies (above pill) */}
          {replies.length > 0 && !isStreaming && (
            <div className="flex items-center gap-1.5 mb-2.5 flex-wrap">
              {replies.map((r) => (
                <button
                  key={r}
                  onClick={() => onSend(r)}
                  className="group flex items-center gap-1.5 px-3 py-1.5 bg-[var(--color-surface)] text-[var(--color-ink-soft)] border border-[var(--color-border)] rounded-full text-[12px] font-medium hover:border-[var(--color-primary)] hover:text-[var(--color-primary-deep)] hover:bg-[var(--color-primary-bg)] transition-colors shadow-sm min-h-[32px]"
                  title={QUICK_REPLY_DESC[r]}
                >
                  <span>{r}</span>
                </button>
              ))}
            </div>
          )}

          {/* The floating pill */}
          <div
            className={cn(
              "flex items-end gap-1.5 p-2 bg-[var(--color-surface)] rounded-2xl border border-[var(--color-border)] transition-all",
              "shadow-[0_8px_32px_rgba(28,25,23,0.08),0_2px_8px_rgba(28,25,23,0.04)]",
              "focus-within:border-[var(--color-primary)] focus-within:shadow-[0_8px_32px_rgba(217,119,6,0.12),0_2px_8px_rgba(28,25,23,0.06)]"
            )}
          >
            <button
              aria-label="添加附件"
              className="w-9 h-9 rounded-xl text-[var(--color-ink-mute)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] flex items-center justify-center transition-colors shrink-0"
            >
              <Plus className="w-4 h-4" />
            </button>

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
              aria-label="消息输入"
              placeholder="输入指令或问题，QuickBid 来处理…"
              rows={1}
              className="flex-1 bg-transparent text-[14px] text-[var(--color-ink)] placeholder:text-[var(--color-ink-mute)] focus:outline-none resize-none px-1 py-2 max-h-[140px] leading-[1.5]"
            />

            <div className="flex items-center gap-1 pb-0.5">
              <button
                aria-label="附件"
                className="w-9 h-9 rounded-xl text-[var(--color-ink-mute)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] flex items-center justify-center transition-colors"
              >
                <Paperclip className="w-4 h-4" />
              </button>
              <button
                aria-label="提及"
                className="w-9 h-9 rounded-xl text-[var(--color-ink-mute)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] flex items-center justify-center transition-colors"
              >
                <AtSign className="w-4 h-4" />
              </button>
              {isStreaming ? (
                <button
                  onClick={onStop}
                  aria-label="停止生成"
                  className="ml-1 w-9 h-9 rounded-xl bg-[var(--color-ink)] text-[var(--color-paper)] hover:bg-[var(--color-danger)] flex items-center justify-center transition-colors"
                >
                  <Square className="w-3.5 h-3.5" fill="currentColor" />
                </button>
              ) : (
                <button
                  onClick={send}
                  disabled={!input.trim()}
                  aria-label="发送"
                  className="ml-1 w-9 h-9 rounded-xl bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-deep)] disabled:opacity-30 disabled:hover:bg-[var(--color-primary)] flex items-center justify-center transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
