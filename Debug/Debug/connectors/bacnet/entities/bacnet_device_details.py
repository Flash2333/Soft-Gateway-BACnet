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

from bacpypes3.apdu import IAmRequest
from bacpypes3.pdu import RemoteStation


class BACnetDeviceDetails:
    def __init__(self, i_am_request: IAmRequest):
        # 解决地址解析错误，updated by jackie kuang
        pdu = i_am_request.pduSource
        if isinstance(pdu, RemoteStation):
            saddr_hex = hex(pdu.addrAddr[0])
            saddr_dec = str(int(saddr_hex, 16))
            self.address = str(pdu.addrNet) + ":" + saddr_dec  #RemoteStation. 例如101:16
        else:
            self.address = pdu.exploded  # IP address

        self.__object_identifier = i_am_request.iAmDeviceIdentifier[1]
        self.__vendor_id = i_am_request.vendorID
        self.__object_name = i_am_request.deviceName

    def __str__(self):
        return (f"DeviceDetails(address={self.address}, objectIdentifier={self.__object_identifier}, "
                f"vendorId={self.__vendor_id}, objectName={self.__object_name}")

    @property
    def as_dict(self):
        return {
            "address": self.address,
            "objectIdentifier": self.__object_identifier,
            "vendorId": self.__vendor_id,
            "objectName": self.__object_name
        }
