import React, { useState, useEffect, useCallback, useRef, forwardRef, useImperativeHandle } from 'react';
import './JobQueueMonitor.css';

interface JobQueueItem {
  job_id: string;
  filename: string;
  status: 'queued' | 'pending' | 'processing' | 'completed' | 'failed';
  stage?: string;
  progress?: number;
  created_at: string;
  completed_at?: string;
  processing_time?: number;
  error_message?: string;
}

interface JobQueueMonitorProps {
  onJobComplete?: (jobId: string) => void;
  maxDisplayJobs?: number;
}

export interface JobQueueMonitorRef {
  addJob: (jobId: string, filename: string) => void;
}

const JobQueueMonitor = forwardRef<JobQueueMonitorRef, JobQueueMonitorProps>(({ 
  onJobComplete, 
  maxDisplayJobs = 10 
}, ref) => {
  const [jobs, setJobs] = useState<JobQueueItem[]>([]);
  const [isPolling, setIsPolling] = useState(false);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch job status from API
  const fetchJobStatus = useCallback(async (jobId: string): Promise<JobQueueItem | null> => {
    try {
      const response = await fetch(`/v1/jobs/${jobId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          return null; // Job not found, remove from queue
        }
        throw new Error(`Failed to fetch job status: ${response.status}`);
      }

      const data = await response.json();
      
      // Map API response to our interface
      const job: JobQueueItem = {
        job_id: jobId,
        filename: data.filename || 'Unknown',
        status: mapApiStatus(data.status),
        stage: data.stage,
        progress: data.progress,
        created_at: data.created_at || new Date().toISOString(),
        completed_at: data.completed_at,
        processing_time: data.processing_time,
        error_message: data.error_message || (data.status === 'FAILURE' ? data.result : undefined),
      };

      return job;
    } catch (error) {
      console.error(`Error fetching job ${jobId}:`, error);
      return null;
    }
  }, []);

  // Map API status to our standardized status
  const mapApiStatus = (apiStatus: string): JobQueueItem['status'] => {
    switch (apiStatus?.toUpperCase()) {
      case 'SUCCESS':
      case 'COMPLETED':
        return 'completed';
      case 'FAILURE':
      case 'FAILED':
        return 'failed';
      case 'PENDING':
        return 'pending';
      case 'STARTED':
      case 'PROGRESS':
      case 'PROCESSING':
        return 'processing';
      case 'QUEUED':
      default:
        return 'queued';
    }
  };

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // Update all jobs in the queue
  const updateAllJobs = useCallback(async () => {
    const activeJobs = jobs.filter(job => 
      job.status === 'queued' || 
      job.status === 'pending' || 
      job.status === 'processing'
    );

    if (activeJobs.length === 0) {
      stopPolling();
      return;
    }

    const updates = await Promise.allSettled(
      activeJobs.map(job => fetchJobStatus(job.job_id))
    );

    setJobs(prevJobs => {
      const updatedJobs = [...prevJobs];
      
      updates.forEach((result, index) => {
        const jobId = activeJobs[index].job_id;
        const jobIndex = updatedJobs.findIndex(j => j.job_id === jobId);
        
        if (result.status === 'fulfilled' && result.value && jobIndex !== -1) {
          const updatedJob = result.value;
          updatedJobs[jobIndex] = updatedJob;
          
          // Notify when job completes
          if ((updatedJob.status === 'completed' || updatedJob.status === 'failed') && 
              prevJobs[jobIndex].status !== updatedJob.status) {
            onJobComplete?.(updatedJob.job_id);
          }
        } else if (result.status === 'fulfilled' && !result.value && jobIndex !== -1) {
          // Job not found, remove from queue
          updatedJobs.splice(jobIndex, 1);
        }
      });
      
      return updatedJobs;
    });
  }, [jobs, onJobComplete, fetchJobStatus, stopPolling]);

  // Start polling for job updates
  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) return;
    
    setIsPolling(true);
    pollIntervalRef.current = setInterval(updateAllJobs, 2000); // Poll every 2 seconds
  }, [updateAllJobs]);

  // Start monitoring a new job
  const addJobToQueue = useCallback((jobId: string, filename: string) => {
    const newJob: JobQueueItem = {
      job_id: jobId,
      filename,
      status: 'queued',
      created_at: new Date().toISOString(),
    };
    
    setJobs(prev => {
      const filtered = prev.filter(job => job.job_id !== jobId);
      return [newJob, ...filtered].slice(0, maxDisplayJobs);
    });

    // Start polling if not already running
    if (!isPolling) {
      startPolling();
    }
  }, [maxDisplayJobs, isPolling, startPolling]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Auto-start polling when jobs are added
  useEffect(() => {
    const hasActiveJobs = jobs.some(job => 
      job.status === 'queued' || 
      job.status === 'pending' || 
      job.status === 'processing'
    );

    if (hasActiveJobs && !isPolling) {
      startPolling();
    } else if (!hasActiveJobs && isPolling) {
      stopPolling();
    }
  }, [jobs, isPolling, startPolling, stopPolling]);

  // Clear completed job from queue
  const clearJob = (jobId: string) => {
    setJobs(prev => prev.filter(job => job.job_id !== jobId));
  };

  // Clear all completed/failed jobs
  const clearCompletedJobs = () => {
    setJobs(prev => prev.filter(job => 
      job.status !== 'completed' && job.status !== 'failed'
    ));
  };

  // Get status display info
  const getStatusInfo = (job: JobQueueItem) => {
    switch (job.status) {
      case 'queued':
        return { color: 'status-queued', icon: '⏳', text: 'Queued' };
      case 'pending':
        return { color: 'status-pending', icon: '⏳', text: 'Pending' };
      case 'processing':
        return { color: 'status-processing', icon: '⚙️', text: getProcessingText(job) };
      case 'completed':
        return { color: 'status-completed', icon: '✅', text: 'Success' };
      case 'failed':
        return { color: 'status-failed', icon: '❌', text: 'Failed' };
      default:
        return { color: 'status-unknown', icon: '❓', text: job.status };
    }
  };

  // Get processing stage text
  const getProcessingText = (job: JobQueueItem): string => {
    if (job.stage) {
      switch (job.stage.toLowerCase()) {
        case 'parsing':
          return 'Parsing';
        case 'analyzing':
        case 'analyzing with gemini':
          return 'Analyzing with Gemini';
        case 'completed':
        case 'complete':
          return 'Completing';
        default:
          return job.stage;
      }
    }
    return 'Processing';
  };

  // Format processing time
  const formatProcessingTime = (seconds?: number): string => {
    if (!seconds) return '';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(1)}s`;
  };

  // Format relative time
  const formatRelativeTime = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.abs(now.getTime() - date.getTime()) / 1000;

    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  // Expose addJobToQueue method for parent components
  useImperativeHandle(ref, () => ({
    addJob: addJobToQueue,
  }), [addJobToQueue]);

  if (jobs.length === 0) {
    return (
      <div className="job-queue-monitor empty">
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <h3>No Active Jobs</h3>
          <p>Upload a document to start monitoring processing status</p>
        </div>
      </div>
    );
  }

  return (
    <div className="job-queue-monitor">
      <div className="queue-header">
        <h3>Job Processing Queue</h3>
        <div className="queue-actions">
          {jobs.some(job => job.status === 'completed' || job.status === 'failed') && (
            <button onClick={clearCompletedJobs} className="clear-btn">
              Clear Completed
            </button>
          )}
          <div className="polling-indicator">
            {isPolling && <span className="polling-dot">●</span>}
            <span className="job-count">{jobs.length} job{jobs.length !== 1 ? 's' : ''}</span>
          </div>
        </div>
      </div>

      <div className="job-queue-list">
        {jobs.map((job) => {
          const statusInfo = getStatusInfo(job);
          return (
            <div key={job.job_id} className={`job-queue-item ${statusInfo.color}`}>
              <div className="job-main-info">
                <div className="job-status-icon">{statusInfo.icon}</div>
                <div className="job-details">
                  <div className="job-filename">{job.filename}</div>
                  <div className="job-meta">
                    <span className="job-id">ID: {job.job_id.slice(0, 8)}...</span>
                    <span className="job-time">{formatRelativeTime(job.created_at)}</span>
                  </div>
                </div>
                <div className="job-status-info">
                  <div className="status-text">{statusInfo.text}</div>
                  {job.processing_time && (
                    <div className="processing-time">
                      {formatProcessingTime(job.processing_time)}
                    </div>
                  )}
                </div>
              </div>

              {/* Progress Bar for Processing Jobs */}
              {job.status === 'processing' && job.progress !== undefined && (
                <div className="progress-section">
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${Math.max(job.progress, 5)}%` }}
                    ></div>
                  </div>
                  <div className="progress-text">{job.progress}%</div>
                </div>
              )}

              {/* Error Message */}
              {job.status === 'failed' && job.error_message && (
                <div className="error-section">
                  <div className="error-message">{job.error_message}</div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="job-actions">
                {(job.status === 'completed' || job.status === 'failed') && (
                  <button 
                    onClick={() => clearJob(job.job_id)} 
                    className="action-btn clear-job-btn"
                    title="Remove from queue"
                  >
                    ✕
                  </button>
                )}
                <button 
                  onClick={() => window.open(`/live/job/${job.job_id}`, '_blank')} 
                  className="action-btn view-btn"
                  title="View job details"
                >
                  👁️
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});

JobQueueMonitor.displayName = 'JobQueueMonitor';

export default JobQueueMonitor;