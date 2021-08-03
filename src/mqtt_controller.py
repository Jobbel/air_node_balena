import json

import paho.mqtt.client as mqtt
import yaml

config = yaml.safe_load(open("config.yml"))


class MQTTController(object):

    def __init__(self, config):
        self._config = config
        self.mqtt_connected = False
        self.client = mqtt.Client()
        self.client.on_connect = self.onConnect
        self.client.on_disconnect = self.onDisconnect

        if 'mqtt_user' in config and 'mqtt_pass' in self._config:
            print("Authenticating with user:", self._config['mqtt_user'], "on MQTT Connection")
            self.client.username_pw_set(config['mqtt_user'], self._config['mqtt_pass'])

        if config['mqtt_use_tls'] is True:
            print("using TLS for MQTT Connection")
            self.client.tls_set()

        try:
            self.client.connect(self._config['mqtt_server'], self._config['mqtt_port'], 60)
        except:
            print("Cannot connect to MQTT Broker:", self._config['mqtt_server'], "at port:", self._config['mqtt_port'])

        self.client.loop_start()  # Start MQTT handling in a new thread

    def onConnect(self, client, userdata, flags, rc):
        print("Connected to MQTT Broker:", self._config['mqtt_server'], "at port:", self._config['mqtt_port'])
        self.mqtt_connected = True

    def onDisconnect(self, client, userdata, rc):
        print("Disconnected from MQTT Broker:", self._config['mqtt_server'], "at port:", self._config['mqtt_port'])
        self.mqtt_connected = False

    def publishData(self, data):
        json_data = json.dumps(data, indent=4)
        self.client.publish(self._config['mqtt_base_topic'] + "/" + self._config['node_id'], json_data, qos=2)
        #print("mqtt publish: ", data)
