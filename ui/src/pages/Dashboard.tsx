import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import './Dashboard.css';

interface Job {
  id: string;
  filename: string;
  status: string;
  created_at: string;
  processing_type?: string;
  page_count?: number;
}

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [stats, setStats] = useState({
    total_jobs: 0,
    completed_jobs: 0,
    processing_jobs: 0,
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchJobs();
    fetchStats();
  }, []);

  const fetchJobs = async () => {
    try {
      const response = await fetch('/v1/jobs/my-jobs', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setJobs(data);
      }
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('/v1/jobs/stats', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
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

  return (
    <div className="dashboard">
      <div className="dashboard-container">
        <div className="dashboard-header">
          <h1>Welcome back, {user?.username}!</h1>
          <p>Manage your document processing jobs and view analytics.</p>
        </div>

        <div className="stats-section">
          <div className="stat-card">
            <div className="stat-value">{stats.total_jobs}</div>
            <div className="stat-label">Total Jobs</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.completed_jobs}</div>
            <div className="stat-label">Completed</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.processing_jobs}</div>
            <div className="stat-label">Processing</div>
          </div>
        </div>

        <div className="actions-section">
          <Link to="/upload" className="action-card primary">
            <div className="action-icon">📤</div>
            <div className="action-content">
              <h3>Upload Document</h3>
              <p>Process new documents with AI-powered analysis</p>
            </div>
          </Link>
          <Link to="/profile" className="action-card secondary">
            <div className="action-icon">👤</div>
            <div className="action-content">
              <h3>Profile Settings</h3>
              <p>Manage your account and preferences</p>
            </div>
          </Link>
        </div>

        <div className="jobs-section">
          <div className="section-header">
            <h2>Recent Jobs</h2>
            <Link to="/jobs" className="view-all-link">
              View All
            </Link>
          </div>

          {isLoading ? (
            <div className="loading">Loading your jobs...</div>
          ) : jobs.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📄</div>
              <h3>No jobs yet</h3>
              <p>Upload your first document to get started!</p>
              <Link to="/upload" className="cta-button">
                Upload Document
              </Link>
            </div>
          ) : (
            <div className="jobs-list">
              {jobs.slice(0, 5).map((job) => (
                <div key={job.id} className="job-item">
                  <div className="job-info">
                    <div className="job-filename">{job.filename}</div>
                    <div className="job-details">
                      {job.page_count && (
                        <span className="job-detail">{job.page_count} pages</span>
                      )}
                      <span className="job-detail">{formatDate(job.created_at)}</span>
                    </div>
                  </div>
                  <div className="job-status">
                    <span className={`status-badge ${getStatusColor(job.status)}`}>
                      {job.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
