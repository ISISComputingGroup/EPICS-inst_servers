from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
HOST, PORT = '', 8880

class myHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        path = self.path
        if path == "/test1":
            self.wfile.write("Hello World!")
        elif path != "/test1" and path != "/favicon.ico":
            path = path.split('/')
            if len(path) < 4:
                answer = "Please type calculation into URL"
                self.send_response(404)
            elif path[2] == 'add':
                answer = int(path[1]) + int(path[3])
            elif path[2] == 'subtract':
                answer = int(path[1]) - int(path[3])
            elif path[2] == 'multiply':
                answer = int(path[1]) * int(path[3])
            elif path[2] == 'divide':
                answer = int(path[1]) / int(path[3])
            else:
                answer = "Please type calculation into URL"
                self.send_response(404)
            self.wfile.write(answer)


server=HTTPServer(('',PORT), myHandler)
print "Serving HTTP on port %s ..." % PORT
server.serve_forever()