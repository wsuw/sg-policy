export interface PolicyComparisonPair {
  id: string;
  dimension: string; // 变更维度，如：市场交易电价浮动范围
  changeType: "modified" | "added" | "removed"; // 变动性质
  impactLevel?: "high" | "medium" | "low";
  // 旧政策条款（如果是纯新增机制，则为 null）
  oldClause: {
    section: string;
    title: string;
    content: string;
    docTitle: string;
    docId?: string;
    docUrl?: string;
  } | null;
  // 新政策条款（如果是废止条款，则为 null）
  newClause: {
    section: string;
    title: string;
    content: string;
    docTitle: string;
    docId?: string;
    docUrl?: string;
  } | null;
}

export interface PolicyComparisonData {
  id: string;
  title: string;
  oldPolicyTag: string;
  newPolicyTag: string;
  pairs: PolicyComparisonPair[];
}

export const PRESET_COMPARISONS: PolicyComparisonData[] = [
  {
    id: "coal-power-pricing",
    title: "燃煤发电上网电价市场化改革新旧政策比对",
    oldPolicyTag: "基准旧规",
    newPolicyTag: "现行新规",
    pairs: [
      {
        id: "pair-1",
        dimension: "市场交易电价浮动范围",
        changeType: "modified",
        impactLevel: "high",
        oldClause: {
          section: "第二条",
          title: "基准价与浮动区间标准",
          docTitle: "发改价格规〔2019〕1658号《深化燃煤发电上网电价机制指导意见》",
          content:
            "将现行燃煤发电标杆上网电价机制改为‘基准价+上下浮动’的市场化价格机制。基准价按当地现行标杆电价确定，浮动范围为上浮不超过10%、下浮原则上不超过15%。",
        },
        newClause: {
          section: "第二条",
          title: "扩大市场交易电价浮动范围并放开高耗能限制",
          docTitle: "发改价格〔2021〕1439号《关于进一步深化燃煤发电上网电价市场化改革的通知》",
          content:
            "将燃煤发电市场交易电价浮动范围由现行的上浮不超过10%、下浮原则上不超过15%，扩大为上下浮动原则上均不超过20%。高耗能企业市场交易电价不受上浮20%限制。电力现货价格不受上述幅度限制。",
        },
      },
      {
        id: "pair-2",
        dimension: "上网电量入市比例",
        changeType: "modified",
        impactLevel: "high",
        oldClause: {
          section: "第一条",
          title: "稳步推进燃煤发电电量入市",
          docTitle: "发改价格规〔2019〕1658号《深化燃煤发电上网电价机制指导意见》",
          content:
            "坚持市场化方向，具备市场交易条件的燃煤发电电量通过市场化方式在浮动范围内形成。现阶段对尚未参与市场化交易的电量，仍由各省电网企业按原规定调度收购。",
        },
        newClause: {
          section: "第一条",
          title: "推动燃煤发电电量全部进入电力市场",
          docTitle: "发改价格〔2021〕1439号《关于进一步深化燃煤发电上网电价市场化改革的通知》",
          content:
            "各地要有序放开全部燃煤发电电量，推动燃煤发电电量全部进入电力市场，在‘基准价+上下浮动’范围内形成交易电价。取消各地燃煤发电标杆上网电价政策，实行‘能涨能跌’的市场化价格机制。",
        },
      },
      {
        id: "pair-3",
        dimension: "工商业销售电价机制",
        changeType: "modified",
        impactLevel: "high",
        oldClause: {
          section: "第三条",
          title: "继续执行目录销售电价",
          docTitle: "发改价格〔2018〕156号《关于降低一般工商业电价有关事项的通知》",
          content:
            "继续执行工商业及居民、农业目录销售电价。参与电力市场交易的用户，交易电价加上输配电价和政府性基金及附加，形成最终用电价格；未参与交易用户执行目录电价。",
        },
        newClause: {
          section: "第三条",
          title: "全面取消工商业目录电价并建立代理购电机制",
          docTitle: "发改办价格〔2021〕809号《关于组织开展电网企业代理购电工作有关事项的通知》",
          content:
            "全面放开工商业用户进入电力市场。各地要有序推动工商业用户全部进入电力市场，按照市场价格购电；取消工商业目录销售电价。对暂未直接从电力市场购电的用户由电网企业代理购电，代理购电价格按市场交易价格等额传导。",
        },
      },
      {
        id: "pair-4",
        dimension: "电力现货与辅助服务衔接",
        changeType: "added",
        impactLevel: "medium",
        oldClause: {
          section: "第五条",
          title: "现货试点探索（旧要求）",
          docTitle: "发改能源〔2017〕1453号《关于开展电力现货市场建设试点工作的通知》",
          content:
            "国家电力现货试点地区应稳步推进现货交易，做好中长期合同与现货交易之间的衔接配套工作，尚未建立用户侧辅助服务分摊机制。",
        },
        newClause: {
          section: "第五条",
          title: "现货价格不限浮动与辅助服务分摊",
          docTitle: "国能发监管〔2021〕61号《电力辅助服务管理办法》",
          content:
            "各地要加快推进电力现货市场建设，电力现货交易价格不受‘上下浮动20%’限制，充分反映实时供求关系；健全辅助服务费用向工商业用户合理分摊机制，保障系统安全充裕度。",
        },
      },
    ],
  },
];
