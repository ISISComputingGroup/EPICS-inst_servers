import asyncio
from threading import RLock, Thread
from time import sleep
from typing import Awaitable, Optional

import tornado.ioloop
import tornado.web

HOST, PORT = "", 8008
_config = ""


class MyHandler(tornado.web.RequestHandler):
    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def get(self, *args) -> None:
        """
        This is called by RequestHandler every time a client does a GET.
        """
        if self.request.path == "/favicon.ico":
            pass
        self.set_header("Content-Type", "text/html")
        self.set_status(200)
        global _config
        self.write(_config)


def make_app():
    return tornado.web.Application(
        [
            (r"/", MyHandler),
            (r"/(favicon.ico)", MyHandler),
        ]
    )


class Server(Thread):
    def run(self):
        # Workaround - as documented at https://github.com/tornadoweb/tornado/issues/2608
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        self._lock_config = RLock()
        asyncio.set_event_loop(asyncio.new_event_loop())
        app = make_app()
        app.listen(PORT)
        tornado.ioloop.IOLoop.instance().start()

    def set_config(self, set_to):
        """
        :param set_to: The config to serve, converted to JSON.
        """
        with self._lock_config:
            global _config
            _config = set_to


if __name__ == "__main__":
    _server = Server()
    try:
        _server.start()
        _server.set_config("TEST")
        sleep(10)
        _server.set_config("NOT TEST")
    except KeyboardInterrupt:
        print("stopping server")
        tornado.ioloop.IOLoop.instance().stop()
        _server.join(1)
