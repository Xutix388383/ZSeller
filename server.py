
import http.server
import socketserver
import socket

def find_free_port():
    """Find a free port starting from 5000"""
    for port in range(5000, 5100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    raise RuntimeError("No free ports available in range 5000-5099")

if __name__ == "__main__":
    PORT = find_free_port()
    Handler = http.server.SimpleHTTPRequestHandler
    
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Server started at http://0.0.0.0:{PORT}")
        print(f"Serving files from current directory")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")
