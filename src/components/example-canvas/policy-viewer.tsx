"use client";

import React, { useState, useEffect } from "react";
import { useAgent } from "@copilotkit/react-core/v2";
import {
  FileText,
  FileSpreadsheet,
  FileCode,
  CheckCircle2,
  FolderOpen,
  Search,
  ExternalLink,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { findDocAggByName, type DocAggItem } from "@/lib/citation-service";
import { FilePreviewer } from "@/components/citation/file-previewer";

export function PolicyDocumentViewer() {
  const { agent } = useAgent();
  const [activeDoc, setActiveDoc] = useState<DocAggItem | null>(null);
  const [docList, setDocList] = useState<DocAggItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  // 加载全量知识库文档列表，并与当前对话命中的切片聚合合并
  useEffect(() => {
    const fetchDatasetDocuments = async () => {
      try {
        const res = await fetch("/api/documents?page=1&page_size=100");
        if (res.ok) {
          const json = await res.json();
          const docsData = json?.data?.docs || json?.data || [];
          if (Array.isArray(docsData) && docsData.length > 0) {
            const list: DocAggItem[] = docsData.map((d: any) => ({
              doc_id: d.id || d.doc_id || "",
              doc_name: d.name || d.doc_name || "未知文档",
              count: d.chunk_num || d.count || 0,
              dataset_id: d.kb_id || d.dataset_id || "d4d0e9c6a05c11f199bf45be651e52f0",
            }));

            setDocList((prev) => {
              // 优先保留已有文档，把全量知识库中其余文档也合并进来
              const seen = new Set<string>();
              const merged: DocAggItem[] = [];
              for (const doc of prev) {
                seen.add(doc.doc_name);
                merged.push(doc);
              }
              for (const doc of list) {
                if (!seen.has(doc.doc_name)) {
                  seen.add(doc.doc_name);
                  merged.push(doc);
                }
              }
              if (!activeDoc && merged.length > 0) {
                setActiveDoc(merged[0]);
              }
              return merged;
            });
          }
        }
      } catch (err) {
        console.error("获取知识库文档列表失败:", err);
      }
    };

    fetchDatasetDocuments();
  }, []);

  // 同步从 AgentState 获取当前对话涉及的所有参考政策文件（提升置顶）
  useEffect(() => {
    const ragDict = (agent?.state as any)?.rag_citations;
    const hitDocs: DocAggItem[] = [];
    const seen = new Set<string>();

    if (ragDict && typeof ragDict === "object") {
      for (const ctx of Object.values(ragDict) as any[]) {
        if (ctx?.doc_aggs && Array.isArray(ctx.doc_aggs)) {
          for (const doc of ctx.doc_aggs) {
            if (doc?.doc_name && !seen.has(doc.doc_name)) {
              seen.add(doc.doc_name);
              hitDocs.push(doc);
            }
          }
        }
      }
    }

    if (hitDocs.length > 0) {
      setDocList((prev) => {
        const merged: DocAggItem[] = [...hitDocs];
        for (const doc of prev) {
          if (!seen.has(doc.doc_name)) {
            merged.push(doc);
          }
        }
        return merged;
      });
      setActiveDoc(hitDocs[0]);
    }
  }, [agent?.state]);

  const getDocBadgeIcon = (name: string) => {
    const lower = name.toLowerCase();
    if (lower.endsWith(".xlsx") || lower.endsWith(".xls") || lower.endsWith(".csv")) {
      return (
        <span className="p-1 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 shrink-0 inline-flex">
          <FileSpreadsheet className="w-4 h-4" />
        </span>
      );
    }
    if (lower.endsWith(".docx") || lower.endsWith(".doc")) {
      return (
        <span className="p-1 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 shrink-0 inline-flex">
          <FileText className="w-4 h-4" />
        </span>
      );
    }
    return (
      <span className="p-1 rounded bg-stone-500/10 text-stone-600 dark:text-stone-300 border border-stone-500/20 shrink-0 inline-flex">
        <FileCode className="w-4 h-4" />
      </span>
    );
  };

  const cleanDocName = (name: string = "") => {
    return name.replace(/^documents\//, "").replace(/^\/+/, "");
  };

  const filteredDocs = docList.filter((d) =>
    cleanDocName(d.doc_name).toLowerCase().includes(searchQuery.toLowerCase())
  );

  const effectiveDatasetId = activeDoc?.dataset_id || "d4d0e9c6a05c11f199bf45be651e52f0";
  const previewUrl = activeDoc?.doc_id
    ? `/api/documents/${effectiveDatasetId}/${activeDoc.doc_id}`
    : "";

  return (
    <div className="h-full flex flex-col bg-stone-50/70 dark:bg-stone-950/80 border-l border-border select-none">
      {/* Top Header */}
      <div className="shrink-0 px-6 py-4 border-b border-border bg-card/60 backdrop-blur-md flex items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600/10 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold">
            <FolderOpen className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
              国网政策知识库沙盘
              <span className="px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 font-mono text-[10px] font-medium border border-blue-500/20">
                {docList.length} 篇关联文档
              </span>
            </h3>
            <p className="text-[11px] text-muted-foreground">
              字字有据，行行可溯 · 原生零转化安全渲染
            </p>
          </div>
        </div>

        {activeDoc && previewUrl && (
          <a
            href={previewUrl}
            download={cleanDocName(activeDoc.doc_name)}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-secondary hover:bg-secondary/80 text-secondary-foreground text-xs font-medium transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" /> 下载源文件
          </a>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Left Side: Policy Document List */}
        <div className="w-72 shrink-0 border-r border-border flex flex-col bg-card/30">
          <div className="p-3 border-b border-border">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="搜索检索到的政策文档..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-muted/60 text-xs text-foreground placeholder:text-muted-foreground border border-border/60 focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {filteredDocs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 px-4 text-center text-muted-foreground space-y-2">
                <Sparkles className="w-8 h-8 opacity-40 text-blue-500" />
                <p className="text-xs">暂无关联政策文档</p>
                <p className="text-[10px] opacity-75">在左侧提问后，系统将自动汇聚检索到的权威政策</p>
              </div>
            ) : (
              filteredDocs.map((doc) => {
                const displayName = cleanDocName(doc.doc_name);
                const isSelected = activeDoc?.doc_name === doc.doc_name;
                return (
                  <button
                    key={doc.doc_id || doc.doc_name}
                    type="button"
                    onClick={() => setActiveDoc(doc)}
                    className={`w-full text-left p-2.5 rounded-xl border transition-all flex items-start gap-2.5 cursor-pointer ${
                      isSelected
                        ? "bg-blue-50/80 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800/80 shadow-xs"
                        : "bg-card hover:bg-muted/50 border-border/60"
                    }`}
                  >
                    {getDocBadgeIcon(displayName)}
                    <div className="flex-1 min-w-0">
                      <h4
                        className={`text-xs font-semibold truncate leading-tight ${
                          isSelected
                            ? "text-blue-600 dark:text-blue-400"
                            : "text-foreground"
                        }`}
                        title={displayName}
                      >
                        {displayName}
                      </h4>
                      <div className="flex items-center gap-1.5 mt-1 text-[10px] text-muted-foreground font-mono">
                        {doc.count && doc.count > 0 ? (
                          <span>{doc.count} 处切片</span>
                        ) : (
                          <span>全文就绪</span>
                        )}
                        {isSelected && (
                          <span className="text-blue-500 font-sans ml-auto flex items-center">
                            阅读中 <ChevronRight className="w-3 h-3 ml-0.5" />
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Side: Active Document FileViewer */}
        <div className="flex-1 p-4 bg-muted/20 overflow-hidden flex flex-col">
          {activeDoc && previewUrl ? (
            <div className="h-full flex flex-col rounded-xl overflow-hidden border border-border bg-card shadow-xs">
              <div className="shrink-0 px-4 py-2.5 bg-muted/40 border-b border-border/80 flex items-center justify-between text-xs">
                <span className="font-semibold text-foreground truncate max-w-md">
                  《{cleanDocName(activeDoc.doc_name)}》
                </span>
                <span className="text-[11px] text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" /> 企业权威政策源件
                </span>
              </div>
              <div className="flex-1 p-3 overflow-hidden">
                <FilePreviewer
                  url={previewUrl}
                  fileName={cleanDocName(activeDoc.doc_name)}
                  className="h-full"
                />
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground space-y-3 p-6">
              <div className="w-14 h-14 rounded-2xl bg-muted flex items-center justify-center">
                <FileText className="w-7 h-7 opacity-40 text-blue-500" />
              </div>
              <h4 className="font-bold text-sm text-foreground">请选择左侧政策文档进行在线研读</h4>
              <p className="text-xs max-w-sm text-muted-foreground">
                支持 Word (.docx)、Excel (.xlsx)、PDF 等全格式规程条款的浏览器端原生零转化渲染。
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
