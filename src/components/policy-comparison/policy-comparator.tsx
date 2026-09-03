"use client";

import React, { useState, useEffect } from "react";
import {
  GitCompare,
  Bookmark,
  Sparkles,
  FileText,
  X,
  ExternalLink,
  Eye,
  MessageSquareDiff,
} from "lucide-react";
import {
  type PolicyComparisonData,
  type PolicyComparisonPair,
} from "./preset-data";
import { useAgent } from "@copilotkit/react-core/v2";
import { FilePreviewer } from "@/components/citation/file-previewer";

interface PolicyComparatorProps {
  customData?: PolicyComparisonData | null;
}

export function PolicyComparator({ customData }: PolicyComparatorProps) {
  // 如果没有对话触发的数据，默认为 null（空状态）
  const activeComparison: PolicyComparisonData | null = customData || null;

  // 知识库文档列表（用于根据条款所属的 docTitle 智能匹配在线预览）
  const [docsMap, setDocsMap] = useState<
    Record<string, { doc_id: string; dataset_id: string; name: string }>
  >({});

  // 预览弹窗状态
  const [previewTarget, setPreviewTarget] = useState<{
    title: string;
    url: string;
    fileName: string;
  } | null>(null);

  useEffect(() => {
    const loadDocs = async () => {
      try {
        const res = await fetch("/api/documents?page=1&page_size=100");
        if (res.ok) {
          const json = await res.json();
          const docsData = json?.data?.docs || json?.data || [];
          if (Array.isArray(docsData)) {
            const map: Record<
              string,
              { doc_id: string; dataset_id: string; name: string }
            > = {};
            for (const d of docsData) {
              const name = (d.name || d.doc_name || "").trim();
              const id = d.id || d.doc_id || "";
              const kbId =
                d.kb_id || d.dataset_id || "d4d0e9c6a05c11f199bf45be651e52f0";
              if (name && id) {
                map[name.toLowerCase()] = { doc_id: id, dataset_id: kbId, name };
              }
            }
            setDocsMap(map);
          }
        }
      } catch (err) {
        console.error("加载文档匹配库失败:", err);
      }
    };
    loadDocs();
  }, []);

  const { agent } = useAgent();

  // 针对具体条款卡片的查看原文处理
  const handlePreviewClauseDoc = (clause: {
    docTitle: string;
    docId?: string;
    docUrl?: string;
    title?: string;
  }) => {
    const rawDocName = (clause.docTitle || clause.title || "").trim();
    if (!rawDocName) return;

    // 清理书名号等干扰字符，提升匹配率
    const cleanDocName = rawDocName.replace(/[《》]/g, "").trim();

    if (clause.docUrl) {
      setPreviewTarget({
        title: cleanDocName,
        url: clause.docUrl,
        fileName: cleanDocName.includes(".") ? cleanDocName : `${cleanDocName}.pdf`,
      });
      return;
    }

    const defaultDatasetId = "d4d0e9c6a05c11f199bf45be651e52f0";

    // 1. 如果自带明确的 docId
    if (clause.docId) {
      setPreviewTarget({
        title: cleanDocName,
        url: `/api/documents/${defaultDatasetId}/${clause.docId}`,
        fileName: cleanDocName.includes(".") ? cleanDocName : `${cleanDocName}.pdf`,
      });
      return;
    }

    // 2. 优先从当前 Agent 对话的 RAG 切片和文档元数据中精准匹配（100% 准确对应当前轮次）
    const ragDict = (agent?.state as any)?.rag_citations || {};
    for (const [, ctx] of Object.entries(ragDict) as [string, any][]) {
      // 查 doc_aggs
      for (const d of ctx?.doc_aggs || []) {
        const dName = (d.doc_name || "").replace(/[《》]/g, "").trim();
        if (dName && (dName.includes(cleanDocName) || cleanDocName.includes(dName))) {
          setPreviewTarget({
            title: d.doc_name,
            url: `/api/documents/${d.dataset_id || defaultDatasetId}/${d.doc_id}`,
            fileName: d.doc_name,
          });
          return;
        }
      }
      // 查 chunks
      for (const c of ctx?.chunks || []) {
        const cName = (c.doc_name || "").replace(/[《》]/g, "").trim();
        if (cName && (cName.includes(cleanDocName) || cleanDocName.includes(cName)) && c.doc_id) {
          setPreviewTarget({
            title: c.doc_name,
            url: `/api/documents/${c.dataset_id || defaultDatasetId}/${c.doc_id}`,
            fileName: c.doc_name,
          });
          return;
        }
      }
    }

    // 3. 从系统全量文档匹配库 (docsMap) 进行模糊匹配
    const lower = cleanDocName.toLowerCase();
    for (const [name, meta] of Object.entries(docsMap)) {
      const cleanMetaName = name.replace(/[《》]/g, "").toLowerCase();
      if (lower.includes(cleanMetaName) || cleanMetaName.includes(lower)) {
        setPreviewTarget({
          title: meta.name,
          url: `/api/documents/${meta.dataset_id}/${meta.doc_id}`,
          fileName: meta.name,
        });
        return;
      }
    }

    // 4. 如果仍未找到对应真实文件，提示暂无源文件下载链接
    alert(`暂未在知识库中找到《${cleanDocName}》的原始文件下载链接。`);
  };

  const getChangeBadge = (type: PolicyComparisonPair["changeType"]) => {
    switch (type) {
      case "added":
        return (
          <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20">
            新增机制
          </span>
        );
      case "modified":
        return (
          <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/20">
            重大调整
          </span>
        );
      case "removed":
        return (
          <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-rose-500/15 text-rose-700 dark:text-rose-300 border border-rose-500/20">
            废止取消
          </span>
        );
    }
  };

  // 1. 默认为空状态视图（尚未通过对话触发比对）
  if (!activeComparison || !activeComparison.pairs || activeComparison.pairs.length === 0) {
    return (
      <div className="h-full flex flex-col bg-background text-foreground overflow-hidden">
        {/* 顶部标题栏: 统一固定 h-[72px] */}
        <div className="shrink-0 h-[72px] px-6 border-b border-border bg-card/60 flex items-center justify-between gap-4 pr-72">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600/10 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-xs shrink-0">
              <GitCompare className="w-4 h-4" />
            </div>
            <h3 className="font-bold text-sm tracking-tight text-foreground">
              新旧政策比对沙盘
            </h3>
          </div>
        </div>

        {/* 纯净空状态占位 */}
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted-foreground select-none">
          <div className="w-14 h-14 rounded-2xl bg-muted/60 border border-border/80 flex items-center justify-center mb-4 text-muted-foreground/80 shadow-2xs">
            <MessageSquareDiff className="w-7 h-7" />
          </div>
          <h4 className="font-bold text-sm text-foreground mb-1.5">
            暂无政策对比任务
          </h4>
          <p className="text-xs max-w-sm leading-relaxed text-muted-foreground">
            在左侧对话中询问有关新旧政策变化、电价机制演进或条款对比的问题，系统将自动检索知识库并在此生成左右对齐的条款差异。
          </p>
        </div>
      </div>
    );
  }

  // 2. 有对话比对数据时的对比视图
  return (
    <div className="h-full flex flex-col bg-background text-foreground overflow-hidden relative">
      {/* 顶部标题栏: 统一固定 h-[72px] */}
      <div className="shrink-0 h-[72px] px-6 border-b border-border bg-card/60 flex items-center justify-between gap-4 pr-72">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-xs">
            <GitCompare className="w-4 h-4" />
          </div>
          <div className="min-w-0 flex flex-col justify-center">
            <h3 className="font-bold text-sm tracking-tight text-foreground truncate">
              {activeComparison.title || "新旧政策条款对比"}
            </h3>
            <span className="text-[11px] text-muted-foreground font-medium flex items-center gap-1.5 mt-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
              共识别 {activeComparison.pairs.length} 项条款变动
            </span>
          </div>
        </div>
      </div>

      {/* 列头（旧政策规定 vs 新政策规定） */}
      <div className="shrink-0 px-4 pt-3 pb-2 grid grid-cols-2 gap-3.5 text-xs font-bold border-b border-border/60 bg-muted/20">
        <div className="flex items-center justify-between text-rose-800 dark:text-rose-300 px-1">
          <span className="flex items-center gap-1.5">
            <Bookmark className="w-3.5 h-3.5 text-rose-600" />
            旧政策规定条款（{activeComparison.oldPolicyTag}）
          </span>
        </div>
        <div className="flex items-center justify-between text-emerald-800 dark:text-emerald-300 px-1">
          <span className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
            修订后新政策条款（{activeComparison.newPolicyTag}）
          </span>
        </div>
      </div>

      {/* 主体：左右严格 1 对 1 对应每一行变动 */}
      <div className="flex-1 min-h-0 p-4 overflow-y-auto space-y-4">
        {activeComparison.pairs.map((pair, idx) => (
          <div
            key={pair.id}
            className="rounded-xl border border-border bg-card/40 p-3 shadow-2xs hover:border-blue-500/30 transition-colors flex flex-col gap-2.5"
          >
            {/* 条目维度的标题栏 */}
            <div className="flex items-center justify-between text-xs pb-1.5 border-b border-border/50">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 font-mono text-[11px] font-bold flex items-center justify-center">
                  {idx + 1}
                </span>
                <span className="font-bold text-foreground">
                  {pair.dimension}
                </span>
              </div>
              <div>{getChangeBadge(pair.changeType)}</div>
            </div>

            {/* 左右 1 对 1 严格并排对称 */}
            <div className="grid grid-cols-2 gap-3.5 items-stretch text-xs">
              {/* 左侧：旧政策条款 */}
              <div className="flex flex-col justify-between p-3 rounded-lg border border-rose-200/50 dark:border-rose-900/30 bg-rose-50/30 dark:bg-rose-950/10">
                {pair.oldClause ? (
                  <>
                    <div>
                      <div className="font-bold text-rose-950 dark:text-rose-100 mb-1">
                        {pair.oldClause.section} {pair.oldClause.title}
                      </div>
                      <p className="text-stone-600 dark:text-stone-300 leading-relaxed mb-3">
                        {pair.oldClause.content}
                      </p>
                    </div>

                    {/* 来源与查看原文 */}
                    <div className="pt-2 border-t border-rose-200/40 dark:border-rose-900/30 flex items-center justify-between gap-2 text-[11px]">
                      <span
                        className="text-muted-foreground truncate flex-1 flex items-center gap-1 font-mono"
                        title={pair.oldClause.docTitle}
                      >
                        <FileText className="w-3 h-3 shrink-0 text-rose-600/70" />
                        <span className="truncate">
                          {pair.oldClause.docTitle}
                        </span>
                      </span>

                      <button
                        onClick={() => handlePreviewClauseDoc(pair.oldClause!)}
                        className="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded bg-background hover:bg-rose-500/10 text-rose-700 dark:text-rose-300 border border-border/80 hover:border-rose-500/30 font-medium transition-colors cursor-pointer shadow-2xs"
                      >
                        <Eye className="w-3 h-3" />
                        查看原文
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground italic text-[11px]">
                    （旧政策无此项要求 / 新增机制）
                  </div>
                )}
              </div>

              {/* 右侧：新政策条款 */}
              <div className="flex flex-col justify-between p-3 rounded-lg border border-emerald-200/50 dark:border-emerald-900/30 bg-emerald-50/30 dark:bg-emerald-950/10">
                {pair.newClause ? (
                  <>
                    <div>
                      <div className="font-bold text-emerald-950 dark:text-emerald-100 mb-1">
                        {pair.newClause.section} {pair.newClause.title}
                      </div>
                      <p className="text-stone-700 dark:text-stone-200 leading-relaxed mb-3">
                        {pair.newClause.content}
                      </p>
                    </div>

                    {/* 来源与查看原文 */}
                    <div className="pt-2 border-t border-emerald-200/40 dark:border-emerald-900/30 flex items-center justify-between gap-2 text-[11px]">
                      <span
                        className="text-muted-foreground truncate flex-1 flex items-center gap-1 font-mono"
                        title={pair.newClause.docTitle}
                      >
                        <FileText className="w-3 h-3 shrink-0 text-emerald-600/70" />
                        <span className="truncate">
                          {pair.newClause.docTitle}
                        </span>
                      </span>

                      <button
                        onClick={() => handlePreviewClauseDoc(pair.newClause!)}
                        className="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded bg-background hover:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-border/80 hover:border-emerald-500/30 font-medium transition-colors cursor-pointer shadow-2xs"
                      >
                        <Eye className="w-3 h-3" />
                        查看原文
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground italic text-[11px]">
                    （该项规定在新政策中已废止）
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 原生原文档在线预览弹窗 (Modal) */}
      {previewTarget && (
        <div className="absolute inset-0 z-50 bg-background/90 backdrop-blur-sm flex flex-col">
          <div className="px-5 py-3 border-b border-border bg-card flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0 pr-4">
              <FileText className="w-4 h-4 text-blue-600 shrink-0" />
              <span className="font-bold text-xs sm:text-sm truncate">
                原文件预览：{previewTarget.title}
              </span>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <a
                href={previewTarget.url}
                download={previewTarget.fileName}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-secondary hover:bg-secondary/80 text-secondary-foreground text-xs font-medium transition-colors"
              >
                <ExternalLink className="w-3 h-3" />
                下载源件
              </a>
              <button
                onClick={() => setPreviewTarget(null)}
                className="p-1 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                title="关闭预览"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div className="flex-1 min-h-0 bg-stone-50 dark:bg-stone-950 p-2">
            <FilePreviewer
              url={previewTarget.url}
              fileName={previewTarget.fileName}
            />
          </div>
        </div>
      )}
    </div>
  );
}
