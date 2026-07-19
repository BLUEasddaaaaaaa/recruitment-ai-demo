import { useState, useEffect } from "react";
import { 
  BrainCircuit, Calendar, CheckSquare, Sparkles, AlertCircle, 
  Copy, Check, FileText, TrendingUp, Users, Inbox, ArrowUpRight, 
  RefreshCw, MessageSquareCode, ArrowRight, CornerDownLeft, Info
} from "lucide-react";
import { TodayTodo, AIInsights } from "../types";
import { DEMO_MODE, DEMO_DASHBOARD } from "../demoData";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

interface AiOpsAssistantProps {
  candidatesCount: number;
}

export default function AiOpsAssistant({ candidatesCount }: AiOpsAssistantProps) {
  const [todos, setTodos] = useState<TodayTodo[]>([]);
  const [insights, setInsights] = useState<AIInsights | null>(null);
  const [report, setReport] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  const fetchAIInsights = async () => {
    setIsLoading(true);
    setError("");
    if (DEMO_MODE) {
      setTodos(DEMO_DASHBOARD.todos);
      setInsights(DEMO_DASHBOARD.insights);
      setReport(DEMO_DASHBOARD.report);
      setIsLoading(false);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/ai/dashboard`);
      if (!res.ok) throw new Error("Failed to load AI Insights");
      const data = await res.json();
      
      setTodos(data.todos);
      setInsights(data.insights);
      setReport(data.report);
    } catch (e: any) {
      setError("无法连接到 AI 服务进行实时运营分析。");
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAIInsights();
  }, [candidatesCount]); // Refetch if candidate count changes

  const handleCopyReport = async () => {
    try {
      await navigator.clipboard.writeText(report);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch (err) {
      console.error("Failed to copy text: ", err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header banner with refresh */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 border border-slate-800 shadow-md">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="bg-indigo-500 text-white text-[10px] px-2 py-0.5 rounded-full font-sans font-bold uppercase tracking-wider flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-amber-300 shrink-0" /> Real-time GenAI
            </span>
              <span className="text-xs text-indigo-300 font-sans font-semibold">
                Python 招聘 AI 后端智能化招聘治理
              </span>
          </div>
          <h2 className="text-xl font-sans font-bold text-white tracking-tight flex items-center gap-2 mt-1">
            <BrainCircuit className="w-5 h-5 text-indigo-400 shrink-0" />
            AI 招聘运营助手
          </h2>
          <p className="text-xs text-slate-300 max-w-xl leading-relaxed">
            基于当前招聘台账的全部候选人漏斗数据，大模型自动推导今日跟进任务、发现流程堵点、生成结构化洞察报告。
          </p>
        </div>
        
        <button
          onClick={fetchAIInsights}
          disabled={isLoading}
          className="self-start md:self-auto flex items-center gap-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-sans font-bold transition-all shrink-0 shadow-lg shadow-indigo-600/20 active:scale-[0.98]"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>{isLoading ? "AI 正在分析大盘..." : "重新跑大模型生成分析"}</span>
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-900 text-xs rounded-xl flex items-center gap-2 font-sans shadow-sm">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Grid: 1. Today's Todos (Highlight Standout), 2. Insights & 3. One-click Brief Report */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Span: Today's To-Dos (Highly Prominent Area) */}
        <div className="lg:col-span-7 space-y-5">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-rose-50 flex items-center justify-center text-rose-500">
                  <CheckSquare className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-sans font-bold text-slate-800 tracking-tight">
                    1. 今日待办 (AI 智能生成)
                  </h3>
                  <p className="text-[11px] text-slate-400 font-sans">
                    根据流程滞留状态和决策时间计算，优先级最高、需今日处理
                  </p>
                </div>
              </div>
              <span className="text-[10px] bg-rose-50 text-rose-700 px-2 py-0.5 rounded-full border border-rose-200 font-sans font-semibold">
                待办任务: {todos.length} 项
              </span>
            </div>

            {isLoading ? (
              <div className="py-20 text-center space-y-2">
                <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
                <p className="text-xs text-slate-400 font-sans">AI 正在深度扫描台账流程卡点...</p>
              </div>
            ) : todos.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400 font-sans bg-slate-50 border border-dashed border-slate-200 rounded-xl">
                今日无高优待办项，简历漏斗极其健康！
              </div>
            ) : (
              <div className="space-y-3.5">
                {todos.map((todo) => (
                  <div 
                    key={todo.id} 
                    className="p-4 rounded-xl border border-slate-200 hover:border-slate-300 bg-slate-50/50 hover:bg-slate-50 transition-all flex flex-col md:flex-row gap-3 items-start justify-between"
                  >
                    <div className="space-y-1.5 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`text-[9.5px] font-sans font-bold px-1.5 py-0.5 rounded ${
                          todo.priority === "high" 
                            ? "bg-rose-50 text-rose-700 border border-rose-150" 
                            : todo.priority === "medium" 
                            ? "bg-amber-50 text-amber-700 border border-amber-150" 
                            : "bg-slate-100 text-slate-600 border border-slate-200"
                        }`}>
                          {todo.priority === "high" ? "最高优先级" : todo.priority === "medium" ? "中等优先级" : "日常跟进"}
                        </span>
                        <h4 className="text-xs font-sans font-bold text-slate-800">{todo.title}</h4>
                      </div>
                      
                      {/* Candidate info badge */}
                      <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-sans text-slate-500">
                        <span className="bg-slate-200/60 text-slate-700 px-1.5 py-0.5 rounded font-semibold">{todo.candidateName}</span>
                        <span>投递</span>
                        <span className="text-slate-700 font-medium">{todo.jobTitle}</span>
                        <span>({todo.department})</span>
                      </div>

                      {/* AI Action tip */}
                      <p className="text-xs text-slate-600 font-sans leading-relaxed pl-2 border-l-2 border-indigo-400/80 bg-white p-2 rounded-lg border border-slate-100/50 mt-1">
                        <strong>建议动作：</strong>{todo.suggestedAction}
                      </p>
                    </div>

                    <div className="text-[10px] text-indigo-600 font-sans font-semibold shrink-0 self-end md:self-center bg-indigo-50 border border-indigo-100 px-2.5 py-1.5 rounded-lg">
                      待跟进
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Span: 2. Insights & 3. One-click Brief Report */}
        <div className="lg:col-span-5 space-y-6">
          {/* 2. AI Operational Insights */}
          <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-500">
                <TrendingUp className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-sans font-bold text-slate-800 tracking-tight">
                  2. AI 运营洞察 (自然语言分析)
                </h3>
                <p className="text-[11px] text-slate-400 font-sans">
                  基于实时大盘的多维漏斗深度总结与预警
                </p>
              </div>
            </div>

            {isLoading ? (
              <div className="py-12 text-center text-xs text-slate-400 font-sans">
                AI 正在撰写宏观洞察报告...
              </div>
            ) : insights ? (
              <div className="space-y-4 animate-fade-in">
                {/* Micro stat block */}
                <div className="grid grid-cols-2 gap-3 text-center">
                  <div className="bg-indigo-50/50 border border-indigo-100 rounded-xl p-3">
                    <span className="text-[10px] font-sans font-bold text-indigo-800 uppercase">
                      卡点筛选中候选人
                    </span>
                    <div className="text-2xl font-sans font-bold text-indigo-950 mt-1">
                      {insights.stuckCandidatesCount} 人
                    </div>
                  </div>
                  <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3">
                    <span className="text-[10px] font-sans font-bold text-slate-500 uppercase">
                      当前主招核心岗位
                    </span>
                    <div className="text-sm font-sans font-bold text-slate-800 truncate mt-2">
                      {insights.suggestedFocusJob}
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-indigo-950/5 rounded-xl border border-indigo-100/40 text-xs text-slate-700 leading-relaxed font-sans font-medium">
                  {insights.summary}
                </div>

                <ul className="space-y-2.5 text-xs text-slate-600 font-sans">
                  {insights.bulletPoints.map((pt, i) => (
                    <li key={i} className="flex items-start gap-2 leading-relaxed">
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                      <span>{pt}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="text-center py-6 text-xs text-slate-400 font-sans">
                暂无洞察数据，请点击上方重新分析。
              </div>
            )}
          </div>

          {/* 3. One-click Report Area */}
          <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-500">
                  <MessageSquareCode className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-sans font-bold text-slate-800 tracking-tight">
                    3. 一键生成汇报简报
                  </h3>
                  <p className="text-[11px] text-slate-400 font-sans">
                    可直接一键复制到企业微信群，展现招聘成效
                  </p>
                </div>
              </div>
            </div>

            {isLoading ? (
              <div className="py-12 text-center text-xs text-slate-400 font-sans">
                AI 正在排版企业微信格式简报...
              </div>
            ) : report ? (
              <div className="space-y-3 animate-fade-in">
                {/* Text Block Area */}
                <div className="relative">
                  <textarea
                    readOnly
                    rows={6}
                    value={report}
                    className="w-full text-xs font-mono bg-slate-900 text-slate-200 rounded-xl p-3.5 focus:outline-none leading-relaxed resize-none border border-slate-800"
                  />
                  <div className="absolute top-2 right-2 text-[9px] uppercase font-mono text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded">
                    wechat style
                  </div>
                </div>

                {/* Big Action Button */}
                <button
                  onClick={handleCopyReport}
                  className={`w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-xs font-sans font-bold transition-all shadow-md ${
                    copied 
                      ? "bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-600/10" 
                      : "bg-slate-900 hover:bg-slate-850 text-white shadow-slate-900/10"
                  }`}
                >
                  {copied ? (
                    <>
                      <Check className="w-4 h-4 text-emerald-300" />
                      <span>已成功复制到剪贴板！可以直接发送了</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 text-slate-300" />
                      <span>复制到企业微信群汇报</span>
                    </>
                  )}
                </button>
              </div>
            ) : (
              <div className="text-center py-6 text-xs text-slate-400 font-sans">
                暂无简报数据。
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
