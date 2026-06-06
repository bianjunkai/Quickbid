"use client";

import {
  ChevronRight,
  Check,
  X,
  Calendar,
  Clock,
  Banknote,
  ShieldCheck,
  AlertOctagon,
  Scale,
  Cpu,
  Receipt,
  ListOrdered,
  Truck,
  Briefcase,
  Presentation,
  Send,
  FileText,
  Hash,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ComponentType, ReactElement, SVGProps } from "react";

// ============================================================
// 8 个模块的元信息（icon、name、accordion header 摘要）
// ============================================================

type ModuleSummary = (data: any) => string;

const MODULES: {
  key: string;
  name: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  accent: string;
  summary: ModuleSummary;
}[] = [
  {
    key: "base",
    name: "基本信息",
    icon: Briefcase,
    accent: "bg-[var(--color-primary)]/10 text-[var(--color-primary-deep)]",
    summary: (d) => `${d ? Object.keys(d).length : 0} 项字段`,
  },
  {
    key: "qualification",
    name: "资质要求",
    icon: ShieldCheck,
    accent: "bg-[var(--color-success-bg)] text-[var(--color-success)]",
    summary: (d) => `${d?.requirements?.length ?? 0} 项要求`,
  },
  {
    key: "rejection",
    name: "废标条款",
    icon: AlertOctagon,
    accent: "bg-[var(--color-danger-bg)] text-[var(--color-danger)]",
    summary: (d) => `${d?.conditions?.length ?? 0} 条条款`,
  },
  {
    key: "scoring",
    name: "评分标准",
    icon: Scale,
    accent: "bg-sky-50 text-sky-700",
    summary: (d) =>
      d?.method
        ? `${d.method} · ${d?.dimensions?.length ?? 0} 维度`
        : `${d?.dimensions?.length ?? 0} 个维度`,
  },
  {
    key: "tech",
    name: "技术要求",
    icon: Cpu,
    accent: "bg-violet-50 text-violet-700",
    summary: (d) => {
      const reqs = d?.functional_requirements?.length ?? 0;
      const mods = new Set(
        (d?.functional_requirements || []).map((r: any) => r.module).filter(Boolean)
      ).size;
      return `${mods} 个模块 · ${reqs} 项需求`;
    },
  },
  {
    key: "commercial",
    name: "商务条款",
    icon: Receipt,
    accent: "bg-amber-50 text-amber-700",
    summary: (d) => `${d ? Object.keys(d).length : 0} 项字段`,
  },
  {
    key: "templates",
    name: "章节模板",
    icon: ListOrdered,
    accent: "bg-emerald-50 text-emerald-700",
    summary: (d) => `${d?.bid_doc_structure?.length ?? 0} 章`,
  },
  {
    key: "logistics",
    name: "开标与递交",
    icon: Truck,
    accent: "bg-stone-200 text-stone-700",
    summary: (d) => {
      const method = d?.bid_submission?.method;
      const origs = d?.originals_to_bring?.length ?? 0;
      return `${method ?? "—"} · ${origs} 项原件`;
    },
  },
];

const MODULE_VIEWS: Record<string, (p: { data: any }) => ReactElement> = {
  base: BaseView,
  qualification: QualificationView,
  rejection: RejectionView,
  scoring: ScoringView,
  tech: TechView,
  commercial: CommercialView,
  templates: TemplatesView,
  logistics: LogisticsView,
};

// ============================================================
// Schema 主入口
// ============================================================

export function Schema({ data }: { data: any }) {
  const present = MODULES.filter((m) => data?.[m.key]);
  if (present.length === 0) {
    return <Empty text="无结构化数据（manual 模式可能为空）" />;
  }
  return (
    <div className="space-y-2.5">
      {present.map((meta) => {
        const Icon = meta.icon;
        const mod = data[meta.key];
        const summary = meta.summary(mod);
        return (
          <details key={meta.key} open className="card-soft overflow-hidden group">
            <summary className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-[var(--color-paper-warm)] transition-colors list-none">
              <ChevronRight className="w-3.5 h-3.5 text-[var(--color-ink-mute)] transition-transform group-open:rotate-90 shrink-0" />
              <span className={cn("w-6 h-6 rounded-md flex items-center justify-center shrink-0", meta.accent)}>
                <Icon className="w-3.5 h-3.5" />
              </span>
              <span className="text-[12.5px] font-semibold text-[var(--color-ink)]">
                {meta.name}
              </span>
              <span className="text-[10.5px] text-[var(--color-ink-mute)] font-mono">
                {summary}
              </span>
            </summary>
            <div className="border-t border-[var(--color-border)] bg-[var(--color-paper-warm)] p-4">
              <ModuleView moduleKey={meta.key} data={mod} />
            </div>
          </details>
        );
      })}
    </div>
  );
}

function ModuleView({ moduleKey, data }: { moduleKey: string; data: any }) {
  const View = MODULE_VIEWS[moduleKey];
  return <View data={data} />;
}

// ============================================================
// 公共小组件
// ============================================================

function Empty({ text }: { text: string }) {
  return (
    <div className="text-[12.5px] text-[var(--color-ink-mute)] text-center py-6">
      {text}
    </div>
  );
}

function SectionLabel({ children, count }: { children: React.ReactNode; count?: number }) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <h4 className="text-[11px] font-semibold text-[var(--color-ink)] uppercase tracking-wider">
        {children}
      </h4>
      {typeof count === "number" && (
        <span className="text-[10.5px] text-[var(--color-ink-mute)] font-mono">{count}</span>
      )}
    </div>
  );
}

function fmtMoney(amount: number | null | undefined, currency?: string) {
  if (amount == null) return null;
  const n = Number(amount);
  if (Number.isNaN(n)) return String(amount);
  const sym = currency === "CNY" || !currency ? "\u00a5" : `${currency} `;
  return `${sym} ${n.toLocaleString("zh-CN", { maximumFractionDigits: 2 })}`;
}

function fmtDate(s: any) {
  if (!s || typeof s !== "string") return null;
  const isoMatch = s.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  if (isoMatch) {
    return `${isoMatch[1]}-${isoMatch[2]}-${isoMatch[3]} ${isoMatch[4]}:${isoMatch[5]}`;
  }
  return s;
}

function BooleanDot({ value, trueLabel, falseLabel }: { value: boolean | null | undefined; trueLabel?: string; falseLabel?: string }) {
  if (value === true)
    return (
      <span className="inline-flex items-center gap-1 text-[11.5px] text-[var(--color-success)]">
        <Check className="w-3 h-3" />
        {trueLabel ?? "是"}
      </span>
    );
  if (value === false)
    return (
      <span className="inline-flex items-center gap-1 text-[11.5px] text-[var(--color-ink-mute)]">
        <X className="w-3 h-3" />
        {falseLabel ?? "否"}
      </span>
    );
  return <span className="text-[var(--color-ink-mute)] text-[11.5px]">\u2014</span>;
}

function RatioBar({ label, value, color }: { label: string; value: number | null | undefined; color: string }) {
  const v = typeof value === "number" ? value : null;
  return (
    <div className="flex items-center gap-3">
      <span className="text-[11.5px] text-[var(--color-ink)] w-12 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-[var(--color-border-soft)] rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", color)}
          style={{ width: v == null ? "0%" : `${Math.max(0, Math.min(100, v))}%` }}
        />
      </div>
      <span className="text-[11.5px] text-[var(--color-ink)] font-mono tabular-nums w-12 text-right shrink-0">
        {v == null ? "\u2014" : `${v}%`}
      </span>
    </div>
  );
}

function SeverityBadge({ severity }: { severity?: string | null }) {
  const map: Record<string, { color: string; bg: string; label: string }> = {
    FATAL: { color: "text-[var(--color-danger)]", bg: "bg-[var(--color-danger-bg)]", label: "FATAL" },
    HIGH: { color: "text-[var(--color-warning)]", bg: "bg-[var(--color-warning-bg)]", label: "HIGH" },
    CRITICAL: { color: "text-[var(--color-warning)]", bg: "bg-[var(--color-warning-bg)]", label: "CRITICAL" },
    MEDIUM: { color: "text-amber-700", bg: "bg-amber-50", label: "MEDIUM" },
    LOW: { color: "text-[var(--color-ink-mute)]", bg: "bg-[var(--color-paper-warm)]", label: "LOW" },
  };
  const s = severity ? map[severity.toUpperCase()] : null;
  if (!s) return <span className="text-[var(--color-ink-mute)] text-[11px]">\u2014</span>;
  return (
    <span className={cn("inline-flex items-center text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded", s.bg, s.color)}>
      {s.label}
    </span>
  );
}

function PriorityBadge({ priority }: { priority?: string | null }) {
  const map: Record<string, { color: string; bg: string; label: string }> = {
    FATAL: { color: "text-[var(--color-danger)]", bg: "bg-[var(--color-danger-bg)]", label: "\u25cf \u5fc5\u5e94" },
    HIGH: { color: "text-[var(--color-warning)]", bg: "bg-[var(--color-warning-bg)]", label: "\u25cf \u9ad8\u4f18" },
    MEDIUM: { color: "text-amber-700", bg: "bg-amber-50", label: "\u25cf \u4e2d" },
    LOW: { color: "text-[var(--color-ink-mute)]", bg: "bg-[var(--color-paper-warm)]", label: "\u25cb \u4f4e" },
  };
  const p = priority ? map[priority.toUpperCase()] : null;
  if (!p) return null;
  return (
    <span className={cn("inline-flex items-center text-[10px] font-mono px-1.5 py-0.5 rounded shrink-0", p.bg, p.color)}>
      {p.label}
    </span>
  );
}

function InfoCell({ label, value, large, mono, icon: Icon }: { label: string; value: React.ReactNode; large?: boolean; mono?: boolean; icon?: ComponentType<SVGProps<SVGSVGElement>> }) {
  return (
    <div className="card-soft p-3 bg-white">
      <div className="flex items-center gap-1 text-[10px] text-[var(--color-ink-mute)] uppercase tracking-wider font-medium mb-1.5">
        {Icon && <Icon className="w-3 h-3" />}
        <span>{label}</span>
      </div>
      <div
        className={cn(
          "text-[var(--color-ink)] break-words",
          large ? "text-[18px] font-semibold leading-snug" : "text-[13px] font-medium",
          mono && "font-mono"
        )}
      >
        {value || <span className="text-[var(--color-ink-mute)]">\u2014</span>}
      </div>
    </div>
  );
}

// ============================================================
// 模块 1：base — 基本信息
// ============================================================

function BaseView({ data }: { data: any }) {
  if (!data) return <Empty text="无基本信息" />;
  const cells: Array<React.ComponentProps<typeof InfoCell>> = [
    { label: "项目名称", value: data.project_name, large: true, icon: Briefcase },
    { label: "招标编号", value: data.project_no, mono: true, icon: Hash },
    { label: "投标模式", value: data.bid_doc_mode, icon: FileText },
    { label: "投标截止", value: fmtDate(data.bid_opening?.deadline), mono: true, icon: Calendar },
    { label: "开标时间", value: fmtDate(data.bid_opening?.open_time), mono: true, icon: Clock },
    { label: "预算金额", value: fmtMoney(data.budget?.amount, data.budget?.currency), large: true, icon: Banknote },
    { label: "投标保证金", value: fmtMoney(data.bid_security), icon: Banknote },
    { label: "投标有效期", value: data.bid_validity_days != null ? `${data.bid_validity_days} 天` : null, icon: Clock },
  ];
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
      {cells.map((c, i) => (
        <InfoCell key={i} {...c} />
      ))}
    </div>
  );
}

// ============================================================
// 模块 2：qualification — 资质要求
// ============================================================

function QualificationView({ data }: { data: any }) {
  const reqs: any[] = data?.requirements || [];
  if (reqs.length === 0) return <Empty text="无资质要求" />;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[12.5px] border-separate border-spacing-0">
        <thead>
          <tr className="text-[10.5px] text-[var(--color-ink-mute)] uppercase tracking-wider">
            <th className="text-left font-medium pb-2 pr-3 w-12">#</th>
            <th className="text-left font-medium pb-2 pr-3">资质/要求</th>
            <th className="text-left font-medium pb-2 pr-3">类型</th>
            <th className="text-left font-medium pb-2 pr-3">证明方式</th>
            <th className="text-center font-medium pb-2 w-20">强制</th>
          </tr>
        </thead>
        <tbody>
          {reqs.map((r: any, i: number) => (
            <tr key={r.id || i} className="group hover:bg-white/60 transition-colors">
              <td className="py-2 pr-3 font-mono text-[11px] text-[var(--color-ink-mute)] align-top border-t border-[var(--color-border-soft)]">
                {r.id || `Q${String(i + 1).padStart(2, "0")}`}
              </td>
              <td className="py-2 pr-3 text-[var(--color-ink)] align-top border-t border-[var(--color-border-soft)] font-medium">
                {r.name || "\u2014"}
              </td>
              <td className="py-2 pr-3 text-[var(--color-ink-soft)] align-top border-t border-[var(--color-border-soft)]">
                {r.type ? (
                  <span className="text-[10.5px] px-1.5 py-0.5 rounded bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)] font-mono">
                    {r.type}
                  </span>
                ) : (
                  "\u2014"
                )}
              </td>
              <td className="py-2 pr-3 text-[var(--color-ink-soft)] align-top border-t border-[var(--color-border-soft)]">
                {r.proof_type || "\u2014"}
              </td>
              <td className="py-2 text-center align-top border-t border-[var(--color-border-soft)]">
                <BooleanDot value={r.is_mandatory} trueLabel="强制" falseLabel="可选" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============================================================
// 模块 3：rejection — 废标条款
// ============================================================

function RejectionView({ data }: { data: any }) {
  const conds: any[] = data?.conditions || [];
  if (conds.length === 0 && !data?.sign_stamp_requirements)
    return <Empty text="无废标条款" />;
  return (
    <div className="space-y-3">
      {conds.length > 0 && (
        <div className="space-y-2">
          {conds.map((c: any, i: number) => (
            <div key={c.id || i} className="card-soft bg-white p-3 flex gap-3 items-start">
              <div className="font-mono text-[10px] text-[var(--color-ink-mute)] shrink-0 mt-0.5 w-7 tabular-nums">
                {c.id || `R${String(i + 1).padStart(2, "0")}`}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1.5">
                  <span className="text-[12px] font-semibold text-[var(--color-ink)]">
                    {c.type || "废标"}
                  </span>
                  <SeverityBadge severity={c.severity} />
                  {c.source_marker && (
                    <span className="text-[14px] font-bold text-[var(--color-primary)]">
                      {c.source_marker}
                    </span>
                  )}
                </div>
                <div className="text-[12.5px] text-[var(--color-ink-soft)] leading-relaxed">
                  {c.condition || "\u2014"}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      {data?.sign_stamp_requirements && (
        <div className="card-soft bg-[var(--color-warning-bg)] p-3 flex gap-2.5 items-start">
          <FileText className="w-3.5 h-3.5 text-[var(--color-warning)] mt-0.5 shrink-0" />
          <div className="flex-1">
            <div className="text-[11px] font-semibold text-[var(--color-warning)] uppercase tracking-wider mb-1">
              签章 / 盖章 / 签字要求
            </div>
            <div className="text-[12.5px] text-[var(--color-ink-soft)] leading-relaxed">
              {data.sign_stamp_requirements}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// 模块 4：scoring — 评分标准
// ============================================================

function ScoringView({ data }: { data: any }) {
  if (!data) return <Empty text="无评分标准" />;
  const dims: any[] = data.dimensions || [];
  const bonus: any[] = data.bonus_items || [];
  return (
    <div className="space-y-4">
      <div className="card-soft bg-white p-3 flex items-center gap-3">
        <div className="text-[10.5px] text-[var(--color-ink-mute)] uppercase tracking-wider shrink-0">
          评标方法
        </div>
        <div className="text-[14px] font-semibold text-[var(--color-ink)]">
          {data.method || "\u2014"}
        </div>
      </div>

      <div className="card-soft bg-white p-3.5">
        <SectionLabel count={3}>权重分配</SectionLabel>
        <div className="space-y-2.5">
          <RatioBar label="价格" value={data.price_ratio} color="bg-amber-500" />
          <RatioBar label="技术" value={data.tech_ratio} color="bg-sky-500" />
          <RatioBar label="商务" value={data.commercial_ratio} color="bg-emerald-500" />
        </div>
      </div>

      {dims.length > 0 && (
        <div className="card-soft bg-white p-3.5">
          <SectionLabel count={dims.length}>评分维度</SectionLabel>
          <div className="space-y-3">
            {dims.map((d: any, i: number) => (
              <div key={i}>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[12.5px] font-semibold text-[var(--color-ink)]">
                    {d.name}
                  </span>
                  <span className="text-[11px] text-[var(--color-ink-mute)] font-mono">
                    满分 {d.max_score ?? "\u2014"}
                  </span>
                </div>
                {Array.isArray(d.sub_items) && d.sub_items.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pl-3 border-l-2 border-[var(--color-border-soft)]">
                    {d.sub_items.map((s: any, j: number) => (
                      <div key={j} className="flex items-baseline gap-2 text-[11.5px] text-[var(--color-ink-soft)]">
                        <span className="font-mono text-[10.5px] text-[var(--color-ink-mute)] w-6 shrink-0 tabular-nums">
                          {s.score ?? "\u2014"}
                        </span>
                        <span className="font-medium text-[var(--color-ink)] shrink-0">
                          {s.name}
                        </span>
                        {s.criteria && (
                          <span className="text-[var(--color-ink-mute)] truncate">
                            · {s.criteria}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : d.criteria ? (
                  <div className="text-[11.5px] text-[var(--color-ink-soft)] pl-3 border-l-2 border-[var(--color-border-soft)]">
                    {d.criteria}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      )}

      {bonus.length > 0 && (
        <div className="card-soft bg-[var(--color-success-bg)] p-3.5">
          <SectionLabel count={bonus.length}>加分项</SectionLabel>
          <div className="space-y-1.5">
            {bonus.map((b: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-[12px] text-[var(--color-ink-soft)]">
                <span className="text-[var(--color-success)] font-semibold">+{b.max_score ?? "\u2014"}</span>
                <span>{b.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// 模块 5：tech — 技术要求
// ============================================================

function TechView({ data }: { data: any }) {
  if (!data) return <Empty text="无技术要求" />;
  const reqs: any[] = data.functional_requirements || [];

  const grouped: Array<[string, any[]]> = [];
  const indexOf = (k: string) => grouped.findIndex(([m]) => m === k);
  for (const r of reqs) {
    const m = r.module || "其他";
    const i = indexOf(m);
    if (i >= 0) grouped[i][1].push(r);
    else grouped.push([m, [r]]);
  }

  const nfr = data.non_functional_requirements || {};
  const sec = data.security_requirements || {};
  const deliverables: string[] = data.deliverables || [];

  return (
    <div className="space-y-4">
      {data.project_background?.summary && (
        <div className="card-soft bg-white p-3.5">
          <SectionLabel>项目背景</SectionLabel>
          <p className="text-[12.5px] text-[var(--color-ink-soft)] leading-relaxed">
            {data.project_background.summary}
          </p>
        </div>
      )}

      {grouped.length > 0 && (
        <div>
          <SectionLabel count={reqs.length}>功能需求（按模块）</SectionLabel>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {grouped.map(([mod, items]) => (
              <div key={mod} className="card-soft bg-white p-3">
                <div className="flex items-center gap-2 mb-2 pb-2 border-b border-[var(--color-border-soft)]">
                  <Cpu className="w-3.5 h-3.5 text-[var(--color-primary)]" />
                  <span className="text-[12.5px] font-semibold text-[var(--color-ink)]">
                    {mod}
                  </span>
                  <span className="text-[10.5px] text-[var(--color-ink-mute)] font-mono ml-auto">
                    {items.length} 项
                  </span>
                </div>
                <ul className="space-y-1.5">
                  {items.map((r: any, j: number) => (
                    <li key={j} className="flex items-start gap-2 text-[12px]">
                      <PriorityBadge priority={r.priority} />
                      <div className="flex-1 min-w-0">
                        <div className="text-[var(--color-ink)] font-medium">{r.name || "\u2014"}</div>
                        {r.description && (
                          <div className="text-[11.5px] text-[var(--color-ink-mute)] leading-relaxed mt-0.5">
                            {r.description}
                          </div>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      {(nfr.performance || nfr.availability || nfr.scalability || sec.level || sec.items?.length) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {(nfr.performance || nfr.availability || nfr.scalability) && (
            <div className="card-soft bg-white p-3.5">
              <SectionLabel>非功能性要求</SectionLabel>
              <dl className="space-y-2 text-[12px]">
                {nfr.performance && <NFDRow label="性能" value={nfr.performance} />}
                {nfr.availability && <NFDRow label="可用性" value={nfr.availability} />}
                {nfr.scalability && <NFDRow label="扩展性" value={nfr.scalability} />}
              </dl>
            </div>
          )}
          {(sec.level || sec.items?.length) && (
            <div className="card-soft bg-white p-3.5">
              <SectionLabel>安全要求</SectionLabel>
              {sec.level && (
                <div className="mb-2">
                  <span className="text-[10.5px] text-[var(--color-ink-mute)] uppercase tracking-wider">
                    等保级别
                  </span>
                  <div className="text-[14px] font-semibold text-[var(--color-ink)] mt-0.5">
                    {sec.level}
                  </div>
                </div>
              )}
              {Array.isArray(sec.items) && sec.items.length > 0 && (
                <ul className="space-y-1">
                  {sec.items.map((it: string, i: number) => (
                    <li key={i} className="flex items-start gap-1.5 text-[12px] text-[var(--color-ink-soft)]">
                      <span className="text-[var(--color-primary)] mt-1">•</span>
                      <span>{it}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}

      {deliverables.length > 0 && (
        <div className="card-soft bg-white p-3.5">
          <SectionLabel count={deliverables.length}>交付物</SectionLabel>
          <div className="flex flex-wrap gap-1.5">
            {deliverables.map((d: string, i: number) => (
              <span
                key={i}
                className="text-[11.5px] px-2 py-0.5 rounded-full bg-[var(--color-primary-bg)] text-[var(--color-primary-deep)]"
              >
                {d}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function NFDRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start gap-3">
      <dt className="text-[10.5px] text-[var(--color-ink-mute)] uppercase tracking-wider w-14 shrink-0 pt-0.5">
        {label}
      </dt>
      <dd className="text-[12px] text-[var(--color-ink)] flex-1 leading-relaxed">{value}</dd>
    </div>
  );
}

// ============================================================
// 模块 6：commercial — 商务条款
// ============================================================

function CommercialView({ data }: { data: any }) {
  if (!data) return <Empty text="无商务条款" />;
  const days = data.delivery_cycle_days;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
      <InfoCell label="付款方式" value={data.payment} icon={Banknote} />
      <InfoCell label="合同类型" value={data.contract_type} icon={FileText} />
      {days != null ? (
        <div className="card-soft p-3 bg-white">
          <div className="flex items-center gap-1 text-[10px] text-[var(--color-ink-mute)] uppercase tracking-wider font-medium mb-1.5">
            <Clock className="w-3 h-3" />
            <span>交付周期</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-[24px] font-semibold text-[var(--color-ink)] tabular-nums leading-none">
              {days}
            </span>
            <span className="text-[12px] text-[var(--color-ink-mute)]">天</span>
          </div>
        </div>
      ) : (
        <InfoCell label="交付周期" value={null} icon={Clock} />
      )}
      <InfoCell label="质保期" value={data.warranty} icon={ShieldCheck} />
      <InfoCell label="违约责任" value={data.penalty_clauses} icon={AlertOctagon} />
    </div>
  );
}

// ============================================================
// 模块 7：templates — 章节模板
// ============================================================

function TemplatesView({ data }: { data: any }) {
  if (!data) return <Empty text="无章节模板" />;
  const chapters: any[] = data.bid_doc_structure || [];
  const fmt = data.format_requirements || {};
  const copies = fmt.copies || {};
  return (
    <div className="space-y-3">
      {chapters.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-[12.5px] border-separate border-spacing-0">
            <thead>
              <tr className="text-[10.5px] text-[var(--color-ink-mute)] uppercase tracking-wider">
                <th className="text-left font-medium pb-2 pr-3 w-16">章节号</th>
                <th className="text-left font-medium pb-2 pr-3">名称</th>
                <th className="text-center font-medium pb-2 pr-3 w-16">必需</th>
                <th className="text-right font-medium pb-2 w-20">最少页数</th>
              </tr>
            </thead>
            <tbody>
              {chapters.map((c: any, i: number) => (
                <tr key={i} className="hover:bg-white/60">
                  <td className="py-2 pr-3 font-mono text-[11.5px] text-[var(--color-ink-mute)] align-top border-t border-[var(--color-border-soft)]">
                    {c.section_no || "\u2014"}
                  </td>
                  <td className="py-2 pr-3 text-[var(--color-ink)] align-top border-t border-[var(--color-border-soft)] font-medium">
                    {c.name || "\u2014"}
                  </td>
                  <td className="py-2 pr-3 text-center align-top border-t border-[var(--color-border-soft)]">
                    <BooleanDot value={c.required} trueLabel="必需" falseLabel="可选" />
                  </td>
                  <td className="py-2 text-right align-top border-t border-[var(--color-border-soft)] font-mono text-[12px] text-[var(--color-ink-soft)] tabular-nums">
                    {c.pages_min ?? "\u2014"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(copies.original || copies.copy || fmt.electronic_format || fmt.binding_method) && (
        <div className="card-soft bg-white p-3.5">
          <SectionLabel>格式 / 份数 / 装订</SectionLabel>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-[12.5px]">
            {(copies.original || copies.copy) && (
              <div>
                <div className="text-[10.5px] text-[var(--color-ink-mute)] uppercase tracking-wider mb-1">
                  份数
                </div>
                <div className="text-[var(--color-ink)]">
                  正本 <span className="font-mono font-semibold">{copies.original ?? "?"}</span> / 副本{" "}
                  <span className="font-mono font-semibold">{copies.copy ?? "?"}</span>
                </div>
              </div>
            )}
            {fmt.electronic_format && (
              <div>
                <div className="text-[10.5px] text-[var(--color-ink-mute)] uppercase tracking-wider mb-1">
                  电子版
                </div>
                <div className="text-[var(--color-ink)]">{fmt.electronic_format}</div>
              </div>
            )}
            {fmt.binding_method && (
              <div>
                <div className="text-[10.5px] text-[var(--color-ink-mute)] uppercase tracking-wider mb-1">
                  装订
                </div>
                <div className="text-[var(--color-ink)]">{fmt.binding_method}</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// 模块 8：logistics — 开标与递交
// ============================================================

function LogisticsView({ data }: { data: any }) {
  if (!data) return <Empty text="无开标与递交信息" />;
  const origs: string[] = data.originals_to_bring || [];
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <LogisticsCard
          title="投标递交"
          icon={Send}
          accent="bg-amber-50 text-amber-700"
          rows={[
            { label: "方式", value: data.bid_submission?.method },
            { label: "截止", value: fmtDate(data.bid_submission?.deadline), mono: true },
            { label: "地址", value: data.bid_submission?.address, full: true },
          ]}
        />
        <LogisticsCard
          title="开标"
          icon={Calendar}
          accent="bg-sky-50 text-sky-700"
          rows={[
            { label: "时间", value: fmtDate(data.bid_opening?.time), mono: true },
            { label: "地点", value: data.bid_opening?.location, full: true },
            {
              label: "直播",
              value: <BooleanDot value={data.bid_opening?.live} trueLabel="直播" falseLabel="不直播" />,
            },
          ]}
        />
        <LogisticsCard
          title="演示 / 答辩"
          icon={Presentation}
          accent="bg-violet-50 text-violet-700"
          rows={[
            {
              label: "需要演示",
              value: (
                <BooleanDot
                  value={data.presentation_demo?.required}
                  trueLabel="需要"
                  falseLabel="不需要"
                />
              ),
            },
            {
              label: "时长",
              value:
                data.presentation_demo?.duration_min != null
                  ? `${data.presentation_demo.duration_min} 分钟`
                  : null,
            },
            { label: "形式", value: data.presentation_demo?.format },
          ]}
        />
      </div>

      {origs.length > 0 && (
        <div className="card-soft bg-white p-3.5">
          <SectionLabel count={origs.length}>现场需携带的原件</SectionLabel>
          <div className="flex flex-wrap gap-1.5">
            {origs.map((o: string, i: number) => (
              <span
                key={i}
                className="text-[11.5px] px-2 py-0.5 rounded-full bg-[var(--color-paper-warm)] text-[var(--color-ink-soft)] border border-[var(--color-border)]"
              >
                {o}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function LogisticsCard({
  title,
  icon: Icon,
  accent,
  rows,
}: {
  title: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  accent: string;
  rows: Array<{ label: string; value: React.ReactNode; mono?: boolean; full?: boolean }>;
}) {
  return (
    <div className="card-soft bg-white p-3.5">
      <div className="flex items-center gap-2 mb-3">
        <span className={cn("w-6 h-6 rounded-md flex items-center justify-center", accent)}>
          <Icon className="w-3.5 h-3.5" />
        </span>
        <h4 className="text-[12.5px] font-semibold text-[var(--color-ink)]">{title}</h4>
      </div>
      <dl className="space-y-2">
        {rows.map((r, i) => (
          <div key={i}>
            <dt className="text-[10.5px] text-[var(--color-ink-mute)] uppercase tracking-wider mb-0.5">
              {r.label}
            </dt>
            <dd className={cn("text-[12.5px] text-[var(--color-ink)]", r.mono && "font-mono tabular-nums")}>
              {r.value || <span className="text-[var(--color-ink-mute)]">\u2014</span>}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
