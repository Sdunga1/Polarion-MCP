import json
import os
import time
import webbrowser
import re
from typing import Dict, List, Optional, Tuple
from loguru import logger
from mcp.server.fastmcp import FastMCP
import requests
# Helper functions for coverage analysis will be defined inline

# Create an MCP server
mcp = FastMCP("Polarion-MCP-Server")

# Configuration
POLARION_BASE_URL = "http://dev.polarion.atoms.tech/polarion"
LOGIN_URL = POLARION_BASE_URL  # Use the main URL, not a specific login path
TOKEN_PAGE_URL = f"{POLARION_BASE_URL}/#/user_tokens?id=admin"
TOKEN_FILE = "polarion_token.json"

# Reasonable network timeout for all Polarion API calls (seconds)
REQUEST_TIMEOUT_SECONDS = 8
# Small, consistent field set for work items to keep payloads light
WORK_ITEM_MIN_FIELDS = "id,title,type,description"

class PolarionClient:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
    
    def _ensure_token(self):
        if not self.token:
            self.token = self.load_token()
        if not self.token:
            raise Exception("No token available. Please set or generate a token first.")
    
    def _handle_api_response(self, response, operation_name: str):
        """Handle API response and provide meaningful error messages with workflow guidance."""
        if response.status_code == 200:
            return True
        
        if response.status_code == 401:
            raise Exception(f"""
Authentication failed: Token may be expired or invalid.

NEXT STEPS:
1. Use check_polarion_status() to verify token status
2. Use open_polarion_login() to get new token  
3. Use set_polarion_token() to update token
4. Then retry {operation_name}
""")
        elif response.status_code == 403:
            raise Exception(f"""
Access denied: You don't have permission to {operation_name}.

TROUBLESHOOTING:
1. Verify you have access to this project/resource
2. Check if project_id is correct using get_polarion_projects()
3. Contact administrator for permissions
""")
        elif response.status_code == 404:
            raise Exception(f"""
Resource not found: {operation_name} failed.

TROUBLESHOOTING:
1. Use get_polarion_projects() to verify project exists
2. Use get_polarion_work_items() to discover available work items
3. Check spelling of IDs and names - they are case-sensitive
4. For documents: Space names must be provided by user or found in work item references
""")
        elif response.status_code == 500:
            raise Exception(f"""
Polarion server error: {operation_name} failed.

NEXT STEPS:
1. Wait a moment and retry
2. Check if Polarion instance is accessible
3. Try with smaller page sizes or simpler queries
""")
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

# Helper functions for coverage analysis
def _validate_coverage_analysis_inputs(project_id: str, topic: str, github_repo_url: str) -> Optional[str]:
    """Validate inputs for coverage analysis"""
    if not (polarion_client.token or polarion_client.load_token()):
        return json.dumps({
            "status": "error",
            "message": "Polarion authentication required",
            "next_steps": [
                "Use open_polarion_login() to authenticate",
                "Then use set_polarion_token() with generated token",
                "Finally retry this analysis"
            ]
        }, indent=2)
    
    if not github_repo_url or not github_repo_url.startswith("https://github.com/"):
        return json.dumps({
            "status": "error", 
            "message": "Invalid GitHub repository URL",
            "expected_format": "https://github.com/username/repository.git",
            "provided": github_repo_url
        }, indent=2)
    
    if not project_id or not topic:
        return json.dumps({
            "status": "error",
            "message": "Missing required parameters",
            "required": ["project_id", "topic", "github_repo_url"]
        }, indent=2)
    
    return None

def _fetch_topic_requirements(project_id: str, topic: str) -> Dict:
    """Fetch requirements related to a specific topic from Polarion (FRESH DATA - no caching)"""
    try:
        logger.info(f"🔄 Making LIVE API calls to Polarion - no cached data used")
        query_patterns = [f"{topic} AND type:requirement", f"title:{topic}", f"{topic}"]
        all_requirements = []
        
        for i, query in enumerate(query_patterns, 1):
            logger.info(f"📡 API Call {i}/{len(query_patterns)}: Fetching with query '{query}'")
            work_items = polarion_client.get_work_items(project_id, limit=50, query=query)
            all_requirements.extend(work_items)
            logger.info(f"✅ Received {len(work_items)} items from API call {i}")
        
        unique_requirements = {}
        for item in all_requirements:
            if item.get('id') and 'type' in item:
                item_text = f"{item.get('title', '')} {item.get('description', '')}".lower()
                if (item.get('type', '').lower() in ['requirement', 'req'] or topic.lower() in item_text):
                    unique_requirements[item['id']] = item
        
        requirements_list = list(unique_requirements.values())
        logger.info(f"🎯 FRESH DATA PROCESSED: Found {len(requirements_list)} unique requirements for topic '{topic}'")
        return {
            "status": "success", 
            "requirements": requirements_list, 
            "count": len(requirements_list),
            "data_freshness": "live_api_fetch",
            "fetch_timestamp": time.time()
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch requirements: {str(e)}"}

def _analyze_github_implementation(github_repo_url: str, folder: str, requirements: List[Dict]) -> Dict:
    """Analyze GitHub repository for requirement implementations using GitHub MCP tools"""
    try:
        # Extract owner and repo from URL
        url_parts = github_repo_url.replace("https://github.com/", "").replace(".git", "").split("/")
        if len(url_parts) < 2:
            return {"error": "Invalid GitHub URL format", "expected": "https://github.com/owner/repo"}
        
        owner, repo = url_parts[0], url_parts[1]
        
        github_analysis = {
            "repository_url": github_repo_url,
            "owner": owner,
            "repo": repo,
            "analyzed_folder": folder,
            "requirement_references": {},
            "analysis_method": "Dynamic GitHub content analysis using MCP tools",
            "files_analyzed": []
        }
        
        # Note: In a real implementation, this would use the GitHub MCP tools
        # For now, we'll indicate that dynamic analysis should be implemented
        github_analysis["note"] = f"This function should be updated to use GitHub MCP tools to analyze {owner}/{repo}"
        github_analysis["suggested_tools"] = [
            "mcp_github_get_me() - to verify GitHub access",
            f"mcp_github_get_file_contents(owner='{owner}', repo='{repo}', path='{folder}/') - to list files",
            f"mcp_github_get_file_contents(owner='{owner}', repo='{repo}', path='<file>') - to analyze code"
        ]
        
        # For testing purposes, maintain some basic logic but mark it as placeholder
        github_analysis["placeholder_note"] = "This is placeholder logic - should be replaced with dynamic GitHub analysis"
        
        return github_analysis
        
    except Exception as e:
        logger.error(f"GitHub analysis failed: {e}")
        return {
            "error": f"GitHub analysis failed: {str(e)}",
            "suggestion": "Ensure GitHub repository URL is accessible and MCP GitHub tools are available"
        }

def _perform_coverage_analysis(requirements: List[Dict], github_analysis: Dict) -> Dict:
    """Perform coverage analysis between requirements and implementation"""
    implemented, missing = [], []
    requirement_refs = github_analysis.get("requirement_references", {})
    
    for req in requirements:
        req_id = req.get('id', '')
        req_title = req.get('title', '')
        
        if req_id in requirement_refs and requirement_refs[req_id].get('found', False):
            implemented.append({"id": req_id, "title": req_title, "implementation": requirement_refs[req_id].get('implementation', '')})
        else:
            missing.append({"id": req_id, "title": req_title, "description": req.get('description', '')[:200] + "..." if req.get('description', '') else "No description"})
    
    total_count = len(requirements)
    implemented_count = len(implemented)
    coverage_percentage = (implemented_count / total_count * 100) if total_count > 0 else 0
    
    return {
        "total_requirements": total_count,
        "implemented_count": implemented_count,
        "missing_count": len(missing),
        "coverage_percentage": coverage_percentage,
        "implemented_requirements": implemented,
        "missing_requirements": missing,
        "coverage_status": "excellent" if coverage_percentage >= 90 else "good" if coverage_percentage >= 70 else "needs_improvement"
    }

def _generate_recommendations(coverage_analysis: Dict, topic: str) -> List[str]:
    """Generate actionable recommendations based on coverage analysis"""
    recommendations = []
    coverage_pct = coverage_analysis.get("coverage_percentage", 0)
    missing_reqs = coverage_analysis.get("missing_requirements", [])
    
    if coverage_pct == 100:
        recommendations.append(f"✅ Excellent! All {topic} requirements are implemented.")
    elif coverage_pct >= 80:
        recommendations.append(f"✅ Good coverage ({coverage_pct:.1f}%) for {topic} requirements.")
    else:
        recommendations.append(f"⚠️ Coverage needs improvement ({coverage_pct:.1f}%) for {topic} requirements.")
    
    if missing_reqs:
        recommendations.append(f"🔴 Priority: Implement {len(missing_reqs)} missing requirements:")
        for req in missing_reqs[:3]:
            recommendations.append(f"   - {req.get('id', 'Unknown')}: {req.get('title', 'No title')[:60]}...")
    
    recommendations.append("💡 Next steps: Review missing requirements and create implementation plan.")
    return recommendations

@mcp.tool()
def open_polarion_login() -> str:
    """
    <purpose>Open Polarion login page in browser for manual authentication</purpose>
    
    <when_to_use>
    - When you need to authenticate with Polarion for the first time
    - When existing token has expired (401 errors)
    - When check_polarion_status() shows no valid token
    </when_to_use>
    
    <workflow_position>
    STEP 1: Use this tool first if you don't have authentication
    STEP 2: Complete login in browser and generate token
    STEP 3: Use set_polarion_token() with the generated token
    STEP 4: Use check_polarion_status() to verify authentication
    STEP 5: Begin exploring with get_polarion_projects()
    </workflow_position>
    
    <output>Instructions for manual authentication process</output>
    """
    logger.info("Opening Polarion login page for manual authentication")
    return polarion_client.open_login_page()

@mcp.tool()
def set_polarion_token(token: str) -> str:
    """
    <purpose>Set Polarion access token after generating it in browser</purpose>
    
    <when_to_use>
    - After using open_polarion_login() and generating token manually
    - When you have a valid Polarion token to configure
    - When replacing an expired token
    </when_to_use>
    
    <workflow_position>
    STEP 2: Use this after open_polarion_login() and manual token generation
    NEXT: Use check_polarion_status() to verify token is working
    THEN: Begin data exploration with get_polarion_projects()
    </workflow_position>
    
    <parameters>
    - token: The bearer token generated from Polarion's user token page
    </parameters>
    
    <output>Confirmation of token storage and next steps</output>
    """
    logger.info("Setting Polarion token manually")
    return polarion_client.set_token_manually(token)

@mcp.tool()
def get_polarion_projects(limit: int = 10) -> str:
    """
    <purpose>Discover available Polarion projects for exploration</purpose>
    
    <when_to_use>
    - ALWAYS use this FIRST when starting Polarion exploration
    - When you need to find the correct project_id for other operations
    - When user asks about projects without specifying project name
    - To verify authentication is working
    </when_to_use>
    
    <workflow_position>
    STEP 1: Use this tool first to discover available projects
    STEP 2: Choose relevant project_id from results  
    STEP 3: Use get_polarion_work_items() to explore project contents
    STEP 4: Use get_polarion_work_item() for detailed information
    </workflow_position>
    
    <parameters>
    - limit: Number of projects to retrieve (default 10, increase for comprehensive view)
    </parameters>
    
    <examples>
    - Finding automotive projects: Look for "AutoCar", "Vehicle", "Car" in project names
    - Comprehensive discovery: Use limit=50 to see all available projects
    </examples>
    
    <output>List of projects with basic info - use project 'id' field for subsequent calls</output>
    """
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
    """
    <purpose>Get detailed information about a specific Polarion project</purpose>
    
    <when_to_use>
    - When you need detailed project metadata (description, settings, etc.)
    - After using get_polarion_projects() to identify the project_id
    - When you need project configuration details
    - RARELY needed for most exploration tasks
    </when_to_use>
    
    <workflow_position>
    OPTIONAL: Use after get_polarion_projects() if project details are needed
    USUALLY SKIP: Most tasks should go directly to get_polarion_work_items()
    </workflow_position>
    
    <parameters>
    - project_id: Exact project ID from get_polarion_projects() results
    - fields: "@basic" for essential info, "@all" for complete details
    </parameters>
    
    <note>Most users should skip this and go directly to exploring work items</note>
    """
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
    """
    <purpose>Discover and search work items (requirements, tasks, etc.) in a Polarion project</purpose>
    
    <when_to_use>
    - MAIN DISCOVERY TOOL: Use this to explore project contents
    - When searching for specific topics (e.g., "HMI", "requirements")
    - When you need to understand project scope and available work items
    - BEFORE using get_polarion_work_item() for detailed info
    </when_to_use>
    
    <workflow_position>
    STEP 1: After get_polarion_projects(), use this to explore project contents
    STEP 2: Analyze results to identify relevant work items
    STEP 3: Use get_polarion_work_item() for detailed information on specific items
    OPTIONAL: Use get_polarion_document() if user provides specific space/document names
    </workflow_position>
    
    <parameters>
    - project_id: Required. Get from get_polarion_projects() results
    - limit: Number of items (default 10). Use 30-50 for comprehensive searches
    - query: POWERFUL filter. Examples:
      * "HMI" - finds HMI-related items
      * "type:requirement" - only requirements
      * "HMI AND type:requirement" - HMI requirements
      * "title:system" - items with "system" in title
    </parameters>
    
    <examples>
    - Finding HMI requirements: query="HMI AND type:requirement", limit=30
    - Project overview: query="", limit=50
    - Security items: query="security OR safety", limit=20
    - All requirements: query="type:requirement", limit=100
    </examples>
    
    <output>
    Minimal fields (id, title, type, description) - use get_polarion_work_item() for full details
    Contains rich information including work item relationships and metadata
    </output>
    
    <critical_note>
    This tool often contains all the information you need. Work items include:
    - Requirements, specifications, tasks
    - Relationships between items
    - Project structure and organization
    Check results thoroughly before seeking additional tools
    </critical_note>
    """
    logger.info(f"Fetching {limit} work items from project {project_id}")
    work_items = polarion_client.get_work_items(project_id, limit, query)
    if work_items:
        return json.dumps({
            "status": "success",
            "message": f"Successfully fetched {len(work_items)} work items from project {project_id}",
            "work_items": work_items,
            "count": len(work_items),
            "project_id": project_id,
            "next_steps": "Use get_polarion_work_item() for detailed info on specific items"
        }, indent=2)
    return json.dumps({
        "status": "error",
        "message": f"Failed to fetch work items from project {project_id}. Check token, project ID, or permissions."
    }, indent=2)

@mcp.tool()
def get_polarion_work_item(project_id: str, work_item_id: str, fields: str = "@basic") -> str:
    """
    <purpose>Get detailed information about a specific work item</purpose>
    
    <when_to_use>
    - AFTER using get_polarion_work_items() to identify specific work items of interest
    - When you need complete details about a requirement, task, or specification
    - When you need full content, relationships, and metadata
    - For deep analysis of specific work items
    </when_to_use>
    
    <workflow_position>
    STEP 1: Use get_polarion_work_items() to discover and filter work items
    STEP 2: Identify specific work_item_id from the results
    STEP 3: Use this tool to get complete details
    STEP 4: Analyze relationships and linked items if needed
    </workflow_position>
    
    <parameters>
    - project_id: Required. Must match project from previous search
    - work_item_id: Required. Get from get_polarion_work_items() results
    - fields: "@basic" for essential info, "@all" for complete details including relationships
    </parameters>
    
    <examples>
    - Detailed requirement analysis: fields="@all"
    - Quick verification: fields="@basic"
    - Understanding relationships: fields="@all" (includes linked items)
    </examples>
    
    <output>
    Complete work item details including:
    - Full description and content
    - Relationships to other work items
    - Metadata and status information
    - Approval and review information
    </output>
    
    <note>
    Use this tool sparingly - only when you need detailed information about specific items
    identified through get_polarion_work_items() searches
    </note>
    """
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
    """
    <purpose>Access specific structured documents within a Polarion space</purpose>
    
    <when_to_use>
    - When you need access to organized documents (specifications, manuals)
    - When user provides specific space and document names
    - When work items reference specific documents that need direct access
    - For accessing curated requirement collections in document format
    </when_to_use>
    
    <workflow_position>
    STEP 1: Use get_polarion_projects() to identify project
    STEP 2: Use get_polarion_work_items() to explore and potentially discover space references
    STEP 3: Use this tool when you have specific space_id and document_name
    ALTERNATIVE: Often get_polarion_work_items() provides equivalent or better information
    </workflow_position>
    
    <parameters>
    - project_id: Required. From get_polarion_projects()
    - space_id: Required. EXACT space name (user-provided or from work item references)
    - document_name: Required. Document name (e.g., "HMI", "System Requirements Specification")
    - fields: "@basic" for summary, "@all" for complete content
    </parameters>
    
    <examples>
    - HMI specifications: project_id="AutoCar", space_id="Master Specifications", document_name="HMI"
    - System requirements: project_id="AutoCar", space_id="Requirements", document_name="System"
    </examples>
    
    <critical_requirements>
    - space_id must be EXACT name (case-sensitive)
    - document_name is case-sensitive
    - Use quotes around space names with spaces (e.g., "Master Specifications")
    - Space names typically provided by user or discovered from work item exploration
    </critical_requirements>
    
    <output>
    Structured document content including organized requirements and specifications
    Often contains similar information to work items but in document format
    </output>
    
    <troubleshooting>
    If 404 error: Verify space_id and document_name spelling
    Common spaces: "Master Specifications", "Requirements", "Design Documents"
    Try exploring with get_polarion_work_items() first for context
    </troubleshooting>
    
    <note>
    Space names are not discoverable via API - they come from user knowledge or work item references
    </note>
    """
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
    """
    <purpose>Verify Polarion authentication and connection status</purpose>
    
    <when_to_use>
    - When experiencing authentication errors
    - To verify setup before starting exploration
    - When debugging connection issues
    - As a diagnostic tool when other tools fail
    </when_to_use>
    
    <workflow_position>
    DIAGNOSTIC: Use when authentication issues occur
    VERIFICATION: Use after set_polarion_token() to confirm setup
    TROUBLESHOOTING: Use when other tools return 401 errors
    </workflow_position>
    
    <output>
    Authentication status and next steps if issues found
    </output>
    
    <next_steps>
    If no token: Use open_polarion_login() then set_polarion_token()
    If token exists: Try get_polarion_projects() to test connectivity
    </next_steps>
    """
    logger.info("Checking Polarion status")
    status = {
        "has_token": bool(polarion_client.token or polarion_client.load_token()),
        "token_saved": os.path.exists(TOKEN_FILE)
    }
    
    # Add helpful next steps based on status
    next_steps = []
    if not status["has_token"]:
        next_steps.append("Use open_polarion_login() to authenticate")
        next_steps.append("Then use set_polarion_token() with generated token")
    else:
        next_steps.append("Authentication appears ready")
        next_steps.append("Use get_polarion_projects() to begin exploration")
    
    return json.dumps({
        "status": "success",
        "polarion_status": status,
        "next_steps": next_steps
    }, indent=2)

@mcp.tool()
def polarion_github_requirements_coverage(project_id: str, topic: str, github_repo_url: str, github_folder: str = "") -> str:
    """
    <purpose>Cross-platform requirements coverage analysis between Polarion and GitHub with real-time data</purpose>
    
    <when_to_use>
    - When you need to verify if requirements are implemented in code
    - For gap analysis between specifications and implementation
    - When user asks to "check if requirements are implemented" or "find missing implementations"
    - For requirements traceability and coverage validation
    - When you need fresh, real-time data from both Polarion and GitHub
    </when_to_use>
    
    <workflow_position>
    COMPREHENSIVE CROSS-PLATFORM ANALYSIS TOOL: Use this for end-to-end requirements coverage analysis
    STEP 1: This tool fetches FRESH requirements from Polarion in real-time
    STEP 2: This tool provides guidance for analyzing GitHub repository implementation
    STEP 3: This tool requires manual code analysis to determine actual implementation status
    </workflow_position>
    
    <fresh_data_guarantee>
    REAL-TIME DATA FETCHING: This tool always works with fresh data
    - Polarion: Fetches requirements directly from API (no caching)
    - GitHub: Provides guidance for live repository analysis via GitHub MCP tools
    - No stale data: Each execution gets current state from both platforms
    - Team-safe: Works correctly even when colleagues make concurrent changes
    </fresh_data_guarantee>
    
    <parameters>
    - project_id: Required. Polarion project ID (e.g., "AutoCar")
    - topic: Required. Requirements topic to analyze (e.g., "HMI", "braking", "perception")
    - github_repo_url: Required. GitHub repository URL (e.g., "https://github.com/Sdunga1/AutoCar.git")
    - github_folder: Optional. Specific folder to analyze (e.g., "hmi", "braking"). Empty means analyze entire repo
    </parameters>
    
    <examples>
    - HMI analysis: project_id="AutoCar", topic="HMI", github_repo_url="https://github.com/Sdunga1/AutoCar.git", github_folder="hmi"
    - Complete system: project_id="AutoCar", topic="automated_driving", github_repo_url="https://github.com/Sdunga1/AutoCar.git"
    - Braking system: project_id="AutoCar", topic="braking", github_repo_url="https://github.com/Sdunga1/AutoCar.git", github_folder="braking"
    </examples>
    
    <output>
    Comprehensive requirements coverage analysis including:
    - List of requirements found in Polarion for the topic
    - Guidance for analyzing GitHub implementation
    - Framework for determining implementation status
    - Recommendations for closing gaps
    </output>
    
    <critical_requirements>
    - Requires both Polarion authentication and GitHub access
    - Provides requirements from Polarion with IDs (e.g., AC-96, AC-97)
    - Requires manual code analysis to determine actual implementation status
    - Does NOT automatically search for requirement IDs in code
    - Provides actionable insights for development teams
    </critical_requirements>
    
    <dynamic_integration_note>
    This tool integrates with GitHub MCP tools for real-time dynamic analysis:
    1. Uses mcp_github_get_me() to verify current GitHub access
    2. Uses mcp_github_get_file_contents() to explore live repository structure
    3. Uses mcp_github_get_file_contents() to analyze current code files for ACTUAL implementation
    4. Dynamically extracts owner/repo from GitHub URL for proper tool calls
    5. Requires manual analysis of code structure, functions, and logic to determine implementation status
    6. Always fetches fresh data - no caching, no stale information
    </dynamic_integration_note>
    
    <team_collaboration_safety>
    CONCURRENT CHANGE SAFE: This tool is designed for team environments
    - Each execution fetches live data from Polarion API
    - GitHub analysis uses current repository state via MCP tools
    - Safe to use even when teammates are actively making changes
    - Results reflect the actual current state of both platforms
    </team_collaboration_safety>
    
    <use_case_example>
    "Get me the HMI related requirements from my polarion and see if any implementation is missing from the github repository"
    This tool will:
    1. Search Polarion for HMI requirements (AC-96, AC-97, etc.)
    2. Provide guidance for analyzing GitHub code implementation
    3. Require manual analysis of actual code to determine what's implemented
    4. Help identify missing implementations based on code structure and logic
    </use_case_example>
    
    <important_note>
    ⚠️  CRITICAL: This tool does NOT automatically search for requirement IDs in code text.
    It provides requirements from Polarion and guidance for analyzing GitHub implementation.
    To determine actual implementation status, you must:
    1. Read the actual code files using mcp_github_get_file_contents()
    2. Analyze the code structure, functions, and logic
    3. Compare implementation against Polarion requirements
    4. Determine what's missing based on actual code analysis
    </important_note>
    """
    logger.info(f"Starting FRESH requirements coverage analysis for {topic} in project {project_id}")
    logger.info("🔄 REAL-TIME DATA FETCH: Getting current data from both Polarion and GitHub")
    
    try:
        # Validate inputs and authentication
        validation_result = _validate_coverage_analysis_inputs(project_id, topic, github_repo_url)
        if validation_result:
            return validation_result
        
        # Fetch FRESH requirements from Polarion (no caching)
        logger.info(f"📡 Fetching LIVE {topic} requirements from Polarion project {project_id} (real-time API call)")
        requirements_result = _fetch_topic_requirements(project_id, topic)
        if "error" in requirements_result:
            return json.dumps(requirements_result, indent=2)
        
        requirements = requirements_result["requirements"]
        if not requirements:
            return json.dumps({
                "status": "warning",
                "message": f"No requirements found for topic '{topic}' in project {project_id}",
                "suggestion": "Try different topic keywords or check Polarion project contents"
            }, indent=2)
        
        # Analyze GitHub repository (prepare for fresh analysis)
        logger.info(f"🔍 Preparing LIVE GitHub repository analysis: {github_repo_url}")
        logger.info("⚠️  Will guide to fetch current repository state via GitHub MCP tools")
        github_analysis = _analyze_github_implementation(github_repo_url, github_folder, requirements)
        
        # Check if GitHub analysis indicates it needs dynamic tools
        if "note" in github_analysis and "should be updated" in github_analysis["note"]:
            return json.dumps({
                "status": "partial_success",
                "message": "✅ FRESH requirements fetched from Polarion, 🔄 GitHub analysis needs real-time steps",
                "fresh_data_timestamp": time.time(),
                "polarion_requirements": requirements,
                "github_analysis_needed": github_analysis,
                "real_time_steps_required": [
                    f"1. 🔐 Use mcp_github_get_me() to verify current GitHub access",
                    f"2. 📁 Use mcp_github_get_file_contents(owner='{github_analysis.get('owner')}', repo='{github_analysis.get('repo')}', path='{github_folder or ''}/') to explore CURRENT repository",
                    f"3. 📄 Use mcp_github_get_file_contents() to analyze LATEST code files",
                    f"4. 🔍 Search current code for requirement IDs: {', '.join([req.get('id', '') for req in requirements[:5]])}",
                    f"5. 💡 Look for implementation evidence in comments, function names, and docstrings"
                ],
                "requirements_to_verify": [{"id": req.get("id"), "title": req.get("title")} for req in requirements],
                "data_freshness_note": "Polarion data is live/current. GitHub analysis will use real-time repository state.",
                "suggestion": "For complete FRESH analysis, use GitHub MCP tools to examine current code files"
            }, indent=2)
        
        # Perform coverage analysis
        coverage_analysis = _perform_coverage_analysis(requirements, github_analysis)
        
        # Generate comprehensive report
        report = {
            "status": "success",
            "analysis_summary": {
                "project_id": project_id,
                "topic": topic,
                "github_repo": github_repo_url,
                "analyzed_folder": github_folder or "entire repository",
                "total_requirements": len(requirements),
                "implemented_requirements": coverage_analysis["implemented_count"],
                "missing_implementations": coverage_analysis["missing_count"],
                "coverage_percentage": coverage_analysis["coverage_percentage"]
            },
            "requirements_details": requirements,
            "implementation_analysis": github_analysis,
            "coverage_results": coverage_analysis,
            "recommendations": _generate_recommendations(coverage_analysis, topic)
        }
        
        logger.info(f"Coverage analysis completed: {coverage_analysis['coverage_percentage']:.1f}% coverage")
        return json.dumps(report, indent=2)
        
    except Exception as e:
        logger.error(f"Requirements coverage analysis failed: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Requirements coverage analysis failed: {str(e)}",
            "troubleshooting": [
                "Verify Polarion authentication with check_polarion_status()",
                "Ensure GitHub repository URL is accessible",
                "Check that project_id and topic are correct",
                "Try with get_polarion_work_items() first to verify data access"
            ]
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