from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
HOST, PORT = '', 8880

class myHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        if self.path == "/test1":
            self.wfile.write("Hello!")
        else:
            self.wfile.write("Hello World!")


server=HTTPServer(('',PORT), myHandler)
print "Serving HTTP on port %s ..." % PORT
server.serve_forever()