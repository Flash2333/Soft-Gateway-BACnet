#     Copyright 2024. ThingsBoard
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

import time
from threading import Thread

from bacpypes3.primitivedata import ObjectIdentifier

from connectors.bacnet.bacnet_uplink_converter import AsyncBACnetUplinkConverter
from connectors.bacnet.entities.bacnet_device_details import BACnetDeviceDetails
from connectors.bacnet.entities.device_info import DeviceInfo
from connectors.bacnet.entities.device_object_config import DeviceObjectConfig
from connectors.bacnet.entities.uplink_converter_config import UplinkConverterConfig
from gateway.constants import UPLINK_PREFIX, CONVERTER_PARAMETER
from tb_utility.tb_loader import TBModuleLoader
from tb_utility.tb_logger import TbLogger


class Device(Thread):
    def __init__(self, connector_type, config, i_am_request, callback, logger: TbLogger):
        super().__init__()

        self.__connector_type = connector_type
        self.__config = config
        DeviceObjectConfig.update_address_in_config_util(self.__config)
        self.alternative_responses_addresses = self.__config.get('altResponsesAddresses', [])

        self.__log = logger

        self.__stopped = False
        self.active = True
        self.callback = callback
        self.daemon = True

        if not hasattr(i_am_request, 'deviceName'):
            i_am_request.deviceName = str(i_am_request.iAmDeviceIdentifier[1])
            #self.__log.debug('Device name is not provided in IAmRequest. Device Id will be used as "objectName') # warning->debug
        self.details = BACnetDeviceDetails(i_am_request)
        self.device_info = DeviceInfo(self.__config.get('deviceInfo', {}), self.details)
        self.uplink_converter_config = UplinkConverterConfig(self.__config, self.device_info, self.details)

        self.name = self.device_info.device_name

        self.__poll_period = self.__config.get('pollPeriod', 10000) / 1000
        self.attributes_updates = self.__config.get('attributeUpdates', [])
        self.server_side_rpc = self.__config.get('serverSideRpc', [])

        self.uplink_converter = self.__load_uplink_converter()

        self.__last_poll_time = 0

        self.start()

    def __str__(self):
        return f"Device(name={self.name}, address={self.details.address})"

    def __load_uplink_converter(self):
        try:
            if self.__config.get(UPLINK_PREFIX + CONVERTER_PARAMETER) is not None:
                converter_class = TBModuleLoader.import_module(self.__connector_type,
                                                               self.__config[UPLINK_PREFIX + CONVERTER_PARAMETER])
                converter = converter_class(self.uplink_converter_config, self.__log)
            else:
                converter = AsyncBACnetUplinkConverter(self.uplink_converter_config, self.__log)

            return converter
        except Exception as e:
            self.__log.exception('Failed to load uplink converter for % device: %s', self.name, e)

    def stop(self):
        self.active = False
        self.__stopped = True

    def run(self):
        while not self.__stopped:
            if time.monotonic() - self.__last_poll_time >= self.__poll_period and self.active:
                self.__send_callback()
                self.__last_poll_time = time.monotonic()

            time.sleep(.01)

    def __send_callback(self):
        try:
            self.callback(self)
        except Exception as e:
            self.__log.error('Error sending callback from device %s: %s', self, e)

    @staticmethod
    def find_self_in_config(devices_config, device_address): #apdu => device_address, 解决非IP地址(比如：SNET:SADR)的转换问题，没有exploded属性
        #device_config = list(filter(lambda x: x['address'] == apdu.pduSource.exploded or apdu.pduSource.exploded in x.get('altResponsesAddresses', []), devices_config))
        device_config = list(filter(lambda x: x['address'] == device_address
                                              or device_address in x.get('altResponsesAddresses', []), devices_config))
        if len(device_config):
            return device_config #[0] 更新为返回所有设备，而不是第1个，updated by jackie kuang

    @staticmethod
    def get_object_id(config):
        return ObjectIdentifier("%s:%s" % (config['objectType'], config['objectId']))
