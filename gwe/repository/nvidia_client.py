import os
import socket
import json
import logging
from typing import Dict, Any, Optional

_LOG = logging.getLogger(__name__)

# Socket configuration - must match the server
SOCKET_PATH = "/tmp/nvidia_root_service.sock"

# TODO check if service is running and if not show dialog that it can't work
class NvidiaRootClient:
    """Client for communicating with the NVIDIA root service"""

    @staticmethod
    def send_command(command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a command to the NVIDIA root service

        Args:
            command: The command to execute
            params: Parameters for the command

        Returns:
            Dict containing the response from the service
        """
        if params is None:
            params = {}

        request = {
            'command': command,
            'params': params
        }

        try:
            # Create a socket connection to the server
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(10.0)  # 10 second timeout
            client.connect(SOCKET_PATH)

            # Send the request
            client.sendall(json.dumps(request).encode('utf-8'))

            # Signal end of message
            client.shutdown(socket.SHUT_WR)

            # Receive the response
            data = b''
            while True:
                try:
                    chunk = client.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                except socket.timeout:
                    break

            # Parse and return the response
            if data:
                return json.loads(data.decode('utf-8'))
            else:
                return {'success': False, 'error': 'No response from service'}

        except ConnectionRefusedError:
            _LOG.error("Connection refused. Is the NVIDIA root service running?")
            return {'success': False, 'error': 'Connection refused'}
        except FileNotFoundError:
            _LOG.error(f"Socket file not found: {SOCKET_PATH}")
            return {'success': False, 'error': 'Socket file not found'}
        except Exception as e:
            _LOG.exception(f"Error communicating with NVIDIA root service: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            try:
                client.close()
            except:
                pass

    @staticmethod
    def set_fan_speed(gpu_index: int, speed: int = 100, manual_control: bool = True) -> bool:
        """
        Set the fan speed for a GPU

        Args:
            gpu_index: Index of the GPU
            speed: Fan speed percentage (0-100)
            manual_control: If True, set to manual mode with specified speed.
                           If False, reset to automatic/default mode.

        Returns:
            True if successful, False otherwise
        """
        response = NvidiaRootClient.send_command('set_fan_speed', {
            'gpu_index': gpu_index,
            'speed': speed,
            'manual_control': manual_control
        })

        return response.get('success', False)

    @staticmethod
    def has_nvml_shared_library() -> bool:
        """
        Check if the NVML shared library is available

        Returns:
            True if available, False otherwise
        """
        response = NvidiaRootClient.send_command('has_nvml_shared_library')
        if response.get('success', False):
            return response.get('result', False)
        return False

    @staticmethod
    def has_min_driver_version() -> bool:
        """
        Check if the minimum required driver version is installed

        Returns:
            True if minimum version is met, False otherwise
        """
        response = NvidiaRootClient.send_command('has_min_driver_version')
        if response.get('success', False):
            return response.get('result', False)
        return False
