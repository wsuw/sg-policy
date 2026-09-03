interface ModeToggleProps {
  mode: "chat" | "app" | "compare";
  onModeChange: (mode: "chat" | "app" | "compare") => void;
}

export function ModeToggle({ mode, onModeChange }: ModeToggleProps) {
  return (
    <div className="fixed top-4 right-4 z-50 flex items-center min-h-[46px] rounded-[4px] border border-[var(--border)] bg-[var(--secondary)] p-1.5 shadow-xs">
      <button
        onClick={() => onModeChange("chat")}
        className={`px-3 sm:px-4 py-1.5 rounded-[2px] text-[13px] leading-[20px] font-medium transition-all cursor-pointer ${
          mode === "chat"
            ? "bg-[var(--card)] text-[var(--card-foreground)] shadow-sm"
            : "text-[var(--muted-foreground)] hover:text-foreground"
        }`}
      >
        对话
      </button>
      <button
        onClick={() => onModeChange("app")}
        className={`px-3 sm:px-4 py-1.5 rounded-[2px] text-[13px] leading-[20px] font-medium transition-all cursor-pointer ${
          mode === "app"
            ? "bg-[var(--card)] text-[var(--card-foreground)] shadow-sm"
            : "text-[var(--muted-foreground)] hover:text-foreground"
        }`}
      >
        政策沙盘
      </button>
      <button
        onClick={() => onModeChange("compare")}
        className={`px-3 sm:px-4 py-1.5 rounded-[2px] text-[13px] leading-[20px] font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
          mode === "compare"
            ? "bg-[var(--card)] text-blue-600 dark:text-blue-400 font-bold shadow-sm"
            : "text-[var(--muted-foreground)] hover:text-foreground"
        }`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
        政策比对
      </button>
    </div>
  );
}
