"use client";

export function ToolFallback({
  toolName,
  state,
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
    <div className="card-soft overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[var(--color-border)] bg-[var(--color-paper-warm)]">
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)]" />
        <span className="text-[11px] font-mono font-semibold text-[var(--color-ink)]">{toolName}</span>
        <span className="ml-auto text-[10px] text-[var(--color-ink-mute)] font-mono">{state}</span>
      </div>
      {errorText && (
        <div className="px-4 py-2 bg-[var(--color-danger-bg)] border-b border-[var(--color-danger)]">
          <span className="text-[10px] text-[var(--color-danger)] font-semibold uppercase tracking-wider mr-2">
            错误
          </span>
          <span className="text-[11px] text-[var(--color-danger)] font-mono">{errorText}</span>
        </div>
      )}
      {output && (
        <pre className="text-[11px] font-mono text-[var(--color-ink)] overflow-x-auto max-h-60 overflow-y-auto px-4 py-3 bg-[var(--color-paper-warm)] leading-[1.6]">
          {JSON.stringify(output, null, 2)}
        </pre>
      )}
    </div>
  );
}
