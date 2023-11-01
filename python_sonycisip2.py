
from commandset import commands_dict
from variables import variables_dict

import socket
import json
import asyncio

class SonyCISIP2:
    def __init__(self, host, port=33336):
        """
        Initialize the SonyCISIP2 class with the IP address and port of the Sony receiver.
        """
        self.host = host
        self.port = port
        self.socket = None

    def connect(self):
        """
        Establish a TCP socket connection to the Sony receiver.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))

    def send_message(self, message_type, feature, value=None):
        """
        Send a message to the Sony receiver.
        Constructs a JSON message based on the type, feature, and value provided.
        """
        message = {
            "type": message_type,
            "feature": feature
        }
        if value is not None:
            message["value"] = value

        json_message = json.dumps(message)
        self.socket.sendall(json_message.encode('utf-8'))

    def receive_message(self):
        """
        Receive a message from the Sony receiver.
        Returns the message as a JSON object.
        """
        data = self.socket.recv(1024)
        return json.loads(data.decode('utf-8'))

    def send_and_receive_message(self, message_type, feature, value=None):
        """
        Send a message to the Sony receiver and wait for a reply.
        Constructs a JSON message based on the type, feature, and value provided.
        Returns the received response.
        """
        self.send_message(message_type, feature, value)
        return self.receive_message()


    def set_feature(self, feature, value):
        """
        Send a 'set' command to the Sony receiver to set a feature to a specific value.
        Returns the result as 'ACK', 'NAK', or 'ERR'.
        """
        self.send_message("set", feature, value)
        response = self.receive_message()
        result_value = response.get("value", "Unknown Response")
        if result_value in ["ACK", "NAK", "ERR"]:
            return result_value
        else:
            return "Unknown Response"

    commands_dict = commands_dict
    variables_dict = variables_dict

    def get_feature(self, feature):
        """
        Send a 'get' command to the Sony receiver to get the value of a feature.
        Returns the value of the feature.
        """
        self.send_message("get", feature)
        response = self.receive_message()
        return response.get("value", "Unknown Value")

    async def listen_for_notifications(self, callback=None):
        """
        Asynchronously listen for 'notify' messages from the Sony receiver.
        If a callback function is provided, it will be invoked with the notification message.
        """
        while True:
            message = self.receive_message()
            if message["type"] == "notify":
                if callback:
                    callback(message)
                else:
                    print(f"Received notification: {message}")
            await asyncio.sleep(0.1)  # To prevent high CPU usage

def replace_command_placeholders(command_str, variables_dict):
    """
    Replaces placeholders in the command string with actual values from the variables dictionary.
    """
    for placeholder, value in variables_dict.items():
        command_str = command_str.replace(f"{{{{{placeholder}}}}}", value)
    return command_str
