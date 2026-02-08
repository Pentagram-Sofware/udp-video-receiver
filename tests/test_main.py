import builtins
import unittest
from unittest import mock

import main


class DummySocket:
    def setsockopt(self, *args, **kwargs):
        pass

    def settimeout(self, *args, **kwargs):
        pass

    def bind(self, *args, **kwargs):
        pass

    def getsockname(self):
        return ("0.0.0.0", 9999)

    def close(self):
        pass


class TestUDPVideoClientRouting(unittest.TestCase):
    def test_routes_pickle_jpeg(self):
        client = main.UDPVideoClient.__new__(main.UDPVideoClient)
        client.stream_format = "pickle_jpeg"
        client.process_pickled_frame = mock.Mock()
        client.process_h264_frame = mock.Mock()

        client.process_frame_data(b"data")

        client.process_pickled_frame.assert_called_once_with(b"data")
        client.process_h264_frame.assert_not_called()

    def test_routes_h264(self):
        client = main.UDPVideoClient.__new__(main.UDPVideoClient)
        client.stream_format = "h264"
        client.process_pickled_frame = mock.Mock()
        client.process_h264_frame = mock.Mock()

        client.process_frame_data(b"data")

        client.process_h264_frame.assert_called_once_with(b"data")
        client.process_pickled_frame.assert_not_called()

    def test_h264_requires_pyav(self):
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            # Force PyAV import to fail while allowing other imports.
            if name == "av":
                raise ImportError("No module named av")
            return real_import(name, *args, **kwargs)

        with mock.patch("socket.socket", return_value=DummySocket()):
            with mock.patch("builtins.__import__", side_effect=fake_import):
                with self.assertRaises(RuntimeError) as ctx:
                    main.UDPVideoClient("127.0.0.1", stream_format="h264")

        self.assertIn("PyAV", str(ctx.exception))
