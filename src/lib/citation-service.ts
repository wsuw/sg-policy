export interface CitationChunk {
  ref_id: number;
  chunk_id?: string;
  doc_id?: string;
  doc_name: string;
  doc_type?: string;
  similarity: number;
  content: string;
  dataset_id?: string;
  vector_similarity?: number | null;
  term_similarity?: number | null;
}

export interface DocAggItem {
  doc_id: string;
  doc_name: string;
  count: number;
  dataset_id?: string;
}

export interface MessageRAGContext {
  chunks: CitationChunk[];
  doc_aggs: DocAggItem[];
}

// 按轮次 messageId 隔离存储每一轮的切片与文档数据
const roundContextMap = new Map<string, MessageRAGContext>();
// 全局切片平铺缓存
const flatChunkCache = new Map<number, CitationChunk>();

/**
 * 注册指定 messageId 轮次的 RAGContext 到客户端缓存
 */
export function registerMessageRAGContext(messageId: string, context: MessageRAGContext) {
  if (!messageId || !context) return;
  roundContextMap.set(messageId, context);
  for (const chunk of context.chunks || []) {
    if (chunk && typeof chunk.ref_id === "number") {
      flatChunkCache.set(chunk.ref_id, chunk);
    }
  }
}

/**
 * 批量同步整个 state.rag_citations 字典
 */
export function syncRAGCitationsDict(dict?: Record<string, MessageRAGContext> | null) {
  if (!dict || typeof dict !== "object") return;
  for (const [msgId, ctx] of Object.entries(dict)) {
    if (ctx && typeof ctx === "object") {
      registerMessageRAGContext(msgId, ctx);
    }
  }
}

/**
 * 获取指定轮次及 refId 的切片详情
 */
export function getMessageCitationChunk(refId: number, messageId?: string): CitationChunk {
  // 1. 优先查本轮上下文
  if (messageId && roundContextMap.has(messageId)) {
    const ctx = roundContextMap.get(messageId)!;
    const found = ctx.chunks?.find((c) => c.ref_id === refId);
    if (found) return found;
  }

  // 2. 全局缓存命中
  if (flatChunkCache.has(refId)) {
    return flatChunkCache.get(refId)!;
  }

  // 3. 遍历所有历史轮次上下文
  for (const ctx of roundContextMap.values()) {
    const found = ctx.chunks?.find((c) => c.ref_id === refId);
    if (found) return found;
  }

  return {
    ref_id: refId,
    doc_name: `知识库切片 #${refId}`,
    doc_type: "docx",
    content: `正在加载知识库切片 #${refId} 的原文详情...`,
    similarity: 0.85,
  };
}

/**
 * 根据文件名在已加载的来源文档中查找对应的 doc_id 和 dataset_id
 */
export function findDocAggByName(docName: string): DocAggItem | undefined {
  if (!docName) return undefined;
  const clean = docName.trim();
  for (const ctx of roundContextMap.values()) {
    const found = ctx.doc_aggs?.find((d) => d.doc_name.trim() === clean);
    if (found) return found;
  }
  return undefined;
}

/**
 * 清空历史切片缓存
 */
export function clearCitationCache() {
  roundContextMap.clear();
  flatChunkCache.clear();
}
