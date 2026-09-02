"use client";

import { ExampleLayout } from "@/components/example-layout";
import { ExampleCanvas } from "@/components/example-canvas";
import { useGenerativeUIExamples, useExampleSuggestions } from "@/hooks";
import { CitationAssistantMessage, RAGStateSynchronizer } from "@/components/citation";

import {
  CopilotChat,
  CopilotChatConfigurationProvider,
  CopilotThreadsDrawer,
} from "@copilotkit/react-core/v2";

import styles from "./page.module.css";

export default function HomePage() {
  useGenerativeUIExamples();
  // useExampleSuggestions(); // 暂时隐藏测试建议按钮，留作后续测试使用

  return (
    <CopilotChatConfigurationProvider
      agentId="default"
      labels={{
        welcomeMessageText: "您好！我是国网智策 Policy Copilot，有什么可以帮您？",
        chatInputPlaceholder: "请输入您想咨询的电力政策、规程或业务需求...",
        modalHeaderTitle: "国网电策通",
      }}
    >
      <RAGStateSynchronizer />
      <div className={styles.layout}>
        <div className={styles.mainPanel}>
          <ExampleLayout
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
          />
        </div>
      </div>
    </CopilotChatConfigurationProvider>
  );
}
