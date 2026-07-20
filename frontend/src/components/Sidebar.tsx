import { FileText, Users, BrainCircuit, Sparkles, LogOut, Briefcase } from "lucide-react";

interface SidebarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  candidateCount: number;
}

export default function Sidebar({ currentTab, setCurrentTab, candidateCount }: SidebarProps) {
  const menuItems = [
    { id: "resume", name: "简历智能录入", icon: FileText, desc: "AI 解析与确认入库" },
    { id: "candidates", name: "候选人全流程", icon: Users, desc: "招聘台账与面试跟进" },
    { id: "assistant", name: "AI 招聘运营助手", icon: BrainCircuit, desc: "待办、洞察与简报" },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-100 flex flex-col h-full border-r border-slate-800">
      {/* Brand Header */}
      <div className="p-6 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-600 rounded-lg text-white">
            <Sparkles className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h1 className="font-sans font-bold text-lg tracking-tight text-white leading-none">智聘 AI</h1>
            <p className="text-xs text-slate-400 mt-1">企业级 AI 招聘运营工作台</p>
          </div>
        </div>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 p-4 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setCurrentTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-left transition-all group ${
                isActive
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/10"
                  : "text-slate-300 hover:bg-slate-850 hover:text-white"
              }`}
            >
              <Icon className={`w-5 h-5 shrink-0 ${isActive ? "text-white" : "text-slate-400 group-hover:text-slate-200"}`} />
              <div className="flex-1 min-w-0">
                <div className="font-sans font-medium text-sm leading-snug flex items-center justify-between">
                  <span>{item.name}</span>
                  {item.id === "candidates" && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-sans font-semibold ${
                      isActive ? "bg-indigo-500 text-white" : "bg-slate-800 text-slate-400"
                    }`}>
                      {candidateCount}
                    </span>
                  )}
                  {item.id === "assistant" && (
                    <span className="flex h-2 w-2 relative">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                  )}
                </div>
                <p className={`text-[11px] truncate mt-0.5 ${isActive ? "text-indigo-200" : "text-slate-400 group-hover:text-slate-300"}`}>
                  {item.desc}
                </p>
              </div>
            </button>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/40">
        <div className="flex items-center gap-3 p-2 bg-slate-850 rounded-xl">
          <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold text-slate-200 uppercase">
            HR
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-slate-200 truncate">HR 运营专家</p>
            <p className="text-[10px] text-slate-400 truncate">zhaomolan123@gmail.com</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
