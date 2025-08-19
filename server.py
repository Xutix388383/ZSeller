
import http.server
import socketserver
import socket
import os

def find_free_port(start_port=5000):
    """Find a free port starting from the specified port"""
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No free ports available in range {start_port}-{start_port + 99}")

def get_port():
    """Get port from environment variable or find a free one"""
    # Try to get port from environment variable (for deployment platforms)
    port = os.environ.get('PORT')
    if port:
        try:
            return int(port)
        except ValueError:
            print(f"Invalid PORT environment variable: {port}")
    
    # Try common web development ports
    preferred_ports = [5000, 3000, 8000, 8080, 4200]
    for preferred_port in preferred_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', preferred_port))
                return preferred_port
        except OSError:
            continue
    
    # Fall back to finding any free port
    return find_free_port(5000)

if __name__ == "__main__":
    PORT = get_port()
    Handler = http.server.SimpleHTTPRequestHandler
    
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Server started at http://0.0.0.0:{PORT}")
        print(f"Serving files from current directory")
        print(f"Available externally on all interfaces")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")
