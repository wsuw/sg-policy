"use client";

import { PolicyDocumentViewer } from "./policy-viewer";

export function ExampleCanvas() {
  return (
    <div className="h-full w-full overflow-hidden bg-[--background]">
      <PolicyDocumentViewer />
    </div>
  );
}
