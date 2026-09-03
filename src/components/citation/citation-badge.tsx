"use client";

import React, { useMemo } from "react";
import { useAgent } from "@copilotkit/react-core/v2";
import { getMessageCitationChunk, type CitationChunk, type MessageRAGContext } from "@/lib/citation-service";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { FileText, FileSpreadsheet, FileCode, CheckCircle2 } from "lucide-react";

interface CitationBadgeProps {
  refId: number;
  messageId?: string;
  initialChunk?: CitationChunk;
}

export function CitationBadge({ refId, messageId, initialChunk }: CitationBadgeProps) {
  const [open, setOpen] = React.useState(false);
  const { agent } = useAgent();

  // 动态且响应式地解析当前切片，优先从 agent.state.rag_citations 全局字典读取
  const chunk = useMemo(() => {
    if (initialChunk) return initialChunk;

    const ragDict = (agent?.state as any)?.rag_citations;
    if (ragDict && typeof ragDict === "object") {
      const entries: [string, MessageRAGContext][] = Object.entries(ragDict);
      // 1. 匹配对应 messageId
      if (messageId && ragDict[messageId]?.chunks) {
        const found = ragDict[messageId].chunks.find((c: any) => c.ref_id === refId);
        if (found) return found;
      }
      // 2. 逆序遍历最近的 round
      for (const [, ctx] of [...entries].reverse()) {
        const found = ctx?.chunks?.find((c: any) => c.ref_id === refId);
        if (found) return found;
      }
    }

    // 3. 降级查本地 service 缓存
    return getMessageCitationChunk(refId, messageId);
  }, [agent?.state, refId, messageId, initialChunk]);

  const getDocIcon = (docName: string = "") => {
    const lower = docName.toLowerCase();
    if (lower.endsWith(".xlsx") || lower.endsWith(".xls") || lower.endsWith(".csv")) {
      return (
        <span className="p-1 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 shrink-0 inline-flex">
          <FileSpreadsheet className="w-3.5 h-3.5" />
        </span>
      );
    }
    if (lower.endsWith(".docx") || lower.endsWith(".doc")) {
      return (
        <span className="p-1 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 shrink-0 inline-flex">
          <FileText className="w-3.5 h-3.5" />
        </span>
      );
    }
    return (
      <span className="p-1 rounded bg-stone-500/10 text-stone-600 dark:text-stone-300 border border-stone-500/20 shrink-0 inline-flex">
        <FileCode className="w-3.5 h-3.5" />
      </span>
    );
  };

  return (
    <span className="inline-block align-baseline mx-0.5 select-none">
      <HoverCard
        open={open}
        onOpenChange={setOpen}
      >
        <HoverCardTrigger
          className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-mono font-medium no-underline decoration-transparent select-none bg-stone-100 hover:bg-blue-50 text-stone-700 hover:text-blue-600 dark:bg-stone-800 dark:text-stone-300 dark:hover:bg-blue-950/60 dark:hover:text-blue-400 border border-stone-300/70 dark:border-stone-700/80 transition-all duration-150 cursor-pointer shadow-2xs hover:shadow-xs active:scale-95 [text-decoration:none!important]"
        >
          <span className="no-underline [text-decoration:none!important]">Fig.</span>
          <span className="no-underline [text-decoration:none!important]">{refId}</span>
        </HoverCardTrigger>

        {/* shadcn/ui HoverCard Popup */}
        <HoverCardContent
          side="top"
          align="center"
          sideOffset={8}
          className="w-[420px] max-w-[90vw] p-4 rounded-xl bg-popover/98 backdrop-blur-md text-popover-foreground shadow-xl border border-border space-y-3 animate-in fade-in zoom-in-95 duration-150"
        >
          {/* Header */}
          <div className="flex items-center justify-between gap-2 pb-2 border-b border-border/80 text-xs">
            <div className="font-semibold text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-blue-500" />
              <span>知识库切片引用 [Fig. {refId}]</span>
            </div>
            {chunk.similarity ? (
              <span className="px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 font-mono text-[11px] font-medium border border-blue-500/20">
                匹配度 {(chunk.similarity * 100).toFixed(0)}%
              </span>
            ) : null}
          </div>

          {/* Chunk Content */}
          <div className="text-xs text-foreground/90 leading-relaxed max-h-56 overflow-y-auto pr-1 whitespace-pre-wrap font-sans bg-muted/40 p-3 rounded-lg border border-border/50 selection:bg-blue-600 selection:text-white min-h-[60px]">
            {chunk.content || "正在检索知识库切片详细内容..."}
          </div>

          {/* Document Source Footer */}
          <div className="pt-2 border-t border-border/80 flex items-center gap-2 text-xs">
            {getDocIcon(chunk.doc_name)}
            <span
              className="truncate text-muted-foreground font-medium text-[11px]"
              title={chunk.doc_name}
            >
              {chunk.doc_name || `文档切片 #${refId}`}
            </span>
          </div>
        </HoverCardContent>
      </HoverCard>
    </span>
  );
}
