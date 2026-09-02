"use client";

import type { ReactNode } from "react";
import { useState } from "react";
import { ModeToggle } from "./mode-toggle";
import { useFrontendTool } from "@copilotkit/react-core/v2";

interface ExampleLayoutProps {
  chatContent: ReactNode;
  appContent: ReactNode;
}

export function ExampleLayout({ chatContent, appContent }: ExampleLayoutProps) {
  const [mode, setMode] = useState<"chat" | "app">("chat");

  useFrontendTool({
    name: "enableAppMode",
    description:
      "Enable app mode, make sure its open when interacting with todos.",
    handler: async () => {
      setMode("app");
    },
  });

  useFrontendTool({
    name: "enableChatMode",
    description: "Enable chat mode",
    handler: async () => {
      setMode("chat");
    },
  });

  return (
    <div className="h-full flex flex-row pb-2">
      <ModeToggle mode={mode} onModeChange={setMode} />

      {/* Chat Content */}
      <div
        className={`h-full flex flex-col dark:bg-stone-950 ${
          mode === "app"
            ? "w-1/2 px-6 max-lg:hidden" // Half/half with the canvas; hidden on mobile in app mode
            : "flex-1 max-lg:px-4"
        }`}
      >
        {/* Clear the threads drawer's floating launcher/collapsed cluster, which
            is fixed at the top-left corner. Below 1024px (mobile off-canvas) that
            is always present → max-lg:pl-24. On desktop it only appears when the
            drawer is COLLAPSED — detected via --cpk-drawer-reserved-width, which
            the drawer sets to 0px on collapse (else its 320px default): the pl
            calc resolves to 1.5rem (pl-6) when expanded and ~6rem when collapsed,
            so the logo never sits under the cluster. max-lg:pt-2.5 + pb-0
            vertically center the logo with that launcher and the top-right
            Chat/App toggle (both pinned at top-2). */}
        <div className="shrink-0 pt-[23px] px-6 pb-2 flex gap-3 items-center align-center border-b border-stone-200/50 dark:border-stone-800/60 pb-3.5 mb-1">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center text-white shadow-xs font-bold text-sm tracking-wider">
            SG
          </div>
          <div className="flex flex-col">
            <span className="font-extrabold text-lg tracking-tight text-stone-900 dark:text-stone-100 leading-tight">
              国网电策通 <span className="text-xs font-mono font-medium text-blue-600 dark:text-blue-400">SG-Policy</span>
            </span>
            <span className="text-[11px] text-stone-500 dark:text-stone-400 font-medium">
              字字有据，行行可溯 · 智能决策沙盘
            </span>
          </div>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto">{chatContent}</div>

        {/* 底部政策来源提示条 */}
        <div className="shrink-0 mx-4 mb-2 px-3.5 py-1.5 rounded-lg bg-blue-50/80 dark:bg-blue-950/40 border border-blue-200/70 dark:border-blue-800/60 flex items-center justify-between text-xs text-blue-900 dark:text-blue-200 shadow-2xs backdrop-blur-xs">
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-600 dark:bg-blue-400"></span>
            </span>
            <span className="font-medium tracking-tight">
              演示政策依据：本系统所有研读、诊断与检索的政策数据均来源于国家电网官方服务平台{" "}
              <a
                href="https://www.95598.cn"
                target="_blank"
                rel="noreferrer"
                className="font-semibold underline decoration-blue-400 underline-offset-2 hover:text-blue-600 dark:hover:text-blue-300 transition-colors"
              >
                95598.cn
              </a>{" "}
              公开信息
            </span>
          </div>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-100/70 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 hidden sm:inline-block">
            权威公开溯源
          </span>
        </div>
      </div>

      {/* State Panel */}
      {mode === "app" && (
        <div className="h-full w-1/2 max-lg:w-full border-l border-[var(--border)] max-lg:border-l-0 overflow-hidden">
          <div className="w-full h-full">{appContent}</div>
        </div>
      )}
    </div>
  );
}
