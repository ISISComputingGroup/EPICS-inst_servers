from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import time

HOST, PORT = '', 8800
class myHandler(BaseHTTPRequestHandler):
    recursions = 0

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.wfile.write('<html><head><meta http-equiv="refresh" content="10"></head>')
        self.recursions = self.recursions + 1
        self.wfile.write("Hello (" + str(int(self.recursions)) + ")!")


server = HTTPServer(('',PORT), myHandler)
print "Serving HTTP on port %s ..." % PORT
server.serve_forever()