import React, { useState } from "react";
import { Upload, Sparkles, AlertTriangle, CheckCircle, FileText, ArrowRight, CornerDownLeft, RefreshCw, Loader2, HelpCircle } from "lucide-react";
import { ParsedResumeInfo, Candidate } from "../types";
import { DEMO_MODE, DEMO_PARSE_RESULT } from "../demoData";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

interface ResumeEntryProps {
  onCandidateAdded: (candidate: Candidate) => void;
}

// Preset resume templates for HR testing
const RESUME_TEMPLATES = [
  {
    title: "【BOSS直聘】陈静 - 数据分析师（推荐测试）",
    text: `求职意向：数据分析师
期望部门：数据部
姓名：陈静
性别：女
电话：13812349876
邮箱：chenjing@example.com
教育经历：北京大学 统计学硕士 (2020 - 2023)
专业技能：SQL, Python, R, Tableau, Excel, PowerBI
工作经验：
2023.07 - 至今 | 某知名互联网大厂 | 数据分析师
- 负责用户增长数据模型搭建，通过漏斗分析与 A/B 测试定位流失瓶颈，优化后次留率提高 5.2%。
- 独立编写日常分析脚本与自动化看板，减少团队 30% 重复取数工作量。
自我评价：具有深厚的数理统计基础和敏锐的商业嗅觉，善于挖掘核心指标并推动业务落地。`
  },
  {
    title: "【智联招聘】刘强 - 资深前端开发工程师",
    text: `姓名：刘强
手机：15987651234
邮箱：liuqiang@example.com
求职岗位：前端开发工程师
求职方向：研发部 / 前端技术部
学历：浙江大学 软件工程本科 (2017 - 2021)
技术栈：精通 React, TypeScript, Vue3, Webpack, Vite, 浏览器渲染优化, 微前端
工作经历：
2021.06 - 至今 | 杭州某电商独角兽 | 核心前端开发
- 负责公司核心B端SAAS系统的架构升级，由 Webpack 迁移至 Vite，构建速度提升 60%。
- 主导落地核心页面的极致性能优化（懒加载、首屏SSR、缓存策略），首屏 FCP 时间从 2.8s 降至 0.9s。
- 作为前端技术组长，指导过 3 名初中级前端，编写了团队内部工程化规范文档。`
  },
  {
    title: "【猎聘】张子涵 - 算法工程师",
    text: `求职意向：算法工程师
求职部门：AI研究部
姓名：张子涵
电话：13623456789
邮箱：zihan.zhang@example.com
教育：复旦大学 应用数学本科 (2018 - 2022)
专业技能：PyTorch, TensorFlow, Python, NLP, LLM Fine-tuning, RAG, CUDA
主要项目经历：
- 带领团队从 0 搭建了企业级知识库问答系统（RAG），检索召回率提升至 92%，业务问答准确率达 88%。
- 参与多模态大模型的微调与剪枝优化，使推理延迟降低 45%，成功在边缘设备完成部署部署。
- 熟悉常用的语言模型基础架构及预训练流程。`
  }
];

const BINARY_EXTENSIONS = new Set([".pdf", ".docx", ".doc"]);

export default function ResumeEntry({ onCandidateAdded }: ResumeEntryProps) {
  const [inputText, setInputText] = useState("");
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [fileName, setFileName] = useState("");
  const [parsedInfo, setParsedInfo] = useState<ParsedResumeInfo | null>(null);
  
  // Edited form state
  const [editedName, setEditedName] = useState("");
  const [editedPhone, setEditedPhone] = useState("");
  const [editedEmail, setEditedEmail] = useState("");
  const [editedJobTitle, setEditedJobTitle] = useState("");
  const [editedDepartment, setEditedDepartment] = useState("");
  const [editedEducation, setEditedEducation] = useState("");
  const [editedExperience, setEditedExperience] = useState("");
  const [editedSkills, setEditedSkills] = useState("");
  const [editedSummary, setEditedSummary] = useState("");
  const [editedHrName, setEditedHrName] = useState("");
  const [editedConfidence, setEditedConfidence] = useState<ParsedResumeInfo["confidence"] | null>(null);

  const [notification, setNotification] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  // Trigger quick template paste
  const handleApplyTemplate = (text: string, title: string) => {
    setInputText(text);
    setFileName(title.split(" ")[0] + "_简历.txt");
    setFileContent(null);
  };

  // Drag and drop handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const readUploadedFile = (file: File) => {
    setFileName(file.name);
    const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();

    if (BINARY_EXTENSIONS.has(extension)) {
      // DOCX/PDF are ZIP/PDF binary files: send as base64, do NOT read as UTF-8 text.
      const reader = new FileReader();
      reader.onload = (event) => {
        if (event.target?.result) {
          const dataUrl = event.target.result as string;
          const base64 = dataUrl.split(",")[1] || "";
          setFileContent(base64);
          setInputText(`【已上传文件：${file.name}】点击“开始 AI 智能提取”后，原文将显示在此处。`);
        }
      };
      reader.readAsDataURL(file);
    } else {
      // TXT / MD / pasted text
      const reader = new FileReader();
      reader.onload = (event) => {
        if (event.target?.result) {
          setInputText(event.target.result as string);
          setFileContent(null);
        }
      };
      reader.readAsText(file);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      readUploadedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      readUploadedFile(e.target.files[0]);
    }
  };

  // Core parsing triggers API
  const handleStartParse = async () => {
    if (!inputText.trim()) {
      showToast('error', "请输入简历内容或选择简历文件。");
      return;
    }

    setIsParsing(true);
    setNotification(null);
    try {
      if (DEMO_MODE) {
        const data = DEMO_PARSE_RESULT;
        setParsedInfo(data);
        setInputText(data.extractedText);
        setEditedName(data.name);
        setEditedPhone(data.phone);
        setEditedEmail(data.email);
        setEditedJobTitle(data.jobTitle);
        setEditedDepartment(data.department);
        setEditedEducation(data.education);
        setEditedExperience(data.experience);
        setEditedSkills(data.skills.join("、"));
        setEditedSummary(data.summary);
        setEditedConfidence(data.confidence);
        showToast('success', "演示模式：已加载示例解析结果，可直接确认入库。");
        return;
      }

      const response = await fetch(`${API_BASE}/api/resume/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: inputText,
          fileName: fileName || "手动粘贴简历.txt",
          fileContent: fileContent || undefined,
        })
      });

      if (!response.ok) {
        throw new Error("API parsing returned error code");
      }

      const data: ParsedResumeInfo & { extractedText?: string } = await response.json();
      setParsedInfo(data);
      if (data.extractedText) {
        setInputText(data.extractedText);
      }
      
      // Load into edit states
      setEditedName(data.name);
      setEditedPhone(data.phone);
      setEditedEmail(data.email);
      setEditedJobTitle(data.jobTitle);
      setEditedDepartment(data.department);
      setEditedEducation(data.education);
      setEditedExperience(data.experience);
      setEditedSkills(data.skills.join("、"));
      setEditedSummary(data.summary);
      setEditedConfidence(data.confidence);

      showToast('success', "AI 简历智能解析成功！字段已预填，请 HR 进行核实与微调。");
    } catch (e) {
      console.error(e);
      showToast('error', "AI 解析发生异常，请检查网络或重试。已加载智能预设，请 HR 手动补齐。");
    } finally {
      setIsParsing(false);
    }
  };

  const showToast = (type: 'success' | 'error', text: string) => {
    setNotification({ type, text });
    setTimeout(() => {
      setNotification(null);
    }, 6000);
  };

  // Submit and Save to DB
  const handleConfirmEntry = async () => {
    if (!editedName.trim()) {
      showToast('error', "候选人姓名不能为空！");
      return;
    }

    if (!editedHrName.trim()) {
      showToast('error', "负责 HR 姓名不能为空！这是必填项。");
      return;
    }

    try {
      if (DEMO_MODE) {
        const newCand: Candidate = {
          id: `APP-DEMO-${Date.now()}`,
          name: editedName,
          phone: editedPhone,
          email: editedEmail,
          hrName: editedHrName,
          jobTitle: editedJobTitle,
          department: editedDepartment,
          status: "screening",
          currentRound: 0,
          latestConclusion: "简历已入库（演示模式）",
          resumeFileName: fileName || "解析简历.txt",
          resumeText: inputText,
          interviews: [],
          createdAt: new Date().toLocaleString("zh-CN"),
          parsedInfo: {
            name: editedName,
            phone: editedPhone,
            email: editedEmail,
            jobTitle: editedJobTitle,
            department: editedDepartment,
            education: editedEducation,
            experience: editedExperience,
            skills: editedSkills.split(/[、,，\s]+/).filter(Boolean),
            summary: editedSummary,
            confidence: editedConfidence || {
              name: "high", phone: "high", email: "high", jobTitle: "high",
              department: "high", education: "high", experience: "high",
            },
          },
        };
        onCandidateAdded(newCand);
        setParsedInfo(null);
        setInputText("");
        setFileName("");
        setFileContent(null);
        setEditedHrName("");
        showToast('success', `入库成功（演示）！候选人 ${newCand.name} 已编入招聘台账。`);
        return;
      }

      const newCandPayload: Partial<Candidate> = {
        name: editedName,
        phone: editedPhone,
        email: editedEmail,
        hrName: editedHrName,
        jobTitle: editedJobTitle,
        department: editedDepartment,
        status: "screening",
        currentRound: 0,
        latestConclusion: "简历已入库，等待用人部门筛选",
        resumeFileName: fileName || "解析简历.txt",
        resumeText: inputText,
        interviews: [],
        parsedInfo: {
          name: editedName,
          phone: editedPhone,
          email: editedEmail,
          jobTitle: editedJobTitle,
          department: editedDepartment,
          education: editedEducation,
          experience: editedExperience,
          skills: editedSkills.split(/[、,，\s]+/).filter(Boolean),
          summary: editedSummary,
          confidence: editedConfidence || {
            name: "high",
            phone: "high",
            email: "high",
            jobTitle: "high",
            department: "high",
            education: "high",
            experience: "high"
          }
        }
      };

      const res = await fetch(`${API_BASE}/api/candidates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newCandPayload)
      });

      if (!res.ok) throw new Error("Failed to save candidate");

      const savedCandidate: Candidate = await res.json();
      onCandidateAdded(savedCandidate);
      
      // Reset State
      setParsedInfo(null);
      setInputText("");
      setFileName("");
      setEditedHrName("");
      showToast('success', `入库成功！候选人 ${savedCandidate.name} 已编入“候选人全流程”招聘台账。`);
    } catch (err) {
      console.error(err);
      showToast('error', "入库失败，请重试。");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Info */}
      <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-sans font-bold text-slate-900 tracking-tight flex items-center gap-2">
            简历智能解析与录入
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            支持一键解析各大平台简历文本，由 Python 招聘 AI 后端智能预填入库。
          </p>
        </div>
        <div className="flex items-center gap-2 self-start md:self-auto bg-amber-50 text-amber-800 px-4 py-2 rounded-xl border border-amber-200 text-xs font-medium font-sans animate-fade-in shadow-sm">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>核心提示：AI 智能预填后，请 HR 核实并确认入库！</span>
        </div>
      </div>

      {notification && (
        <div className={`p-4 rounded-xl border text-sm flex items-start gap-2.5 transition-all animate-slide-in shadow-sm ${
          notification.type === 'success' 
            ? 'bg-emerald-50 text-emerald-900 border-emerald-200' 
            : 'bg-rose-50 text-rose-900 border-rose-200'
        }`}>
          {notification.type === 'success' ? (
            <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          )}
          <div className="font-sans">{notification.text}</div>
        </div>
      )}

      {/* Main Grid: Paste resume on Left, AI Autofilled review on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Side: Upload / Raw Paste */}
        <div className="lg:col-span-5 space-y-5">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5 space-y-4">
            <h3 className="text-sm font-sans font-bold text-slate-800 tracking-tight flex items-center justify-between">
              <span>第一步：选择简历输入</span>
              <span className="text-xs font-normal text-slate-400">支持拖拽文件/纯文本粘贴</span>
            </h3>

            {/* Quick Presets */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-sans font-semibold text-slate-400 tracking-wider uppercase block">
                试用预设简历数据：
              </span>
              <div className="flex flex-col gap-1.5">
                {RESUME_TEMPLATES.map((tmpl, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleApplyTemplate(tmpl.text, tmpl.title)}
                    className="text-left text-xs bg-slate-50 hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 rounded-xl px-3 py-2 text-slate-600 hover:text-indigo-900 font-sans transition-all flex items-center justify-between group"
                  >
                    <span className="truncate pr-2 font-medium">{tmpl.title}</span>
                    <CornerDownLeft className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 text-indigo-500 transition-all shrink-0" />
                  </button>
                ))}
              </div>
            </div>

            {/* Drag & Drop Box */}
            <div
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-xl p-6 text-center transition-all cursor-pointer relative ${
                dragActive 
                  ? "border-indigo-500 bg-indigo-50/50" 
                  : "border-slate-200 bg-slate-50/50 hover:bg-slate-50 hover:border-slate-300"
              }`}
            >
              <input
                id="file-upload"
                type="file"
                className="hidden"
                accept=".txt,.pdf,.doc,.docx"
                onChange={handleFileChange}
              />
              <label htmlFor="file-upload" className="cursor-pointer space-y-2 block">
                <div className="mx-auto w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 group-hover:scale-105 transition-all">
                  <Upload className="w-5 h-5 text-slate-500" />
                </div>
                <div className="text-xs font-sans text-slate-600">
                  <span className="font-semibold text-indigo-600 hover:text-indigo-700">点击上传简历</span> 或拖拽到此处
                </div>
                <p className="text-[10px] text-slate-400 font-sans">
                  支持 PDF, TXT, Word 格式文件
                </p>
              </label>
            </div>

            {fileName && (
              <div className="bg-indigo-50/60 border border-indigo-100 rounded-xl px-3 py-2 flex items-center justify-between text-xs text-indigo-950 font-sans font-medium">
                <span className="flex items-center gap-1.5 truncate">
                  <FileText className="w-4 h-4 text-indigo-600" />
                  <span className="truncate">{fileName}</span>
                </span>
                <button 
                  onClick={() => { setFileName(""); setInputText(""); setFileContent(null); }}
                  className="text-slate-400 hover:text-rose-500 shrink-0 font-sans font-bold"
                >
                  清除
                </button>
              </div>
            )}

            {/* Text Area Input */}
            <div className="space-y-1">
              <label className="text-xs font-sans font-bold text-slate-600">
                简历源文本内容
              </label>
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="直接粘贴招聘软件的简历详情文本、BOSS消息，或拖入文件自动生成..."
                rows={10}
                className="w-full text-xs font-sans bg-slate-50 border border-slate-200 rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 font-medium resize-y"
              />
            </div>

            {/* Action Parse Button */}
            <button
              onClick={handleStartParse}
              disabled={isParsing || !inputText.trim()}
              className={`w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-xs font-sans font-bold transition-all shadow-md shadow-indigo-600/10 ${
                isParsing || !inputText.trim()
                  ? "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200"
                  : "bg-indigo-600 text-white hover:bg-indigo-700 hover:scale-[1.01]"
              }`}
            >
              {isParsing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>AI 后端正在解析中...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>开始 AI 智能提取</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Side: Parsed Form & HR Confirmation */}
        <div className="lg:col-span-7">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-sm font-sans font-bold text-slate-800 tracking-tight flex items-center gap-1.5">
                  <CheckCircle className="w-4 h-4 text-indigo-600" />
                  <span>第二步：AI 提取字段核实与入库</span>
                </h3>
                <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                  对低置信度的字段提供醒目橙色框提示，HR 手动修正后即可一键确认入库。
                </p>
              </div>
              <span className={`text-[10px] px-2.5 py-1 rounded-full font-sans font-bold shadow-sm ${
                parsedInfo 
                  ? "bg-emerald-100 text-emerald-800 border border-emerald-200" 
                  : "bg-slate-100 text-slate-400 border border-slate-200"
              }`}>
                {parsedInfo ? "解析就绪" : "等待输入"}
              </span>
            </div>

            {!parsedInfo ? (
              <div className="py-20 text-center space-y-3">
                <div className="inline-flex w-12 h-12 rounded-full bg-indigo-50 items-center justify-center text-indigo-500 text-sm">
                  <Sparkles className="w-6 h-6" />
                </div>
                <div className="max-w-sm mx-auto">
                  <p className="text-xs font-sans font-bold text-slate-700">暂无待入库解析结果</p>
                  <p className="text-xs text-slate-400 font-sans mt-1">
                    请在左侧选择上方“推荐测试”的预设简历模板，或直接复制您的候选人简历文本，点击“开始 AI 智能提取”。
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4 animate-fade-in">
                {/* 2-column core demographics */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Name */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-sans font-bold text-slate-600 flex items-center gap-1">
                        候选人姓名 <span className="text-rose-500">*</span>
                      </label>
                      {editedConfidence?.name === "low" && (
                        <span className="text-[9px] bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded border border-amber-200 flex items-center gap-0.5">
                          <AlertTriangle className="w-2.5 h-2.5 text-amber-600" /> 低置信
                        </span>
                      )}
                    </div>
                    <input
                      type="text"
                      value={editedName}
                      onChange={(e) => setEditedName(e.target.value)}
                      className={`w-full text-xs font-sans border rounded-xl p-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 font-medium ${
                        editedConfidence?.name === "low"
                          ? "border-amber-400 bg-amber-50/20 focus:border-amber-500"
                          : "border-slate-200 focus:border-indigo-500"
                      }`}
                    />
                  </div>

                  {/* Phone */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-sans font-bold text-slate-600 flex items-center gap-1">
                        联系电话
                      </label>
                      {editedConfidence?.phone === "low" && (
                        <span className="text-[9px] bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded border border-amber-200 flex items-center gap-0.5">
                          <AlertTriangle className="w-2.5 h-2.5 text-amber-600" /> 低置信
                        </span>
                      )}
                    </div>
                    <input
                      type="text"
                      value={editedPhone}
                      onChange={(e) => setEditedPhone(e.target.value)}
                      className={`w-full text-xs font-sans border rounded-xl p-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 font-medium ${
                        editedConfidence?.phone === "low"
                          ? "border-amber-400 bg-amber-50/20 focus:border-amber-500"
                          : "border-slate-200 focus:border-indigo-500"
                      }`}
                    />
                  </div>

                  {/* Email */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-sans font-bold text-slate-600 flex items-center gap-1">
                        电子邮箱
                      </label>
                      {editedConfidence?.email === "low" && (
                        <span className="text-[9px] bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded border border-amber-200 flex items-center gap-0.5">
                          <AlertTriangle className="w-2.5 h-2.5 text-amber-600" /> 低置信
                        </span>
                      )}
                    </div>
                    <input
                      type="email"
                      value={editedEmail}
                      onChange={(e) => setEditedEmail(e.target.value)}
                      className={`w-full text-xs font-sans border rounded-xl p-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 font-medium ${
                        editedConfidence?.email === "low"
                          ? "border-amber-400 bg-amber-50/20 focus:border-amber-500"
                          : "border-slate-200 focus:border-indigo-500"
                      }`}
                    />
                  </div>

                  {/* Job Title */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-sans font-bold text-slate-600 flex items-center gap-1">
                        投递岗位
                      </label>
                      {editedConfidence?.jobTitle === "low" && (
                        <span className="text-[9px] bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded border border-amber-200 flex items-center gap-0.5">
                          <AlertTriangle className="w-2.5 h-2.5 text-amber-600" /> 低置信
                        </span>
                      )}
                    </div>
                    <input
                      type="text"
                      value={editedJobTitle}
                      onChange={(e) => setEditedJobTitle(e.target.value)}
                      className={`w-full text-xs font-sans border rounded-xl p-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 font-medium ${
                        editedConfidence?.jobTitle === "low"
                          ? "border-amber-400 bg-amber-50/20 focus:border-amber-500"
                          : "border-slate-200 focus:border-indigo-500"
                      }`}
                    />
                  </div>

                  {/* Department */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-sans font-bold text-slate-600 flex items-center gap-1">
                        求职部门
                      </label>
                      {editedConfidence?.department === "low" && (
                        <span className="text-[9px] bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded border border-amber-200 flex items-center gap-0.5">
                          <AlertTriangle className="w-2.5 h-2.5 text-amber-600" /> 推理低置信度
                        </span>
                      )}
                    </div>
                    <select
                      value={editedDepartment}
                      onChange={(e) => setEditedDepartment(e.target.value)}
                      className={`w-full text-xs font-sans border rounded-xl p-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 font-medium ${
                        editedConfidence?.department === "low"
                          ? "border-amber-400 bg-amber-50/20 focus:border-amber-500"
                          : "border-slate-200 focus:border-indigo-500"
                      }`}
                    >
                      <option value="研发部">研发部</option>
                      <option value="数据部">数据部</option>
                      <option value="AI研究部">AI研究部</option>
                      <option value="产品部">产品部</option>
                      <option value="运营部">运营部</option>
                      <option value="待定">待定/需核实</option>
                    </select>
                  </div>

                  {/* Education */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-sans font-bold text-slate-600 flex items-center gap-1">
                        学历院校
                      </label>
                      {editedConfidence?.education === "low" && (
                        <span className="text-[9px] bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded border border-amber-200 flex items-center gap-0.5">
                          <AlertTriangle className="w-2.5 h-2.5 text-amber-600" /> 低置信
                        </span>
                      )}
                    </div>
                    <input
                      type="text"
                      value={editedEducation}
                      onChange={(e) => setEditedEducation(e.target.value)}
                      className={`w-full text-xs font-sans border rounded-xl p-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 font-medium ${
                        editedConfidence?.education === "low"
                          ? "border-amber-400 bg-amber-50/20 focus:border-amber-500"
                          : "border-slate-200 focus:border-indigo-500"
                      }`}
                    />
                  </div>

                  {/* Responsible HR Name */}
                  <div className="space-y-1">
                    <label className="text-xs font-sans font-bold text-slate-600 flex items-center gap-1">
                      负责 HR 姓名 <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="请输入负责该候选人的 HR 姓名"
                      value={editedHrName}
                      onChange={(e) => setEditedHrName(e.target.value)}
                      className="w-full text-xs font-sans border border-slate-200 rounded-xl p-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 font-medium focus:border-indigo-500"
                    />
                  </div>
                </div>

                {/* Experience */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-sans font-bold text-slate-600">
                      核心工作经历摘要
                    </label>
                    {editedConfidence?.experience === "low" && (
                      <span className="text-[9px] bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded border border-amber-200 flex items-center gap-0.5">
                        <AlertTriangle className="w-2.5 h-2.5 text-amber-600" /> 低置信
                      </span>
                    )}
                  </div>
                  <textarea
                    value={editedExperience}
                    onChange={(e) => setEditedExperience(e.target.value)}
                    rows={3}
                    className={`w-full text-xs font-sans border rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 font-medium resize-none ${
                      editedConfidence?.experience === "low"
                        ? "border-amber-400 bg-amber-50/20 focus:border-amber-500"
                        : "border-slate-200 focus:border-indigo-500"
                    }`}
                  />
                </div>

                {/* Skills */}
                <div className="space-y-1">
                  <label className="text-xs font-sans font-bold text-slate-600">
                    专业技能（顿号或逗号分隔）
                  </label>
                  <input
                    type="text"
                    value={editedSkills}
                    onChange={(e) => setEditedSkills(e.target.value)}
                    className="w-full text-xs font-sans border border-slate-200 rounded-xl p-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 font-medium focus:border-indigo-500"
                  />
                </div>

                {/* Summary / Evaluation */}
                <div className="space-y-1">
                  <label className="text-xs font-sans font-bold text-slate-600">
                    AI 简历综合评价洞察
                  </label>
                  <textarea
                    value={editedSummary}
                    onChange={(e) => setEditedSummary(e.target.value)}
                    rows={3}
                    className="w-full text-xs font-sans border border-slate-200 rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 font-medium resize-none focus:border-indigo-500"
                  />
                </div>

                {/* low confidence alert explanation banner */}
                {Object.values(editedConfidence || {}).includes("low") && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                    <p className="text-[11px] text-amber-900 leading-relaxed font-sans">
                      <strong>AI 提示：</strong>橙色标记的字段为模型根据内容关联推理（如由岗位类型反推投递部门），可能存在细微偏差，请 HR 核对后修改。
                    </p>
                  </div>
                )}

                {/* Confirm and enter database button */}
                <button
                  type="button"
                  onClick={handleConfirmEntry}
                  className="w-full mt-4 flex items-center justify-center gap-2 py-3.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-sans font-bold transition-all shadow-md shadow-emerald-600/15"
                >
                  <CheckCircle className="w-4 h-4" />
                  <span>确认无误，正式确认入库</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
