import SocketServer
from threading import Thread


class BogusHandler(SocketServer.StreamRequestHandler):
    """
    Custom handler to use in TCPServer.
    This handler has hability to map requests to registered handler callers.
    It doesn't check anything about the request, unless you don't send a method or a
    status code, which we need to map the handler to the request being made.
    """

    def handle(self):
        """
        Parse requests to find registered handlers to redirect them, if it
        doesn't find any handlers and promiscuous is set to True, the server will
        respond with an empty body and a 200 status code. If promiscuous is set
        to False it returns an empty body and a 404 status code.
        """
        self.raw_requestline = self.rfile.readline(65537)
        self.parse_request()
        headers = "Content-Length: {}"

        handler, custom_headers = self.find_handler()
        if custom_headers:
            custom_headers = ['{}: {}'.format(k, v) for k, v in custom_headers.items()]
            custom_headers = "\r\n".join(custom_headers)
            headers = "\r\n".join([headers, custom_headers])

        if handler:
            body, status = self._call_handler(handler)
            headers = headers.format(len(body))
            response = "HTTP/1.1 {0} OK\r\n{1}\r\n\r\n{2}".format(status, headers, body)
            self.response = response
            self.request.sendall(response)
            return

        self.response = "HTTP/1.1 200 OK\r\n{}".format(headers.format(0))
        self.request.sendall(self.response)

    def _call_handler(self, handler, *args):
        response = handler()
        if type(response) is not tuple:
            raise ValueError("handler function should return 2 arguments.")
        if len(response) != 2:
            raise ValueError("handler function should return 2 arguments.")
        if type(response[1]) is not int:
            raise ValueError("handler function second return type must be an integer indicating the status code.")

        return response

    def find_handler(self):
        if not hasattr(self, "handlers"):
            return False, False

        if not self.method in self.handlers.keys():
            return False, False
        else:
            for handler_dict in self.handlers[self.method]:
                path, handler_fn = handler_dict["handler"]
                if path == self.path:
                    return handler_fn, handler_dict["headers"]
        return False, False

    def parse_request(self):
        """
        Parses the request first line to get the status and method.
        Saves it on instances variables.
        """
        reqline = self.raw_requestline.rstrip('\r\n')
        self.requestline = reqline

        words = reqline.split()
        if len(words) == 3:
            method, path, _ = words
        elif len(words) == 2:
            method, path = words
        else:
            self.send_error(400, "Bad request syntax (%r)" % self.requestline)
            return

        self.method = method
        self.path = path
        Bogus.called_paths.append(path) # so the user can know what has been called

    @classmethod
    def register_handler(cls, handler, method="GET", headers=None):
        """
        Register a handler within a given method, the default method is get.
        The data structure used to store the handler is a dictionary of arrays, each array
        entry contains the handler tuple (path, callable). It looks like this:
            {"GET": ("/profile", profileHandler), ("/settings", settingsHandler)}
        The registered handler should return 2 values, the response body and status code.
        """
        if not hasattr(cls, "handlers"):
            cls.handlers = {method: [{"handler": handler, "headers": headers}]}
        elif method in cls.handlers.keys():
            cls.handlers[method].append({"handler": handler, "headers": headers})
        else:
            cls.handlers[method] = [{"handler": handler, "headers": headers}]


class Bogus(object):

    called_paths = []

    def __init__(self, promiscuous=True):
        self.promiscuous = promiscuous

    def serve(self):
        """
        Starts up the HTTP server.
        """
        httpd = SocketServer.TCPServer(("127.0.0.1", 0), BogusHandler)
        thread = Thread(target=httpd.serve_forever)
        thread.setDaemon(True)
        thread.start()
        while not thread.is_alive():
            continue
        self.url = "http://{0}:{1}".format(httpd.server_address[0], httpd.server_address[1])
        return self.url

    def register(self, handler, method="GET", headers=None):
        BogusHandler.register_handler(handler, method, headers)
