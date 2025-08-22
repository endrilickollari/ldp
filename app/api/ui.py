"""
UI Router - Serves the React front-end application
"""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os

router = APIRouter()

# Set up templates - check if build directory exists
build_dir = "ui/build"
if os.path.exists(build_dir):
    templates = Jinja2Templates(directory=build_dir)
else:
    templates = None

@router.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_react_app(request: Request, full_path: str):
    """
    Serve the React app and handle client-side routing.
    
    This catches all routes under /live and serves the React index.html,
    allowing the React Router to handle client-side navigation.
    """
    if templates is None:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>LDP UI - Build Required</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                    .container { max-width: 800px; margin: 0 auto; }
                    .error { background: #f8d7da; color: #721c24; padding: 20px; border-radius: 5px; }
                    .steps { background: #d1ecf1; color: #0c5460; padding: 20px; border-radius: 5px; margin-top: 20px; }
                    code { background: #f8f9fa; padding: 2px 4px; border-radius: 3px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🚀 LDP UI - Development Mode</h1>
                    <div class="error">
                        <h3>⚠️ React App Not Built</h3>
                        <p>The React application hasn't been built yet. To see the UI, you need to build it first.</p>
                    </div>
                    
                    <div class="steps">
                        <h3>📋 Quick Setup Steps:</h3>
                        <ol>
                            <li>Open a terminal and navigate to the project directory</li>
                            <li>Run: <code>cd ui</code></li>
                            <li>Run: <code>npm run build</code></li>
                            <li>Refresh this page</li>
                        </ol>
                        
                        <h4>🔄 Alternative: Development Mode</h4>
                        <p>For development with hot-reload:</p>
                        <ol>
                            <li>Run: <code>cd ui && npm start</code></li>
                            <li>Visit: <a href="http://localhost:3000">http://localhost:3000</a></li>
                        </ol>
                    </div>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                        <h4>🔗 API Endpoints Available:</h4>
                        <ul>
                            <li><a href="/docs">API Documentation (Swagger)</a></li>
                            <li><a href="/v1/auth/register">Authentication</a></li>
                            <li><a href="/v1/jobs">Job Processing</a></li>
                        </ul>
                    </div>
                </div>
            </body>
            </html>
            """,
            status_code=200
        )
    
    return templates.TemplateResponse("index.html", {"request": request})
