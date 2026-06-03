"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { ParserReport } from "./parser-report";

/**
 * parseTender 工具的渲染。
 *  - state: input-streaming / input-available / output-available
 *  - input: { mode, projectId }
 *  - output: ParsedData（full K01-K14 + meta + 8 modules + markers）
 */
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
      <div className="bg-red-50 border border-red-200 rounded-sm p-3 text-xs text-danger">
        解析失败：{errorText}
      </div>
    );
  }

  // input-available 但 output 还没来 → 显示进度
  if (state === "input-available" || state === "input-streaming") {
    return (
      <div className="bg-surface border border-border rounded-sm p-3">
        <div className="flex items-center gap-2 text-xs text-ink-light">
          <span className="inline-block w-2 h-2 bg-amber rounded-full animate-pulse" />
          解析进行中… (mode={input?.mode ?? "auto"})
        </div>
      </div>
    );
  }

  // output-available → 完整报告
  if (state === "output-available" && output) {
    return (
      <div className="bg-surface border border-border rounded-sm overflow-hidden">
        <button
          onClick={() => setExpanded((e) => !e)}
          className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-paper/50"
        >
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-ink">解析报告</span>
            <span className="text-[10px] text-stone uppercase">
              {output._mode ?? "full"}
            </span>
          </div>
          <span className="text-xs text-stone">{expanded ? "收起" : "展开"}</span>
        </button>
        {expanded && <ParserReport data={output} />}
      </div>
    );
  }

  return null;
}
