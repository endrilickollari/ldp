import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Upload.css';

interface UploadFormData {
  file: File | null;
  page_start: number | '';
  page_end: number | '';
  output_format: 'combined' | 'per_page';
}

const Upload: React.FC = () => {
  const [formData, setFormData] = useState<UploadFormData>({
    file: null,
    page_start: '',
    page_end: '',
    output_format: 'combined',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setFormData({ ...formData, file });
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: name === 'page_start' || name === 'page_end' 
        ? (value === '' ? '' : parseInt(value)) 
        : value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!formData.file) {
      setError('Please select a file to upload');
      return;
    }

    if (formData.file.type !== 'application/pdf') {
      setError('Please select a PDF file');
      return;
    }

    setIsLoading(true);

    try {
      const submitFormData = new FormData();
      submitFormData.append('file', formData.file);
      submitFormData.append('output_format', formData.output_format);
      
      if (formData.page_start !== '') {
        submitFormData.append('page_start', formData.page_start.toString());
      }
      
      if (formData.page_end !== '') {
        submitFormData.append('page_end', formData.page_end.toString());
      }

      const response = await fetch('/v1/jobs/process', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: submitFormData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const result = await response.json();
      navigate(`/job/${result.job_id}`);
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="upload-page">
      <div className="upload-container">
        <div className="upload-header">
          <h1>Upload Document</h1>
          <p>Upload your PDF document for AI-powered processing and analysis.</p>
        </div>

        <form onSubmit={handleSubmit} className="upload-form">
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <div className="form-section">
            <h3>Document Selection</h3>
            <div className="file-upload-area">
              <input
                type="file"
                id="file"
                accept=".pdf"
                onChange={handleFileChange}
                disabled={isLoading}
                className="file-input"
              />
              <label htmlFor="file" className="file-upload-label">
                {formData.file ? (
                  <div className="file-selected">
                    <span className="file-icon">📄</span>
                    <div className="file-info">
                      <div className="file-name">{formData.file.name}</div>
                      <div className="file-size">
                        {(formData.file.size / 1024 / 1024).toFixed(2)} MB
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="file-placeholder">
                    <span className="upload-icon">📤</span>
                    <div className="upload-text">
                      <div className="upload-title">Click to upload PDF</div>
                      <div className="upload-subtitle">or drag and drop</div>
                    </div>
                  </div>
                )}
              </label>
            </div>
          </div>

          <div className="form-section">
            <h3>Processing Options</h3>
            
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="page_start">Start Page (optional)</label>
                <input
                  type="number"
                  id="page_start"
                  name="page_start"
                  min="1"
                  value={formData.page_start}
                  onChange={handleInputChange}
                  disabled={isLoading}
                  placeholder="e.g., 1"
                />
              </div>

              <div className="form-group">
                <label htmlFor="page_end">End Page (optional)</label>
                <input
                  type="number"
                  id="page_end"
                  name="page_end"
                  min="1"
                  value={formData.page_end}
                  onChange={handleInputChange}
                  disabled={isLoading}
                  placeholder="e.g., 10"
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="output_format">Output Format</label>
              <select
                id="output_format"
                name="output_format"
                value={formData.output_format}
                onChange={handleInputChange}
                disabled={isLoading}
              >
                <option value="combined">Combined (all pages together)</option>
                <option value="per_page">Per Page (separate results)</option>
              </select>
              <div className="form-hint">
                {formData.output_format === 'combined' 
                  ? 'All pages will be processed together into a single result'
                  : 'Each page will be processed separately with individual results'
                }
              </div>
            </div>
          </div>

          <button
            type="submit"
            className="submit-button"
            disabled={isLoading || !formData.file}
          >
            {isLoading ? 'Processing...' : 'Start Processing'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Upload;
