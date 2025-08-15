# 🔐 Authentication & User Plans Guide

## Overview

The Document Processing API now includes a comprehensive authentication system with user plans, JWT tokens, and API key management. This guide covers all authentication features and usage.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python init_db.py
```

### 3. Start the Server
```bash
uvicorn app.main:app --reload
```

## 📋 User Plans

### Free Plan - $0/month
- ✅ 10 documents per month
- ✅ 5MB max file size
- ✅ Community support
- ✅ Standard processing speed
- ✅ Basic document types (PDF, Excel, Images)

### Premium Plan - $29.99/month
- ✅ 100 documents per month
- ✅ 25MB max file size
- ✅ Priority processing queue
- ✅ Email support
- ✅ All document types supported
- ✅ Advanced AI analysis
- ✅ API access

### Extra Premium Plan - $99.99/month
- ✅ 500 documents per month
- ✅ 100MB max file size
- ✅ Highest priority processing
- ✅ Phone + Email support
- ✅ All document types supported
- ✅ Advanced AI analysis
- ✅ Full API access
- ✅ Custom integrations support
- ✅ Dedicated account manager

## 🔑 Authentication Methods

### 1. JWT Tokens (Recommended for web apps)
- Short-lived tokens (configurable expiry)
- Secure and stateless
- Includes user context and plan information

### 2. API Keys (Recommended for server-to-server)
- Long-lived credentials
- Easy to revoke
- Tracks usage per key

## 📚 API Endpoints

### Authentication Endpoints

#### Register User
```http
POST /v1/auth/register
Content-Type: application/json

{
    "email": "user@example.com",
    "username": "username",
    "full_name": "John Doe",
    "password": "securepassword"
}
```

#### Login User
```http
POST /v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword
```

Response:
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
        "id": 1,
        "email": "user@example.com",
        "username": "username",
        "plan_type": "free"
    }
}
```

#### Get User Profile
```http
GET /v1/auth/me
Authorization: Bearer <jwt_token>
```

#### Create API Key
```http
POST /v1/auth/api-keys
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
    "key_name": "My API Key"
}
```

Response:
```json
{
    "id": 1,
    "key_name": "My API Key",
    "api_key": "ldp_abc123...",
    "is_active": true,
    "created_at": "2025-01-01T00:00:00Z"
}
```

### Plans & Usage Endpoints

#### Get Available Plans
```http
GET /v1/plans/plans
```

#### Get Current Plan & Usage
```http
GET /v1/plans/current-plan
Authorization: Bearer <jwt_token>
```

#### Get Usage Statistics
```http
GET /v1/plans/usage
Authorization: Bearer <jwt_token>
```

Response:
```json
{
    "documents_processed": 45,
    "current_month_usage": 8,
    "remaining_documents": 2,
    "plan_limit": 10
}
```

### Document Processing (Protected)

#### Process Document
```http
POST /v1/jobs
Authorization: Bearer <jwt_token_or_api_key>
Content-Type: multipart/form-data

file=@document.pdf
```

## 🛡️ Security Features

### Password Security
- Bcrypt hashing with salt
- Strong password requirements (implement as needed)
- Secure password storage

### JWT Tokens
- HS256 algorithm
- Configurable expiry time
- Includes user and plan context
- Stateless authentication

### API Keys
- Cryptographically secure generation
- Per-user key limits (max 5 active keys)
- Usage tracking per key
- Easy revocation

### Rate Limiting
- Plan-based document limits
- File size restrictions per plan
- Monthly usage tracking
- Real-time usage validation

## 🔄 Usage Flow Example

### 1. Using JWT Tokens (Web Applications)

```python
import requests

# 1. Register or login to get token
login_data = {
    "username": "user@example.com",
    "password": "password"
}
response = requests.post("http://localhost:8000/v1/auth/login", data=login_data)
token = response.json()["access_token"]

# 2. Use token for authenticated requests
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8000/v1/auth/me", headers=headers)
```

### 2. Using API Keys (Server Integration)

```python
import requests

# 1. Create API key through web interface or JWT token
headers = {"Authorization": "Bearer <jwt_token>"}
api_key_data = {"key_name": "Production API Key"}
response = requests.post("http://localhost:8000/v1/auth/api-keys", 
                        json=api_key_data, headers=headers)
api_key = response.json()["api_key"]

# 2. Use API key for document processing
headers = {"Authorization": f"Bearer {api_key}"}
files = {"file": open("document.pdf", "rb")}
response = requests.post("http://localhost:8000/v1/jobs", 
                        files=files, headers=headers)
```

## 📊 Usage Tracking & Analytics

### Automatic Usage Logging
- Every API call is logged with:
  - User ID and API key used
  - Document filename and size
  - Processing time and token usage
  - Success/failure status
  - Timestamp

### Usage Enforcement
- Real-time plan limit checking
- File size validation
- Monthly usage tracking
- Automatic blocking when limits exceeded

### Usage Statistics
```json
{
    "documents_processed": 156,
    "current_month_usage": 23,
    "remaining_documents": 77,
    "plan_limit": 100,
    "success_rate": 98.5,
    "average_processing_time": 4.2
}
```

## ⚙️ Configuration

### Environment Variables
```env
# JWT Configuration
SECRET_KEY="your-secret-key-change-this-in-production"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database
DATABASE_URL="sqlite:///./app.db"

# Google AI
GOOGLE_API_KEY="your-google-api-key"
```

### Plan Configuration
Plans are configured in `app/services/user_service.py`. You can modify:
- Monthly document limits
- File size limits
- Processing priorities
- Support levels
- Pricing

## 🚀 Deployment Considerations

### Production Security
1. **Change the SECRET_KEY** to a long, random string
2. **Use HTTPS** for all API communications
3. **Set up CORS** properly for web applications
4. **Configure rate limiting** at the reverse proxy level
5. **Use PostgreSQL** instead of SQLite for production

### Database Migration
To migrate from SQLite to PostgreSQL:
1. Update `DATABASE_URL` in environment
2. Install PostgreSQL adapter: `pip install psycopg2-binary`
3. Run database initialization: `python init_db.py`

### Monitoring & Logging
- Set up proper logging for authentication events
- Monitor usage patterns and potential abuse
- Track API key usage and billing metrics
- Set up alerts for unusual activity

## 🧪 Testing

### Run Authentication Tests
```bash
python test_auth.py
```

### Manual Testing
1. Start the API server
2. Visit http://localhost:8000/docs for interactive API documentation
3. Test registration, login, and authenticated endpoints

## 🔄 Plan Upgrade Flow

Currently, plan upgrades are simulated. For production:

1. **Integrate Payment Processing**:
   - Stripe, PayPal, or other payment processors
   - Webhook handling for payment events
   - Subscription management

2. **Plan Change Logic**:
   - Immediate upgrades
   - Prorated billing
   - Downgrade handling

3. **Billing Management**:
   - Invoice generation
   - Payment tracking
   - Dunning management

## 📞 Support & Troubleshooting

### Common Issues

**"Could not validate credentials"**
- Check token expiry
- Verify token format (Bearer <token>)
- Ensure SECRET_KEY matches

**"Monthly limit exceeded"**
- Check current usage with `/v1/plans/usage`
- Upgrade plan or wait for next month
- Contact support for emergency increases

**"File size exceeds limit"**
- Check file size against plan limits
- Compress files if possible
- Upgrade to higher plan

### Error Codes
- `401`: Unauthorized (invalid/expired token)
- `403`: Forbidden (insufficient permissions)
- `429`: Too Many Requests (rate limited)
- `400`: Bad Request (validation errors)

## 🛠️ Development

### Adding New Plans
1. Update `PlanType` enum in `app/models/user.py`
2. Add plan configuration in `UserService.get_plan_limits()`
3. Update plan display in `app/api/plans.py`
4. Run database migration if needed

### Custom Authentication
Extend the authentication system by:
1. Adding OAuth2 providers (Google, GitHub, etc.)
2. Implementing MFA (Multi-Factor Authentication)
3. Adding role-based permissions
4. Custom user fields

This authentication system provides a solid foundation for a production-ready document processing API with proper user management, billing, and security.
