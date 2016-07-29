from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from threading import Thread
from time import sleep
HOST, PORT = '', 8008
place = 0

_response = {}

class myHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        if self.path == "/RAW":
            self.wfile.write(_response)
        elif self.path == "/human_readable":
            self.wfile.write('<html><head><meta http-equiv="refresh" content="10"></head>')
            global _response
            title = '<h1><b>' + _response['name'] + '</h1></b>'
            self.wfile.write(title)
            self.wfile.write('<br>')
            description = '<h3>' + _response['description'] + '<h3>'
            self.wfile.write(description)
            self.wfile.write('<br>')
            self.wfile.write('<h2><b> Blocks </h2></b>')
            blocks = _response['blocks']
            #names=str(block).split(':')
            for block in blocks:
                #place += 11
                self.wfile.write(block['name'])
                self.wfile.write('<br>')
                #place += 13
            self.wfile.write('<br>')
            self.wfile.write('<h2><b> IOCs </h2></b>')
#            ioc = _response['iocs']
#            self.wfile.write(ioc)



class Server(Thread):

    def run(self):
        self.server = HTTPServer(('',PORT), myHandler)
        print "Serving HTTP on port %s ..." % PORT
        self.server.serve_forever()

    def set_config(self,set_config_to):
        global _response
        _response = set_config_to


if __name__ == '__main__':
    server = Server()
    server.start()
    server.set_config("TEST")
    sleep(10)
    server.set_config("NOT TEST")