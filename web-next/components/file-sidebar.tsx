"use client";

import { useState, useEffect } from "react";
import {
  Folder,
  FolderOpen,
  FileText,
  ChevronLeft,
  ChevronRight,
  Plus,
  ExternalLink,
  Loader2,
  Upload,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Material, ProjectDetail, TenderSummary } from "@/lib/api";
import {
  listMaterials,
  listTenderFiles,
  type TenderFileEntry,
  type TenderFileTree,
  type TenderFolder,
  uploadProjectMaterial,
} from "@/lib/api";
import { useRouter } from "next/navigation";

const MATERIAL_CATEGORIES = [
  { key: "01_公司资质", label: "公司资质" },
  { key: "02_业绩案例", label: "业绩案例" },
  { key: "03_技术方案", label: "技术方案" },
  { key: "04_实施方案", label: "实施方案" },
  { key: "05_商务文件", label: "商务文件" },
  { key: "06_其他", label: "其他" },
];

export function FileSidebar({
  project,
  onOpenReport,
}: {
  project: ProjectDetail;
  onOpenReport?: () => void;
}) {
  const router = useRouter();
  const [shut, setShut] = useState(false);
  const [openFolders, setOpenFolders] = useState<Set<string>>(new Set());
  const [fileTrees, setFileTrees] = useState<Record<number, TenderFileTree>>({});
  const [loadingTree, setLoadingTree] = useState(false);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [materialsLoading, setMaterialsLoading] = useState(false);
  const [materialCategory, setMaterialCategory] = useState("03_技术方案");
  const [uploadingMaterial, setUploadingMaterial] = useState(false);
  const [materialError, setMaterialError] = useState<string | null>(null);
  const activeTenderId = project.active_main_tender_id ?? project.tender_id;
  const tenders = project.tenders || [];
  const mainTender =
    tenders.find((t) => t.id === activeTenderId) ||
    (activeTenderId ? ({ id: activeTenderId, type: "main" } as TenderSummary) : undefined);
  const subTenders = tenders.filter((t) => t.type === "sub" && t.draft_path);
  const mainFileTree = activeTenderId ? fileTrees[activeTenderId] : null;
  const tenderIdsToLoad = Array.from(
    new Set([
      ...(mainTender?.id ? [mainTender.id] : []),
      ...subTenders.map((t) => t.id),
    ])
  );
  const tenderIdsKey = tenderIdsToLoad.join(",");
  const selectedMaterialCategory = MATERIAL_CATEGORIES.find(
    (cat) => cat.key === materialCategory
  );

  const refreshMaterials = () => {
    setMaterialsLoading(true);
    listMaterials({ category: materialCategory })
      .then(setMaterials)
      .catch((e) => setMaterialError(e.message))
      .finally(() => setMaterialsLoading(false));
  };

  // 动态拉取文件树（主标 + 已落盘陪标）
  useEffect(() => {
    const shouldLoad =
      tenderIdsToLoad.length > 0 &&
      (project.status === "generating" ||
        project.status === "generated" ||
        project.status === "reviewed" ||
        project.status === "done");
    if (!shouldLoad) {
      setFileTrees({});
      return;
    }
    let cancelled = false;
    setLoadingTree(true);
    Promise.all(
      tenderIdsToLoad.map((tenderId) =>
        listTenderFiles(project.id, tenderId).then((tree) => [tenderId, tree] as const)
      )
    )
      .then((entries) => {
        if (!cancelled) setFileTrees(Object.fromEntries(entries));
      })
      .catch((e) => {
        console.error("拉取文件树失败：", e);
        if (!cancelled) setFileTrees({});
      })
      .finally(() => {
        if (!cancelled) setLoadingTree(false);
      });
    return () => {
      cancelled = true;
    };
  }, [project.id, project.status, tenderIdsKey]);

  useEffect(() => {
    refreshMaterials();
    const onUpdated = () => refreshMaterials();
    window.addEventListener("quickbid:materials-updated", onUpdated);
    return () => window.removeEventListener("quickbid:materials-updated", onUpdated);
  }, [materialCategory]);

  const handleMaterialUpload = async (file: File) => {
    setUploadingMaterial(true);
    setMaterialError(null);
    try {
      await uploadProjectMaterial(project.id, { file, category: materialCategory });
      refreshMaterials();
    } catch (e: any) {
      setMaterialError(e.message || "材料上传失败");
    } finally {
      setUploadingMaterial(false);
    }
  };

  const toggleFolder = (key: string) => {
    setOpenFolders((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <aside
      className={cn(
        "relative bg-[var(--color-surface)] border-l border-[var(--color-border)] transition-all duration-200 shrink-0 flex flex-col h-full",
        shut ? "w-10" : "w-72"
      )}
      aria-label="项目文件"
    >
      {/* Toggle */}
      <button
        onClick={() => setShut((s) => !s)}
        aria-label={shut ? "展开文件栏" : "收起文件栏"}
        aria-expanded={!shut}
        className="absolute -left-3 top-6 z-10 w-6 h-6 bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-ink-mute)] rounded-md flex items-center justify-center hover:bg-[var(--color-ink)] hover:text-[var(--color-paper)] hover:border-[var(--color-ink)] transition-colors shadow-sm"
      >
        {shut ? (
          <ChevronLeft className="w-3 h-3" />
        ) : (
          <ChevronRight className="w-3 h-3" />
        )}
      </button>

      {shut ? null : (
        <div className="flex flex-col h-full overflow-hidden">
          {/* Header */}
          <div className="px-4 pt-4 pb-3">
            <h3 className="text-[11px] font-medium text-[var(--color-ink-mute)] uppercase tracking-wider">
              项目文件
            </h3>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-3 pb-4 space-y-4">
            {/* Tender file */}
            {project.tender_file_path && (
              <div>
                <div className="section-label">
                  <span>招标文件</span>
                  <span className="count">01</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-2 bg-[var(--color-surface-sunk)] border border-[var(--color-border)] rounded-xl">
                  <div className="w-7 h-7 rounded-md bg-white border border-[var(--color-border)] flex items-center justify-center shrink-0">
                    <FileText className="w-3.5 h-3.5 text-[var(--color-primary)]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[12px] text-[var(--color-ink)] truncate font-medium" title={project.tender_file_path}>
                      {project.tender_file_path.split("/").pop()}
                    </div>
                    <div className="text-[10px] text-[var(--color-ink-mute)] font-mono mt-0.5">PDF · TENDER</div>
                  </div>
                </div>
              </div>
            )}

            {/* Parsed overview */}
            {project.parsed_data && (
              <div>
                <div className="section-label">
                  <span>解析概览</span>
                  <span className="count">02</span>
                </div>
                <ParsedOverview data={project.parsed_data} onOpenReport={onOpenReport} />
              </div>
            )}

            {/* Main bid */}
            <div>
              <div className="section-label">
                <span>主标</span>
                <span className="count">03</span>
              </div>
              {loadingTree ? (
                <div className="flex items-center gap-2 px-3 py-2 text-[11px] text-[var(--color-ink-mute)]">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  加载文件树…
                </div>
              ) : mainFileTree && (mainFileTree.top_files.length > 0 || mainFileTree.folders.length > 0) ? (
                <TenderTreeView
                  tree={mainFileTree}
                  openFolders={openFolders}
                  onToggleFolder={toggleFolder}
                  onFileClick={(tenderId, filePath) =>
                    router.push(`/projects/${project.id}?tender=${tenderId}&file=${encodeURIComponent(filePath)}`)
                  }
                />
              ) : (
                <div className="px-3 py-2 text-[11px] text-[var(--color-ink-mute)]">
                  暂无文件
                </div>
              )}
            </div>

            {/* Project material library */}
            <div>
              <div className="section-label">
                <span>主标材料库</span>
                <span className="count">{String(materials.length).padStart(2, "0")}</span>
              </div>
              <div className="card-soft p-3 space-y-3">
                <div className="flex items-center gap-2">
                  <select
                    value={materialCategory}
                    onChange={(e) => setMaterialCategory(e.target.value)}
                    className="min-w-0 flex-1 h-8 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-sunk)] px-2 text-[11px] text-[var(--color-ink-soft)]"
                  >
                    {MATERIAL_CATEGORIES.map((cat) => (
                      <option key={cat.key} value={cat.key}>{cat.label}</option>
                    ))}
                  </select>
                  <label className="h-8 px-2.5 rounded-lg border border-dashed border-[var(--color-border)] text-[11px] font-medium text-[var(--color-ink-soft)] hover:text-[var(--color-primary-deep)] hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] flex items-center gap-1.5 cursor-pointer transition-colors">
                    {uploadingMaterial ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />}
                    添加
                    <input
                      type="file"
                      accept=".md,.txt,.docx,.pdf"
                      className="hidden"
                      disabled={uploadingMaterial}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleMaterialUpload(file);
                        e.currentTarget.value = "";
                      }}
                    />
                  </label>
                </div>
                {materialError && (
                  <div className="text-[11px] text-[var(--color-danger)] leading-relaxed">
                    {materialError}
                  </div>
                )}
                {materialsLoading ? (
                  <div className="flex items-center gap-2 text-[11px] text-[var(--color-ink-mute)]">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    加载材料…
                  </div>
                ) : materials.length === 0 ? (
                  <div className="text-[11px] text-[var(--color-ink-mute)]">
                    {selectedMaterialCategory?.label ?? "当前分类"}暂无材料
                  </div>
                ) : (
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {materials.slice(0, 12).map((material) => (
                      <div
                        key={`${material.category}-${material.title}-${material.id}`}
                        className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-sunk)] px-2.5 py-2"
                      >
                        <div className="text-[11.5px] font-medium text-[var(--color-ink)] truncate" title={material.title}>
                          {material.title}
                        </div>
                        <div className="mt-0.5 flex items-center justify-between gap-2 text-[10px] text-[var(--color-ink-mute)]">
                          <span className="truncate">{prettyCategory(material.category)}</span>
                          <span className="font-mono tabular-nums">{material.char_count || 0} 字</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Sub-bids */}
            {subTenders.length > 0 && (
              <div>
                <div className="section-label">
                  <span>陪标</span>
                  <span className="count">{String(subTenders.length).padStart(2, "0")}</span>
                </div>
                <div className="space-y-3">
                  {subTenders.map((tender, idx) => {
                    const tree = fileTrees[tender.id];
                    return (
                      <div key={tender.id} className="space-y-1.5">
                        <div className="px-2.5 text-[10px] text-[var(--color-ink-mute)] font-mono">
                          SUB-{String(idx + 1).padStart(2, "0")} · T{tender.id}
                        </div>
                        {tree && (tree.top_files.length > 0 || tree.folders.length > 0) ? (
                          <TenderTreeView
                            tree={tree}
                            openFolders={openFolders}
                            onToggleFolder={toggleFolder}
                            onFileClick={(tenderId, filePath) =>
                              router.push(`/projects/${project.id}?tender=${tenderId}&file=${encodeURIComponent(filePath)}`)
                            }
                          />
                        ) : (
                          <div className="px-3 py-2 text-[11px] text-[var(--color-ink-mute)]">
                            暂无文件
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            <button
              type="button"
              className="w-full flex items-center justify-center gap-1.5 py-2 text-[12px] text-[var(--color-ink-mute)] bg-transparent border border-dashed border-[var(--color-border)] rounded-xl hover:border-[var(--color-primary)] hover:text-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] transition-colors min-h-[36px]"
            >
              <Plus className="w-3.5 h-3.5" />
              添加陪标
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}

function TenderTreeView({
  tree,
  openFolders,
  onToggleFolder,
  onFileClick,
}: {
  tree: TenderFileTree;
  openFolders: Set<string>;
  onToggleFolder: (key: string) => void;
  onFileClick: (tenderId: number, filePath: string) => void;
}) {
  return (
    <div className="space-y-2">
      {tree.top_files.length > 0 && (
        <TopFilesList
          files={tree.top_files}
          onFileClick={(filePath) => onFileClick(tree.tender_id, filePath)}
        />
      )}
      <div className="space-y-0.5">
        {tree.folders.map((folder) => {
          const key = `${tree.tender_id}:${folder.category}`;
          return (
            <DynamicFolderRow
              key={key}
              folder={folder}
              open={openFolders.has(key)}
              onToggle={() => onToggleFolder(key)}
              onFileClick={(filePath) => onFileClick(tree.tender_id, filePath)}
            />
          );
        })}
      </div>
    </div>
  );
}

function DynamicFolderRow({
  folder,
  open,
  onToggle,
  onFileClick,
}: {
  folder: TenderFolder;
  open: boolean;
  onToggle: () => void;
  onFileClick: (filePath: string) => void;
}) {
  const displayName = folder.name || prettyCategory(folder.category);
  return (
    <div>
      <button
        onClick={onToggle}
        aria-expanded={open}
        className="group w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[12.5px] text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] transition-colors text-left min-h-[30px]"
      >
        <ChevronRight
          className={cn(
            "w-3 h-3 text-[var(--color-ink-mute)] transition-transform shrink-0",
            open && "rotate-90 text-[var(--color-primary)]"
          )}
        />
        {open ? (
          <FolderOpen className="w-3.5 h-3.5 text-[var(--color-primary)] shrink-0" />
        ) : (
          <Folder className="w-3.5 h-3.5 text-[var(--color-ink-mute)] group-hover:text-[var(--color-primary)] shrink-0" />
        )}
        <span className="truncate">{displayName}</span>
        <span className="ml-auto text-[10px] text-[var(--color-ink-mute)] font-mono tabular-nums">
          {folder.files?.length || 0}
        </span>
      </button>
      {open && folder.files && folder.files.length > 0 && (
        <div className="ml-6 mt-0.5 space-y-0.5">
          {folder.files.map((file) => (
            <FileRow key={file.path} file={file} onFileClick={onFileClick} />
          ))}
        </div>
      )}
    </div>
  );
}

function TopFilesList({
  files,
  onFileClick,
}: {
  files: TenderFileEntry[];
  onFileClick: (filePath: string) => void;
}) {
  return (
    <div className="space-y-0.5 border-b border-[var(--color-border)] pb-2">
      {files.map((file) => (
        <FileRow key={file.path} file={file} onFileClick={onFileClick} />
      ))}
    </div>
  );
}

function FileRow({
  file,
  onFileClick,
}: {
  file: TenderFileEntry;
  onFileClick: (filePath: string) => void;
}) {
  const meta = topFileMeta(file.name);
  const displayName = meta?.label ?? file.name;
  const subLabel = meta?.subLabel;
  return (
    <button
      onClick={() => onFileClick(file.path)}
      className="group w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[12px] text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] transition-colors text-left"
      title={`${displayName} · ${file.name} · ${file.size || 0} 字符`}
    >
      <FileText className="w-3 h-3 text-[var(--color-ink-mute)] group-hover:text-[var(--color-primary)] shrink-0" />
      <span className="min-w-0 flex-1">
        <span className="block truncate">{displayName}</span>
        {subLabel && (
          <span className="block text-[10px] text-[var(--color-ink-mute)] font-mono truncate">
            {subLabel}
          </span>
        )}
      </span>
      {file.chapter_no && (
        <span className="text-[10px] text-[var(--color-ink-mute)] font-mono tabular-nums">
          #{file.chapter_no}
        </span>
      )}
    </button>
  );
}

function topFileMeta(name: string): { label: string; subLabel: string } | null {
  if (name === "cover.md") {
    return { label: "封面与目录", subLabel: "cover.md" };
  }
  if (name === "draft.md") {
    return { label: "主标正文", subLabel: "draft.md" };
  }
  if (name === "deviation.md") {
    return { label: "商务/技术偏离表", subLabel: "deviation.md" };
  }
  return null;
}

function prettyCategory(category: string): string {
  const idx = category.indexOf("_");
  return idx >= 0 ? category.slice(idx + 1) : category;
}

function FolderRow({
  name,
  open,
  onToggle,
}: {
  name: string;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      aria-expanded={open}
      className="group w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[12.5px] text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)] transition-colors text-left min-h-[30px]"
    >
      <ChevronRight
        className={cn(
          "w-3 h-3 text-[var(--color-ink-mute)] transition-transform shrink-0",
          open && "rotate-90 text-[var(--color-primary)]"
        )}
      />
      {open ? (
        <FolderOpen className="w-3.5 h-3.5 text-[var(--color-primary)] shrink-0" />
      ) : (
        <Folder className="w-3.5 h-3.5 text-[var(--color-ink-mute)] group-hover:text-[var(--color-primary)] shrink-0" />
      )}
      <span className="truncate">{name}</span>
    </button>
  );
}

function ParsedOverview({
  data,
  onOpenReport,
}: {
  data: any;
  onOpenReport?: () => void;
}) {
  // K 字段新 shape：{value, source_page} / {items, source_pages}，
  // 旧 shape：标量字符串 / 数组 string[]。统一抽出可显示字符串。
  const readKValue = (raw: any): string => {
    if (raw && typeof raw === "object" && !Array.isArray(raw)) {
      if (Array.isArray(raw.items)) {
        return raw.items
          .map((it: any) => (typeof it === "string" ? it : JSON.stringify(it)))
          .filter(Boolean)
          .join("；");
      }
      if (raw.value === undefined || raw.value === null || raw.value === "") return "";
      if (Array.isArray(raw.value)) {
        return raw.value
          .map((it: any) => (typeof it === "string" ? it : JSON.stringify(it)))
          .filter(Boolean)
          .join("；");
      }
      return String(raw.value);
    }
    if (Array.isArray(raw)) {
      return raw
        .map((it: any) => (typeof it === "string" ? it : JSON.stringify(it)))
        .filter(Boolean)
        .join("；");
    }
    return raw == null ? "" : String(raw);
  };

  const k = (key: string) => {
    const raw = data?.[key] ?? data?.base?.[key];
    if (raw === undefined) return undefined;
    return readKValue(raw);
  };

  const fields = [
    { label: "项目名称", value: k("K01_project_name") || k("project_name") },
    { label: "招标编号", value: k("K02_tender_no") || k("tender_no") },
    { label: "预算", value: k("K04_budget") || k("budget") },
  ].filter((f) => f.value);

  if (fields.length === 0) return null;

  return (
    <div className="card-soft p-3.5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[var(--color-success)]" />
          <span className="text-[11px] font-semibold text-[var(--color-ink)]">已解析</span>
        </div>
        {onOpenReport && (
          <button
            onClick={onOpenReport}
            className="text-[11px] text-[var(--color-primary)] hover:text-[var(--color-primary-deep)] font-medium flex items-center gap-0.5"
            aria-label="在主区打开完整报告"
          >
            打开
            <ExternalLink className="w-3 h-3" />
          </button>
        )}
      </div>
      <dl className="space-y-2">
        {fields.map((f) => (
          <div key={f.label}>
            <dt className="text-[10px] text-[var(--color-ink-mute)] uppercase tracking-wider mb-0.5">
              {f.label}
            </dt>
            <dd className="text-[12px] text-[var(--color-ink)] font-mono truncate">
              {String(f.value).slice(0, 40)}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
