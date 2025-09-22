from bacpypes.core import run, stop
from bacpypes.pdu import Address, GlobalBroadcast
from bacpypes.app import BIPSimpleApplication
from bacpypes.apdu import WhoIsRequest, IAmRequest
from bacpypes.basetypes import DeviceObjectPropertyReference
from bacpypes.object import get_datatype

# 创建一个BACnet应用程序实例
app = BIPSimpleApplication(Address('192.168.1.100'))

# 定义一个回调函数来处理接收到的IAm请求
def iam_handler(apdu):
    print(f"Received IAm from device {apdu.iAmDeviceIdentifier[1]} at address {apdu.pduSource}")
    # 可以在这里添加代码来获取设备的更多信息，例如对象列表、属性值等

# 注册IAm请求的回调函数
app._request_handlers[IAmRequest] = iam_handler

# 发送WhoIs请求
request = WhoIsRequest()
app.request(request)

# 运行BACnet应用程序
run()
