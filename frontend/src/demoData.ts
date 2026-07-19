// 演示模式（demo mode）内置数据。
// 当构建时设置了 VITE_DEMO_MODE=1，前端不连任何后端，
// 直接用这里的数据展示完整 UI 与交互流程，便于公网部署后分享。
import { AIInsights, Candidate, ParsedResumeInfo, TodayTodo } from "./types";

export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "1";

const HIGH = "high" as const;
const LOW = "low" as const;

export const DEMO_CANDIDATES: Candidate[] = [
  {
    id: "APP-2026-001",
    name: "陈静",
    phone: "13812349876",
    email: "chenjing@example.com",
    hrName: "张经理",
    jobTitle: "数据分析师",
    department: "数据部",
    status: "screening",
    currentRound: 0,
    latestConclusion: "简历已入库，等待用人部门筛选",
    resumeFileName: "陈静-数据分析师.txt",
    resumeText:
      "求职意向：数据分析师\n姓名：陈静\n电话：13812349876\n教育经历：北京大学 统计学硕士\n专业技能：SQL, Python, R, Tableau, Excel, PowerBI",
    parsedInfo: {
      name: "陈静",
      phone: "13812349876",
      email: "chenjing@example.com",
      jobTitle: "数据分析师",
      department: "数据部",
      education: "北京大学 统计学硕士 (2020 - 2023)",
      experience: "某知名互联网大厂 | 数据分析师：负责用户增长数据模型搭建，优化后次留率提高 5.2%",
      skills: ["SQL", "Python", "R", "Tableau", "Excel", "PowerBI"],
      summary: "候选人技能：SQL、Python、Tableau；具有深厚的数理统计基础与商业嗅觉。",
      confidence: {
        name: HIGH, phone: HIGH, email: HIGH, jobTitle: HIGH,
        department: LOW, education: HIGH, experience: HIGH,
      },
    },
    interviews: [],
    createdAt: "2026-07-15 09:24",
  },
  {
    id: "APP-2026-002",
    name: "刘强",
    phone: "15987651234",
    email: "liuqiang@example.com",
    hrName: "张经理",
    jobTitle: "前端开发工程师",
    department: "研发部",
    status: "interviewing",
    currentRound: 1,
    latestConclusion: "技术面通过，进入综合面试轮",
    resumeFileName: "刘强-前端开发.txt",
    resumeText:
      "姓名：刘强\n手机：15987651234\n求职岗位：前端开发工程师\n技术栈：React, TypeScript, Vue3",
    parsedInfo: {
      name: "刘强",
      phone: "15987651234",
      email: "liuqiang@example.com",
      jobTitle: "前端开发工程师",
      department: "研发部",
      education: "浙江大学 软件工程本科 (2017 - 2021)",
      experience: "杭州某电商独角兽 | 核心前端开发：主导 Webpack 迁 Vite，构建速度提升 60%",
      skills: ["React", "TypeScript", "Vue3", "Webpack", "Vite"],
      summary: "候选人技能：React、TypeScript、Vue3；前端架构经验丰富。",
      confidence: {
        name: HIGH, phone: HIGH, email: HIGH, jobTitle: HIGH,
        department: LOW, education: HIGH, experience: HIGH,
      },
    },
    interviews: [
      {
        id: "INT-001",
        round: 1,
        interviewer: "技术总监-王",
        date: "2026-07-20 14:00",
        result: "pass",
        feedback: "基础扎实，工程化经验丰富，通过。",
      },
    ],
    createdAt: "2026-07-16 11:02",
  },
  {
    id: "APP-2026-003",
    name: "王芳",
    phone: "13600001111",
    email: "wangfang@example.com",
    hrName: "李经理",
    jobTitle: "产品经理",
    department: "产品部",
    status: "offer",
    currentRound: 3,
    latestConclusion: "三轮面试通过，已发 Offer，待入职",
    resumeFileName: "王芳-产品经理.txt",
    resumeText: "姓名：王芳\n邮箱：wangfang@example.com\n求职意向：产品经理",
    parsedInfo: {
      name: "王芳",
      phone: "13600001111",
      email: "wangfang@example.com",
      jobTitle: "产品经理",
      department: "产品部",
      education: "复旦大学 管理学本科",
      experience: "5 年 B 端产品经验，主导过 3 条核心业务线",
      skills: ["需求分析", "Axure", "数据驱动", "PRD"],
      summary: "候选人技能：需求分析、Axure；5 年 B 端产品经验。",
      confidence: {
        name: HIGH, phone: HIGH, email: HIGH, jobTitle: HIGH,
        department: LOW, education: HIGH, experience: HIGH,
      },
    },
    interviews: [
      {
        id: "INT-002",
        round: 1,
        interviewer: "产品负责人-赵",
        date: "2026-07-12 10:00",
        result: "pass",
        feedback: "产品 sense 好，通过。",
      },
      {
        id: "INT-003",
        round: 2,
        interviewer: "业务负责人-钱",
        date: "2026-07-15 15:30",
        result: "pass",
        feedback: "业务理解深，通过。",
      },
      {
        id: "INT-004",
        round: 3,
        interviewer: "HRD-孙",
        date: "2026-07-18 16:00",
        result: "pass",
        feedback: "文化匹配，发放 Offer。",
      },
    ],
    createdAt: "2026-07-10 14:30",
  },
];

export const DEMO_PARSE_RESULT: ParsedResumeInfo & { extractedText: string } = {
  name: "张子涵",
  phone: "13623456789",
  email: "zihan.zhang@example.com",
  jobTitle: "算法工程师",
  department: "AI研究部",
  education: "复旦大学 应用数学本科 (2018 - 2022)",
  experience:
    "企业级知识库问答系统（RAG）负责人：检索召回率提升至 92%，业务问答准确率达 88%。",
  skills: ["PyTorch", "TensorFlow", "Python", "NLP", "LLM Fine-tuning", "RAG"],
  summary:
    "候选人技能：PyTorch、TensorFlow、NLP、RAG；有从 0 搭建企业级 RAG 系统的实战经验。",
  confidence: {
    name: HIGH, phone: HIGH, email: HIGH, jobTitle: HIGH,
    department: LOW, education: HIGH, experience: HIGH,
  },
  extractedText:
    "求职意向：算法工程师\n求职部门：AI研究部\n姓名：张子涵\n电话：13623456789\n邮箱：zihan.zhang@example.com\n教育：复旦大学 应用数学本科 (2018 - 2022)\n专业技能：PyTorch, TensorFlow, Python, NLP, LLM Fine-tuning, RAG, CUDA\n主要项目经历：\n- 带领团队从 0 搭建企业级知识库问答系统（RAG），检索召回率提升至 92%，业务问答准确率达 88%。\n- 参与多模态大模型的微调与剪枝优化，推理延迟降低 45%。",
};

export const DEMO_DASHBOARD: {
  todos: TodayTodo[];
  insights: AIInsights;
  report: string;
} = {
  todos: [
    {
      id: "todo-APP-2026-001",
      title: "待部门初筛",
      candidateName: "陈静",
      jobTitle: "数据分析师",
      department: "数据部",
      suggestedAction: "发送简历给数据部负责人，并在企业微信群催办反馈",
      priority: "high",
    },
    {
      id: "todo-APP-2026-002",
      title: "待安排下一轮面试",
      candidateName: "刘强",
      jobTitle: "前端开发工程师",
      department: "研发部",
      suggestedAction: "确认综合面试官与面试时间，推进下一轮",
      priority: "medium",
    },
  ],
  insights: {
    summary: "当前共有 3 名候选人、3 条申请，重点关注 数据分析师 / 前端开发工程师。",
    bulletPoints: [
      "筛选待处理 1 条，面试中 1 条，建议优先推进卡在筛选环节的候选人。",
      "当前主招核心岗位：数据分析师、前端开发工程师。",
      "评价记录可继续沉淀为结构化数据，后续可训练岗位画像与面试通过率分析。",
    ],
    suggestedFocusJob: "数据分析师",
    stuckCandidatesCount: 1,
  },
  report:
    "企业微信招聘进展简报：\n今日共有 3 条招聘申请，待筛选 1 条，面试中 1 条，已发 Offer 1 条。\n重点岗位：数据分析师、前端开发工程师。\n建议 HR 优先跟进待筛选候选人（陈静），并提醒用人部门及时反馈。",
};
