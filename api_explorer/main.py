"""
FastAPI-based API Explorer for modules.

This module provides a web interface similar to FastAPI's /docs for
exploring and testing module APIs in real-time.
"""

import sys
import os
import argparse
import logging
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add the parent directory to the path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import the ApiExplorer directly - FIX: changed import path
from api_explorer import ApiExplorer

def run_explorer(host: str = "127.0.0.1", port: int = 8000, block: bool = True) -> ApiExplorer:
    """
    Start the API Explorer.
    
    Args:
        host: Host to bind the server to
        port: Port to bind the server to
        block: Whether to block the current thread
        
    Returns:
        The ApiExplorer instance
    """
    # Get or create the ApiExplorer instance
    explorer = ApiExplorer.get_instance()
    
    # Start the server
    explorer.start_server(host=host, port=port, block=block)
    
    return explorer

def main():
    """Run the API Explorer from command line."""
    parser = argparse.ArgumentParser(description="Run the API Explorer")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Dynamic API Explorer")
    print("=" * 60)
    print(f"Starting server at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        run_explorer(host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\nServer stopped by user")

if __name__ == "__main__":
    main()
