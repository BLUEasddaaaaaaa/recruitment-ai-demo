export interface InterviewRecord {
  id: string;
  round: number;
  interviewer: string;
  date: string;
  result: 'pass' | 'fail' | 'pending';
  feedback: string;
}

export interface ParsedResumeInfo {
  name: string;
  phone: string;
  email: string;
  jobTitle: string;
  department: string;
  education: string;
  experience: string;
  skills: string[];
  summary: string;
  confidence: {
    name: 'high' | 'low';
    phone: 'high' | 'low';
    email: 'high' | 'low';
    jobTitle: 'high' | 'low';
    department: 'high' | 'low';
    education: 'high' | 'low';
    experience: 'high' | 'low';
  };
}

export interface Candidate {
  id: string; // Application ID, e.g. "APP-2026-001"
  name: string;
  phone: string;
  email: string;
  hrName: string;
  jobTitle: string;
  department: string;
  status: 'screening' | 'interviewing' | 'rejected' | 'offer';
  currentRound: number;
  latestConclusion: string;
  resumeFileName?: string;
  resumeText?: string;
  parsedInfo?: ParsedResumeInfo;
  interviews: InterviewRecord[];
  createdAt: string;
}

export interface TodayTodo {
  id: string;
  title: string;
  candidateName: string;
  jobTitle: string;
  department: string;
  suggestedAction: string;
  priority: 'high' | 'medium' | 'low';
}

export interface AIInsights {
  summary: string;
  bulletPoints: string[];
  suggestedFocusJob: string;
  stuckCandidatesCount: number;
}

export interface AIReport {
  text: string;
}
