import { useState, useEffect } from "react";
import { Sparkles, Calendar, HelpCircle, Server, Activity } from "lucide-react";
import Sidebar from "./components/Sidebar";
import ResumeEntry from "./components/ResumeEntry";
import CandidateFlow from "./components/CandidateFlow";
import AiOpsAssistant from "./components/AiOpsAssistant";
import { Candidate } from "./types";
import { DEMO_MODE, DEMO_CANDIDATES } from "./demoData";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function App() {
  const [currentTab, setCurrentTab] = useState<string>("resume");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch candidates from our backend (or use built-in demo data)
  const fetchCandidates = async () => {
    if (DEMO_MODE) {
      setCandidates(DEMO_CANDIDATES);
      setIsLoading(false);
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/api/candidates`);
      if (!response.ok) throw new Error("Failed to load candidates");
      const data = await response.json();
      setCandidates(data);
    } catch (e) {
      console.error("Error loading candidates database:", e);
    } finally {
      setIsLoading(false);
    }
  };

  // Used by CandidateFlow. In demo mode we accept the locally-mutated list,
  // otherwise we re-fetch from the backend.
  const handleUpdateCandidates = (next?: Candidate[]) => {
    if (DEMO_MODE) {
      setCandidates(next ?? DEMO_CANDIDATES);
    } else {
      fetchCandidates();
    }
  };

  useEffect(() => {
    fetchCandidates();
  }, []);

  // Sync date representation
  const [currentDateTime, setCurrentDateTime] = useState("");
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      // Format to Chinese custom date-time format for SaaS consistency
      const options: Intl.DateTimeFormatOptions = {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false
      };
      setCurrentDateTime(now.toLocaleString("zh-CN", options) + " (CST)");
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const getPageMeta = () => {
    switch (currentTab) {
      case "resume":
        return {
          title: "简历智能录入工作区",
          desc: "智能提取 BOSS/智联等文本，AI 智能预置并支持人机协同确认入库",
        };
      case "candidates":
        return {
          title: "招聘台账全流程生命周期",
          desc: "掌握全量候选人面试状态与筛选结论，支持快速安排后续日程",
        };
      case "assistant":
        return {
          title: "AI 招聘运营助手大盘",
          desc: "大模型智能扫描流程漏洞，自动梳理今日待办事项、宏观运营洞察与微信一键汇报",
        };
      default:
        return { title: "智聘 AI 平台", desc: "智能化驱动的企业招聘 SaaS 系统" };
    }
  };

  const meta = getPageMeta();

  return (
    <div className="flex h-screen bg-slate-100 text-slate-800 overflow-hidden font-sans">
      {/* Sidebar navigation */}
      <Sidebar 
        currentTab={currentTab} 
        setCurrentTab={setCurrentTab} 
        candidateCount={candidates.length} 
      />

      {/* Main Workspace Frame */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-50">
        {/* Top bar header */}
        <header className="bg-white border-b border-slate-200 h-16 shrink-0 px-8 flex items-center justify-between shadow-sm z-10">
          <div>
            <h2 className="text-sm font-sans font-extrabold text-slate-900 tracking-tight leading-none">
              {meta.title}
            </h2>
            <p className="text-[11px] text-slate-400 font-sans mt-1">
              {meta.desc}
            </p>
          </div>

          {/* Right utility items */}
          <div className="flex items-center gap-4">
            {/* Real-time CST Clock */}
            <div className="hidden md:flex items-center gap-1.5 text-slate-500 font-mono text-[11px] bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-xl font-medium">
              <Calendar className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span>{currentDateTime}</span>
            </div>

            {/* AI Engine Status Badge */}
            <div className="flex items-center gap-2 bg-indigo-50 border border-indigo-100 px-3 py-1.5 rounded-xl">
              <div className="flex h-2 w-2 relative shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
              </div>
              <span className="text-[10px] font-sans font-extrabold text-indigo-950 uppercase tracking-wider flex items-center gap-1">
                <Activity className="w-3 h-3 text-indigo-500" /> AI Engine: Python 后端
              </span>
            </div>
          </div>
        </header>

        {/* Content canvas with scroll support */}
        <main className="flex-1 overflow-y-auto p-8 max-w-7xl w-full mx-auto">
          {isLoading ? (
            <div className="h-full flex items-center justify-center flex-col gap-3">
              <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin shrink-0" />
              <p className="text-xs text-slate-400 font-sans font-medium">正在读取智聘数据库中...</p>
            </div>
          ) : (
            <div className="space-y-6">
              {currentTab === "resume" && (
                <ResumeEntry onCandidateAdded={(cand) => {
                  setCandidates([cand, ...candidates]);
                  setCurrentTab("candidates"); // Jump to ledger table upon entry
                }} />
              )}
              
              {currentTab === "candidates" && (
                <CandidateFlow 
                  candidates={candidates} 
                  onUpdateCandidates={handleUpdateCandidates} 
                />
              )}

              {currentTab === "assistant" && (
                <AiOpsAssistant 
                  candidatesCount={candidates.length} 
                />
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
