"use client";

import { useState } from "react";
import { ExampleLayout } from "@/components/example-layout";
import { ExampleCanvas } from "@/components/example-canvas";
import { PolicyComparator, type PolicyComparisonData } from "@/components/policy-comparison";
import {
  useGenerativeUIExamples,
  useExampleSuggestions,
  usePolicyComparisonTool,
} from "@/hooks";
import { CitationAssistantMessage, RAGStateSynchronizer } from "@/components/citation";

import {
  CopilotChat,
  CopilotChatConfigurationProvider,
} from "@copilotkit/react-core/v2";

import styles from "./page.module.css";

export default function HomePage() {
  const [layoutMode, setLayoutMode] = useState<"chat" | "app" | "compare">("chat");
  const [activeComparisonData, setActiveComparisonData] =
    useState<PolicyComparisonData | null>(null);

  useGenerativeUIExamples();

  // 注册 policy comparison Copilot tool
  usePolicyComparisonTool({
    onTriggerComparison: (data) => {
      setActiveComparisonData(data);
      setLayoutMode("compare");
    },
  });

  return (
    <CopilotChatConfigurationProvider
      agentId="default"
      labels={{
        welcomeMessageText: "您好！有什么我可以帮您？",
        chatInputPlaceholder: "咨询电力政策、规程或新旧政策对比...",
        modalHeaderTitle: "国网电策通",
      }}
    >
      <RAGStateSynchronizer />
      <div className={styles.layout}>
        <div className={styles.mainPanel}>
          <ExampleLayout
            mode={layoutMode}
            onModeChange={setLayoutMode}
            chatContent={
              <CopilotChat
                attachments={{ enabled: true }}
                input={{
                  disclaimer: () => null,
                  className: "pb-4 mb-2",
                }}
                messageView={{
                  assistantMessage: CitationAssistantMessage as any,
                }}
              />
            }
            appContent={<ExampleCanvas />}
            compareContent={
              <PolicyComparator customData={activeComparisonData} />
            }
          />
        </div>
      </div>
    </CopilotChatConfigurationProvider>
  );
}
