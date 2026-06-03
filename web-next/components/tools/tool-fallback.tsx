"use client";

/**
 * 通用工具 fallback — 渲染 JSON input/output
 */
export function ToolFallback({
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
  return (
    <div className="bg-surface border border-border rounded-sm p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[10px] font-mono px-1.5 py-0.5 bg-amber-light text-amber rounded-sm">
          {toolName}
        </span>
        <span className="text-[10px] text-stone">{state}</span>
      </div>
      {errorText && (
        <div className="text-xs text-danger mb-2">{errorText}</div>
      )}
      {output && (
        <pre className="text-[10px] font-mono text-ink-light overflow-x-auto max-h-60 overflow-y-auto">
          {JSON.stringify(output, null, 2)}
        </pre>
      )}
    </div>
  );
}
