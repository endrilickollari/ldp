import React, { useState, useEffect } from 'react';
import './EditableTable.css';

interface EditableTableProps {
  data: object;
  onSave: (updatedData: object) => void;
}

const EditableTable: React.FC<EditableTableProps> = ({ data, onSave }) => {
  const [editedData, setEditedData] = useState<any>({});

  useEffect(() => {
    // Flatten the JSON data for table display
    const flattenObject = (obj: any, prefix = '') => {
      return Object.keys(obj).reduce((acc, k) => {
        const pre = prefix.length ? prefix + '.' : '';
        if (typeof obj[k] === 'object' && obj[k] !== null && !Array.isArray(obj[k])) {
          Object.assign(acc, flattenObject(obj[k], pre + k));
        } else {
          acc[pre + k] = obj[k];
        }
        return acc;
      }, {} as any);
    };
    setEditedData(flattenObject(data));
  }, [data]);

  const handleInputChange = (key: string, value: string) => {
    setEditedData((prev: any) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    // Reconstruct the nested object from the flattened data
    const unflattenObject = (obj: any) => {
      return Object.keys(obj).reduce((acc, k) => {
        const keys = k.split('.');
        keys.reduce((a, c, i) => {
          if (i === keys.length - 1) {
            a[c] = obj[k];
          } else {
            a[c] = a[c] || {};
          }
          return a[c];
        }, acc);
        return acc;
      }, {} as any);
    };
    onSave(unflattenObject(editedData));
    alert('Data saved! (Check console for the updated object)');
  };

  return (
    <div className="editable-table-container">
      <table className="editable-table">
        <thead>
          <tr>
            <th>Key</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(editedData).map(([key, value]) => (
            <tr key={key}>
              <td>{key}</td>
              <td>
                {Array.isArray(value) ? (
                  <textarea
                    value={JSON.stringify(value, null, 2)}
                    onChange={(e) => handleInputChange(key, e.target.value)}
                    className="editable-textarea"
                  />
                ) : (
                  <input
                    type="text"
                    value={value as any}
                    onChange={(e) => handleInputChange(key, e.target.value)}
                    className="editable-input"
                  />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="editable-table-actions">
        <button onClick={handleSave} className="json-viewer-button save-button">
          Save Data
        </button>
      </div>
    </div>
  );
};

export default EditableTable;
