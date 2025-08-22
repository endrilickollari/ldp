import React from 'react';
import { Link } from 'react-router-dom';
import './Home.css';

const Home: React.FC = () => {
  return (
    <div className="home">
      <div className="home-container">
        <div className="hero-section">
          <h1 className="hero-title">
            Intelligent Document Processing
          </h1>
          <p className="hero-subtitle">
            Transform your documents with AI-powered analysis. Upload, process, and extract insights from your PDFs with advanced multi-page processing capabilities.
          </p>
          <div className="hero-actions">
            <Link to="/register" className="cta-button primary">
              Get Started
            </Link>
            <Link to="/login" className="cta-button secondary">
              Sign In
            </Link>
          </div>
        </div>

        <div className="features-section">
          <h2 className="features-title">Key Features</h2>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">📄</div>
              <h3>Multi-Page Processing</h3>
              <p>Process specific page ranges or entire documents with per-page analysis and results.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🤖</div>
              <h3>AI-Powered Analysis</h3>
              <p>Advanced machine learning algorithms extract meaningful insights from your documents.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">⚡</div>
              <h3>Fast Processing</h3>
              <p>Efficient document processing with real-time status updates and job tracking.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🔒</div>
              <h3>Secure & Private</h3>
              <p>Your documents are processed securely with enterprise-grade security measures.</p>
            </div>
          </div>
        </div>

        <div className="stats-section">
          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-number">10K+</div>
              <div className="stat-label">Documents Processed</div>
            </div>
            <div className="stat-item">
              <div className="stat-number">99.9%</div>
              <div className="stat-label">Uptime</div>
            </div>
            <div className="stat-item">
              <div className="stat-number">50+</div>
              <div className="stat-label">Languages Supported</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;
