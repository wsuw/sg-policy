import { z } from "zod";
import { useFrontendTool } from "@copilotkit/react-core/v2";
import type { PolicyComparisonData } from "@/components/policy-comparison";

interface UsePolicyComparisonToolProps {
  onTriggerComparison: (data: PolicyComparisonData) => void;
}

export function usePolicyComparisonTool({
  onTriggerComparison,
}: UsePolicyComparisonToolProps) {
  useFrontendTool({
    name: "comparePolicies",
    description:
      "用于新旧政策对比与演进展示。当用户询问政策问题（如北京市居民阶梯电价），且知识库中存在新旧不同历史版本（如2004年单一电价调整 vs 2012年至今阶梯电价）、政策修订演变、或条款冲突时，必须调用该工具在右侧工作台呈现新旧条款1对1对照。",
    parameters: z.object({
      title: z.string().describe("比对主题，如：燃煤发电上网电价市场化改革新旧政策比对"),
      oldPolicyTag: z.string().describe("旧政策简短标签，如：基准旧规"),
      newPolicyTag: z.string().describe("新政策简短标签，如：现行新规"),
      pairs: z.array(
        z.object({
          id: z.string().describe("唯一ID，如 pair-1"),
          dimension: z.string().describe("变动维度，如：市场交易电价浮动范围、工商业目录电价取消"),
          changeType: z.enum(["modified", "added", "removed"]).describe("变动类型：modified(重大调整), added(新增机制), removed(废止取消)"),
          impactLevel: z.enum(["high", "medium", "low"]).optional(),
          oldClause: z
            .object({
              section: z.string().describe("章节/条目编号，如：第二条"),
              title: z.string().describe("条目标题"),
              content: z.string().describe("旧政策条款原文"),
              docTitle: z.string().describe("该条款所属的具体文件全称或发文字号"),
              docId: z.string().optional(),
              docUrl: z.string().optional(),
            })
            .nullable()
            .describe("对应的旧政策条款；若为纯新增条款则为 null"),
          newClause: z
            .object({
              section: z.string().describe("章节/条目编号，如：第二条"),
              title: z.string().describe("条目标题"),
              content: z.string().describe("新政策条款原文"),
              docTitle: z.string().describe("该条款所属的具体文件全称或发文字号"),
              docId: z.string().optional(),
              docUrl: z.string().optional(),
            })
            .nullable()
            .describe("对应的新政策条款；若为废止条款则为 null"),
        })
      ).describe("仅包含发生变动的对应条款对列表"),
    }),
    handler: async (args) => {
      onTriggerComparison({
        id: "dynamic-" + Date.now(),
        title: args.title,
        oldPolicyTag: args.oldPolicyTag,
        newPolicyTag: args.newPolicyTag,
        pairs: args.pairs,
      });
      return "已成功为用户打开政策比对沙盘，展示发生变动的新旧政策条款 1 对 1 对照。";
    },
  });
}
