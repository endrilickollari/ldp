import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import './JobStatus.css';

interface JobData {
  id: string;
  filename: string;
  status: string;
  created_at: string;
  completed_at?: string;
  error_message?: string;
  result?: any;
  page_count?: number;
  processing_options?: {
    page_start?: number;
    page_end?: number;
    output_format: string;
  };
}

const JobStatus: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<JobData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchJobStatus = async () => {
      try {
        const response = await fetch(`/v1/jobs/${jobId}/status`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
        });

        if (!response.ok) {
          throw new Error('Failed to fetch job status');
        }

        const data = await response.json();
        setJob(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    if (jobId) {
      fetchJobStatus();
      const interval = setInterval(fetchJobStatus, 2000); // Poll every 2 seconds
      return () => clearInterval(interval);
    }
  }, [jobId]);

  const downloadResults = async () => {
    if (!job) return;

    try {
      const response = await fetch(`/v1/jobs/${job.id}/download`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to download results');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${job.filename}_results.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'status-completed';
      case 'processing':
        return 'status-processing';
      case 'failed':
        return 'status-failed';
      default:
        return 'status-pending';
    }
  };

  if (isLoading) {
    return (
      <div className="job-status-page">
        <div className="loading">Loading job status...</div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="job-status-page">
        <div className="error-state">
          <h2>Error</h2>
          <p>{error || 'Job not found'}</p>
          <Link to="/dashboard" className="back-button">
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="job-status-page">
      <div className="job-status-container">
        <div className="job-header">
          <div className="job-title">
            <h1>{job.filename}</h1>
            <span className={`status-badge ${getStatusColor(job.status)}`}>
              {job.status}
            </span>
          </div>
          <div className="job-actions">
            <Link to="/dashboard" className="back-button">
              ← Dashboard
            </Link>
            {job.status === 'completed' && (
              <button onClick={downloadResults} className="download-button">
                📥 Download Results
              </button>
            )}
          </div>
        </div>

        <div className="job-details-section">
          <h3>Job Details</h3>
          <div className="details-grid">
            <div className="detail-item">
              <span className="detail-label">Job ID:</span>
              <span className="detail-value">{job.id}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Created:</span>
              <span className="detail-value">{formatDate(job.created_at)}</span>
            </div>
            {job.completed_at && (
              <div className="detail-item">
                <span className="detail-label">Completed:</span>
                <span className="detail-value">{formatDate(job.completed_at)}</span>
              </div>
            )}
            {job.page_count && (
              <div className="detail-item">
                <span className="detail-label">Pages:</span>
                <span className="detail-value">{job.page_count}</span>
              </div>
            )}
          </div>
        </div>

        {job.processing_options && (
          <div className="processing-options-section">
            <h3>Processing Options</h3>
            <div className="details-grid">
              <div className="detail-item">
                <span className="detail-label">Output Format:</span>
                <span className="detail-value">
                  {job.processing_options.output_format === 'per_page' ? 'Per Page' : 'Combined'}
                </span>
              </div>
              {job.processing_options.page_start && (
                <div className="detail-item">
                  <span className="detail-label">Start Page:</span>
                  <span className="detail-value">{job.processing_options.page_start}</span>
                </div>
              )}
              {job.processing_options.page_end && (
                <div className="detail-item">
                  <span className="detail-label">End Page:</span>
                  <span className="detail-value">{job.processing_options.page_end}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {job.status === 'processing' && (
          <div className="processing-section">
            <div className="processing-spinner"></div>
            <p>Your document is being processed. This page will update automatically.</p>
          </div>
        )}

        {job.status === 'failed' && job.error_message && (
          <div className="error-section">
            <h3>Error Details</h3>
            <div className="error-message">
              {job.error_message}
            </div>
          </div>
        )}

        {job.status === 'completed' && job.result && (
          <div className="results-section">
            <h3>Processing Results</h3>
            <div className="results-preview">
              <pre>{JSON.stringify(job.result, null, 2)}</pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default JobStatus;
