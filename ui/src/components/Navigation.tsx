import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import './Navigation.css';

const Navigation: React.FC = () => {
  const location = useLocation();
  const { user, logout } = useAuth();

  const isActive = (path: string) => {
    return location.pathname === path ? 'nav-link active' : 'nav-link';
  };

  return (
    <nav className="navigation">
      <div className="nav-container">
        <Link to="/" className="nav-brand">
          <span className="nav-brand-icon">🚀</span>
          LDP
        </Link>
        
        <div className="nav-links">
          {user ? (
            <>
              <Link to="/dashboard" className={isActive('/dashboard')}>
                Dashboard
              </Link>
              <Link to="/upload" className={isActive('/upload')}>
                Upload
              </Link>
              <Link to="/profile" className={isActive('/profile')}>
                Profile
              </Link>
              <button onClick={logout} className="nav-link logout-btn">
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/" className={isActive('/')}>
                Home
              </Link>
              <Link to="/login" className={isActive('/login')}>
                Login
              </Link>
              <Link to="/register" className={isActive('/register')}>
                Register
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
