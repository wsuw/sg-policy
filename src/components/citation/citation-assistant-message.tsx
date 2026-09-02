"use client";

import React, { useMemo } from "react";
import { Streamdown } from "streamdown";
import {
  CopilotChatAssistantMessage,
  useAgent,
  type CopilotChatAssistantMessageProps,
} from "@copilotkit/react-core/v2";
import { CitationBadge } from "@/components/citation/citation-badge";
import { DocumentPill } from "@/components/citation/document-pill";
import {
  syncRAGCitationsDict,
  getMessageCitationChunk,
  type CitationChunk,
  type DocAggItem,
  type MessageRAGContext,
} from "@/lib/citation-service";

/**
 * 将包含 [REF:n] 和 [DOC:xxx] 的纯文本分割并替换为交互组件
 */
function renderTextWithCitations(text: string, messageId?: string): React.ReactNode {
  if (!text) return text;

  const pattern = /\[REF:(\d+)\]|\[DOC:([^\]]+)\]/g;
  const elements: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      elements.push(text.substring(lastIndex, match.index));
    }

    if (match[1] !== undefined) {
      const refId = parseInt(match[1], 10);
      elements.push(
        <CitationBadge
          key={`ref-${refId}-${match.index}`}
          refId={refId}
          messageId={messageId}
        />
      );
    } else if (match[2] !== undefined) {
      const docName = match[2].trim();
      elements.push(<DocumentPill key={`doc-${docName}-${match.index}`} docName={docName} />);
    }

    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) {
    elements.push(text.substring(lastIndex));
  }

  return elements;
}

/**
 * 递归遍历 React 节点树，将文本中的 [REF:n] 转换为引用角标
 */
function transformCitationsInReactNode(
  node: React.ReactNode,
  messageId?: string,
  keyPrefix = "c"
): React.ReactNode {
  if (typeof node === "string") {
    if (node.includes("[REF:") || node.includes("[DOC:")) {
      return renderTextWithCitations(node, messageId);
    }
    return node;
  }

  if (Array.isArray(node)) {
    return node.map((child, i) =>
      transformCitationsInReactNode(child, messageId, `${keyPrefix}-${i}`)
    );
  }

  if (React.isValidElement(node)) {
    const props = node.props as { children?: React.ReactNode };
    if (props && props.children) {
      return React.cloneElement(node, {
        ...props,
        children: transformCitationsInReactNode(props.children, messageId, `${keyPrefix}-child`),
      } as any);
    }
  }

  return node;
}

/**
 * 自定义 Markdown 渲染插槽
 */
function CitationMarkdownRenderer({
  content,
  className,
  messageId,
  ...props
}: {
  content?: string;
  className?: string;
  messageId?: string;
  [key: string]: any;
}) {
  const text = content || "";
  const { agent } = useAgent();

  // 从 agent.state.rag_citations 中获取当前引用的文档
  const docAggs = useMemo<DocAggItem[]>(() => {
    if (!text || !text.includes("[REF:")) {
      return [];
    }

    const refMatches = Array.from(text.matchAll(/\[REF:(\d+)\]/g));
    const refIds = Array.from(new Set(refMatches.map((m: any) => parseInt(m[1], 10))));
    if (refIds.length === 0) return [];

    const ragDict = (agent?.state as any)?.rag_citations || {};
    const dictEntries: [string, MessageRAGContext][] =
      typeof ragDict === "object" ? Object.entries(ragDict) : [];

    // 优先匹配包含当前 refIds 的 round
    let roundContext: MessageRAGContext | undefined;
    for (const [, ctx] of dictEntries) {
      if (ctx?.chunks?.some((c) => refIds.includes(c.ref_id))) {
        roundContext = ctx;
        break;
      }
    }
    if (!roundContext && dictEntries.length > 0) {
      roundContext = dictEntries[dictEntries.length - 1][1];
    }

    const allCandidateChunks: CitationChunk[] = [
      ...(roundContext?.chunks || []),
      ...dictEntries.flatMap(([, ctx]) => ctx?.chunks || []),
    ];

    const docsMap = new Map<string, DocAggItem>();
    for (const refId of refIds) {
      const chunk =
        allCandidateChunks.find((c) => c.ref_id === refId) ||
        getMessageCitationChunk(refId, messageId);

      if (chunk && chunk.doc_name && !chunk.doc_name.startsWith("知识库切片 #")) {
        if (!docsMap.has(chunk.doc_name)) {
          docsMap.set(chunk.doc_name, {
            doc_id: chunk.doc_id || "",
            doc_name: chunk.doc_name,
            count: 1,
            dataset_id: chunk.dataset_id,
          });
        }
      }
    }

    if (docsMap.size > 0) {
      return Array.from(docsMap.values());
    }

    return roundContext?.doc_aggs || (dictEntries.length > 0 ? dictEntries[dictEntries.length - 1][1]?.doc_aggs : []) || [];
  }, [text, agent?.state, messageId]);

  const components = useMemo(() => ({
    p: ({ node, children, ...rest }: any) => (
      <p {...rest} className="my-3 leading-7">
        {transformCitationsInReactNode(children, messageId)}
      </p>
    ),
    li: ({ node, children, ...rest }: any) => (
      <li {...rest} className="my-1.5 leading-7">
        {transformCitationsInReactNode(children, messageId)}
      </li>
    ),
    h1: ({ node, children, ...rest }: any) => (
      <h1 {...rest} className="text-2xl font-bold mt-6 mb-3">
        {transformCitationsInReactNode(children, messageId)}
      </h1>
    ),
    h2: ({ node, children, ...rest }: any) => (
      <h2 {...rest} className="text-xl font-bold mt-5 mb-2.5">
        {transformCitationsInReactNode(children, messageId)}
      </h2>
    ),
    h3: ({ node, children, ...rest }: any) => (
      <h3 {...rest} className="text-lg font-bold mt-4 mb-2">
        {transformCitationsInReactNode(children, messageId)}
      </h3>
    ),
    h4: ({ node, children, ...rest }: any) => (
      <h4 {...rest} className="text-base font-bold mt-3 mb-1.5">
        {transformCitationsInReactNode(children, messageId)}
      </h4>
    ),
    strong: ({ node, children, ...rest }: any) => (
      <strong {...rest} className="font-semibold text-stone-900 dark:text-stone-100">
        {transformCitationsInReactNode(children, messageId)}
      </strong>
    ),
    em: ({ node, children, ...rest }: any) => (
      <em {...rest} className="italic">
        {transformCitationsInReactNode(children, messageId)}
      </em>
    ),
    td: ({ node, children, ...rest }: any) => (
      <td {...rest} className="px-3 py-2 text-sm border border-stone-200 dark:border-stone-800">
        {transformCitationsInReactNode(children, messageId)}
      </td>
    ),
    th: ({ node, children, ...rest }: any) => (
      <th {...rest} className="px-3 py-2 text-sm font-semibold bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-800">
        {transformCitationsInReactNode(children, messageId)}
      </th>
    ),
    blockquote: ({ node, children, ...rest }: any) => (
      <blockquote {...rest} className="border-l-4 border-blue-500/50 pl-4 my-3 italic text-stone-600 dark:text-stone-300">
        {transformCitationsInReactNode(children, messageId)}
      </blockquote>
    ),
  }), [messageId]);

  return (
    <div className={`prose dark:prose-invert max-w-none text-[15px] leading-7 text-stone-800 dark:text-stone-200 prose-a:no-underline ${className || ""}`}>
      <Streamdown components={components} {...props}>
        {text}
      </Streamdown>

      {/* 消息正文正下方无缝呈现参考来源文档列表 */}
      {docAggs.length > 0 && (
        <div className="pt-3 mt-3 border-t border-stone-200/70 dark:border-stone-800/80 not-prose animate-in fade-in duration-300">
          <div className="text-xs text-stone-500 dark:text-stone-400 mb-2 font-medium flex items-center gap-1.5">
            <span>参考来源文档 ({docAggs.length})</span>
          </div>
          <div className="flex flex-wrap gap-2 items-center">
            {docAggs.map((doc, idx) => (
              <DocumentPill
                key={`doc-agg-${doc.doc_id || idx}-${doc.doc_name}`}
                docName={doc.doc_name}
                docId={doc.doc_id}
                datasetId={doc.dataset_id}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * 结构化 RAG 状态同步器：监听 agent.state.rag_citations 字典
 */
export function RAGStateSynchronizer() {
  const { agent } = useAgent();

  React.useEffect(() => {
    const ragDict = (agent?.state as any)?.rag_citations;
    if (ragDict && typeof ragDict === "object") {
      syncRAGCitationsDict(ragDict);
    }
  }, [agent?.state]);

  return null;
}

/**
 * 统一导出的 AssistantMessage 插槽组件
 */
export function CitationAssistantMessage(props: CopilotChatAssistantMessageProps) {
  const messageId = props.message?.id;

  const renderMarkdown = React.useCallback(
    (renderProps: any) => (
      <CitationMarkdownRenderer
        {...renderProps}
        messageId={messageId}
      />
    ),
    [messageId]
  );

  return (
    <CopilotChatAssistantMessage
      {...props}
      markdownRenderer={renderMarkdown}
    />
  );
}
