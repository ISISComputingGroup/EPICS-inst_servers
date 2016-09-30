from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from threading import Thread, Lock
from time import sleep
import re
from get_webpage import scrape_webpage
import json
HOST, PORT = '', 60000

_scraped_data = scrape_webpage()
_lock = Lock()

class MyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        """
        This is called by BaseHTTPRequestHandler every time a client does a GET.
        The response is written to self.wfile
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Look for the callback
        # JSONP requires a response of the format "name_of_callback(json_string)"
        # e.g. myFunction({ "a": 1, "b": 2})
        result = re.search('/?callback=(\w+)&_', self.path)
        if len(result.groups()) > 0:
            callback = result.groups()[0]
            with _lock:
                ans = "%s(%s)" % (callback, json.dumps(_scraped_data))
            self.wfile.write(ans)

    def log_message(self, format, *args):
        """ By overriding this method and doing nothing we disable writing to console
         for every client request. Remove this to re-enable """
        return


class Server(Thread):
    def run(self):
        server = HTTPServer(('', PORT), MyHandler)
        server.serve_forever()

        while True:
            with _lock:
                global _scraped_data
                _scraped_data = scrape_webpage()
                sleep(1)

if __name__ == '__main__':
    try:
        server = Server()
        server.start()
    except KeyboardInterrupt as e:
        server.join()
