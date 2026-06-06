export type ActionItemStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED";
export type MeetingStatus = "CREATED" | "ANALYZING" | "ANALYZED" | "FAILED";
export type InsightType = "SUMMARY" | "DECISION" | "FOLLOW_UP";

export interface ApiSuccess<T> {
  traceId: string;
  success: true;
  data: T;
}
export interface ApiError {
  traceId: string;
  success: false;
  error: { code: string; message: string; details?: unknown };
}

export interface Citation {
  timestamp: string;
  segmentIndex?: number | null;
  verified?: boolean;
}

export interface Insight {
  id: string;
  type: InsightType;
  text: string;
  groundingScore: number;
  citations: Citation[];
}

export interface ActionItem {
  id: string;
  meetingId: string;
  task: string;
  assignee: string | null;
  status: ActionItemStatus;
  dueDate: string | null;
  groundingScore: number;
  source: string;
  citations: Citation[];
  createdAt: string;
  updatedAt: string;
}

export interface TranscriptSegment {
  id: string;
  ordinal: number;
  timestamp: string;
  speaker: string;
  text: string;
}

export interface MeetingSummary {
  id: string;
  title: string;
  meetingDate: string;
  participants: string[];
  status: MeetingStatus;
  segmentCount: number;
  actionItemCount: number;
  createdAt: string;
}

export interface MeetingDetail extends MeetingSummary {
  transcript: TranscriptSegment[];
  insights: Insight[];
  actionItems: ActionItem[];
}

export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}
export interface Paginated<T> {
  items: T[];
  meta: PaginationMeta;
}

export interface AnalysisResult {
  meetingId: string;
  summary: Insight[];
  decisions: Insight[];
  followUps: Insight[];
  actionItems: ActionItem[];
  groundingScore: number;
  droppedCount: number;
  provider?: string;
}

export interface Analytics {
  totals: {
    meetings: number;
    actionItems: number;
    overdue: number;
    completed: number;
    avgGroundingScore: number;
  };
  statusDistribution: Record<string, number>;
  byAssignee: { assignee: string; open: number; overdue: number }[];
  recentActivity: { date: string; created: number }[];
}

export interface SearchHit {
  segmentId: string;
  meetingId: string;
  meetingTitle: string;
  speaker: string;
  timestamp: string;
  text: string;
  score: number;
  mode: "semantic" | "keyword";
}

export interface AuthUser {
  id: string;
  email: string;
  name: string;
}
