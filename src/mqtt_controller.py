import json
import paho.mqtt.client as mqtt
import config


class MQTTController(object):

    def __init__(self):
        self.mqtt_connected = False
        self.client = mqtt.Client()
        self.client.on_connect = self.onConnect
        self.client.on_disconnect = self.onDisconnect

        try:
            print("Authenticating with user:", config.MQTT_USER, "on MQTT connection")
            self.client.username_pw_set(config.MQTT_USER, config.MQTT_PASS)
        except:
            print("Using no authentication on MQTT connection")

        if config.MQTT_USE_TLS:
            print("using TLS for MQTT Connection")
            self.client.tls_set()

        try:
            self.client.connect(config.MQTT_SERVER, config.MQTT_PORT, 60)
        except:
            print("Cannot connect to MQTT Broker:", config.MQTT_SERVER, "at port:", config.MQTT_PORT)

        self.client.loop_start()  # Start MQTT handling in a new thread

    def getConnected(self):
        return self.mqtt_connected

    def onConnect(self, client, userdata, flags, rc):
        print("Connected to MQTT Broker:", config.MQTT_SERVER, "at port:", config.MQTT_PORT)
        self.mqtt_connected = True

    def onDisconnect(self, client, userdata, rc):
        print("Disconnected from MQTT Broker:", config.MQTT_SERVER, "at port:", config.MQTT_PORT)
        self.mqtt_connected = False

    def publishData(self, data):
        json_data = json.dumps(data, indent=4)
        self.client.publish(config.MQTT_BASE_TOPIC + "/" + config.NODE_ID, json_data, qos=2)
        #print("mqtt publish: ", data)
