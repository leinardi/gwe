import os
import sys
import logging
import threading
import time
import signal
import json
import socket
from typing import List, Dict, Optional, Tuple, Callable, Any
from ctypes import *

from Xlib import display
from Xlib.ext.nvcontrol import Gpu, Cooler
from injector import singleton, inject
import pynvml

# from gwe.model.clocks import Clocks
# from gwe.model.fan import Fan
# from gwe.model.gpu_status import GpuStatus
# from gwe.model.info import Info
# from gwe.model.overclock import Overclock
# from gwe.model.power import Power
# from gwe.model.status import Status
# from gwe.model.temp import Temp
from gwe.util.concurrency import synchronized_with_attr

_LOG = logging.getLogger(__name__)
nv_control_extension = False

# Socket configuration
SOCKET_PATH = "/tmp/nvidia_root_service.sock"


class NvidiaRepository:
    # TODO inject?
    @inject
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._gpu_count = 0
        self._gpu_setting_cache: List[Dict[str, str]] = []
        self._ctrl_display: Optional[str] = None

    def set_ctrl_display(self, ctrl_display: str) -> None:
        self._ctrl_display = ctrl_display

    @synchronized_with_attr("_lock")
    def has_nvml_shared_library(self) -> bool:
        try:
            pynvml.nvmlInit()
            pynvml.nvmlShutdown()
            return True
        except:
            _LOG.exception("Error while checking NVML Shared Library")
        return False

    @synchronized_with_attr("_lock")
    def has_min_driver_version(self) -> bool:
        try:
            pynvml.nvmlInit()
            driver = self._nvml_get_val(pynvml.nvmlSystemGetDriverVersion)
            pynvml.nvmlShutdown()
        except:
            _LOG.exception("Error while checking NVML Shared Library")
            return False
        vmajor = int(driver.split(".", 1)[0])
        if 'WAYLAND_DISPLAY' not in os.environ and vmajor >= 535 or vmajor >= 555:
            return True

    def _nvml_get_val(self, func, *args):
        try:
            return func(*args)
        except Exception as e:
            _LOG.error(f"NVML error in {func.__name__}: {e}")
            return None

    def set_fan_speed(self, gpu_index: int, speed: int = 100, manual_control: bool = False) -> bool:
        pynvml.nvmlInit()
        handle = self._nvml_get_val(pynvml.nvmlDeviceGetHandleByIndex, gpu_index)
        fan_indexes = self._nvml_get_val(pynvml.nvmlDeviceGetNumFans, handle)
        if fan_indexes is not None and fan_indexes > 0:
            for fan_index in range(fan_indexes):
                try:
                    if manual_control:
                        ret = pynvml.nvmlDeviceSetFanSpeed_v2(handle, fan_index, speed)
                        _LOG.error(f"test set_fan_speed 3: {ret}")
                    else:
                        ret = pynvml.nvmlDeviceSetDefaultFanSpeed_v2(handle, fan_index)
                        _LOG.error(f"test set_fan_speed 4: {ret}")
                except pynvml.NVMLError as err:
                    _LOG.warning(f"Error setting speed for fan{fan_index} on gpu{gpu_index}: {err}")
                    return True
        pynvml.nvmlShutdown()


def check_root_privileges():
    """
    Check if the current process is running with root privileges.

    Raises:
        PermissionError: If the process is not running as root.
    """
    if os.geteuid() != 0:
        raise PermissionError("This service must be run as root")


# Flag to control the service loop
running = True


def signal_handler(sig, frame):
    """Handle termination signals to gracefully shut down the service"""
    global running
    print("Received termination signal. Shutting down...")
    running = False


def setup_logging():
    """Configure logging for the service"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def handle_client_request(repo, data):
    """Process client requests and execute the appropriate functions"""
    try:
        command = data.get('command')
        params = data.get('params', {})

        if command == 'set_fan_speed':
            gpu_index = params.get('gpu_index', 0)
            speed = params.get('speed', 100)
            manual_control = params.get('manual_control', True)

            result = repo.set_fan_speed(gpu_index, speed, manual_control)
            return {'success': result}
        elif command == 'has_nvml_shared_library':
            result = repo.has_nvml_shared_library()
            return {'success': True, 'result': result}
        elif command == 'has_min_driver_version':
            result = repo.has_min_driver_version()
            return {'success': True, 'result': result}
        else:
            return {'success': False, 'error': f'Unknown command: {command}'}
    except Exception as e:
        _LOG.exception(f"Error handling client request: {e}")
        return {'success': False, 'error': str(e)}


def setup_socket_server():
    """Set up the Unix domain socket server for IPC"""
    # Remove the socket file if it already exists
    try:
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)
    except OSError as e:
        _LOG.error(f"Error removing existing socket file: {e}")
        sys.exit(1)

    # Create the socket server
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)

    # Set permissions to allow non-root processes to connect
    os.chmod(SOCKET_PATH, 0o666)

    server.listen(5)
    server.settimeout(1.0)  # 1 second timeout to allow checking the running flag

    return server


def main():
    try:
        check_root_privileges()
        setup_logging()

        # Register signal handlers for graceful termination
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        print("NVIDIA root service started. Running until terminated...")
        _LOG.info("NVIDIA root service started")

        # Initialize repository
        repo = NvidiaRepository()

        # Set up socket server
        server = setup_socket_server()
        _LOG.info(f"Socket server listening on {SOCKET_PATH}")

        # Main service loop
        while running:
            try:
                # Accept connections with timeout to allow checking the running flag
                client, _ = server.accept()
                client.settimeout(5.0)  # 5 second timeout for client operations

                try:
                    # Receive data from client
                    data = b''
                    while True:
                        chunk = client.recv(4096)
                        if not chunk:
                            break
                        data += chunk

                    if data:
                        # Parse the request
                        request = json.loads(data.decode('utf-8'))
                        _LOG.info(f"Received request: {request}")

                        # Process the request
                        response = handle_client_request(repo, request)

                        # Send the response
                        client.sendall(json.dumps(response).encode('utf-8'))
                finally:
                    client.close()
            except socket.timeout:
                # This is expected due to the timeout we set
                pass
            except Exception as e:
                if running:  # Only log if we're still supposed to be running
                    _LOG.exception(f"Error in socket server: {e}")

        # Clean up
        server.close()
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)

        _LOG.info("NVIDIA root service shutting down")
        print("NVIDIA root service shut down")

    except PermissionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        _LOG.exception("Unexpected error in NVIDIA root service")
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

# test with sudo python3 -m gwe.repository.nvidia_root_service
if __name__ == '__main__':
    main()
