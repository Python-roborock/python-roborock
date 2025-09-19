from roborock.broadcast_protocol import RoborockProtocol


def test_l01_data():
    data = bytes.fromhex(
        "4c30310000000000000043841496d5a31e34b5b02c1867c445509ba5a21aec1fa4b307bddeb27a75d9b366193e8a97d0534dc39851c"
        "980609f2670cdcaee04594ec5c93e3c5ae609b0c9a203139ac8e40c8c"
    )
    prot = RoborockProtocol()
    prot.datagram_received(data, None)
    device = prot.devices_found[0]
    assert device.duid == "ZrQn1jfZtJQLoPOL7620e"
    assert device.ip == "192.168.1.4"
    assert device.version == b"L01"


def test_v1_data():
    data = bytes.fromhex(
        "312e30000003e003e80040b87035058b439f36af42f249605f8661897173f111bb849a6231831f5874a0cf220a25872ea412d796b4902ee"
        "57fdc120074b901b482acb1fe6d06317e3a72ddac654fe0"
    )
    prot = RoborockProtocol()
    prot.datagram_received(data, None)
    device = prot.devices_found[0]
    assert device.duid == "h96rOV3e8DTPMAOLiypREl"
    assert device.ip == "192.168.20.250"
    assert device.version == b"1.0"
