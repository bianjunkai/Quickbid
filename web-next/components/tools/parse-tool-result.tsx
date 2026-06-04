"use client";

import { useState } from "react";
import { ChevronDown, AlertOctagon, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { ParserReport } from "./parser-report";

export function ParseToolResult({
  state,
  input,
  output,
  errorText,
}: {
  state: string;
  input?: { mode?: string; projectId?: number };
  output?: any;
  errorText?: string;
}) {
  const [expanded, setExpanded] = useState(true);

  if (errorText) {
    return (
      <div className="card-soft p-4 border border-[var(--color-danger)]">
        <div className="flex items-center gap-2 mb-2">
          <AlertOctagon className="w-4 h-4 text-[var(--color-danger)]" />
          <span className="text-[12px] font-semibold text-[var(--color-danger)] uppercase tracking-wider">
            解析失败
          </span>
        </div>
        <div className="text-[13px] text-[var(--color-ink)] font-mono">{errorText}</div>
      </div>
    );
  }

  if (state === "input-available" || state === "input-streaming") {
    return (
      <div className="card-soft p-4">
        <div className="flex items-center gap-3">
          <Loader2 className="w-4 h-4 text-[var(--color-primary)] animate-spin" />
          <div className="flex-1">
            <div className="text-[12px] font-semibold text-[var(--color-ink)]">正在解析…</div>
            <div className="text-[11px] text-[var(--color-ink-mute)] font-mono mt-0.5">
              mode={input?.mode ?? "auto"} · project=#{String(input?.projectId ?? 0).padStart(3, "0")}
            </div>
          </div>
        </div>
        <div className="mt-3 h-1 rounded-full bg-[var(--color-paper-warm)] overflow-hidden">
          <div className="h-full w-1/3 bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-soft)] rounded-full animate-pulse" />
        </div>
      </div>
    );
  }

  if (state === "output-available" && output) {
    return (
      <div className="card-soft overflow-hidden">
        <button
          onClick={() => setExpanded((e) => !e)}
          className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-[var(--color-paper-warm)] transition-colors"
          aria-expanded={expanded}
        >
          <ChevronDown
            className={cn(
              "w-3.5 h-3.5 text-[var(--color-ink-mute)] transition-transform",
              !expanded && "-rotate-90"
            )}
          />
          <span className="w-2 h-2 rounded-full bg-[var(--color-success)]" />
          <span className="text-[13px] font-semibold text-[var(--color-ink)]">解析报告</span>
          <span className="text-[11px] text-[var(--color-ink-mute)] font-mono">
            · {output._mode ?? "full"}
          </span>
        </button>
        {expanded && (
          <div className="border-t border-[var(--color-border)]">
            <ParserReport data={output} />
          </div>
        )}
      </div>
    );
  }

  return null;
}
