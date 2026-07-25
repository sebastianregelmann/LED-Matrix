import time
import paho.mqtt.client as mqtt
import json

class MQTTClient():
    client: mqtt.Client
    topic : str
    broker_address : str
    broker_port : int
    frame_driver : object

    def __init__(self, frame_driver : object, topic : str, broker_address : str,broker_port : int):
        self.frame_driver = frame_driver
        self.topic = topic
        self.broker_address = broker_address
        self.broker_port = broker_port

        self.init_mqqt_client()


    def init_mqqt_client(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        # Assign callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        #connect to broker
        self.client.connect(self.broker_address, self.broker_port, keepalive=60)

        # Start the background thread network loop
        self.client.loop_start()


    # 1. Define callback functions
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("[MQTT CLIENT] Connected successfully to broker!")
            # Subscribe to topics inside on_connect to ensure re-subscriptions 
            self.client.subscribe(self.topic, qos=1)
            self.frame_driver.set_mqtt_client(self)
        else:
            print(f"[MQTT CLIENT] Connection failed with code {reason_code}")

    def on_message(self, client, userdata, msg):
        print(f"[MQTT CLIENT] Received message -> Topic: {msg.topic}")
        try:
            payload_str = msg.payload.decode('utf-8')
            data_dict = json.loads(payload_str)

            self.frame_driver.handle_mode_change_request(data_dict)
        except Exception as e:
            print(f"[MQTT CLIENT] Failed to handle mode change Error: {e} ")


    def publish_status_message(self):
        try: 
            data_dict = self.frame_driver.current_status()
            self.client.publish(self.topic, json.dumps(data_dict))            
            print("[MQTT CLIENT] Published Status")
        except Exception as e:
            print(f"[MQTT CLIENT] Failed to publish data Error: {e} ")
