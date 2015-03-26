import unittest
import requests
from bogus.server import Bogus, BogusHandler
from mock import Mock

class BogusTest(unittest.TestCase):

    def test_init_should_default_promiscuous_flag_to_True(self):
        b = Bogus()
        self.assertTrue(b.promiscuous)

    def test_init_with_promiscuous_false(self):
        b = Bogus(promiscuous=False)
        self.assertFalse(b.promiscuous)

    def test_serve_should_return_and_store_url(self):
        b = Bogus()
        url = b.serve()
        self.assertEqual(url, b.url)

    # intermitent?
    def test_serve_should_start_server_and_respond_to_any_request(self):
        b = Bogus()
        url = b.serve()
        response = requests.get("{}/something".format(url))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, "")
        response = requests.get("{}/something-else".format(url))
        self.assertEqual(response.status_code, 200)

    def test_should_register_a_handler_and_request_it(self):
        b = Bogus()
        handler = ("/json", lambda: ('[{"foo":"bar"}]', 201))
        handler_dict = {"handler": handler, "headers": None}
        b.register(handler, method="POST")
        self.assertIn(handler_dict, BogusHandler.handlers["POST"])
        url = b.serve()
        response = requests.post("{}/json".format(url))
        self.assertEqual('[{"foo":"bar"}]', response.content)

    def test_should_have_called_paths(self):
        b = Bogus()
        url = b.serve()
        requests.get("{}/something".format(url))
        self.assertTrue(hasattr(Bogus, "called_paths"))
        requests.get("{}/something-else".format(url))
        self.assertIn("/something", Bogus.called_paths)
        self.assertIn("/something-else", Bogus.called_paths)

    def test_should_have_set_headers_and_return_them(self):
        b = Bogus()
        handler = ("/headers", lambda: ('[{"foo":"bar"}]', 201))
        handler_dict = {"handler": handler, "headers": {"Location": "/foo/bar"}}
        b.register(handler, method="POST", headers={"Location": "/foo/bar"})
        self.assertIn(handler_dict, BogusHandler.handlers["POST"])
        url = b.serve()
        response = requests.post("{}/headers".format(url))
        self.assertEqual(response.headers.get("Location"), "/foo/bar")


class BogusHandlerTest(unittest.TestCase):

    def setUp(self):
        self.request_mock = Mock()
        # mocks the request line, see http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5
        self.request_mock.makefile.return_value.readline.return_value = "GET /profile HTTP/1.1"
        BogusHandler.handlers = {}
        self.response_line = "HTTP/1.1 {} OK\r\nContent-Length: {}\r\n\r\n{}"

    def test_should_have_a_handle_method(self):
        bh = BogusHandler(self.request_mock, "client_address", "server")
        self.assertTrue(hasattr(bh, "handle"))

    def test_should_register_handlers(self):
        handler = ("/profile", lambda: ("Profile", 200))
        handler_dict = {"handler": handler, "headers": None}
        BogusHandler.register_handler(handler)
        self.assertIn(handler_dict, BogusHandler.handlers["GET"])

        handler = ("/register", lambda: ("Register", 200))
        handler_dict = {"handler": handler, "headers": None}
        BogusHandler.register_handler(handler)
        self.assertIn(handler_dict, BogusHandler.handlers["GET"])

        handler_dict = {"handler": handler, "headers": None}
        BogusHandler.register_handler(handler, method="POST")
        self.assertIn(handler_dict, BogusHandler.handlers["POST"])

    def test_should_register_handler_and_respond_to_request_for_that_handler(self):
        BogusHandler.register_handler(("/register", lambda: ("Register", 200)), method="POST")
        BogusHandler.register_handler(("/profile", lambda: ("Profile", 200)))

        bh = BogusHandler(self.request_mock, "client_address", "server")
        bh.handle()
        expected_response = "Profile"
        expected_response = self.response_line.format(200, len(expected_response), expected_response)
        self.request_mock.sendall.assert_called_with(expected_response)

    def test_send_response_should_first_store_it_on_instance_variable(self):
        BogusHandler.register_handler(("/user/create", lambda: ("user created", 201)), method="POST")
        self.request_mock.makefile.return_value.readline.return_value = "POST /user/create HTTP/1.1"
        bh = BogusHandler(self.request_mock, "client_address", "server")
        bh.handle()

        self.assertTrue(hasattr(bh, "response"))
        expected = "user created"
        expected = self.response_line.format(201, len(expected), expected)
        self.assertEqual(bh.response, expected)
        self.request_mock.sendall.assert_called_with(expected)

    def test_handle_should_validate_an_invalid_handler_return(self):
        BogusHandler.register_handler(("/profile", lambda: (200)))

        with self.assertRaises(ValueError) as e:
            bh = BogusHandler(self.request_mock, "client_address", "server")
            bh.handle()
            self.assertEqual(e.message, "handler function should return 2 arguments.")

    def test_call_handler_calls_handler_returns_response_and_raises_exception_if_its_invalid(self):
        bh = BogusHandler(self.request_mock, "client_address", "server")
        with self.assertRaises(ValueError) as e:
            bh._call_handler(lambda: 200)
            self.assertEqual(e.message, "handler function should return 2 arguments.")
