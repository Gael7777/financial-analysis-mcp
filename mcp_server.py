from fastmcp import FastMCP
import requests
import json
import os
from datetime import datetime

app = FastMCP("financial-analysis-mcp")

# Get configuration from environment variables
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "default-token-change-me")
INFOMANIAK_ENDPOINT = os.getenv("INFOMANIAK_ENDPOINT", "https://www.utility-g.ch/api/receive-analysis.php")

@app.tool()
def post_analysis_to_server(analysis_json: str) -> dict:
    """
    Receive Claude's market analysis and POST it to your Infomaniak PHP backend.
    This bypasses Claude routine sandboxing.
    
    Args:
        analysis_json: JSON string with market analysis from Claude
    
    Returns:
        Status confirmation
    """
    try:
        # Validate and parse the JSON
        analysis = json.loads(analysis_json)
        
        # Add timestamp
        analysis['received_at'] = datetime.now().isoformat()
        
        # POST to your PHP endpoint
        # This request comes FROM Render (unrestricted) TO your Infomaniak (works fine)
        response = requests.post(
            INFOMANIAK_ENDPOINT,
            json=analysis,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SECRET_TOKEN}"
            },
            timeout=30
        )
        
        # Check response
        if response.ok:
            response_data = response.json()
            return {
                "status": "success",
                "message": "Analysis successfully posted to your server",
                "infomaniak_response": response_data
            }
        else:
            return {
                "status": "error",
                "message": f"Infomaniak returned HTTP {response.status_code}",
                "details": response.text
            }
            
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "message": f"Invalid JSON received: {str(e)}"
        }
    except requests.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to reach your server: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }


@app.resource("analysis://status")
def get_status() -> str:
    """Health check endpoint - tests if MCP server is running"""
    return "MCP Server is running and ready to receive analyses from Claude"