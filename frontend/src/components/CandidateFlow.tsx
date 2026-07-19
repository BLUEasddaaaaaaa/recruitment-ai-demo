import React, { useState, useEffect } from "react";
import { 
  Search, Filter, Eye, Plus, ArrowRight, User, Phone, Mail, 
  Building2, Briefcase, Calendar, CheckCircle2, XCircle, Clock, 
  Trash2, Award, ChevronRight, FileText, Send, AlertCircle, RefreshCw 
} from "lucide-react";
import { Candidate, InterviewRecord } from "../types";
import { DEMO_MODE } from "../demoData";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

interface CandidateFlowProps {
  candidates: Candidate[];
  onUpdateCandidates: (next?: Candidate[]) => void;
}

export default function CandidateFlow({ candidates, onUpdateCandidates }: CandidateFlowProps) {
  // Selection
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);

  // Filters
  const [filterJob, setFilterJob] = useState("");
  const [filterDept, setFilterDept] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterHR, setFilterHR] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  // New Interview Form State
  const [formRound, setFormRound] = useState(1);
  const [formInterviewer, setFormInterviewer] = useState("");
  const [formDate, setFormDate] = useState("");
  const [formResult, setFormResult] = useState<"pass" | "fail" | "pending">("pending");
  const [formFeedback, setFormFeedback] = useState("");
  
  const [isSubmittingInterview, setIsSubmittingInterview] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [actionError, setActionError] = useState("");

  // Update selected candidate state whenever database changes
  useEffect(() => {
    if (selectedCandidate) {
      const fresh = candidates.find(c => c.id === selectedCandidate.id);
      if (fresh) {
        setSelectedCandidate(fresh);
      } else {
        setSelectedCandidate(null);
      }
    }
  }, [candidates]);

  // Unique options for filters
  const jobs = Array.from(new Set(candidates.map(c => c.jobTitle))).filter(Boolean);
  const depts = Array.from(new Set(candidates.map(c => c.department))).filter(Boolean);
  const hrs = Array.from(new Set(candidates.map(c => c.hrName))).filter(Boolean);

  // Filtered list
  const filteredCandidates = candidates.filter((c) => {
    if (filterJob && c.jobTitle !== filterJob) return false;
    if (filterDept && c.department !== filterDept) return false;
    if (filterStatus && c.status !== filterStatus) return false;
    if (filterHR && c.hrName !== filterHR) return false;
    if (searchTerm) {
      const match = c.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                    c.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                    c.latestConclusion.toLowerCase().includes(searchTerm.toLowerCase());
      if (!match) return false;
    }
    return true;
  });

  // Handle department status changes (e.g. status transition)
  const handleStatusChange = async (id: string, newStatus: Candidate["status"]) => {
    setIsUpdatingStatus(true);
    setActionError("");
    try {
      let latestConclusion = "";
      if (newStatus === "screening") {
        latestConclusion = "部门筛选中";
      } else if (newStatus === "interviewing") {
        latestConclusion = "已安排面试阶段";
      } else if (newStatus === "rejected") {
        latestConclusion = "简历筛选不通过/淘汰";
      } else if (newStatus === "offer") {
        latestConclusion = "已通过最终考核，发送录取意向书";
      }

      if (DEMO_MODE) {
        const updated = candidates.map((c) =>
          c.id === id ? { ...c, status: newStatus, latestConclusion } : c
        );
        onUpdateCandidates(updated);
        setIsUpdatingStatus(false);
        return;
      }

      const res = await fetch(`${API_BASE}/api/applications/${id}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus, latestConclusion })
      });
      if (!res.ok) throw new Error("Failed to update status");
      
      onUpdateCandidates();
    } catch (err: any) {
      setActionError(err.message || "更新状态失败");
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  // Append Interview Record
  const handleAddInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCandidate) return;
    if (!formInterviewer.trim()) {
      setActionError("请填写面试官名称");
      return;
    }

    setIsSubmittingInterview(true);
    setActionError("");
    const newRecord: InterviewRecord = {
      id: `INT-${Date.now()}`,
      round: Number(formRound),
      interviewer: formInterviewer,
      date: formDate || new Date().toISOString().replace("T", " ").substring(0, 16),
      result: formResult,
      feedback: formFeedback,
    };
    try {
      if (DEMO_MODE) {
        const updated = candidates.map((c) =>
          c.id === selectedCandidate.id
            ? {
                ...c,
                interviews: [...c.interviews, newRecord],
                currentRound: Math.max(c.currentRound, Number(formRound)),
                latestConclusion:
                  formResult === "pass"
                    ? "面试通过，进入下一阶段"
                    : formResult === "fail"
                    ? "本轮考核未通过"
                    : "面试评定中",
              }
            : c
        );
        onUpdateCandidates(updated);
        setFormInterviewer("");
        setFormFeedback("");
        setFormResult("pending");
        setFormRound(selectedCandidate.interviews.length + 2);
        setIsSubmittingInterview(false);
        return;
      }

      const response = await fetch(`${API_BASE}/api/applications/${selectedCandidate.id}/interviews`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          round: Number(formRound),
          interviewer: formInterviewer,
          date: newRecord.date,
          result: formResult,
          feedback: formFeedback
        })
      });

      if (!response.ok) throw new Error("Failed to save interview");

      onUpdateCandidates();
      
      // Clear form states
      setFormInterviewer("");
      setFormFeedback("");
      setFormResult("pending");
      setFormRound(selectedCandidate.interviews.length + 2); // Default to next round
    } catch (err: any) {
      setActionError(err.message || "添加面试记录失败");
    } finally {
      setIsSubmittingInterview(false);
    }
  };

  // Delete Candidate
  const handleDeleteCandidate = async (id: string) => {
    if (!confirm("确认删除该候选人吗？此操作不可逆。")) return;
    if (DEMO_MODE) {
      const updated = candidates.filter((c) => c.id !== id);
      setSelectedCandidate(null);
      onUpdateCandidates(updated);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/candidates/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete candidate");
      setSelectedCandidate(null);
      onUpdateCandidates();
    } catch (e: any) {
      alert("删除失败: " + e.message);
    }
  };

  // Status mapping to colors
  const statusConfig = {
    screening: { label: "部门初筛", bg: "bg-blue-50 text-blue-700 border-blue-200" },
    interviewing: { label: "面试中", bg: "bg-indigo-50 text-indigo-700 border-indigo-200" },
    rejected: { label: "已淘汰", bg: "bg-slate-100 text-slate-500 border-slate-200" },
    offer: { label: "录用/Offer", bg: "bg-emerald-50 text-emerald-700 border-emerald-200" }
  };

  return (
    <div className="space-y-6">
      {/* Search and Filters Bar */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-4 space-y-4">
        <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
          <div className="relative w-full md:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3 shrink-0" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="搜索候选人姓名、申请ID、结论..."
              className="w-full text-xs font-sans pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>

          <div className="flex items-center gap-2 self-end md:self-auto">
            <button
              onClick={() => {
                setFilterJob("");
                setFilterDept("");
                setFilterStatus("");
                setFilterHR("");
                setSearchTerm("");
              }}
              className="text-xs text-slate-500 hover:text-indigo-600 font-sans font-medium px-2 py-1 transition-all"
            >
              重置所有筛选
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {/* Job Filter */}
          <div className="space-y-1">
            <span className="text-[10px] font-sans font-bold text-slate-400 block uppercase">投递岗位</span>
            <select
              value={filterJob}
              onChange={(e) => setFilterJob(e.target.value)}
              className="w-full text-xs font-sans bg-slate-50 border border-slate-200 rounded-xl p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 font-medium"
            >
              <option value="">全部岗位</option>
              {jobs.map((j) => (
                <option key={j} value={j}>{j}</option>
              ))}
            </select>
          </div>

          {/* Department Filter */}
          <div className="space-y-1">
            <span className="text-[10px] font-sans font-bold text-slate-400 block uppercase">负责部门</span>
            <select
              value={filterDept}
              onChange={(e) => setFilterDept(e.target.value)}
              className="w-full text-xs font-sans bg-slate-50 border border-slate-200 rounded-xl p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 font-medium"
            >
              <option value="">全部部门</option>
              {depts.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div className="space-y-1">
            <span className="text-[10px] font-sans font-bold text-slate-400 block uppercase">流程状态</span>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="w-full text-xs font-sans bg-slate-50 border border-slate-200 rounded-xl p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 font-medium"
            >
              <option value="">全部状态</option>
              <option value="screening">部门初筛</option>
              <option value="interviewing">面试中</option>
              <option value="rejected">已淘汰</option>
              <option value="offer">录用/Offer</option>
            </select>
          </div>

          {/* HR Filter */}
          <div className="space-y-1">
            <span className="text-[10px] font-sans font-bold text-slate-400 block uppercase">跟进 HR</span>
            <select
              value={filterHR}
              onChange={(e) => setFilterHR(e.target.value)}
              className="w-full text-xs font-sans bg-slate-50 border border-slate-200 rounded-xl p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 font-medium"
            >
              <option value="">全部 HR</option>
              {hrs.map((h) => (
                <option key={h} value={h}>{h}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Main Content Layout - Split Screen if selected */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Ledger Table */}
        <div className={`transition-all duration-300 ${selectedCandidate ? "w-full lg:w-[58%]" : "w-full"}`}>
          <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <h3 className="text-sm font-sans font-bold text-slate-800 tracking-tight flex items-center gap-1.5">
                <span>招聘台账列表</span>
                <span className="text-[10.5px] font-normal text-slate-400">
                  (已加载 {filteredCandidates.length} / {candidates.length} 条)
                </span>
              </h3>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50 text-[10.5px] font-sans font-bold text-slate-400 uppercase tracking-wider">
                    <th className="py-3 px-4">申请ID / 候选人</th>
                    <th className="py-3 px-4">招聘需求</th>
                    <th className="py-3 px-4">跟进 HR</th>
                    <th className="py-3 px-4">状态 / 进度</th>
                    <th className="py-3 px-4">最近结论</th>
                    <th className="py-3 px-4">简历</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredCandidates.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-xs text-slate-400 font-sans">
                        未检索到匹配的候选人申请记录
                      </td>
                    </tr>
                  ) : (
                    filteredCandidates.map((cand) => {
                      const isSelected = selectedCandidate?.id === cand.id;
                      const status = statusConfig[cand.status] || { label: cand.status, bg: "bg-slate-100 text-slate-600" };
                      
                      return (
                        <tr
                          key={cand.id}
                          onClick={() => {
                            setSelectedCandidate(cand);
                            setFormRound(cand.interviews.length + 1);
                          }}
                          className={`cursor-pointer transition-all text-xs font-sans group ${
                            isSelected 
                              ? "bg-indigo-50/70 border-l-4 border-indigo-600 font-medium" 
                              : "hover:bg-slate-50/80 border-l-4 border-transparent"
                          }`}
                        >
                          {/* ID & Candidate */}
                          <td className="py-3.5 px-4 space-y-1">
                            <div className="font-mono text-[10px] text-slate-400 leading-none">
                              {cand.id}
                            </div>
                            <div className="font-sans font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
                              {cand.name}
                            </div>
                          </td>

                          {/* Job & Dept */}
                          <td className="py-3.5 px-4 space-y-1">
                            <div className="text-slate-800 font-medium">{cand.jobTitle}</div>
                            <div className="text-[10px] text-slate-400">{cand.department}</div>
                          </td>

                          {/* HR Name */}
                          <td className="py-3.5 px-4 text-slate-500 font-medium">
                            {cand.hrName}
                          </td>

                          {/* Status */}
                          <td className="py-3.5 px-4 space-y-1">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-sans font-bold border ${status.bg}`}>
                              {status.label}
                            </span>
                            <div className="text-[10px] text-slate-400 pl-1">
                              已历 {cand.interviews.length} 轮面试
                            </div>
                          </td>

                          {/* Latest Conclusion */}
                          <td className="py-3.5 px-4 max-w-[160px] truncate text-slate-500 text-[11px]" title={cand.latestConclusion}>
                            {cand.latestConclusion}
                          </td>

                          {/* Attachment */}
                          <td className="py-3.5 px-4">
                            <span className="p-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-600 inline-block" title={cand.resumeFileName}>
                              <FileText className="w-3.5 h-3.5" />
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Candidate Detail Panel (Emerges right side) */}
        {selectedCandidate && (
          <div className="w-full lg:w-[42%] bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden animate-slide-in">
            {/* Header with Title and Close button */}
            <div className="p-4 border-b border-slate-100 bg-slate-900 text-white flex items-center justify-between">
              <div>
                <div className="text-[10px] font-mono text-indigo-300 leading-none">
                  {selectedCandidate.id}
                </div>
                <h3 className="text-sm font-sans font-bold text-white mt-1">
                  候选人流程看板: {selectedCandidate.name}
                </h3>
              </div>
              <button
                onClick={() => setSelectedCandidate(null)}
                className="text-slate-400 hover:text-white font-sans text-xs bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded"
              >
                关闭面板
              </button>
            </div>

            {/* Error messaging */}
            {actionError && (
              <div className="m-4 p-3 bg-rose-50 border border-rose-200 text-rose-900 text-xs rounded-xl flex items-center gap-2 font-sans">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{actionError}</span>
              </div>
            )}

            <div className="p-5 space-y-6 max-h-[85vh] overflow-y-auto">
              {/* 1. Candidate Demographics Summary */}
              <div className="bg-slate-50 border border-slate-200/60 rounded-xl p-4 space-y-3">
                <h4 className="text-[11px] font-sans font-bold text-slate-400 tracking-wider uppercase">
                  候选人基本资料摘要
                </h4>
                <div className="grid grid-cols-2 gap-3 text-xs font-sans">
                  <div className="flex items-center gap-2 text-slate-600">
                    <User className="w-4 h-4 text-slate-400 shrink-0" />
                    <span className="font-semibold text-slate-800">{selectedCandidate.name}</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-600">
                    <Phone className="w-4 h-4 text-slate-400 shrink-0" />
                    <span>{selectedCandidate.phone || "暂无电话"}</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-600 col-span-2">
                    <Mail className="w-4 h-4 text-slate-400 shrink-0" />
                    <span className="truncate">{selectedCandidate.email || "暂无邮箱"}</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-600">
                    <Briefcase className="w-4 h-4 text-slate-400 shrink-0" />
                    <span>{selectedCandidate.jobTitle}</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-600">
                    <Building2 className="w-4 h-4 text-slate-400 shrink-0" />
                    <span>{selectedCandidate.department}</span>
                  </div>
                </div>
              </div>

              {/* 2. Resume text snippet or full resume attachment display */}
              <div className="space-y-2">
                <h4 className="text-[11px] font-sans font-bold text-slate-400 tracking-wider uppercase flex items-center justify-between">
                  <span>简历附件内容</span>
                  <span className="text-[10px] text-slate-500 lowercase">
                    {selectedCandidate.resumeFileName || "未命名附件"}
                  </span>
                </h4>
                <div className="bg-slate-50 border border-slate-200/60 rounded-xl p-3 text-[11px] text-slate-600 font-sans leading-relaxed max-h-32 overflow-y-auto whitespace-pre-line bg-indigo-950/5 text-slate-700">
                  {selectedCandidate.resumeText || "该候选人暂无原始简历文本。"}
                </div>
              </div>

              {/* 3. Department Screening Status Update Trigger */}
              <div className="space-y-3 border-t border-slate-100 pt-4">
                <h4 className="text-[11px] font-sans font-bold text-slate-400 tracking-wider uppercase">
                  部门筛选状态更新 (HR/部门联动操作)
                </h4>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-600 font-sans shrink-0">更改状态:</span>
                  <div className="flex-1 flex flex-wrap gap-1.5">
                    {["screening", "interviewing", "rejected", "offer"].map((st) => {
                      const isActive = selectedCandidate.status === st;
                      const label = statusConfig[st as Candidate["status"]].label;
                      
                      return (
                        <button
                          key={st}
                          onClick={() => handleStatusChange(selectedCandidate.id, st as Candidate["status"])}
                          disabled={isUpdatingStatus}
                          className={`text-[10px] font-sans font-bold px-2.5 py-1.5 rounded-lg border transition-all ${
                            isActive
                              ? "bg-slate-900 text-white border-slate-900 shadow-sm"
                              : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                          }`}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* 4. Historical Interview Records */}
              <div className="space-y-3 border-t border-slate-100 pt-4">
                <h4 className="text-[11px] font-sans font-bold text-slate-400 tracking-wider uppercase flex items-center justify-between">
                  <span>历史面试流程记录</span>
                  <span className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded font-mono">
                    共 {selectedCandidate.interviews.length} 轮
                  </span>
                </h4>

                {selectedCandidate.interviews.length === 0 ? (
                  <div className="bg-slate-50 border border-dashed border-slate-200 rounded-xl p-4 text-center text-[11px] text-slate-400 font-sans">
                    暂无历史面试记录。可在下方表格录入第一轮面试结果。
                  </div>
                ) : (
                  <div className="space-y-3 relative before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-[1px] before:bg-slate-200">
                    {selectedCandidate.interviews.map((item, idx) => (
                      <div key={item.id} className="relative pl-8 text-xs font-sans">
                        {/* Node icon */}
                        <div className={`absolute left-1 top-0.5 w-6 h-6 rounded-full border flex items-center justify-center bg-white z-10 ${
                          item.result === "pass" 
                            ? "border-emerald-500 text-emerald-600" 
                            : item.result === "fail" 
                            ? "border-rose-500 text-rose-600" 
                            : "border-amber-500 text-amber-600"
                        }`}>
                          {item.result === "pass" ? (
                            <CheckCircle2 className="w-3.5 h-3.5" />
                          ) : item.result === "fail" ? (
                            <XCircle className="w-3.5 h-3.5" />
                          ) : (
                            <Clock className="w-3.5 h-3.5" />
                          )}
                        </div>

                        <div className="bg-slate-50/70 border border-slate-150 rounded-xl p-3 space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-800">第 {item.round} 轮：{item.interviewer}</span>
                            <span className="text-[10px] text-slate-400">{item.date}</span>
                          </div>
                          <p className="text-[11px] text-slate-600 leading-relaxed font-medium bg-white p-2 rounded-lg border border-slate-100">
                            {item.feedback || "未填写评语结论"}
                          </p>
                          <div className="flex items-center justify-between text-[10px]">
                            <span className="text-slate-400">结论状态:</span>
                            <span className={`font-bold uppercase ${
                              item.result === "pass" 
                                ? "text-emerald-600" 
                                : item.result === "fail" 
                                ? "text-rose-600" 
                                : "text-amber-600"
                            }`}>
                              {item.result === "pass" ? "面试通过" : item.result === "fail" ? "考核淘汰" : "评定中 / 待定"}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* 5. Append Interview Record Form */}
              <form onSubmit={handleAddInterview} className="space-y-3 border-t border-slate-100 pt-4">
                <h4 className="text-[11px] font-sans font-bold text-slate-400 tracking-wider uppercase flex items-center gap-1.5">
                  <Plus className="w-3.5 h-3.5 text-indigo-600" />
                  <span>追加新一轮面试记录</span>
                </h4>

                <div className="grid grid-cols-2 gap-3 text-xs font-sans">
                  {/* Round number */}
                  <div className="space-y-1">
                    <label className="text-slate-600 block font-semibold">面试轮次</label>
                    <input
                      type="number"
                      min={1}
                      value={formRound}
                      onChange={(e) => setFormRound(Number(e.target.value))}
                      className="w-full text-xs font-sans border border-slate-200 rounded-lg p-2 bg-slate-50"
                    />
                  </div>

                  {/* Interviewer */}
                  <div className="space-y-1">
                    <label className="text-slate-600 block font-semibold">面试官 <span className="text-rose-500">*</span></label>
                    <input
                      type="text"
                      placeholder="如：技术总监 - 王敏"
                      value={formInterviewer}
                      onChange={(e) => setFormInterviewer(e.target.value)}
                      className="w-full text-xs font-sans border border-slate-200 rounded-lg p-2 bg-slate-50"
                    />
                  </div>

                  {/* Result */}
                  <div className="space-y-1">
                    <label className="text-slate-600 block font-semibold">考核结论</label>
                    <select
                      value={formResult}
                      onChange={(e) => setFormResult(e.target.value as "pass" | "fail" | "pending")}
                      className="w-full text-xs font-sans border border-slate-200 rounded-lg p-2 bg-slate-50"
                    >
                      <option value="pending">安排中 / 待定 (pending)</option>
                      <option value="pass">面试通过 (pass)</option>
                      <option value="fail">面试不通过 / 淘汰 (fail)</option>
                    </select>
                  </div>

                  {/* Date */}
                  <div className="space-y-1">
                    <label className="text-slate-600 block font-semibold">面试时间</label>
                    <input
                      type="text"
                      placeholder="如：2026-07-19 10:00"
                      value={formDate}
                      onChange={(e) => setFormDate(e.target.value)}
                      className="w-full text-xs font-sans border border-slate-200 rounded-lg p-2 bg-slate-50"
                    />
                  </div>
                </div>

                {/* Feedback */}
                <div className="space-y-1 text-xs font-sans">
                  <label className="text-slate-600 block font-semibold">面试评语与决策要点</label>
                  <textarea
                    rows={2}
                    placeholder="请输入评测结论、提问侧重点、优缺点反馈等具体内容..."
                    value={formFeedback}
                    onChange={(e) => setFormFeedback(e.target.value)}
                    className="w-full text-xs font-sans border border-slate-200 rounded-lg p-2 bg-slate-50 resize-none"
                  />
                </div>

                {/* Submit button */}
                <button
                  type="submit"
                  disabled={isSubmittingInterview}
                  className="w-full flex items-center justify-center gap-2 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-sans font-bold rounded-lg transition-all"
                >
                  {isSubmittingInterview ? "正在记录中..." : "保存记录，同步流程状态"}
                </button>
              </form>

              {/* Extra Danger zone for demo */}
              <div className="border-t border-slate-100 pt-4 flex justify-between items-center">
                <span className="text-[10px] text-slate-400 font-sans">
                  档案建立于: {new Date(selectedCandidate.createdAt).toLocaleDateString()}
                </span>
                <button
                  onClick={() => handleDeleteCandidate(selectedCandidate.id)}
                  className="text-xs text-rose-500 hover:text-rose-700 flex items-center gap-1 font-sans font-semibold border border-rose-100 hover:border-rose-200 px-2 py-1 rounded bg-rose-50/50"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>淘汰并物理删除档案</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
