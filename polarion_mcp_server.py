import json
import os
import time
import webbrowser
from typing import Dict, List, Optional
from loguru import logger
from mcp.server.fastmcp import FastMCP
import requests

# Create an MCP server
mcp = FastMCP("Polarion-MCP-Server")

# Configuration
POLARION_BASE_URL = "http://dev.polarion.atoms.tech/polarion"
LOGIN_URL = POLARION_BASE_URL  # Use the main URL, not a specific login path
TOKEN_PAGE_URL = f"{POLARION_BASE_URL}/#/user_tokens?id=admin"
TOKEN_FILE = os.path.join(os.getenv("TOKEN_DIR", "."), "polarion_token.json")

# Reasonable network timeout for all Polarion API calls (seconds)
REQUEST_TIMEOUT_SECONDS = 8
# Small, consistent field set for work items to keep payloads light
WORK_ITEM_MIN_FIELDS = "id,title,type,description"

class PolarionClient:
    def __init__(self):
        self.session = requests.Session()
        self.token = os.getenv("POLARION_TOKEN")  # Check for env var first
    
    def _ensure_token(self):
        if not self.token:
            self.token = self.load_token()
        if not self.token:
            raise Exception("No token available. Please set or generate a token first.")
    
    def _handle_api_response(self, response, operation_name: str):
        """Handle API response and provide meaningful error messages for common issues."""
        if response.status_code == 200:
            return True
        
        if response.status_code == 401:
            raise Exception(f"Authentication failed: Token may be expired or invalid. Please regenerate your token.")
        elif response.status_code == 403:
            raise Exception(f"Access denied: You don't have permission to {operation_name}.")
        elif response.status_code == 404:
            raise Exception(f"Resource not found: {operation_name} failed.")
        elif response.status_code == 500:
            raise Exception(f"Polarion server error: {operation_name} failed. Please try again later.")
        else:
            raise Exception(f"API error {response.status_code}: {response.text}")
    
    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
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
            return json.dumps({
                "status": "success",
                "message": "Token set successfully. Please test it by fetching work items or projects.",
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
    
    def get_projects(self, limit: int = 10) -> List[Dict]:
        """Fetch projects from Polarion REST API (lightweight fields)."""
        try:
            self._ensure_token()
            api_url = f"{POLARION_BASE_URL}/rest/v1/projects"
            params = {
                'fields[projects]': '@basic',
                'page[size]': limit
            }
            response = self.session.get(api_url, params=params, headers=self._headers(), timeout=REQUEST_TIMEOUT_SECONDS)
            self._handle_api_response(response, "fetch projects")
            data = response.json()
            projects = (data.get('data') or [])[:limit]
            logger.info(f"Fetched {len(projects)} projects")
            return projects
        except Exception as e:
            logger.error(f"Failed to fetch projects: {e}")
            return []

    def get_project(self, project_id: str, fields: str = "@basic") -> Optional[Dict]:
        """Fetch specific project details from Polarion REST API."""
        try:
            self._ensure_token()
            api_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}"
            params = {'fields[projects]': fields}
            response = self.session.get(api_url, params=params, headers=self._headers(), timeout=REQUEST_TIMEOUT_SECONDS)
            if response.status_code == 404:
                logger.warning(f"Project not found: {project_id}")
                return None
            self._handle_api_response(response, f"fetch project {project_id}")
            project_data = response.json()
            logger.info(f"Fetched project: {project_id}")
            return project_data
        except Exception as e:
            logger.error(f"Failed to fetch project {project_id}: {e}")
            return None

    def get_work_items(self, project_id: str, limit: int = 10, query: str = "") -> List[Dict]:
        """Fetch work items (minimal fields). Parameters: project_id, limit, optional query."""
        try:
            self._ensure_token()
            api_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/workitems"
            params = {
                'fields[workitems]': WORK_ITEM_MIN_FIELDS,
                'page[size]': limit
            }
            if query:
                params['query'] = query
            response = self.session.get(api_url, params=params, headers=self._headers(), timeout=REQUEST_TIMEOUT_SECONDS)
            self._handle_api_response(response, f"fetch work items from project {project_id}")
            data = response.json()
            work_items = (data.get('data') or [])[:limit]
            logger.info(f"Fetched {len(work_items)} work items from {project_id}")
            return work_items
        except Exception as e:
            logger.error(f"Failed to fetch work items from {project_id}: {e}")
            return []
    
    def get_work_item(self, project_id: str, work_item_id: str, fields: str = "@basic") -> Optional[Dict]:
        """Fetch a specific work item by ID from Polarion REST API."""
        try:
            self._ensure_token()
            api_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/workitems/{work_item_id}"
            params = {'fields[workitems]': fields}
            response = self.session.get(api_url, params=params, headers=self._headers(), timeout=REQUEST_TIMEOUT_SECONDS)
            if response.status_code == 404:
                logger.warning(f"Work item not found: {work_item_id} in project: {project_id}")
                return None
            self._handle_api_response(response, f"fetch work item {work_item_id} from project {project_id}")
            work_item_data = response.json()
            logger.info(f"Fetched work item: {work_item_id} from project: {project_id}")
            return work_item_data
        except Exception as e:
            logger.error(f"Failed to fetch work item {work_item_id} from project {project_id}: {e}")
            return None

    def get_document(self, project_id: str, space_id: str, document_name: str, fields: str = "@basic") -> Optional[Dict]:
        """Fetch a specific document from Polarion REST API."""
        try:
            self._ensure_token()
            api_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/spaces/{space_id}/documents/{document_name}"
            params = {'fields[documents]': fields}
            response = self.session.get(api_url, params=params, headers=self._headers(), timeout=REQUEST_TIMEOUT_SECONDS)
            if response.status_code == 404:
                logger.warning(f"Document not found: {document_name} in space: {space_id} of project: {project_id}")
                return None
            self._handle_api_response(response, f"fetch document {document_name} from space {space_id} in project {project_id}")
            document_data = response.json()
            logger.info(f"Fetched document: {document_name} from space: {space_id} in project: {project_id}")
            return document_data
        except Exception as e:
            logger.error(f"Failed to fetch document {document_name} from space {space_id} in project {project_id}: {e}")
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
    """Set Polarion access token manually (after generating it in browser) or user providing it"""
    logger.info("Setting Polarion token manually")
    return polarion_client.set_token_manually(token)

@mcp.tool()
def get_polarion_projects(limit: int = 10) -> str:
    """List projects (fast, minimal fields). Parameters: limit."""
    logger.info(f"Fetching {limit} projects from Polarion")
    projects = polarion_client.get_projects(limit)
    if projects:
        return json.dumps({
            "status": "success",
            "message": f"Successfully fetched {len(projects)} projects",
            "projects": projects,
            "count": len(projects)
        }, indent=2)
    return json.dumps({
        "status": "error",
        "message": "Failed to fetch projects. Please check authentication and token."
    }, indent=2)

@mcp.tool()
def get_polarion_project(project_id: str, fields: str = "@basic") -> str:
    """Get a specific project by ID. Parameters: project_id, optional fields (@basic|@all)."""
    logger.info(f"Fetching project {project_id} from Polarion")
    project = polarion_client.get_project(project_id, fields)
    if project:
        return json.dumps({
            "status": "success",
            "message": f"Successfully fetched project: {project_id}",
            "project": project
        }, indent=2)
    return json.dumps({
        "status": "error",
        "message": f"Failed to fetch project {project_id}. Project may not exist or access is denied."
    }, indent=2)

@mcp.tool()
def get_polarion_work_items(project_id: str, limit: int = 10, query: str = "") -> str:
    """List work items with minimal fields. Parameters: project_id, limit, optional query."""
    logger.info(f"Fetching {limit} work items from project {project_id}")
    work_items = polarion_client.get_work_items(project_id, limit, query)
    if work_items:
        return json.dumps({
            "status": "success",
            "message": f"Successfully fetched {len(work_items)} work items from project {project_id}",
            "work_items": work_items,
            "count": len(work_items),
            "project_id": project_id
        }, indent=2)
    return json.dumps({
        "status": "error",
        "message": f"Failed to fetch work items from project {project_id}. Check token, project ID, or permissions."
    }, indent=2)

@mcp.tool()
def get_polarion_work_item(project_id: str, work_item_id: str, fields: str = "@basic") -> str:
    """Get a specific work item by ID. Parameters: project_id, work_item_id, optional fields (@basic|@all)."""
    logger.info(f"Fetching work item {work_item_id} from project {project_id}")
    work_item = polarion_client.get_work_item(project_id, work_item_id, fields)
    if work_item:
        return json.dumps({
            "status": "success",
            "message": f"Successfully fetched work item: {work_item_id} from project {project_id}",
            "work_item": work_item
        }, indent=2)
    return json.dumps({
        "status": "error",
        "message": f"Failed to fetch work item {work_item_id} from project {project_id}. Work item may not exist or access is denied."
    }, indent=2)

@mcp.tool()
def get_polarion_document(project_id: str, space_id: str, document_name: str, fields: str = "@basic") -> str:
    """Get a specific document by name. Parameters: project_id, space_id, document_name, optional fields (@basic|@all)."""
    logger.info(f"Fetching document {document_name} from space {space_id} in project {project_id}")
    document = polarion_client.get_document(project_id, space_id, document_name, fields)
    if document:
        return json.dumps({
            "status": "success",
            "message": f"Successfully fetched document: {document_name} from space {space_id} in project {project_id}",
            "document": document
        }, indent=2)
    return json.dumps({
        "status": "error",
        "message": f"Failed to fetch document {document_name} from space {space_id} in project {project_id}. Document may not exist or access is denied."
    }, indent=2)

@mcp.tool()
def check_polarion_status() -> str:
    """Check the current status of Polarion connection and authentication"""
    logger.info("Checking Polarion status")
    status = {
        "has_token": bool(polarion_client.token or polarion_client.load_token()),
        "token_saved": os.path.exists(TOKEN_FILE)
    }
    return json.dumps({
        "status": "success",
        "polarion_status": status
    }, indent=2)

if __name__ == "__main__":
    print("Starting Polarion MCP Server...")
    
    # Check if we should run in HTTP mode (for hosting) or stdio mode (for local development)
    transport_mode = os.getenv("MCP_TRANSPORT", "stdio")
    
    if transport_mode == "http":
        # HTTP mode for hosting on Render - would need FastAPI setup
        print("HTTP mode not implemented in this version")
        exit(1)
    else:
        # stdio mode for local development
        print("Starting stdio server")
        mcp.run(transport="stdio")