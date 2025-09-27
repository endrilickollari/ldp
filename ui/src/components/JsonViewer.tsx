import React, { useState } from 'react';
import './JsonViewer.css';
import EditableTable from './EditableTable';
import './EditableTable.css';

interface JsonViewerProps {
  data: object;
}

const JsonViewer: React.FC<JsonViewerProps> = ({ data }) => {
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [isReviewMode, setIsReviewMode] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);

  const toggleKey = (key: string) => {
    setExpandedKeys((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const handleSave = (updatedData: object) => {
    console.log('Updated data:', updatedData);
    // Here you would typically send the data to a backend endpoint
    setIsReviewMode(false); // Exit review mode after saving
  };

  const expandAll = () => {
    const getAllKeys = (obj: any, prefix = 'root', level = 0): string[] => {
      let keys: string[] = [];
      if (typeof obj === 'object' && obj !== null) {
        const currentKey = `${prefix}-${level}`;
        if (level > 0) { // Don't include root level in expandedKeys since it's always expanded
          keys.push(currentKey);
        }
        Object.entries(obj).forEach(([key, value]) => {
          keys.push(...getAllKeys(value, `${currentKey}-${key}`, level + 1));
        });
      }
      return keys;
    };
    setExpandedKeys(getAllKeys(data));
  };

  const collapseAll = () => {
    setExpandedKeys([]);
  };

  const handleCopy = async () => {
    const jsonText = JSON.stringify(data, null, 2);
    
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(jsonText);
        setCopySuccess(true);
        setTimeout(() => setCopySuccess(false), 2000);
      } else {
        // Fallback for older browsers or non-secure contexts
        const textArea = document.createElement('textarea');
        textArea.value = jsonText;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);
        
        if (successful) {
          setCopySuccess(true);
          setTimeout(() => setCopySuccess(false), 2000);
        } else {
          throw new Error('Copy command failed');
        }
      }
    } catch (err) {
      console.error('Failed to copy: ', err);
      // Show an alert as last resort
      prompt('Copy this JSON manually:', jsonText);
    }
  };

  const renderValue = (value: any, key: string, level: number, isRoot = false): React.ReactNode => {
    const currentKey = `${key}-${level}`;
    const isExpanded = expandedKeys.includes(currentKey);
    const indent = '  '.repeat(level);

    if (typeof value === 'object' && value !== null) {
      const isArray = Array.isArray(value);
      const entries = Object.entries(value);

      if (entries.length === 0) {
        return <span className="json-bracket">{isArray ? '[]' : '{}'}</span>;
      }

      return (
        <div className="json-object">
          {!isRoot && (
            <span className="json-toggler" onClick={() => toggleKey(currentKey)}>
              {isExpanded ? '−' : '+'}
            </span>
          )}
          <span className="json-bracket">{isArray ? '[' : '{'}</span>
          {(isExpanded || isRoot) ? (
            <>
              {entries.map(([k, v], index) => (
                <div key={k} className="json-entry">
                  <span className="json-indent">{indent}  </span>
                  {!isArray && (
                    <>
                      <span className="json-key">"{k}"</span>
                      <span className="json-bracket">: </span>
                    </>
                  )}
                  {renderValue(v, `${currentKey}-${k}`, level + 1, false)}
                  {index < entries.length - 1 && <span className="json-bracket">,</span>}
                </div>
              ))}
              <div className="json-entry">
                <span className="json-indent">{indent}</span>
                <span className="json-bracket">{isArray ? ']' : '}'}</span>
              </div>
            </>
          ) : (
            <>
              <span className="json-placeholder" onClick={() => toggleKey(currentKey)}>
                ...
              </span>
              <span className="json-bracket">{isArray ? ']' : '}'}</span>
            </>
          )}
        </div>
      );
    } else {
      return <span className={`json-value-${typeof value}`}>{JSON.stringify(value)}</span>;
    }
  };

  return (
    <div className="json-viewer-container">
      {isReviewMode ? (
        <EditableTable data={data} onSave={handleSave} />
      ) : (
        <div className="json-viewer">
          {renderValue(data, 'root', 0, true)}
        </div>
      )}
      <div className="json-viewer-actions">
        <div className="json-viewer-controls">
          <button 
            onClick={expandAll}
            className="json-viewer-button expand-button"
          >
            Expand All
          </button>
          <button 
            onClick={collapseAll}
            className="json-viewer-button collapse-button"
          >
            Collapse All
          </button>
          <button 
            onClick={handleCopy}
            className="json-viewer-button copy-button"
          >
            {copySuccess ? 'Copied!' : 'Copy JSON'}
          </button>
        </div>
        <div className="json-viewer-main-actions">
          <button 
            onClick={() => alert('Data confirmed!')} 
            className="json-viewer-button confirm-button"
          >
            Confirm Data
          </button>
          <button 
            onClick={() => setIsReviewMode(!isReviewMode)} 
            className="json-viewer-button review-button"
          >
            {isReviewMode ? 'Cancel Review' : 'Review Data'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default JsonViewer;
