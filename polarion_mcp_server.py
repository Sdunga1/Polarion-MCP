import json
import os
import time
import webbrowser
from typing import Dict, List, Optional
from loguru import logger
from mcp.server.fastmcp import FastMCP
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Create an MCP server
mcp = FastMCP("Polarion-MCP-Server")

# Create FastAPI app for HTTP transport
app = FastAPI(title="Polarion MCP Server", version="1.0.0")

# HTTP endpoints for the MCP server
@app.get("/")
async def root():
    return {"message": "Polarion MCP Server is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "polarion-mcp"}

@app.post("/open_polarion_login")
async def http_open_polarion_login():
    """HTTP endpoint for opening Polarion login page"""
    try:
        result = polarion_client.open_login_page()
        return JSONResponse(content=json.loads(result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set_polarion_token")
async def http_set_polarion_token(token: str):
    """HTTP endpoint for setting Polarion token"""
    try:
        result = polarion_client.set_token_manually(token)
        return JSONResponse(content=json.loads(result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_polarion_requirements")
async def http_get_polarion_requirements(limit: int = 5):
    """HTTP endpoint for getting Polarion requirements"""
    try:
        requirements = polarion_client.get_requirements(limit)
        if requirements:
            return {
                "status": "success",
                "message": f"Successfully fetched {len(requirements)} requirements",
                "requirements": requirements,
                "count": len(requirements)
            }
        else:
            return {
                "status": "error",
                "message": "Failed to fetch requirements. Please check authentication and token."
            }
    except Exception as e:
        error_message = str(e)
        if "down" in error_message.lower() or "unavailable" in error_message.lower():
            return {
                "status": "error",
                "message": error_message,
                "note": "The Polarion service appears to be down. Please try again later when the service is restored."
            }
        else:
            raise HTTPException(status_code=500, detail=error_message)

@app.get("/check_polarion_status")
async def http_check_polarion_status():
    """HTTP endpoint for checking Polarion status"""
    try:
        status = {
            "authenticated": polarion_client.is_authenticated,
            "has_token": bool(polarion_client.token or polarion_client.load_token()),
            "token_saved": os.path.exists(TOKEN_FILE)
        }
        return {"status": "success", "polarion_status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/check_polarion_connectivity")
async def http_check_polarion_connectivity():
    """HTTP endpoint for checking if Polarion service is reachable"""
    try:
        response = polarion_client.session.get(POLARION_BASE_URL, timeout=5)
        return {
            "status": "success",
            "message": f"Polarion service is reachable (HTTP {response.status_code})",
            "polarion_url": POLARION_BASE_URL,
            "response_code": response.status_code
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": "Cannot connect to Polarion service",
            "polarion_url": POLARION_BASE_URL,
            "note": "The Polarion instance at http://polarion.atoms.tech/polarion appears to be down or unreachable."
        }
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "message": "Connection to Polarion timed out",
            "polarion_url": POLARION_BASE_URL,
            "note": "The Polarion service is not responding within the expected time."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error checking Polarion connectivity: {str(e)}",
            "polarion_url": POLARION_BASE_URL
        }

@app.get("/get_polarion_user/{user_id}")
async def http_get_polarion_user(user_id: str):
    """HTTP endpoint for getting Polarion user information"""
    try:
        user_data = polarion_client.get_user(user_id)
        if user_data:
            return {
                "status": "success",
                "message": f"Successfully fetched user information for: {user_id}",
                "user": user_data
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to fetch user information for: {user_id}. User may not exist or you may not have permission to access this user."
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Configuration
POLARION_BASE_URL = "http://polarion.atoms.tech/polarion"
LOGIN_URL = POLARION_BASE_URL  # Use the main URL, not a specific login path
TOKEN_PAGE_URL = f"{POLARION_BASE_URL}/#/user_tokens?id=admin"
TOKEN_FILE = "polarion_token.json"

class PolarionClient:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.is_authenticated = False
    
    def open_login_page(self) -> str:
        """Open Polarion login page in user's browser for manual authentication"""
        try:
            # Open the login page in the default browser
            webbrowser.open(LOGIN_URL)
            
            return json.dumps({
                "status": "success",
                "message": f"Polarion login page opened in your browser: {LOGIN_URL}",
                "instructions": [
                    "1. Complete the login form in your browser",
                    "2. After successful login, navigate to: " + TOKEN_PAGE_URL,
                    "3. Generate a new token manually",
                    "4. Copy the token and use it with the 'set_polarion_token' command"
                ],
                "login_url": LOGIN_URL,
                "token_page_url": TOKEN_PAGE_URL,
                "note": "If you get an 'Internal server error', try refreshing the page or check if the Polarion instance is accessible"
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to open login page: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Failed to open login page: {e}",
                "manual_url": LOGIN_URL
            }, indent=2)
    
    def set_token_manually(self, token: str) -> str:
        """Set token manually (after user generates it in browser)"""
        try:
            self.token = token
            self.save_token(token)
            self.is_authenticated = True
            return json.dumps({
                "status": "success",
                "message": "Token set successfully. Please test it by fetching requirements.",
                "token_preview": f"{token[:10]}...{token[-10:]}"
            }, indent=2)
        except Exception as e:
            logger.error(f"Failed to set token: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Failed to set token: {e}"
            }, indent=2)
    

    
    def save_token(self, token: str):
        """Save token to file"""
        try:
            token_data = {"token": token, "generated_at": time.time()}
            with open(TOKEN_FILE, 'w') as f:
                json.dump(token_data, f)
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
    
    def load_token(self) -> Optional[str]:
        """Load token from file"""
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'r') as f:
                    token_data = json.load(f)
                    return token_data.get("token")
        except Exception as e:
            logger.error(f"Failed to load token: {e}")
        return None
    
    def get_requirements(self, limit: int = 5) -> List[Dict]:
        """Fetch requirements from Polarion REST API"""
        try:
            # Load token if not already loaded
            if not self.token:
                self.token = self.load_token()
            
            if not self.token:
                raise Exception("No token available. Please generate a token first.")
            
            # API endpoint
            api_url = f"{POLARION_BASE_URL}/rest/v1/projects/drivepilot/workitems"
            params = {
                'query': 'type:systemrequirement OR type:softwarerequirement',
                'fields[workitems]': 'id,title,type,description'
            }
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            response = self.session.get(api_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                requirements = (data.get('data') or [])[:limit]
                logger.info(f"Fetched {len(requirements)} requirements")
                return requirements
            elif response.status_code == 503 or response.status_code == 502:
                raise Exception(f"Polarion service is currently unavailable (HTTP {response.status_code}). Please try again later.")
            elif response.status_code == 404:
                raise Exception(f"Polarion endpoint not found (HTTP 404). The service might be down or the URL has changed.")
            else:
                raise Exception(f"API error: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to Polarion - service might be down")
            raise Exception("Cannot connect to Polarion service. The instance at http://polarion.atoms.tech/polarion might be down or unreachable.")
        except requests.exceptions.Timeout:
            logger.error("Request to Polarion timed out")
            raise Exception("Request to Polarion timed out. The service might be overloaded or down.")
        except Exception as e:
            logger.error(f"Failed to fetch requirements: {e}")
            raise e

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Fetch user information from Polarion REST API"""
        try:
            # Load token if not already loaded
            if not self.token:
                self.token = self.load_token()
            
            if not self.token:
                raise Exception("No token available. Please generate a token first.")
            
            # API endpoint for getting user information
            api_url = f"{POLARION_BASE_URL}/rest/v1/users/{user_id}"
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            response = self.session.get(api_url, headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"Fetched user information for: {user_id}")
                return user_data
            elif response.status_code == 404:
                logger.warning(f"User not found: {user_id}")
                return None
            else:
                raise Exception(f"API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to fetch user information: {e}")
            return None

# Global Polarion client instance
polarion_client = PolarionClient()

@mcp.tool()
def open_polarion_login() -> str:
    """Open Polarion login page in browser for manual authentication (like Google Sheets)"""
    logger.info("Opening Polarion login page for manual authentication")
    return polarion_client.open_login_page()

@mcp.tool()
def set_polarion_token(token: str) -> str:
    """Set Polarion access token manually (after generating it in browser)"""
    logger.info("Setting Polarion token manually")
    return polarion_client.set_token_manually(token)



@mcp.tool()
def get_polarion_requirements(limit: int = 5) -> str:
    """Fetch requirements from Polarion instance"""
    logger.info(f"Fetching {limit} requirements from Polarion")
    
    requirements = polarion_client.get_requirements(limit)
    
    if requirements:
        return json.dumps({
            "status": "success",
            "message": f"Successfully fetched {len(requirements)} requirements",
            "requirements": requirements,
            "count": len(requirements)
        }, indent=2)
    else:
        return json.dumps({
            "status": "error",
            "message": "Failed to fetch requirements. Please check authentication and token."
        }, indent=2)

@mcp.tool()
def check_polarion_status() -> str:
    """Check the current status of Polarion connection and authentication"""
    logger.info("Checking Polarion status")
    
    status = {
        "authenticated": polarion_client.is_authenticated,
        "has_token": bool(polarion_client.token or polarion_client.load_token()),
        "token_saved": os.path.exists(TOKEN_FILE)
    }
    
    return json.dumps({
        "status": "success",
        "polarion_status": status
    }, indent=2)

@mcp.tool()
def get_polarion_user(user_id: str) -> str:
    """Get user information from Polarion REST API"""
    logger.info(f"Fetching user information for: {user_id}")
    
    user_data = polarion_client.get_user(user_id)
    
    if user_data:
        return json.dumps({
            "status": "success",
            "message": f"Successfully fetched user information for: {user_id}",
            "user": user_data
        }, indent=2)
    else:
        return json.dumps({
            "status": "error",
            "message": f"Failed to fetch user information for: {user_id}. User may not exist or you may not have permission to access this user."
        }, indent=2)

if __name__ == "__main__":
    print("Starting Polarion MCP Server...")
    
    # Check if we should run in HTTP mode (for hosting) or stdio mode (for local development)
    transport_mode = os.getenv("MCP_TRANSPORT", "stdio")
    
    if transport_mode == "http":
        # HTTP mode for hosting on Render
        port = int(os.getenv("PORT", 8000))
        print(f"Starting HTTP server on port {port}")
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        # stdio mode for local development
        print("Starting stdio server")
        mcp.run(transport="stdio") 