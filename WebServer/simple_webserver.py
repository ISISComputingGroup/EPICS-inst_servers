from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import time
HOST, PORT = '', 8800
start = time.time()
class myHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        now = time.time()
        difference = now-start
        if difference <= 3:
            self.wfile.write("Hello (1)!")
        elif difference <= 6:
            self.wfile.write("Hello (2)!")
        else:
            self.wfile.write("Hello (3)!")


server = HTTPServer(('',PORT), myHandler)
print "Serving HTTP on port %s ..." % PORT
server.serve_forever()