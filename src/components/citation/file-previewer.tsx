"use client";

import React, { useEffect, useState } from "react";
import { FileViewer } from "@file-viewer/react";
import { officeRenderers } from "@file-viewer/preset-office";
import { Loader2, AlertCircle, RefreshCw } from "lucide-react";

interface FilePreviewerProps {
  url: string;
  fileName: string;
  className?: string;
}

export function FilePreviewer({ url, fileName, className = "" }: FilePreviewerProps) {
  const [fileObject, setFileObject] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDocument = async () => {
    try {
      setLoading(true);
      setError(null);

      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`获取文件失败 (HTTP ${res.status}: ${res.statusText})`);
      }

      const blob = await res.blob();
      // 构造 File 对象传给 file-viewer 引擎
      const file = new File([blob], fileName, {
        type: blob.type || "application/octet-stream",
      });

      setFileObject(file);
    } catch (err: any) {
      console.error("加载文件预览失败:", err);
      setError(err?.message || "网络或服务异常，无法加载文档预览。");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (url) {
      fetchDocument();
    }
  }, [url, fileName]);

  if (loading) {
    return (
      <div className={`flex flex-col items-center justify-center h-full min-h-[400px] gap-3 text-stone-500 dark:text-stone-400 ${className}`}>
        <Loader2 className="w-8 h-8 animate-spin text-blue-600 dark:text-blue-400" />
        <p className="text-sm font-medium">正在从知识库获取原始文档《{fileName}》...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex flex-col items-center justify-center h-full min-h-[400px] gap-3 p-6 text-center text-stone-600 dark:text-stone-300 ${className}`}>
        <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-950/60 text-red-600 dark:text-red-400 flex items-center justify-center">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h4 className="font-semibold text-base">文档预览加载失败</h4>
        <p className="text-xs text-stone-500 dark:text-stone-400 max-w-md">{error}</p>
        <button
          type="button"
          onClick={fetchDocument}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 mt-2 rounded-lg bg-stone-100 hover:bg-stone-200 dark:bg-stone-800 dark:hover:bg-stone-700 text-xs font-medium transition-colors cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" /> 重试加载
        </button>
      </div>
    );
  }

  if (!fileObject) {
    return null;
  }

  const Viewer = FileViewer as any;

  return (
    <div className={`w-full h-full min-h-[500px] flex flex-col bg-stone-50/50 dark:bg-stone-950 rounded-xl overflow-hidden border border-stone-200/80 dark:border-stone-800 ${className}`}>
      <Viewer
        file={fileObject}
        preset={officeRenderers}
        className="w-full h-full flex-1 overflow-auto"
      />
    </div>
  );
}
