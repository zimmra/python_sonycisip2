
from .commandset import commands_dict
from .variables import variables_dict

# Importing required modules
import socket
import json
import asyncio
import logging
from asyncio import Semaphore, Queue

# Defining constants for message types
SET = "set"
GET = "get"
NOTIFY = "notify"
RESULT = "result"

class SonyCISIP2:
    _semaphore = Semaphore(2)

    def __init__(self, host, port=33336, loop=None):
        """
        Initialize the SonyCISIP2 class with the IP address and port of the Sony receiver.
        """
        self.host = host
        self.port = port
        self.loop = loop if loop else asyncio.get_event_loop()
        self.socket = None
        self.logger = logging.getLogger(__name__)
        self.response_queue = Queue()
        self.notification_callback = None 


    async def connect(self):
        """
        Asynchronously establish a TCP socket connection to the Sony receiver.
        """
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            # Start listening for incoming messages in the background
            asyncio.create_task(self.listen_for_incoming_messages())
            print("Started listening for incoming messages.")
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            return False
        return True

    async def send_message(self, message_type, feature, value=None):
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
        try:
            self.writer.write(json_message.encode('utf-8'))
            await self.writer.drain()  # Ensure the message is sent
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")

    async def listen_for_incoming_messages(self):
        """
        Continuously listen for incoming messages from the Sony receiver.
        """
        print("Listening for incoming messages...")
        try:
            while True:
                data = await self.reader.read(1024)
                if data:
                    message = json.loads(data.decode('utf-8'))
                    if message["type"] == NOTIFY:
                        self.handle_notification(message)  # Handle notifications directly
                    elif message["type"] == RESULT:
                        await self.response_queue.put(message)  # Enqueue responses
        except asyncio.CancelledError:
            # Handle cancellation of the task
            pass
        except Exception as e:
            print(f"Error in incoming message listener: {e}")

    async def receive_message(self):
        """
        Receive a message from the queue
        """
        try:
            message = await self.response_queue.get()
            return message
        except Exception as e:
            self.logger.error(f"Failed to receive message: {e}")
            return None

    async def send_and_receive_message(self, message_type, feature, value=None):
        """
        Asynchronously send a message to the Sony receiver and wait for a reply.
        Constructs a JSON message based on the type, feature, and value provided.
        Returns the received response.
        """
        async with self._semaphore:
            await self.send_message(message_type, feature, value)
            return await self.receive_message()

    async def set_feature(self, feature, value):
        """
        Asynchronously send a 'set' command to the Sony receiver to set a feature to a specific value.
        Returns the result as 'ACK', 'NAK', or 'ERR'.
        """
        async with self._semaphore:
            await self.send_message(SET, feature, value)
            response = await self.receive_message()
            result_value = response.get("value", "Unknown Response") if response else "Unknown Response"
            return result_value

    async def get_feature(self, feature):
        """
        Asynchronously send a 'get' command to the Sony receiver to get the value of a feature.
        Returns the value of the feature.
        """
        async with self._semaphore:
            await self.send_message(GET, feature)
            response = await self.receive_message()
            return response.get("value", "Unknown Value") if response else "Unknown Value"


    def register_notification_callback(self, callback):
        """
        Register a callback function to be called when a notification is received.
        """
        self.notification_callback = callback

    def handle_notification(self, message):
        """
        Handle received notification messages.
        Call the registered notification callback function.
        """
        print(f"NOTIFICATION: {message}")
        if self.notification_callback:
            self.notification_callback(message)

# Additional utility function remains the same (future use)
def replace_command_placeholders(command_str, variables_dict):
    """
    Replaces placeholders in the command string with actual values from the variables dictionary.
    """
    for placeholder, value in variables_dict.items():
        command_str = command_str.replace(f"{{{{{placeholder}}}}}", value)
    return command_str
