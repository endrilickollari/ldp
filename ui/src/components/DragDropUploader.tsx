import React, { useState, useEffect, useCallback, useRef } from 'react';
import './DragDropUploader.css';

interface PlanLimits {
  max_file_size_mb: number;
  monthly_documents: number;
  plan_type: string;
  remaining_documents: number;
}

interface DragDropUploaderProps {
  file: File | null;
  onFileChange: (file: File | null) => void;
  disabled?: boolean;
  acceptedTypes?: string[];
  className?: string;
}

interface FileValidationResult {
  isValid: boolean;
  error?: string;
}

const DragDropUploader: React.FC<DragDropUploaderProps> = ({
  file,
  onFileChange,
  disabled = false,
  acceptedTypes = ['.pdf'],
  className = ''
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [planLimits, setPlanLimits] = useState<PlanLimits | null>(null);
  const [isLoadingLimits, setIsLoadingLimits] = useState(true);
  const [validationError, setValidationError] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

  // Fetch user plan limits
  useEffect(() => {
    fetchPlanLimits();
  }, []);

  const fetchPlanLimits = async () => {
    try {
      const response = await fetch('/v1/plans/current-plan', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setPlanLimits({
          max_file_size_mb: data.plan_details.max_file_size_mb,
          monthly_documents: data.plan_details.monthly_documents,
          plan_type: data.current_plan,
          remaining_documents: data.usage.remaining_documents,
        });
      }
    } catch (error) {
      console.error('Failed to fetch plan limits:', error);
    } finally {
      setIsLoadingLimits(false);
    }
  };

  const getPlanUpgradeMessage = useCallback(() => {
    if (planLimits?.plan_type === 'free') {
      return 'Upgrade to Premium for 25MB files and 100 documents/month.';
    } else if (planLimits?.plan_type === 'premium') {
      return 'Upgrade to Extra Premium for 100MB files and 500 documents/month.';
    }
    return 'Contact support for enterprise options.';
  }, [planLimits?.plan_type]);

  const validateFile = useCallback((file: File): FileValidationResult => {
    if (!planLimits) {
      return { isValid: false, error: 'Loading plan information...' };
    }

    // Check file type
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!acceptedTypes.includes(fileExtension)) {
      return { 
        isValid: false, 
        error: `File type not supported. Accepted types: ${acceptedTypes.join(', ')}` 
      };
    }

    // Check file size
    const fileSizeMB = file.size / (1024 * 1024);
    if (fileSizeMB > planLimits.max_file_size_mb) {
      return {
        isValid: false,
        error: `File size (${fileSizeMB.toFixed(2)}MB) exceeds your plan limit of ${planLimits.max_file_size_mb}MB. ${getPlanUpgradeMessage()}`
      };
    }

    // Check remaining documents
    if (planLimits.remaining_documents <= 0) {
      return {
        isValid: false,
        error: `You've reached your monthly document limit of ${planLimits.monthly_documents}. ${getPlanUpgradeMessage()}`
      };
    }

    return { isValid: true };
  }, [planLimits, acceptedTypes, getPlanUpgradeMessage]);

  const handleFileSelect = useCallback((selectedFile: File) => {
    const validation = validateFile(selectedFile);
    
    if (!validation.isValid) {
      setValidationError(validation.error || 'File validation failed');
      onFileChange(null);
      return;
    }

    setValidationError('');
    onFileChange(selectedFile);
  }, [validateFile, onFileChange]);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  };

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    dragCounterRef.current++;
    if (e.dataTransfer.types.includes('Files')) {
      setIsDragOver(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) {
      setIsDragOver(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    setIsDragOver(false);
    dragCounterRef.current = 0;

    if (disabled) return;

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [disabled, handleFileSelect]);

  const handleClick = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleRemoveFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setValidationError('');
    onFileChange(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes: number): string => {
    const mb = bytes / (1024 * 1024);
    return mb >= 1 ? `${mb.toFixed(2)} MB` : `${(bytes / 1024).toFixed(0)} KB`;
  };

  const getPlanBadgeClass = () => {
    switch (planLimits?.plan_type) {
      case 'free': return 'plan-badge-free';
      case 'premium': return 'plan-badge-premium';
      case 'extra_premium': return 'plan-badge-enterprise';
      default: return 'plan-badge-free';
    }
  };

  const getPlanDisplayName = () => {
    switch (planLimits?.plan_type) {
      case 'free': return 'Free';
      case 'premium': return 'Premium';
      case 'extra_premium': return 'Extra Premium';
      default: return 'Unknown';
    }
  };

  return (
    <div className={`drag-drop-uploader ${className}`}>
      {/* Plan Information */}
      {!isLoadingLimits && planLimits && (
        <div className="plan-info">
          <div className={`plan-badge ${getPlanBadgeClass()}`}>
            {getPlanDisplayName()} Plan
          </div>
          <div className="plan-limits">
            <span className="limit-item">
              📁 Max file: {planLimits.max_file_size_mb}MB
            </span>
            <span className="limit-item">
              📊 Remaining: {planLimits.remaining_documents}/{planLimits.monthly_documents} docs
            </span>
          </div>
        </div>
      )}

      {/* Upload Area */}
      <div
        className={`upload-zone ${isDragOver ? 'drag-over' : ''} ${disabled ? 'disabled' : ''} ${file ? 'has-file' : ''}`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={acceptedTypes.join(',')}
          onChange={handleFileInputChange}
          disabled={disabled}
          className="file-input-hidden"
        />

        {file ? (
          // File Selected State
          <div className="file-selected">
            <div className="file-icon">📄</div>
            <div className="file-details">
              <div className="file-name">{file.name}</div>
              <div className="file-meta">
                <span className="file-size">{formatFileSize(file.size)}</span>
                <span className="file-type">{file.type || 'Unknown type'}</span>
              </div>
            </div>
            <button
              type="button"
              onClick={handleRemoveFile}
              className="remove-file-btn"
              disabled={disabled}
            >
              ✕
            </button>
          </div>
        ) : (
          // Empty State
          <div className="upload-placeholder">
            <div className="upload-icon">
              {isDragOver ? '📥' : '📤'}
            </div>
            <div className="upload-content">
              <h3 className="upload-title">
                {isDragOver ? 'Drop file here' : 'Drag & drop your file'}
              </h3>
              <p className="upload-subtitle">
                or <span className="upload-link">click to browse</span>
              </p>
              <div className="upload-formats">
                Supported formats: {acceptedTypes.join(', ')}
              </div>
              {planLimits && (
                <div className="upload-limit">
                  Max size: {planLimits.max_file_size_mb}MB
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Validation Error */}
      {validationError && (
        <div className="validation-error">
          <span className="error-icon">⚠️</span>
          <span className="error-text">{validationError}</span>
        </div>
      )}

      {/* Loading State */}
      {isLoadingLimits && (
        <div className="loading-limits">
          <span className="loading-spinner">⏳</span>
          <span>Loading plan information...</span>
        </div>
      )}
    </div>
  );
};

export default DragDropUploader;