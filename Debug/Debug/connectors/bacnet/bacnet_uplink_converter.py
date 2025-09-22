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
from twisted.python.util import println

from connectors.bacnet.bacnet_converter import AsyncBACnetConverter
from connectors.bacnet.entities.uplink_converter_config import UplinkConverterConfig
from gateway.entities.converted_data import ConvertedData
from gateway.entities.report_strategy_config import ReportStrategyConfig
from gateway.statistics.statistics_service import StatisticsService
from tb_utility.tb_utility import TBUtility


class AsyncBACnetUplinkConverter(AsyncBACnetConverter):
    def __init__(self, config: UplinkConverterConfig, logger):
        self.__log = logger
        self.__config = config

    def convert(self, data):
        if len(data):
            StatisticsService.count_connector_message(self.__log.name, 'convertersMsgProcessed')
            converted_data = ConvertedData(device_name=self.__config.device_name, device_type=self.__config.device_type)
            converted_data_append_methods = {
                'attributes': converted_data.add_to_attributes,
                'telemetry': converted_data.add_to_telemetry
            }

            device_report_strategy = self._get_device_report_strategy(self.__config.report_strategy,
                                                                      self.__config.device_name)

            for config, value in zip(self.__config.objects_to_read, data):
                if isinstance(value, Exception):
                    self.__log.error("Error reading object for key \"%s\", objectId: \"%s\", and propertyId: \"%s\". Error: %s",
                                     config.get('key'),
                                     config.get('objectId',
                                                config.get("objectType", "None") + ":" + config.get("objectId", "None")
                                                ),
                                     config.get('propertyId'),
                                     value)
                    continue

                # 定义转换公式，by jackie kuang
                value_converted = round(value, 2) if isinstance(value, float) else value #注意：必须转，否则小数位数太长会报错：Type is not JSON serializable: Real
                conversion_exp = config.get("conversionExpression", None)
                if conversion_exp is not None and conversion_exp != "":
                    try:
                        conversion_exp = conversion_exp.replace('value',str(value))
                        value_converted = eval(conversion_exp)
                    except Exception as e:
                        self.__log.error("Error converting with custom expression %s: %s", config.get('key'), e)

                try:
                    datapoint_key = TBUtility.convert_key_to_datapoint_key(config['key'],
                                                                           device_report_strategy,
                                                                           config,
                                                                           self.__log)
                    converted_data_append_methods[config['type']]({datapoint_key: value_converted})
                except Exception as e:
                    self.__log.error("Error converting datapoint with key %s: %s", config.get('key'), e)

            StatisticsService.count_connector_message(self.__log.name,
                                                      'convertersAttrProduced',
                                                      count=converted_data.attributes_datapoints_count)
            StatisticsService.count_connector_message(self.__log.name,
                                                      'convertersTsProduced',
                                                      count=converted_data.telemetry_datapoints_count)

            self.__log.debug("Converted data: %s", converted_data)
            return converted_data

    def _get_device_report_strategy(self, report_strategy, device_name):
        try:
            return ReportStrategyConfig(report_strategy)
        except ValueError as e:
            self.__log.trace("Report strategy config is not specified for device %s: %s", device_name, e)
