"""
Simple HTTP server for analysis engine.
Can be deployed as standalone service or triggered by Cloudflare Workers.
"""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import tempfile
import subprocess

from analyze import analyze_repo_from_url


class AnalysisHandler(BaseHTTPRequestHandler):
    """HTTP request handler for analysis endpoints."""
    
    def do_POST(self):
        """Handle POST /analyze requests."""
        if self.path != '/analyze':
            self.send_error(404)
            return
        
        # Read request body
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body)
            repo_url = data.get('repo_url')
            
            if not repo_url:
                self.send_error(400, 'Missing repo_url')
                return
            
            # Run analysis
            result = analyze_repo_from_url(repo_url)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(result, indent=2).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def do_GET(self):
        """Handle GET /health requests."""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            self.wfile.write(json.dumps({
                'status': 'healthy',
                'service': 'reproducibility-validator-analysis'
            }).encode())
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def run_server(port=8080):
    """Start the analysis server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, AnalysisHandler)
    
    print(f'Starting analysis server on port {port}...')
    print(f'Health check: http://localhost:{port}/health')
    print(f'Analysis endpoint: POST http://localhost:{port}/analyze')
    
    httpd.serve_forever()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    run_server(port)
