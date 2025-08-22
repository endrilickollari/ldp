import React from 'react';
import { useAuth } from '../hooks/useAuth';
import './Profile.css';

const Profile: React.FC = () => {
  const { user, logout } = useAuth();

  if (!user) {
    return (
      <div className="profile-page">
        <div className="loading">Loading profile...</div>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="profile-container">
        <div className="profile-header">
          <div className="profile-avatar">
            <span className="avatar-text">
              {user.username.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="profile-info">
            <h1>{user.username}</h1>
            <p className="user-email">{user.email}</p>
            <span className="user-type-badge">{user.user_type.replace('_', ' ')}</span>
          </div>
        </div>

        <div className="profile-sections">
          <div className="profile-section">
            <h3>Account Information</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Username:</span>
                <span className="info-value">{user.username}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Email:</span>
                <span className="info-value">{user.email}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Account Type:</span>
                <span className="info-value">{user.user_type.replace('_', ' ')}</span>
              </div>
              {user.company_id && (
                <div className="info-item">
                  <span className="info-label">Company ID:</span>
                  <span className="info-value">{user.company_id}</span>
                </div>
              )}
            </div>
          </div>

          <div className="profile-section">
            <h3>Account Actions</h3>
            <div className="actions-list">
              <button className="action-button secondary">
                Change Password
              </button>
              <button className="action-button secondary">
                Update Email
              </button>
              <button className="action-button secondary">
                Download My Data
              </button>
            </div>
          </div>

          <div className="profile-section danger-zone">
            <h3>Danger Zone</h3>
            <p className="danger-warning">
              These actions cannot be undone. Please be careful.
            </p>
            <div className="actions-list">
              <button onClick={logout} className="action-button danger">
                Sign Out
              </button>
              <button className="action-button danger">
                Delete Account
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
