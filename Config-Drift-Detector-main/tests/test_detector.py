from detector import detect_drift

def test_no_drift():
    actual = {"port": 8080}
    intended = {"port": 8080}

    result = detect_drift(actual, intended)

    assert len(result) == 0

def test_port_drift():
    actual = {"port": 8080}
    intended = {"port": 9090}

    result = detect_drift(actual, intended)

    assert len(result) > 0

def test_debug_drift():
    actual = '{"debug": true}'
    intended = '{"debug": false}'

    result = detect_drift(intended, actual, "json")

    assert len(result) > 0

def test_cisco_ios_drift():
    intended = """
hostname Router-1
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0
 no shutdown
router ospf 10
 network 192.168.1.0 0.0.0.255 area 0
"""
    actual = """
hostname Router-1
interface GigabitEthernet0/0
 ip address 192.168.1.254 255.255.255.0
 shutdown
router ospf 10
 network 192.168.1.0 0.0.0.255 area 50
"""
    result = detect_drift(intended, actual, "cisco")
    assert len(result) >= 2
    # Verify CCNA severity categorization
    severities = [r['severity'] for r in result]
    assert 'Breaking' in severities

