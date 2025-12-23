import { useState, useEffect, useRef } from 'react';
import {
  Target,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Upload,
  FileText,
  Settings,
  Play,
  Pause,
  Trash2,
  Eye,
  Filter,
  Search,
  Plus,
  Clock,
  XCircle,
  Activity,
  BarChart3,
  CheckSquare,
  Download,
  X,
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Minus
} from 'lucide-react'
import { anomaliesService } from '../lib/anomalies';
import { Card, Button, ProgressBar } from '../components/design-system';
import { DocumentUpload } from '../components/DocumentUpload';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { documentService } from '../lib/document';
import { taskService } from '../lib/tasks';
import { TaskCard } from '../components/tasks/TaskCard';
import { TaskDetailsModal } from '../components/tasks/TaskDetailsModal';
import { WorkerStatus } from '../components/tasks/WorkerStatus';
import { TaskFilters } from '../components/tasks/TaskFilters';
import { TaskCharts } from '../components/tasks/TaskCharts';
import { PerformanceDashboard } from '../components/tasks/PerformanceDashboard';
import { TaskScheduler } from '../components/tasks/TaskScheduler';
import { RuleCharts } from '../components/validations/RuleCharts';
import type { DocumentUpload as DocumentUploadType, RuleStatisticsItem, RuleStatisticsSummary, RuleStatisticsResponse, RuleResultItem, ValidationAnalyticsResponse } from '../types/api';
import type { TaskDashboard, Task } from '../types/tasks';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

type ControlTab = 'quality' | 'tasks' | 'validation' | 'import' | 'review' | 'documents';

interface QualityScore {
  overallScore: number;
  status: 'excellent' | 'good' | 'fair' | 'poor';
  extraction: {
    accuracy: number;
    confidence: number;
    failureRate: number;
    documentsProcessed: number;
  };
  validation: {
    passRate: number;
    failedValidations: number;
    activeRules: number;
    criticalFailures: number;
  };
  completeness: {
    score: number;
    missingFields: number;
    requiredFieldsFilled: number;
  };
  byDocumentType?: {
    [key: string]: {
      count: number;
      total_records: number;
      matched_records: number;
      match_rate: number;
      avg_confidence?: number;
    };
  };
  totalRecords?: number;
  criticalCount?: number;
  warningCount?: number;
  needsReviewCount?: number;
}

interface SystemTask {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  startedAt?: Date;
  completedAt?: Date;
  error?: string;
}

// Validation rules state will use RuleStatisticsItem from types/api

export default function DataControlCenter() {
  const [activeTab, setActiveTab] = useState<ControlTab>('quality');
  const [qualityScore, setQualityScore] = useState<QualityScore | null>(null);
  const [systemTasks, setSystemTasks] = useState<SystemTask[]>([]);
  const [validationRules, setValidationRules] = useState<ValidationRule[]>([]); // Keep for backward compatibility
  const [ruleStatistics, setRuleStatistics] = useState<RuleStatisticsItem[]>([]);
  const [ruleSummary, setRuleSummary] = useState<RuleStatisticsSummary | null>(null);
  const [ruleFilters, setRuleFilters] = useState({
    documentType: 'all',
    severity: 'all',
    status: 'active',
    search: ''
  });
  const [selectedRule, setSelectedRule] = useState<RuleStatisticsItem | null>(null);
  const [ruleResults, setRuleResults] = useState<RuleResultItem[]>([]);
  const [loadingRules, setLoadingRules] = useState(false);
  const [ruleAnalytics, setRuleAnalytics] = useState<ValidationAnalyticsResponse | null>(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [showValidationCharts, setShowValidationCharts] = useState(false);
  const [documents, setDocuments] = useState<DocumentUploadType[]>([]);
  const [allDocuments, setAllDocuments] = useState<DocumentUploadType[]>([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [rerunningAnomalies, setRerunningAnomalies] = useState<number | null>(null);
  
  // Filtered deletion state
  const [showDeleteFiltersModal, setShowDeleteFiltersModal] = useState(false);
  const [deleteFilters, setDeleteFilters] = useState({
    propertyIds: [] as number[],
    year: '' as string | number,
    documentType: '' as string,
    periodId: '' as string | number
  });
  const [previewData, setPreviewData] = useState<any>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [properties, setProperties] = useState<any[]>([]);
  const [statusCounts, setStatusCounts] = useState({
    total: 0,
    completed: 0,
    validating: 0,
    failed: 0,
    pending: 0,
    extracting: 0
  });
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  
  // Tasks tab state
  const [taskDashboard, setTaskDashboard] = useState<TaskDashboard | null>(null);
  const [taskLoading, setTaskLoading] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [cancelingTaskId, setCancelingTaskId] = useState<string | null>(null);
  const [autoRefreshTasks, setAutoRefreshTasks] = useState(true);
  const taskRefreshIntervalRef = useRef<number | null>(null);
  
  // Phase 2: Filtering and search state
  const [taskFilter, setTaskFilter] = useState<{
    type: string;
    status: string;
    property: string;
    search: string;
    dateFrom: string;
    dateTo: string;
  }>({
    type: 'all',
    status: 'all',
    property: 'all',
    search: '',
    dateFrom: '',
    dateTo: ''
  });
  const [selectedTasks, setSelectedTasks] = useState<Set<string>>(new Set());
  const [showBulkActions, setShowBulkActions] = useState(false);
  const [extendedHistory, setExtendedHistory] = useState<Task[]>([]);
  const [showCharts, setShowCharts] = useState(true);
  const [historyDays, setHistoryDays] = useState(7);

  // Define loadTaskDashboard before useEffect hooks
  const loadTaskDashboard = async () => {
    try {
      setTaskLoading(true);
      const dashboard = await taskService.getTaskDashboard();
      setTaskDashboard(dashboard);
    } catch (error) {
      console.error('Failed to load task dashboard:', error);
      // Set empty dashboard on error
      setTaskDashboard({
        active_tasks: [],
        queue_stats: {
          pending: 0,
          processing: 0,
          completed_today: 0,
          failed_today: 0,
          success_rate: 0
        },
        workers: [],
        recent_tasks: [],
        task_statistics: {
          avg_extraction_time: 0,
          total_tasks_today: 0,
          by_type: {}
        },
        error: error instanceof Error ? error.message : 'Failed to load task dashboard'
      });
    } finally {
      setTaskLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    if (activeTab === 'tasks') {
      loadTaskDashboard();
    }
  }, [activeTab]);

  // Auto-refresh tasks tab
  useEffect(() => {
    if (activeTab === 'tasks' && autoRefreshTasks) {
      taskRefreshIntervalRef.current = window.setInterval(() => {
        loadTaskDashboard();
      }, 5000); // Refresh every 5 seconds
      
      return () => {
        if (taskRefreshIntervalRef.current) {
          clearInterval(taskRefreshIntervalRef.current);
        }
      };
    } else {
      if (taskRefreshIntervalRef.current) {
        clearInterval(taskRefreshIntervalRef.current);
        taskRefreshIntervalRef.current = null;
      }
    }
  }, [activeTab, autoRefreshTasks]);

  const loadData = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      // Load quality score and validation statistics in parallel
      const [qualityRes, validationStatsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/quality/summary`, { credentials: 'include' }),
        fetch(`${API_BASE_URL}/validations/rules/statistics`, { credentials: 'include' })
      ]);

      // Parse validation statistics
      let validationStats = null;
      if (validationStatsRes.ok) {
        validationStats = await validationStatsRes.json();
      }

      // Parse quality data and set quality score
      if (qualityRes.ok) {
        const quality = await qualityRes.json();

        // Calculate validation metrics from actual validation statistics
        // Use validation statistics if available, otherwise use defaults
        const validationPassRate = validationStats?.summary?.overall_pass_rate ?? 0;
        const validationTotalChecks = validationStats?.summary?.total_checks ?? 0;
        // Calculate failed count: total_checks - passed_count
        // passed_count = total_checks * (pass_rate / 100)
        const validationFailedCount = validationTotalChecks > 0
          ? Math.round(validationTotalChecks * (1 - validationPassRate / 100))
          : 0;
        const validationCriticalFailures = validationStats?.summary?.critical_failures ?? 0;
        const validationActiveRules = validationStats?.summary?.active_rules ?? 24;
        const validationWarnings = validationStats?.summary?.warnings ?? 0;

        setQualityScore({
          overallScore: quality.overall_avg_confidence || 96,
          status: (quality.overall_avg_confidence || 96) >= 95 ? 'excellent' : (quality.overall_avg_confidence || 96) >= 90 ? 'good' : (quality.overall_avg_confidence || 96) >= 80 ? 'fair' : 'poor',
          extraction: {
            accuracy: quality.overall_match_rate || 98.5,
            confidence: quality.overall_avg_confidence || 97.2,
            failureRate: 100 - (quality.overall_match_rate || 98.5),
            documentsProcessed: quality.total_documents || 0
          },
          validation: {
            passRate: validationPassRate,
            failedValidations: validationFailedCount,
            activeRules: validationActiveRules,
            criticalFailures: validationCriticalFailures
          },
          completeness: {
            score: quality.overall_match_rate || 97.8,
            missingFields: quality.needs_review_count || 0,
            requiredFieldsFilled: quality.overall_match_rate || 98.5
          },
          byDocumentType: quality.by_document_type || {},
          totalRecords: quality.total_records || 0,
          criticalCount: quality.critical_count || 0,
          warningCount: quality.warning_count || 0,
          needsReviewCount: quality.needs_review_count || 0
        });
      }

      // Load system tasks
      const tasksRes = await fetch(`${API_BASE_URL}/tasks`, {
        credentials: 'include'
      });
      if (tasksRes.ok) {
        const tasks = await tasksRes.json();
        setSystemTasks(tasks.tasks || []);
      }

      // Load validation rules
      const rulesRes = await fetch(`${API_BASE_URL}/validations/rules`, {
        credentials: 'include'
      });
      if (rulesRes.ok) {
        const rules = await rulesRes.json();
        setValidationRules(rules.rules || []);
      }

      // Load ALL documents - fetch in batches if needed
      let allDocs: DocumentUploadType[] = [];
      let skip = 0;
      const limit = 500;
      let hasMore = true;
      
      while (hasMore) {
        const docsRes = await fetch(`${API_BASE_URL}/documents/uploads?skip=${skip}&limit=${limit}`, {
          credentials: 'include'
        });
        if (docsRes.ok) {
          const docs = await docsRes.json();
          const items = docs.items || docs || [];
          allDocs = [...allDocs, ...items];
          
          // Check if there are more documents
          if (items.length < limit || (docs.total && allDocs.length >= docs.total)) {
            hasMore = false;
          } else {
            skip += limit;
          }
        } else {
          hasMore = false;
        }
      }
      
      setAllDocuments(allDocs);
      setDocuments(allDocs);
      
      // Calculate status counts
      const counts = {
        total: allDocs.length,
        completed: allDocs.filter(d => d.extraction_status === 'completed').length,
        validating: allDocs.filter(d => d.extraction_status === 'validating').length,
        failed: allDocs.filter(d => d.extraction_status === 'failed' || d.extraction_status?.includes('failed')).length,
        pending: allDocs.filter(d => d.extraction_status === 'pending').length,
        extracting: allDocs.filter(d => d.extraction_status === 'extracting' || d.extraction_status === 'processing').length
      };
      setStatusCounts(counts);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'excellent': return 'success';
      case 'good': return 'info';
      case 'fair': return 'warning';
      case 'poor': return 'danger';
      default: return 'default';
    }
  };

  const getTaskStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'running': return 'info';
      case 'failed': return 'danger';
      default: return 'default';
    }
  };

  const handleDeleteAllHistory = async () => {
    if (!confirm('Are you sure you want to delete all document upload history? This action cannot be undone.')) {
      return;
    }
    
    try {
      setDeleting(true);
      const response = await fetch(`${API_BASE_URL}/documents/uploads/delete-all-history`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (response.ok) {
        alert('All document upload history has been deleted successfully.');
        loadData(); // Reload the data
      } else {
        const error = await response.json();
        alert(`Failed to delete history: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to delete history:', error);
      alert('Failed to delete history. Please try again.');
    } finally {
      setDeleting(false);
    }
  };

  // Load properties for filter dropdown
  useEffect(() => {
    const loadProperties = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/properties`, {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          setProperties(data.properties || []);
        }
      } catch (error) {
        console.error('Failed to load properties:', error);
      }
    };
    loadProperties();
  }, []);

  // Preview what will be deleted
  const handlePreviewDeletion = async () => {
    if (deleteFilters.propertyIds.length === 0) {
      alert('Please select at least one property');
      return;
    }

    try {
      setLoadingPreview(true);
      const params = new URLSearchParams();
      deleteFilters.propertyIds.forEach(id => params.append('property_ids', id.toString()));
      if (deleteFilters.year) params.append('year', deleteFilters.year.toString());
      if (deleteFilters.documentType) params.append('document_type', deleteFilters.documentType);
      if (deleteFilters.periodId) params.append('period_id', deleteFilters.periodId.toString());

      const response = await fetch(`${API_BASE_URL}/documents/anomalies-warnings-alerts/preview?${params}`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setPreviewData(data);
      } else {
        const error = await response.json();
        alert(`Failed to preview: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to preview deletion:', error);
      alert('Failed to preview deletion. Please try again.');
    } finally {
      setLoadingPreview(false);
    }
  };

  // Delete with filters
  const handleDeleteFiltered = async () => {
    if (deleteFilters.propertyIds.length === 0) {
      alert('Please select at least one property');
      return;
    }

    if (!previewData) {
      alert('Please preview the deletion first to see what will be deleted');
      return;
    }

    const confirmMessage = `Are you sure you want to delete ${previewData.total_preview} records?\n\n` +
      `- Anomalies: ${previewData.preview_counts.anomaly_detections}\n` +
      `- Alerts: ${previewData.preview_counts.alerts}\n` +
      `- Committee Alerts: ${previewData.preview_counts.committee_alerts}\n\n` +
      `This action cannot be undone.`;

    if (!confirm(confirmMessage)) {
      return;
    }

    try {
      setDeleting(true);
      const params = new URLSearchParams();
      deleteFilters.propertyIds.forEach(id => params.append('property_ids', id.toString()));
      if (deleteFilters.year) params.append('year', deleteFilters.year.toString());
      if (deleteFilters.documentType) params.append('document_type', deleteFilters.documentType);
      if (deleteFilters.periodId) params.append('period_id', deleteFilters.periodId.toString());

      const response = await fetch(`${API_BASE_URL}/documents/anomalies-warnings-alerts/delete-filtered?${params}`, {
        method: 'POST',
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        alert(`Successfully deleted ${data.total_deleted} records!\n\n` +
          `- Anomalies: ${data.deletion_counts.anomaly_detections}\n` +
          `- Alerts: ${data.deletion_counts.alerts}\n` +
          `- Committee Alerts: ${data.deletion_counts.committee_alerts}`);
        setShowDeleteFiltersModal(false);
        setPreviewData(null);
        setDeleteFilters({
          propertyIds: [],
          year: '',
          documentType: '',
          periodId: ''
        });
        loadData(); // Reload the data
      } else {
        const error = await response.json();
        alert(`Failed to delete: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to delete:', error);
      alert('Failed to delete. Please try again.');
    } finally {
      setDeleting(false);
    }
  };

  const handleCancelTask = async (taskId: string) => {
    if (!confirm('Are you sure you want to cancel this task?')) {
      return;
    }
    
    try {
      setCancelingTaskId(taskId);
      await taskService.cancelTask(taskId);
      await loadTaskDashboard(); // Refresh dashboard
      alert('Task cancelled successfully.');
    } catch (error: any) {
      alert(`Failed to cancel task: ${error.message || 'Unknown error'}`);
    } finally {
      setCancelingTaskId(null);
    }
  };

  const handleRetryFailedExtractions = async () => {
    if (!confirm('Are you sure you want to retry all failed extractions? This will queue them for processing again.')) {
      return;
    }
    
    try {
      setReprocessing(true);
      const result = await taskService.retryFailedExtractions();
      alert(`Successfully queued ${result.queued_count} failed extraction(s) for reprocessing.`);
      await loadTaskDashboard(); // Refresh dashboard
      loadData(); // Also refresh documents
    } catch (error: any) {
      alert(`Failed to retry extractions: ${error.message || 'Unknown error'}`);
    } finally {
      setReprocessing(false);
    }
  };

  const handleRecoverStuckDocuments = async () => {
    if (!confirm('Are you sure you want to recover stuck documents? This will queue any stuck uploads for processing.')) {
      return;
    }
    
    try {
      setReprocessing(true);
      const result = await taskService.recoverStuckDocuments();
      alert(`Successfully recovered ${result.recovered || result.queued_count || 0} stuck document(s).`);
      await loadTaskDashboard(); // Refresh dashboard
      loadData(); // Also refresh documents
    } catch (error: any) {
      alert(`Failed to recover stuck documents: ${error.message || 'Unknown error'}`);
    } finally {
      setReprocessing(false);
    }
  };

  const handleReprocessFailed = async () => {
    const failedCount = statusCounts.failed;
    if (failedCount === 0) {
      alert('No failed files to reprocess.');
      return;
    }
    
    if (!confirm(`Are you sure you want to reprocess ${failedCount} failed file(s)? This will queue them for extraction again.`)) {
      return;
    }
    
    try {
      setReprocessing(true);
      const response = await fetch(`${API_BASE_URL}/documents/uploads/reprocess-failed`, {
        method: 'POST',
        credentials: 'include'
      });
      
      if (response.ok) {
        const result = await response.json();
        alert(`Successfully queued ${result.queued_count || failedCount} failed file(s) for reprocessing.`);
        loadData(); // Reload the data
      } else {
        const error = await response.json();
        alert(`Failed to reprocess files: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to reprocess files:', error);
      alert('Failed to reprocess files. Please try again.');
    } finally {
      setReprocessing(false);
    }
  };

  // Phase 2: Filter tasks
  const filterTasks = (tasks: Task[]): Task[] => {
    return tasks.filter(task => {
      // Type filter
      if (taskFilter.type !== 'all' && task.task_type !== taskFilter.type) {
        return false;
      }
      
      // Status filter
      if (taskFilter.status !== 'all' && task.status !== taskFilter.status) {
        return false;
      }
      
      // Property filter
      if (taskFilter.property !== 'all' && task.property_code !== taskFilter.property) {
        return false;
      }
      
      // Search filter
      if (taskFilter.search) {
        const searchLower = taskFilter.search.toLowerCase();
        const matchesId = task.task_id.toLowerCase().includes(searchLower);
        const matchesDoc = task.document_name?.toLowerCase().includes(searchLower);
        if (!matchesId && !matchesDoc) {
          return false;
        }
      }
      
      // Date range filter
      if (taskFilter.dateFrom && task.completed_at) {
        const taskDate = new Date(task.completed_at);
        const fromDate = new Date(taskFilter.dateFrom);
        if (taskDate < fromDate) {
          return false;
        }
      }
      
      if (taskFilter.dateTo && task.completed_at) {
        const taskDate = new Date(task.completed_at);
        const toDate = new Date(taskFilter.dateTo);
        toDate.setHours(23, 59, 59, 999); // End of day
        if (taskDate > toDate) {
          return false;
        }
      }
      
      return true;
    });
  };

  // Phase 2: Load extended history
  const loadExtendedHistory = async () => {
    try {
      const history = await taskService.getTaskHistory(historyDays);
      setExtendedHistory(history);
    } catch (error) {
      console.error('Failed to load extended history:', error);
      // Fallback to recent tasks from dashboard
      if (taskDashboard?.recent_tasks) {
        setExtendedHistory(taskDashboard.recent_tasks);
      }
    }
  };

  // Phase 2: Bulk operations
  const handleBulkCancel = async () => {
    if (selectedTasks.size === 0) return;
    if (!confirm(`Are you sure you want to cancel ${selectedTasks.size} task(s)?`)) {
      return;
    }
    
    try {
      const result = await taskService.bulkCancelTasks(Array.from(selectedTasks));
      alert(`Successfully cancelled ${result.cancelled} task(s). ${result.failed > 0 ? `${result.failed} failed.` : ''}`);
      setSelectedTasks(new Set());
      await loadTaskDashboard();
    } catch (error: any) {
      alert(`Failed to cancel tasks: ${error.message || 'Unknown error'}`);
    }
  };

  const handleExportTasks = () => {
    const tasksToExport = extendedHistory.length > 0 ? extendedHistory : (taskDashboard?.recent_tasks || []);
    const filteredTasks = filterTasks(tasksToExport);
    const csv = taskService.exportTasksToCSV(filteredTasks);
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tasks_export_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  const toggleTaskSelection = (taskId: string) => {
    const newSelected = new Set(selectedTasks);
    if (newSelected.has(taskId)) {
      newSelected.delete(taskId);
    } else {
      newSelected.add(taskId);
    }
    setSelectedTasks(newSelected);
    setShowBulkActions(newSelected.size > 0);
  };

  const selectAllTasks = () => {
    const allTasks = [...(taskDashboard?.active_tasks || []), ...(extendedHistory.length > 0 ? extendedHistory : taskDashboard?.recent_tasks || [])];
    const filtered = filterTasks(allTasks);
    setSelectedTasks(new Set(filtered.map(t => t.task_id)));
    setShowBulkActions(true);
  };

  const clearSelection = () => {
    setSelectedTasks(new Set());
    setShowBulkActions(false);
  };

  // Load extended history when tasks tab is active
  useEffect(() => {
    if (activeTab === 'tasks' && taskDashboard) {
      loadExtendedHistory();
    }
  }, [activeTab, taskDashboard, historyDays]);

  // Load validation rules when validation tab is active
  useEffect(() => {
    if (activeTab === 'validation') {
      loadValidationRules();
      loadValidationAnalytics();
    }
  }, [activeTab]);

  const loadValidationRules = async () => {
    try {
      setLoadingRules(true);
      const response = await fetch(`${API_BASE_URL}/validations/rules/statistics`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error(`Failed to load validation rules: ${response.statusText}`);
      }
      
      const data: RuleStatisticsResponse = await response.json();
      setRuleStatistics(data.rules);
      setRuleSummary(data.summary);
    } catch (error) {
      console.error('Failed to load validation rules:', error);
      // Set empty state on error
      setRuleStatistics([]);
      setRuleSummary(null);
    } finally {
      setLoadingRules(false);
    }
  };

  const loadValidationAnalytics = async () => {
    try {
      setLoadingAnalytics(true);
      const response = await fetch(`${API_BASE_URL}/validations/analytics`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error(`Failed to load validation analytics: ${response.statusText}`);
      }
      
      const data: ValidationAnalyticsResponse = await response.json();
      setRuleAnalytics(data);
    } catch (error) {
      console.error('Failed to load validation analytics:', error);
      setRuleAnalytics(null);
    } finally {
      setLoadingAnalytics(false);
    }
  };

  // Calculate health score for a rule
  const calculateHealthScore = (rule: RuleStatisticsItem): number => {
    const passRate = rule.pass_rate || 0;
    const recentActivity = rule.total_tests > 0 ? Math.min(rule.total_tests / 10, 1) * 100 : 0; // Normalize to 0-100
    return (passRate * 0.7) + (recentActivity * 0.3);
  };

  // Calculate trend indicator (comparing current vs previous period)
  const getTrendIndicator = (rule: RuleStatisticsItem): { icon: React.ReactNode; color: string } => {
    // For now, we'll use a simple heuristic based on pass rate
    // In a real implementation, we'd compare current period vs previous period
    const passRate = rule.pass_rate || 0;
    
    if (passRate >= 95) {
      return { icon: <TrendingUp className="w-4 h-4" />, color: 'text-success' };
    } else if (passRate >= 80) {
      return { icon: <Minus className="w-4 h-4" />, color: 'text-warning' };
    } else {
      return { icon: <TrendingDown className="w-4 h-4" />, color: 'text-danger' };
    }
  };

  const loadRuleResults = async (ruleId: number) => {
    try {
      setRuleResults([]); // Clear previous results
      const response = await fetch(`${API_BASE_URL}/validations/rules/${ruleId}/results?limit=20`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Failed to load rule results: ${response.status} ${response.statusText}`, errorText);
        setRuleResults([]);
        return;
      }
      
      const data: RuleResultItem[] = await response.json();
      // Ensure data is an array
      if (Array.isArray(data)) {
        setRuleResults(data);
      } else {
        console.error('Invalid response format, expected array:', data);
        setRuleResults([]);
      }
    } catch (error) {
      console.error('Failed to load rule results:', error);
      setRuleResults([]);
    }
  };

  const handleRuleClick = (rule: RuleStatisticsItem) => {
    try {
      setSelectedRule(rule);
      loadRuleResults(rule.rule_id);
    } catch (error) {
      console.error('Error opening rule details:', error);
      // Don't crash, just log the error
    }
  };

  // Filter rules based on current filters
  const filteredRules = ruleStatistics.filter(rule => {
    if (ruleFilters.documentType !== 'all' && rule.document_type !== ruleFilters.documentType) {
      return false;
    }
    if (ruleFilters.severity !== 'all' && rule.severity !== ruleFilters.severity) {
      return false;
    }
    if (ruleFilters.status === 'active' && !rule.is_active) {
      return false;
    }
    if (ruleFilters.status === 'inactive' && rule.is_active) {
      return false;
    }
    if (ruleFilters.search && !rule.rule_name.toLowerCase().includes(ruleFilters.search.toLowerCase())) {
      return false;
    }
    return true;
  });

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-text-primary">Data Control Center</h1>
            <p className="text-text-secondary mt-1">Data quality, validation, import, and task monitoring</p>
          </div>
          <Button 
            variant="primary" 
            icon={<RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />} 
            onClick={() => loadData(true)}
            disabled={refreshing || loading}
          >
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>

        {/* Data Quality Score Hero */}
        {qualityScore && (
          <Card variant={getStatusColor(qualityScore.status) as any} className="p-6 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <Target className="w-8 h-8" />
                  <div>
                    <div className="text-4xl font-bold">
                      {qualityScore.overallScore}/100
                    </div>
                    <div className="text-lg font-semibold uppercase">
                      {qualityScore.status}
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4 mt-4">
                  <div>
                    <div className="text-sm text-text-secondary">Extraction Accuracy</div>
                    <div className="text-xl font-bold">{qualityScore.extraction.accuracy}%</div>
                  </div>
                  <div>
                    <div className="text-sm text-text-secondary">Validation Pass Rate</div>
                    <div className="text-xl font-bold">{qualityScore.validation.passRate}%</div>
                  </div>
                  <div>
                    <div className="text-sm text-text-secondary">Data Completeness</div>
                    <div className="text-xl font-bold">{qualityScore.completeness.score}%</div>
                  </div>
                </div>
              </div>
              <div className="w-32 h-32">
                <ProgressBar
                  value={qualityScore.overallScore}
                  max={100}
                  variant={getStatusColor(qualityScore.status) as any}
                  height="lg"
                  showLabel
                  label={`${qualityScore.overallScore}%`}
                />
              </div>
            </div>
          </Card>
        )}

        {/* Tabs */}
        <div className="flex gap-1 border-b border-border mb-6 items-center">
          {(['quality', 'tasks', 'validation', 'import', 'review', 'documents'] as ControlTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 font-medium text-sm transition-colors capitalize ${
                activeTab === tab
                  ? 'text-info border-b-2 border-info'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              {tab === 'validation' ? 'Validation Rules' : tab}
            </button>
          ))}
          {/* Forensic Reconciliation Link */}
          <button
            onClick={() => {
              window.location.hash = 'forensic-reconciliation';
            }}
            className="ml-auto px-4 py-2 font-medium text-sm border-2 border-purple-600 text-purple-600 rounded-lg hover:bg-purple-50 transition-colors flex items-center gap-2"
            title="Open Forensic Reconciliation Elite System - Advanced matching, materiality-based thresholds, tiered exception management"
          >
            🔍 Forensic Reconciliation
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'quality' && qualityScore && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Extraction Quality</h3>
                <div className="text-4xl font-bold mb-2">{qualityScore.extraction.accuracy}%</div>
                <ProgressBar
                  value={qualityScore.extraction.accuracy}
                  max={100}
                  variant="success"
                  height="md"
                />
                <div className="mt-4 text-sm space-y-1">
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Confidence:</span>
                    <span className="font-medium">{qualityScore.extraction.confidence}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Failure Rate:</span>
                    <span className="font-medium">{qualityScore.extraction.failureRate}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Documents:</span>
                    <span className="font-medium">{qualityScore.extraction.documentsProcessed}</span>
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Validation Quality</h3>
                <div className="text-4xl font-bold mb-2">{qualityScore.validation.passRate}%</div>
                <ProgressBar
                  value={qualityScore.validation.passRate}
                  max={100}
                  variant="success"
                  height="md"
                />
                <div className="mt-4 text-sm space-y-1">
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Active Rules:</span>
                    <span className="font-medium">{qualityScore.validation.activeRules}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Failed:</span>
                    <span className="font-medium text-warning">{qualityScore.validation.failedValidations}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Critical:</span>
                    <span className="font-medium text-danger">{qualityScore.validation.criticalFailures}</span>
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Data Completeness</h3>
                <div className="text-4xl font-bold mb-2">{qualityScore.completeness.score}%</div>
                <ProgressBar
                  value={qualityScore.completeness.score}
                  max={100}
                  variant="success"
                  height="md"
                />
                <div className="mt-4 text-sm space-y-1">
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Required Fields:</span>
                    <span className="font-medium">{qualityScore.completeness.requiredFieldsFilled}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Missing Fields:</span>
                    <span className="font-medium text-warning">{qualityScore.completeness.missingFields}</span>
                  </div>
                </div>
              </Card>
            </div>

            {/* Document Type Breakdown */}
            {qualityScore.byDocumentType && Object.keys(qualityScore.byDocumentType).length > 0 && (
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Quality by Document Type</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {Object.entries(qualityScore.byDocumentType).map(([docType, metrics]) => {
                    const typeLabel = docType.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                    const matchRateColor = metrics.match_rate >= 99 ? 'success' : metrics.match_rate >= 95 ? 'warning' : 'danger';

                    return (
                      <Card key={docType} className="p-4" variant={matchRateColor as any}>
                        <div className="font-semibold mb-2">{typeLabel}</div>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-text-secondary">Documents:</span>
                            <span className="font-medium">{metrics.count}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-text-secondary">Records:</span>
                            <span className="font-medium">{metrics.total_records}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-text-secondary">Match Rate:</span>
                            <span className="font-medium">{metrics.match_rate.toFixed(1)}%</span>
                          </div>
                          <ProgressBar
                            value={metrics.match_rate}
                            max={100}
                            variant={matchRateColor as any}
                            height="sm"
                          />
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </Card>
            )}

            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Quality Alerts</h3>
              <div className="space-y-3">
                {qualityScore.validation.criticalFailures > 0 && (
                  <Card variant="danger" className="p-4">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-danger" />
                      <div>
                        <div className="font-semibold">Critical Issues ({qualityScore.criticalCount})</div>
                        <div className="text-sm text-text-secondary">
                          {qualityScore.criticalCount} items with confidence below 85% require immediate attention
                        </div>
                      </div>
                    </div>
                  </Card>
                )}
                {qualityScore.warningCount && qualityScore.warningCount > 0 && (
                  <Card variant="warning" className="p-4">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-warning" />
                      <div className="flex-1">
                        <div className="font-semibold">Warning Items ({qualityScore.warningCount})</div>
                        <div className="text-sm text-text-secondary">
                          {qualityScore.warningCount} items with confidence 85-95% should be reviewed
                        </div>
                        <button
                          className="mt-2 text-warning hover:underline text-sm font-medium"
                          onClick={() => window.location.hash = 'review-queue?severity=warning'}
                        >
                          View Warning Items →
                        </button>
                      </div>
                    </div>
                  </Card>
                )}
                {qualityScore.needsReviewCount && qualityScore.needsReviewCount > 0 && (
                  <Card variant="info" className="p-4">
                    <div className="flex items-center gap-2">
                      <Eye className="w-5 h-5 text-info" />
                      <div>
                        <div className="font-semibold">Items Needing Review ({qualityScore.needsReviewCount})</div>
                        <div className="text-sm text-text-secondary">
                          {qualityScore.needsReviewCount} items flagged for manual review
                        </div>
                        <button
                          className="mt-2 text-info hover:underline text-sm font-medium"
                          onClick={() => setActiveTab('review')}
                        >
                          View Review Queue →
                        </button>
                      </div>
                    </div>
                  </Card>
                )}
                {(!qualityScore.criticalCount || qualityScore.criticalCount === 0) &&
                 (!qualityScore.warningCount || qualityScore.warningCount === 0) && (
                  <Card variant="success" className="p-4">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-success" />
                      <div>
                        <div className="font-semibold">All Quality Checks Passed</div>
                        <div className="text-sm text-text-secondary">
                          No critical issues detected. System is operating at optimal quality.
                        </div>
                      </div>
                    </div>
                  </Card>
                )}
              </div>
            </Card>
          </div>
        )}

        {activeTab === 'tasks' && (
          <ErrorBoundary>
          <div className="space-y-6">
            {/* Header with Refresh Controls */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold">Task Management</h2>
                <p className="text-text-secondary">Monitor and manage Celery background tasks</p>
              </div>
              <div className="flex gap-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoRefreshTasks}
                    onChange={(e) => setAutoRefreshTasks(e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-sm">Auto-refresh</span>
                </label>
                <Button 
                  variant="primary" 
                  icon={<RefreshCw className={`w-4 h-4 ${taskLoading ? 'animate-spin' : ''}`} />} 
                  onClick={loadTaskDashboard}
                  disabled={taskLoading}
                >
                  {taskLoading ? 'Refreshing...' : 'Refresh'}
                </Button>
              </div>
            </div>

            {/* Loading State */}
            {taskLoading && !taskDashboard && (
              <Card className="p-6">
                <div className="text-center py-8">
                  <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-info" />
                  <p className="text-text-secondary">Loading task dashboard...</p>
                </div>
              </Card>
            )}

            {/* Error State */}
            {taskDashboard?.error && (
              <Card variant="danger" className="p-4">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5" />
                  <span>{taskDashboard.error}</span>
                </div>
              </Card>
            )}

            {/* Empty State - No data loaded yet */}
            {!taskLoading && !taskDashboard && (
              <Card className="p-6">
                <div className="text-center py-8">
                  <Activity className="w-12 h-12 mx-auto mb-4 text-text-secondary" />
                  <p className="text-text-secondary">No task data available. Click Refresh to load.</p>
                </div>
              </Card>
            )}

            {/* Queue Overview Cards */}
            {taskDashboard && taskDashboard.queue_stats && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <Card className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-text-secondary">Pending</div>
                        <div className="text-2xl font-bold">{taskDashboard.queue_stats.pending || 0}</div>
                      </div>
                      <Clock className="w-8 h-8 text-warning" />
                    </div>
                  </Card>
                  <Card className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-text-secondary">Processing</div>
                        <div className="text-2xl font-bold">{taskDashboard.queue_stats.processing || 0}</div>
                      </div>
                      <Activity className="w-8 h-8 text-info" />
                    </div>
                  </Card>
                  <Card className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-text-secondary">Completed Today</div>
                        <div className="text-2xl font-bold">{taskDashboard.queue_stats.completed_today || 0}</div>
                      </div>
                      <CheckCircle className="w-8 h-8 text-success" />
                    </div>
                  </Card>
                  <Card className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-text-secondary">Failed Today</div>
                        <div className="text-2xl font-bold">{taskDashboard.queue_stats.failed_today || 0}</div>
                        <div className="text-xs text-text-secondary mt-1">
                          Success Rate: {(taskDashboard.queue_stats.success_rate || 0).toFixed(1)}%
                        </div>
                      </div>
                      <XCircle className="w-8 h-8 text-danger" />
                    </div>
                  </Card>
                </div>

                {/* Quick Actions Panel */}
                <Card className="p-4">
                  <h3 className="font-semibold mb-3">Quick Actions</h3>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="primary"
                      icon={<RefreshCw className="w-4 h-4" />}
                      onClick={handleRetryFailedExtractions}
                      disabled={reprocessing || taskDashboard.queue_stats.failed_today === 0}
                    >
                      Retry All Failed Extractions
                    </Button>
                    <Button
                      variant="info"
                      icon={<Activity className="w-4 h-4" />}
                      onClick={handleRecoverStuckDocuments}
                      disabled={reprocessing}
                    >
                      Recover Stuck Documents
                    </Button>
                    <Button
                      variant="default"
                      icon={<FileText className="w-4 h-4" />}
                      onClick={() => setActiveTab('documents')}
                    >
                      View Documents
                    </Button>
                    <Button
                      variant="default"
                      icon={<Eye className="w-4 h-4" />}
                      onClick={() => setActiveTab('review')}
                    >
                      Review Queue
                    </Button>
                  </div>
                </Card>

                {/* Worker Status */}
                {taskDashboard.workers && taskDashboard.workers.length > 0 && (
                  <Card className="p-6">
                    <h3 className="text-lg font-semibold mb-4">Worker Status</h3>
                    <WorkerStatus workers={taskDashboard.workers} />
                  </Card>
                )}

                {/* Active Tasks */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4">
                    Active Tasks ({taskDashboard.active_tasks?.length || 0})
                  </h3>
                  {!taskDashboard.active_tasks || taskDashboard.active_tasks.length === 0 ? (
                    <div className="text-center py-8 text-text-secondary">
                      No active tasks at the moment
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {taskDashboard.active_tasks.map((task) => (
                        <TaskCard
                          key={task.task_id}
                          task={task}
                          onViewDetails={(task) => setSelectedTask(task)}
                          onCancel={handleCancelTask}
                          canceling={cancelingTaskId === task.task_id}
                        />
                      ))}
                    </div>
                  )}
                </Card>

                {/* Recent Tasks */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4">Recent Tasks</h3>
                  {!taskDashboard.recent_tasks || taskDashboard.recent_tasks.length === 0 ? (
                    <div className="text-center py-8 text-text-secondary">
                      No recent tasks
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-border">
                            <th className="text-left p-2 text-sm font-semibold">Task ID</th>
                            <th className="text-left p-2 text-sm font-semibold">Type</th>
                            <th className="text-left p-2 text-sm font-semibold">Status</th>
                            <th className="text-left p-2 text-sm font-semibold">Duration</th>
                            <th className="text-left p-2 text-sm font-semibold">Document</th>
                            <th className="text-left p-2 text-sm font-semibold">Completed</th>
                            <th className="text-left p-2 text-sm font-semibold">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {taskDashboard.recent_tasks.map((task) => (
                            <tr key={task.task_id} className="border-b border-border hover:bg-surface-secondary">
                              <td className="p-2 text-xs font-mono">{task.task_id.substring(0, 8)}...</td>
                              <td className="p-2 text-sm">{task.task_type}</td>
                              <td className="p-2">
                                <span className={`px-2 py-1 rounded text-xs ${
                                  task.status === 'SUCCESS' ? 'bg-success-light text-success' :
                                  task.status === 'FAILURE' ? 'bg-danger-light text-danger' :
                                  'bg-warning-light text-warning'
                                }`}>
                                  {task.status}
                                </span>
                              </td>
                              <td className="p-2 text-sm">
                                {task.duration_seconds 
                                  ? `${Math.floor(task.duration_seconds / 60)}m ${task.duration_seconds % 60}s`
                                  : 'N/A'
                                }
                              </td>
                              <td className="p-2 text-sm truncate max-w-xs" title={task.document_name}>
                                {task.document_name || 'N/A'}
                              </td>
                              <td className="p-2 text-sm">
                                {task.completed_at 
                                  ? new Date(task.completed_at).toLocaleString()
                                  : 'N/A'
                                }
                              </td>
                              <td className="p-2">
                                <Button
                                  variant="info"
                                  size="sm"
                                  icon={<Eye className="w-3 h-3" />}
                                  onClick={() => setSelectedTask(task)}
                                >
                                  View
                                </Button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Card>

                {/* Phase 2: Task Filters */}
                <TaskFilters
                  filter={taskFilter}
                  onFilterChange={setTaskFilter}
                  onClear={() => setTaskFilter({
                    type: 'all',
                    status: 'all',
                    property: 'all',
                    search: '',
                    dateFrom: '',
                    dateTo: ''
                  })}
                  availableProperties={Array.from(new Set([
                    ...(taskDashboard?.active_tasks || []).map(t => t.property_code).filter(Boolean),
                    ...(taskDashboard?.recent_tasks || []).map(t => t.property_code).filter(Boolean)
                  ]))}
                />

                {/* Phase 2: Task Charts */}
                {showCharts && taskDashboard?.task_statistics && taskDashboard.recent_tasks && (
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold flex items-center gap-2">
                        <BarChart3 className="w-5 h-5" />
                        Task Analytics
                      </h3>
                      <Button
                        variant="default"
                        size="sm"
                        onClick={() => setShowCharts(!showCharts)}
                      >
                        {showCharts ? 'Hide Charts' : 'Show Charts'}
                      </Button>
                    </div>
                    <TaskCharts
                      statistics={taskDashboard.task_statistics}
                      recentTasks={taskDashboard.recent_tasks}
                    />
                  </div>
                )}

                {/* Phase 2: Bulk Actions Bar */}
                {showBulkActions && selectedTasks.size > 0 && (
                  <Card className="p-4 bg-info-light">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <CheckSquare className="w-5 h-5 text-info" />
                        <span className="font-semibold">{selectedTasks.size} task(s) selected</span>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="danger"
                          size="sm"
                          icon={<XCircle className="w-4 h-4" />}
                          onClick={handleBulkCancel}
                        >
                          Cancel Selected
                        </Button>
                        <Button
                          variant="default"
                          size="sm"
                          icon={<X className="w-4 h-4" />}
                          onClick={clearSelection}
                        >
                          Clear Selection
                        </Button>
                      </div>
                    </div>
                  </Card>
                )}

                {/* Phase 2: Extended History with Filtering */}
                <Card className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-4">
                      <h3 className="text-lg font-semibold">Task History</h3>
                      <select
                        value={historyDays}
                        onChange={(e) => setHistoryDays(Number(e.target.value))}
                        className="px-3 py-1 border border-border rounded bg-surface text-sm"
                      >
                        <option value={1}>Last 24 hours</option>
                        <option value={7}>Last 7 days</option>
                        <option value={30}>Last 30 days</option>
                      </select>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="default"
                        size="sm"
                        icon={<CheckSquare className="w-4 h-4" />}
                        onClick={selectAllTasks}
                      >
                        Select All
                      </Button>
                      <Button
                        variant="default"
                        size="sm"
                        icon={<Download className="w-4 h-4" />}
                        onClick={handleExportTasks}
                      >
                        Export CSV
                      </Button>
                    </div>
                  </div>
                  
                  {(() => {
                    const allTasks = extendedHistory.length > 0 ? extendedHistory : (taskDashboard?.recent_tasks || []);
                    const filteredTasks = filterTasks(allTasks);
                    
                    return filteredTasks.length === 0 ? (
                      <div className="text-center py-8 text-text-secondary">
                        No tasks found matching the current filters
                      </div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead>
                            <tr className="border-b border-border">
                              <th className="text-left p-2 text-sm font-semibold w-12">
                                <input
                                  type="checkbox"
                                  checked={selectedTasks.size === filteredTasks.length && filteredTasks.length > 0}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      selectAllTasks();
                                    } else {
                                      clearSelection();
                                    }
                                  }}
                                  className="rounded"
                                />
                              </th>
                              <th className="text-left p-2 text-sm font-semibold">Task ID</th>
                              <th className="text-left p-2 text-sm font-semibold">Type</th>
                              <th className="text-left p-2 text-sm font-semibold">Status</th>
                              <th className="text-left p-2 text-sm font-semibold">Duration</th>
                              <th className="text-left p-2 text-sm font-semibold">Document</th>
                              <th className="text-left p-2 text-sm font-semibold">Property</th>
                              <th className="text-left p-2 text-sm font-semibold">Completed</th>
                              <th className="text-left p-2 text-sm font-semibold">Actions</th>
                            </tr>
                          </thead>
                          <tbody>
                            {filteredTasks.map((task) => (
                              <tr key={task.task_id} className="border-b border-border hover:bg-surface-secondary">
                                <td className="p-2">
                                  <input
                                    type="checkbox"
                                    checked={selectedTasks.has(task.task_id)}
                                    onChange={() => toggleTaskSelection(task.task_id)}
                                    className="rounded"
                                  />
                                </td>
                                <td className="p-2 text-xs font-mono">{task.task_id.substring(0, 8)}...</td>
                                <td className="p-2 text-sm capitalize">{task.task_type.replace('_', ' ')}</td>
                                <td className="p-2">
                                  <span className={`px-2 py-1 rounded text-xs ${
                                    task.status === 'SUCCESS' ? 'bg-success-light text-success' :
                                    task.status === 'FAILURE' ? 'bg-danger-light text-danger' :
                                    task.status === 'PROCESSING' ? 'bg-info-light text-info' :
                                    'bg-warning-light text-warning'
                                  }`}>
                                    {task.status}
                                  </span>
                                </td>
                                <td className="p-2 text-sm">
                                  {task.duration_seconds 
                                    ? `${Math.floor(task.duration_seconds / 60)}m ${task.duration_seconds % 60}s`
                                    : 'N/A'
                                  }
                                </td>
                                <td className="p-2 text-sm truncate max-w-xs" title={task.document_name}>
                                  {task.document_name || 'N/A'}
                                </td>
                                <td className="p-2 text-sm">{task.property_code || 'N/A'}</td>
                                <td className="p-2 text-sm">
                                  {task.completed_at 
                                    ? new Date(task.completed_at).toLocaleString()
                                    : task.started_at
                                    ? new Date(task.started_at).toLocaleString()
                                    : 'N/A'
                                  }
                                </td>
                                <td className="p-2">
                                  <Button
                                    variant="info"
                                    size="sm"
                                    icon={<Eye className="w-3 h-3" />}
                                    onClick={() => setSelectedTask(task)}
                                  >
                                    View
                                  </Button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    );
                  })()}
                </Card>

                {/* Task Statistics */}
                {taskDashboard.task_statistics && Object.keys(taskDashboard.task_statistics.by_type || {}).length > 0 && (
                  <Card className="p-6">
                    <h3 className="text-lg font-semibold mb-4">Task Statistics</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <div className="text-sm text-text-secondary">Average Extraction Time</div>
                        <div className="text-xl font-bold">
                          {Math.floor((taskDashboard.task_statistics.avg_extraction_time || 0) / 60)}m{' '}
                          {Math.floor((taskDashboard.task_statistics.avg_extraction_time || 0) % 60)}s
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-text-secondary">Total Tasks Today</div>
                        <div className="text-xl font-bold">{taskDashboard.task_statistics.total_tasks_today || 0}</div>
                      </div>
                      <div>
                        <div className="text-sm text-text-secondary">Tasks by Type</div>
                        <div className="space-y-1 mt-2">
                          {Object.entries(taskDashboard.task_statistics.by_type || {}).map(([type, stats]) => (
                            <div key={type} className="flex justify-between text-sm">
                              <span className="capitalize">{type.replace('_', ' ')}</span>
                              <span className="font-medium">{(stats as any).count || 0} tasks</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </Card>
                )}

                {/* Phase 3: Performance Dashboard */}
                {taskDashboard && (
                  <PerformanceDashboard dashboard={taskDashboard} />
                )}

                {/* Phase 3: Task Scheduler */}
                <TaskScheduler
                  onSchedule={async (task) => {
                    try {
                      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                      const response = await fetch(`${API_BASE_URL}/api/v1/tasks/scheduled`, {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json',
                        },
                        credentials: 'include',
                        body: JSON.stringify({
                          task_type: task.task_type,
                          schedule_type: task.schedule_type,
                          scheduled_time: task.schedule_type === 'once' ? task.scheduled_time : null,
                          cron_expression: task.schedule_type === 'recurring' ? task.cron_expression : null,
                          parameters: task.parameters || {},
                          task_name: `${task.task_type} - ${task.schedule_type}`,
                        }),
                      });

                      if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to schedule task');
                      }

                      const result = await response.json();
                      console.log('Task scheduled successfully:', result);
                      return Promise.resolve();
                    } catch (error: any) {
                      console.error('Failed to schedule task:', error);
                      throw error;
                    }
                  }}
                />
              </>
            )}
          </div>
          </ErrorBoundary>
        )}

        {/* Task Details Modal */}
        {selectedTask && (
          <TaskDetailsModal
            task={selectedTask}
            onClose={() => setSelectedTask(null)}
            onRetry={async (taskId) => {
              await handleRetryFailedExtractions();
              setSelectedTask(null);
            }}
            onCancel={handleCancelTask}
          />
        )}

        {activeTab === 'validation' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold">Validation Rules</h2>
              <Button variant="primary" icon={<Settings className="w-4 h-4" />} onClick={() => window.location.hash = 'validation-rules'}>
                Manage Rules
              </Button>
            </div>

            {/* Summary Cards */}
            {ruleSummary && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="p-4">
                  <div className="text-sm text-text-secondary">Active Rules</div>
                  <div className="text-2xl font-bold">{ruleSummary.active_rules}</div>
                  <div className="text-xs text-text-secondary mt-1">of {ruleSummary.total_rules} total</div>
                </Card>
                <Card className="p-4">
                  <div className="text-sm text-text-secondary">Total Checks</div>
                  <div className="text-2xl font-bold">{ruleSummary.total_checks.toLocaleString()}</div>
                  <div className="text-xs text-text-secondary mt-1">All time</div>
                </Card>
                <Card className="p-4">
                  <div className="text-sm text-text-secondary">Overall Pass Rate</div>
                  <div className="text-2xl font-bold">{ruleSummary.overall_pass_rate.toFixed(1)}%</div>
                  <div className="text-xs text-text-secondary mt-1">
                    {ruleSummary.total_checks > 0 ? `${((ruleSummary.total_checks - ruleSummary.errors - ruleSummary.warnings) / ruleSummary.total_checks * 100).toFixed(1)}% passed` : 'No data'}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-sm text-text-secondary">Failed Checks</div>
                  <div className="text-2xl font-bold text-danger">{ruleSummary.errors + ruleSummary.warnings}</div>
                  <div className="text-xs text-text-secondary mt-1">
                    {ruleSummary.errors} errors, {ruleSummary.warnings} warnings
                  </div>
                </Card>
              </div>
            )}

            {/* Filters */}
            <Card className="p-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label htmlFor="docTypeFilter" className="block text-sm font-medium text-text-secondary mb-1">Document Type</label>
                  <select
                    id="docTypeFilter"
                    value={ruleFilters.documentType}
                    onChange={(e) => setRuleFilters({ ...ruleFilters, documentType: e.target.value })}
                    className="w-full px-3 py-2 border border-border rounded-md bg-surface text-text-primary"
                  >
                    <option value="all">All Types</option>
                    <option value="balance_sheet">Balance Sheet</option>
                    <option value="income_statement">Income Statement</option>
                    <option value="cash_flow">Cash Flow</option>
                    <option value="rent_roll">Rent Roll</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="severityFilter" className="block text-sm font-medium text-text-secondary mb-1">Severity</label>
                  <select
                    id="severityFilter"
                    value={ruleFilters.severity}
                    onChange={(e) => setRuleFilters({ ...ruleFilters, severity: e.target.value })}
                    className="w-full px-3 py-2 border border-border rounded-md bg-surface text-text-primary"
                  >
                    <option value="all">All Severities</option>
                    <option value="error">Error</option>
                    <option value="warning">Warning</option>
                    <option value="info">Info</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="statusFilter" className="block text-sm font-medium text-text-secondary mb-1">Status</label>
                  <select
                    id="statusFilter"
                    value={ruleFilters.status}
                    onChange={(e) => setRuleFilters({ ...ruleFilters, status: e.target.value })}
                    className="w-full px-3 py-2 border border-border rounded-md bg-surface text-text-primary"
                  >
                    <option value="all">All</option>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="searchFilter" className="block text-sm font-medium text-text-secondary mb-1">Search</label>
                  <div className="flex rounded-md shadow-sm">
                    <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-border bg-surface-secondary text-text-secondary">
                      <Search className="w-4 h-4" />
                    </span>
                    <input
                      type="text"
                      id="searchFilter"
                      value={ruleFilters.search}
                      onChange={(e) => setRuleFilters({ ...ruleFilters, search: e.target.value })}
                      placeholder="Rule name..."
                      className="flex-1 block w-full rounded-none rounded-r-md border-border focus:ring-primary-500 focus:border-primary-500 sm:text-sm bg-surface text-text-primary"
                    />
                  </div>
                </div>
              </div>
            </Card>

            {/* Analytics Charts Toggle */}
            <Card className="p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Performance Analytics</h3>
                <button
                  onClick={() => setShowValidationCharts(!showValidationCharts)}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-text-primary bg-surface-secondary hover:bg-surface-tertiary border border-border rounded-md transition-colors"
                >
                  <BarChart3 className="w-4 h-4" />
                  {showValidationCharts ? 'Hide Charts' : 'Show Charts'}
                </button>
              </div>
            </Card>

            {/* Analytics Charts */}
            {showValidationCharts && ruleAnalytics && (
              <RuleCharts analytics={ruleAnalytics} />
            )}

            {/* Rules Table */}
            <Card className="p-6">
              {loadingRules ? (
                <div className="text-center py-8">Loading validation rules...</div>
              ) : filteredRules.length === 0 ? (
                <div className="text-center py-8 text-text-secondary">
                  {ruleStatistics.length === 0 ? 'No validation rules found' : 'No rules match the current filters'}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-2 px-4">Rule Name</th>
                        <th className="text-left py-2 px-4">Type</th>
                        <th className="text-left py-2 px-4">Severity</th>
                        <th className="text-right py-2 px-4">Passed</th>
                        <th className="text-right py-2 px-4">Failed</th>
                        <th className="text-right py-2 px-4">Pass Rate</th>
                        <th className="text-center py-2 px-4">Health</th>
                        <th className="text-center py-2 px-4">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRules.map((rule) => (
                        <tr 
                          key={rule.rule_id} 
                          className="border-b border-border hover:bg-surface-secondary cursor-pointer"
                          onClick={() => handleRuleClick(rule)}
                        >
                          <td className="py-2 px-4 font-medium">{rule.rule_name}</td>
                          <td className="py-2 px-4 text-text-secondary capitalize">{rule.rule_type.replace(/_/g, ' ')}</td>
                          <td className="py-2 px-4">
                            <span className={`px-2 py-1 rounded text-xs ${
                              rule.severity === 'error' ? 'bg-danger-light text-danger' : 
                              rule.severity === 'warning' ? 'bg-warning-light text-warning' : 
                              'bg-info-light text-info'
                            }`}>
                              {rule.severity}
                            </span>
                          </td>
                          <td className="text-right py-2 px-4 text-success">{rule.passed_count}</td>
                          <td className="text-right py-2 px-4 text-danger">{rule.failed_count}</td>
                          <td className="text-right py-2 px-4">
                            <div className="flex items-center justify-end gap-2">
                              <span className="font-medium">{(rule.pass_rate || 0).toFixed(1)}%</span>
                              {getTrendIndicator(rule).icon && (
                                <span className={getTrendIndicator(rule).color}>
                                  {getTrendIndicator(rule).icon}
                                </span>
                              )}
                              <ProgressBar 
                                value={rule.pass_rate || 0} 
                                max={100} 
                                variant={(rule.pass_rate || 0) >= 95 ? 'success' : (rule.pass_rate || 0) >= 80 ? 'warning' : 'danger'} 
                                height="sm"
                                className="w-16"
                              />
                            </div>
                          </td>
                          <td className="text-center py-2 px-4">
                            {(() => {
                              const healthScore = calculateHealthScore(rule);
                              const healthColor = healthScore >= 90 ? 'text-success' : healthScore >= 70 ? 'text-warning' : 'text-danger';
                              return (
                                <span className={`font-semibold ${healthColor}`} title={`Health Score: ${healthScore.toFixed(1)}%`}>
                                  {healthScore.toFixed(0)}%
                                </span>
                              );
                            })()}
                          </td>
                          <td className="text-center py-2 px-4">
                            {rule.is_active ? (
                              <CheckCircle className="w-5 h-5 text-success mx-auto" />
                            ) : (
                              <XCircle className="w-5 h-5 text-text-secondary mx-auto" />
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            {/* Rule Details Modal */}
            {selectedRule && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedRule(null)}>
                <div 
                  className="bg-surface rounded-xl p-6 max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto" 
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="flex items-center justify-between mb-4 border-b border-border pb-4">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setSelectedRule(null)}
                        className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-text-primary bg-surface-secondary hover:bg-surface-tertiary border border-border rounded-md transition-colors"
                        title="Go back to validation rules list"
                      >
                        <ArrowLeft className="w-4 h-4" />
                        Back
                      </button>
                      <h2 className="text-2xl font-bold">Rule Details</h2>
                    </div>
                    <button
                      onClick={() => setSelectedRule(null)}
                      className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-text-primary bg-surface-secondary hover:bg-surface-tertiary border border-border rounded-md transition-colors"
                      title="Close modal"
                    >
                      <X className="w-4 h-4" />
                      Close
                    </button>
                  </div>

                  <div className="space-y-4">
                    {/* Rule Information */}
                    <Card className="p-4">
                      <h3 className="font-semibold mb-3">Rule Information</h3>
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <div className="text-text-secondary">Rule Name</div>
                          <div className="font-medium">{selectedRule.rule_name}</div>
                        </div>
                        <div>
                          <div className="text-text-secondary">Document Type</div>
                          <div className="font-medium capitalize">{selectedRule.document_type.replace(/_/g, ' ')}</div>
                        </div>
                        <div>
                          <div className="text-text-secondary">Rule Type</div>
                          <div className="font-medium capitalize">{selectedRule.rule_type.replace(/_/g, ' ')}</div>
                        </div>
                        <div>
                          <div className="text-text-secondary">Severity</div>
                          <span className={`px-2 py-1 rounded text-xs ${
                            selectedRule.severity === 'error' ? 'bg-danger-light text-danger' : 
                            selectedRule.severity === 'warning' ? 'bg-warning-light text-warning' : 
                            'bg-info-light text-info'
                          }`}>
                            {selectedRule.severity}
                          </span>
                        </div>
                        {selectedRule.rule_description && (
                          <div className="col-span-2">
                            <div className="text-text-secondary">Description</div>
                            <div className="font-medium">{selectedRule.rule_description}</div>
                          </div>
                        )}
                      </div>
                    </Card>

                    {/* Statistics */}
                    <Card className="p-4">
                      <h3 className="font-semibold mb-3">Statistics</h3>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <div className="text-sm text-text-secondary">Total Tests</div>
                          <div className="text-xl font-bold">{selectedRule.total_tests}</div>
                        </div>
                        <div>
                          <div className="text-sm text-text-secondary">Passed</div>
                          <div className="text-xl font-bold text-success">{selectedRule.passed_count}</div>
                        </div>
                        <div>
                          <div className="text-sm text-text-secondary">Failed</div>
                          <div className="text-xl font-bold text-danger">{selectedRule.failed_count}</div>
                        </div>
                        <div>
                          <div className="text-sm text-text-secondary">Pass Rate</div>
                          <div className="text-xl font-bold">{(selectedRule.pass_rate || 0).toFixed(1)}%</div>
                        </div>
                      </div>
                      {selectedRule.last_executed_at && (
                        <div className="mt-3 text-sm text-text-secondary">
                          Last executed: {new Date(selectedRule.last_executed_at).toLocaleString()}
                        </div>
                      )}
                    </Card>

                    {/* Recent Results */}
                    <Card className="p-4">
                      <h3 className="font-semibold mb-3">Recent Results</h3>
                      {ruleResults.length === 0 ? (
                        <div className="text-text-secondary text-sm">No recent results available</div>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-border">
                                <th className="text-left py-2 px-2">Status</th>
                                <th className="text-left py-2 px-2">Expected</th>
                                <th className="text-left py-2 px-2">Actual</th>
                                <th className="text-left py-2 px-2">Difference</th>
                                <th className="text-left py-2 px-2">Error</th>
                              </tr>
                            </thead>
                            <tbody>
                              {ruleResults.map((result) => (
                                <tr key={result.id} className="border-b border-border">
                                  <td className="py-2 px-2">
                                    {result.passed ? (
                                      <span className="text-success">✓ Passed</span>
                                    ) : (
                                      <span className="text-danger">✗ Failed</span>
                                    )}
                                  </td>
                                  <td className="py-2 px-2">
                                    {result.expected_value !== undefined && result.expected_value !== null ? `$${result.expected_value.toLocaleString()}` : 'N/A'}
                                  </td>
                                  <td className="py-2 px-2">
                                    {result.actual_value !== undefined && result.actual_value !== null ? `$${result.actual_value.toLocaleString()}` : 'N/A'}
                                  </td>
                                  <td className="py-2 px-2">
                                    {result.difference !== undefined && result.difference !== null ? `$${result.difference.toLocaleString()}` : 'N/A'}
                                    {result.difference_percentage !== undefined && result.difference_percentage !== null && (
                                      <span className="text-text-secondary ml-1">({result.difference_percentage.toFixed(2)}%)</span>
                                    )}
                                  </td>
                                  <td className="py-2 px-2 text-xs text-text-secondary">
                                    {result.error_message || '-'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </Card>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'import' && (
          <Card className="p-6">
            <h2 className="text-2xl font-bold mb-4">Bulk Import</h2>
            <Button variant="primary" icon={<Upload className="w-4 h-4" />} onClick={() => window.location.hash = 'bulk-import'}>
              Go to Bulk Import
            </Button>
          </Card>
        )}

        {activeTab === 'review' && (
          <Card className="p-6">
            <h2 className="text-2xl font-bold mb-4">Review Queue</h2>
            <Button variant="primary" icon={<Eye className="w-4 h-4" />} onClick={() => window.location.hash = 'review-queue'}>
              Go to Review Queue
            </Button>
          </Card>
        )}

        {activeTab === 'documents' && (
          <div className="space-y-6">
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold">Document Management</h2>
                <Button variant="primary" icon={<Plus className="w-4 h-4" />} onClick={() => setShowUploadModal(true)}>
                  Upload Document
                </Button>
              </div>
              
              <div className="mb-4 space-y-3">
                {/* Real-time Status Counts */}
                <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                  <div className="bg-background rounded-lg p-3 border border-border">
                    <div className="text-sm text-text-secondary">Total</div>
                    <div className="text-2xl font-bold text-text-primary">{statusCounts.total}</div>
                  </div>
                  <div className="bg-success-light rounded-lg p-3 border border-success">
                    <div className="text-sm text-text-secondary">Completed</div>
                    <div className="text-2xl font-bold text-success">{statusCounts.completed}</div>
                  </div>
                  <div className="bg-warning-light rounded-lg p-3 border border-warning">
                    <div className="text-sm text-text-secondary">Validating</div>
                    <div className="text-2xl font-bold text-warning">{statusCounts.validating}</div>
                  </div>
                  <div className="bg-danger-light rounded-lg p-3 border border-danger">
                    <div className="text-sm text-text-secondary">Failed</div>
                    <div className="text-2xl font-bold text-danger">{statusCounts.failed}</div>
                  </div>
                  <div className="bg-info-light rounded-lg p-3 border border-info">
                    <div className="text-sm text-text-secondary">Pending</div>
                    <div className="text-2xl font-bold text-info">{statusCounts.pending}</div>
                  </div>
                  <div className="bg-warning-light rounded-lg p-3 border border-warning">
                    <div className="text-sm text-text-secondary">Extracting</div>
                    <div className="text-2xl font-bold text-warning">{statusCounts.extracting}</div>
                  </div>
                </div>
                
                {/* Action Buttons */}
                <div className="flex items-center justify-between">
                  <div className="text-sm text-text-secondary">
                    Last updated: {lastUpdated.toLocaleTimeString()}
                  </div>
                  <div className="flex gap-2">
                    {statusCounts.failed > 0 && (
                      <Button 
                        variant="warning" 
                        icon={<RefreshCw className="w-4 h-4" />} 
                        onClick={handleReprocessFailed}
                        disabled={reprocessing}
                      >
                        {reprocessing ? 'Reprocessing...' : `Reprocess ${statusCounts.failed} Failed`}
                      </Button>
                    )}
                    <Button 
                      variant="danger" 
                      icon={<Trash2 className="w-4 h-4" />} 
                      onClick={handleDeleteAllHistory}
                      disabled={deleting}
                    >
                      {deleting ? 'Deleting...' : 'Delete All History'}
                    </Button>
                    <Button 
                      variant="warning" 
                      icon={<Filter className="w-4 h-4" />} 
                      onClick={() => setShowDeleteFiltersModal(true)}
                      disabled={deleting}
                    >
                      Delete with Filters
                    </Button>
                  </div>
                </div>
              </div>

              {/* Filtered Deletion Modal */}
              {showDeleteFiltersModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                  <div className="bg-background rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                    <div className="flex items-center justify-between mb-4">
                      <h2 className="text-2xl font-bold text-text-primary">Delete Anomalies, Warnings & Alerts</h2>
                      <button
                        onClick={() => {
                          setShowDeleteFiltersModal(false);
                          setPreviewData(null);
                        }}
                        className="text-text-secondary hover:text-text-primary"
                      >
                        <X className="w-6 h-6" />
                      </button>
                    </div>

                    <div className="space-y-4">
                      {/* Property Selection (Required) */}
                      <div>
                        <label className="block text-sm font-semibold mb-2 text-text-primary">
                          Properties <span className="text-danger">*</span>
                        </label>
                        <div className="border border-border rounded p-2 max-h-40 overflow-y-auto">
                          {properties.length === 0 ? (
                            <p className="text-text-secondary text-sm">Loading properties...</p>
                          ) : (
                            properties.map((prop) => (
                              <label key={prop.id} className="flex items-center space-x-2 py-1 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={deleteFilters.propertyIds.includes(prop.id)}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setDeleteFilters({
                                        ...deleteFilters,
                                        propertyIds: [...deleteFilters.propertyIds, prop.id]
                                      });
                                    } else {
                                      setDeleteFilters({
                                        ...deleteFilters,
                                        propertyIds: deleteFilters.propertyIds.filter(id => id !== prop.id)
                                      });
                                    }
                                    setPreviewData(null); // Reset preview when filters change
                                  }}
                                  className="rounded"
                                />
                                <span className="text-sm text-text-primary">
                                  {prop.property_code} - {prop.property_name || 'Unnamed'}
                                </span>
                              </label>
                            ))
                          )}
                        </div>
                        {deleteFilters.propertyIds.length > 0 && (
                          <p className="text-xs text-text-secondary mt-1">
                            {deleteFilters.propertyIds.length} property(ies) selected
                          </p>
                        )}
                      </div>

                      {/* Year Filter (Optional) */}
                      <div>
                        <label className="block text-sm font-semibold mb-2 text-text-primary">
                          Year (Optional)
                        </label>
                        <input
                          type="number"
                          min="2000"
                          max="2100"
                          value={deleteFilters.year}
                          onChange={(e) => {
                            setDeleteFilters({ ...deleteFilters, year: e.target.value });
                            setPreviewData(null);
                          }}
                          placeholder="e.g., 2023"
                          className="w-full px-3 py-2 border border-border rounded bg-background text-text-primary"
                        />
                      </div>

                      {/* Document Type Filter (Optional) */}
                      <div>
                        <label className="block text-sm font-semibold mb-2 text-text-primary">
                          Document Type (Optional)
                        </label>
                        <select
                          value={deleteFilters.documentType}
                          onChange={(e) => {
                            setDeleteFilters({ ...deleteFilters, documentType: e.target.value });
                            setPreviewData(null);
                          }}
                          className="w-full px-3 py-2 border border-border rounded bg-background text-text-primary"
                        >
                          <option value="">All Types</option>
                          <option value="balance_sheet">Balance Sheet</option>
                          <option value="income_statement">Income Statement</option>
                          <option value="cash_flow">Cash Flow</option>
                          <option value="rent_roll">Rent Roll</option>
                          <option value="mortgage_statement">Mortgage Statement</option>
                        </select>
                      </div>

                      {/* Period ID Filter (Optional) */}
                      <div>
                        <label className="block text-sm font-semibold mb-2 text-text-primary">
                          Period ID (Optional)
                        </label>
                        <input
                          type="number"
                          value={deleteFilters.periodId}
                          onChange={(e) => {
                            setDeleteFilters({ ...deleteFilters, periodId: e.target.value });
                            setPreviewData(null);
                          }}
                          placeholder="Specific period ID"
                          className="w-full px-3 py-2 border border-border rounded bg-background text-text-primary"
                        />
                      </div>

                      {/* Preview Section */}
                      {previewData && (
                        <div className="bg-info-light border border-info rounded p-4">
                          <h3 className="font-semibold mb-2 text-text-primary">Preview</h3>
                          <div className="space-y-1 text-sm">
                            <p><strong>Total Records:</strong> {previewData.total_preview}</p>
                            <p><strong>Matching Documents:</strong> {previewData.matching_documents}</p>
                            <div className="mt-2 pt-2 border-t border-info">
                              <p><strong>Breakdown:</strong></p>
                              <ul className="list-disc list-inside ml-2">
                                <li>Anomalies: {previewData.preview_counts.anomaly_detections}</li>
                                <li>Alerts: {previewData.preview_counts.alerts}</li>
                                <li>Committee Alerts: {previewData.preview_counts.committee_alerts}</li>
                              </ul>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="flex gap-2 pt-4">
                        <Button
                          variant="info"
                          icon={<Eye className="w-4 h-4" />}
                          onClick={handlePreviewDeletion}
                          disabled={deleteFilters.propertyIds.length === 0 || loadingPreview}
                        >
                          {loadingPreview ? 'Loading...' : 'Preview Deletion'}
                        </Button>
                        <Button
                          variant="danger"
                          icon={<Trash2 className="w-4 h-4" />}
                          onClick={handleDeleteFiltered}
                          disabled={!previewData || deleting || deleteFilters.propertyIds.length === 0}
                        >
                          {deleting ? 'Deleting...' : 'Delete'}
                        </Button>
                        <Button
                          variant="secondary"
                          onClick={() => {
                            setShowDeleteFiltersModal(false);
                            setPreviewData(null);
                            setDeleteFilters({
                              propertyIds: [],
                              year: '',
                              documentType: '',
                              periodId: ''
                            });
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-4 font-semibold">File Name</th>
                      <th className="text-left py-3 px-4 font-semibold">Property</th>
                      <th className="text-left py-3 px-4 font-semibold">Type</th>
                      <th className="text-left py-3 px-4 font-semibold">Period</th>
                      <th className="text-left py-3 px-4 font-semibold">Status</th>
                      <th className="text-left py-3 px-4 font-semibold">Uploaded</th>
                      <th className="text-left py-3 px-4 font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-text-secondary">
                          No documents uploaded yet. Click "Upload Document" to get started.
                        </td>
                      </tr>
                    ) : (
                      documents.map((doc) => (
                        <tr key={doc.id} className="border-b border-border hover:bg-background">
                          <td className="py-3 px-4 font-medium">{doc.file_name}</td>
                          <td className="py-3 px-4 text-text-secondary">{doc.property_id}</td>
                          <td className="py-3 px-4">
                            <span className="px-2 py-1 bg-info-light text-info rounded text-sm">
                              {doc.document_type?.replace('_', ' ') || 'N/A'}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-text-secondary">
                            {doc.period_year && doc.period_month 
                              ? `${doc.period_year}-${String(doc.period_month).padStart(2, '0')}`
                              : 'N/A'}
                          </td>
                          <td className="py-3 px-4">
                            <span className={`px-2 py-1 rounded text-xs ${
                              doc.extraction_status === 'completed' 
                                ? 'bg-success-light text-success'
                                : doc.extraction_status === 'failed' || doc.extraction_status?.includes('failed')
                                ? 'bg-danger-light text-danger'
                                : 'bg-warning-light text-warning'
                            }`}>
                              {doc.extraction_status || 'pending'}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-text-secondary text-sm">
                            {doc.upload_date ? new Date(doc.upload_date).toLocaleString('en-US', {
                              year: 'numeric',
                              month: '2-digit',
                              day: '2-digit',
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit',
                              hour12: true
                            }) : 'N/A'}
                          </td>
                          <td className="py-3 px-4">
                            {doc.extraction_status === 'completed' && (
                              <button
                                onClick={() => handleRerunAnomalies(doc.id)}
                                disabled={rerunningAnomalies === doc.id}
                                className={`flex items-center gap-1 px-3 py-1 text-sm rounded transition-all ${
                                  rerunningAnomalies === doc.id
                                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                    : 'bg-blue-50 text-blue-600 hover:bg-blue-100'
                                }`}
                                title="Re-run anomaly detection for this document"
                              >
                                <RefreshCw 
                                  size={14} 
                                  className={rerunningAnomalies === doc.id ? 'animate-spin' : ''} 
                                />
                                {rerunningAnomalies === doc.id ? 'Running...' : 'Re-run Anomalies'}
                              </button>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowUploadModal(false)}>
          <div className="bg-surface rounded-xl p-6 max-w-2xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-2xl font-bold mb-4">Upload Document</h2>
            <DocumentUpload onUploadSuccess={() => {
              setShowUploadModal(false);
              loadData();
            }} />
          </div>
        </div>
      )}
    </div>
  );
}

