"use client";

import React, { useState } from "react";
import { X, ExternalLink, FileSpreadsheet, FileText, FileCode, CheckCircle2 } from "lucide-react";
import { findDocAggByName } from "@/lib/citation-service";
import { FilePreviewer } from "./file-previewer";

interface DocumentPillProps {
  docName: string;
  datasetId?: string;
  docId?: string;
}

function middleEllipsis(text: string, maxLength: number = 36): string {
  if (!text || text.length <= maxLength) return text;
  const start = text.slice(0, 18);
  const end = text.slice(-12);
  return `${start}...${end}`;
}

export function DocumentPill({ docName, datasetId, docId }: DocumentPillProps) {
  const [isOpen, setIsOpen] = useState(false);
  const cleanName = docName.trim();
  const displayName = cleanName.replace(/^(documents|uploads)\//i, "");

  // 尝试匹配 doc_id 和 dataset_id
  const matchedDoc = findDocAggByName(cleanName) || findDocAggByName(displayName);
  const effectiveDocId = docId || matchedDoc?.doc_id || "";
  const effectiveDatasetId = datasetId || matchedDoc?.dataset_id || "d4d0e9c6a05c11f199bf45be651e52f0";

  // 通过 Next.js 代理接口获取 RAGFlow 的文件二进制流
  const previewUrl = effectiveDocId
    ? `/api/documents/${effectiveDatasetId}/${effectiveDocId}`
    : "";

  const getDocBadgeIcon = (name: string) => {
    const lower = name.toLowerCase();
    if (lower.endsWith(".xlsx") || lower.endsWith(".xls") || lower.endsWith(".csv")) {
      return (
        <span className="flex items-center justify-center px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold text-[10px] tracking-tighter border border-emerald-500/20">
          XLSX
        </span>
      );
    }
    if (lower.endsWith(".docx") || lower.endsWith(".doc")) {
      return (
        <span className="flex items-center justify-center px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 font-bold text-[10px] tracking-tighter border border-blue-500/20">
          DOCX
        </span>
      );
    }
    if (lower.endsWith(".pdf")) {
      return (
        <span className="flex items-center justify-center px-1.5 py-0.5 rounded bg-red-500/10 text-red-600 dark:text-red-400 font-bold text-[10px] tracking-tighter border border-red-500/20">
          PDF
        </span>
      );
    }
    return (
      <span className="flex items-center justify-center px-1.5 py-0.5 rounded bg-stone-500/10 text-stone-600 dark:text-stone-300 font-bold text-[10px]">
        FILE
      </span>
    );
  };

  return (
    <>
      <span className="inline-block align-middle my-1 mr-2 select-none">
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="group inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-stone-100/90 hover:bg-blue-50 text-stone-800 dark:bg-stone-800/80 dark:hover:bg-blue-950/50 border border-stone-300/60 dark:border-stone-700/70 hover:border-blue-300 dark:hover:border-blue-700 text-xs font-medium transition-all duration-150 cursor-pointer shadow-2xs hover:shadow-xs active:scale-98"
          title={`点击在线预览《${displayName}》`}
        >
          {getDocBadgeIcon(displayName)}
          <span className="text-xs truncate max-w-[320px] font-sans">
            {middleEllipsis(displayName, 36)}
          </span>
          <span className="text-[10px] text-blue-600 dark:text-blue-400 font-normal opacity-80 group-hover:opacity-100 flex items-center gap-0.5">
            预览
          </span>
        </button>
      </span>

      {/* 极速原生物档预览模态框 */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 md:p-6 animate-in fade-in duration-150">
          <div className="relative w-full max-w-5xl h-[88vh] flex flex-col rounded-2xl bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="shrink-0 flex items-center justify-between gap-3 px-6 py-4 border-b border-stone-200/80 dark:border-stone-800 bg-stone-50/50 dark:bg-stone-950/50">
              <div className="flex items-center gap-3 min-w-0">
                {getDocBadgeIcon(displayName)}
                <div className="flex flex-col min-w-0">
                  <h3 className="font-semibold text-sm text-stone-900 dark:text-stone-100 truncate" title={displayName}>
                    {displayName}
                  </h3>
                  <span className="text-[11px] text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5" /> 知识库权威原文档
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {previewUrl && (
                  <a
                    href={previewUrl}
                    download={cleanName}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 dark:bg-stone-800 dark:hover:bg-stone-700 text-stone-700 dark:text-stone-200 text-xs font-medium transition-colors"
                  >
                    <ExternalLink className="w-3.5 h-3.5" /> 下载源文件
                  </a>
                )}
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 rounded-lg text-stone-400 hover:text-stone-600 dark:hover:text-stone-200 hover:bg-stone-100 dark:hover:bg-stone-800 cursor-pointer"
                  title="关闭预览"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Body: File Viewer Container */}
            <div className="flex-1 p-4 bg-stone-100/50 dark:bg-stone-950 overflow-hidden flex flex-col">
              {previewUrl ? (
                <FilePreviewer
                  url={previewUrl}
                  fileName={cleanName}
                  className="flex-1"
                />
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-stone-500 dark:text-stone-400 text-xs">
                  暂未关联到此文档的下载 URL 或 doc_id。
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
