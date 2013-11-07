"""
Unit tests for TCPSocket.

Mocks a listener instead of sending real packets.

"""

from tcp import TCPSocket
from scapy.all import IP, TCP, Ether, rdpcap
from mock_listener import MockListener


def test_syn():
    listener = MockListener()
    conn = TCPSocket(listener, "localhost", 80)
    assert conn.state == "SYN-SENT"
    pkts = listener.received_packets
    assert len(pkts) == 1
    assert pkts[0].sprintf("%TCP.flags%") == "S"

def test_handshake():
    listener = MockListener()
    conn = TCPSocket(listener, "localhost", 80)
    initial_seq = conn.seq

    tcp_packet = TCP(dport=conn.src_port, flags="SA", seq=100, ack=initial_seq + 1)
    syn_ack = Ether() / IP(dst=conn.src_ip) / tcp_packet
    listener.dispatch(syn_ack)

    assert conn.seq == initial_seq + 1
    assert conn.state == "ESTABLISHED"

    # We should have sent exactly two packets
    # Check that they look okay
    pkts = listener.received_packets
    assert len(pkts) == 2
    syn, ack = pkts
    assert ack.seq == syn.seq + 1
    assert syn.sprintf("%TCP.flags%") == "S"
    assert ack.sprintf("%TCP.flags%") == "A"

def create_session(packet_log):
    listener = MockListener()
    syn = packet_log[0]
    listener.source_port = syn.sport - 1
    conn = TCPSocket(listener, syn.payload.dst, syn.dport, )
    # Change the sequence number so that we can test it
    conn.seq = syn.seq
    return listener, conn

def test_send_push_ack():
    packet_log = rdpcap("test/inputs/localhost-wget.pcap")
    listener, conn = create_session(packet_log)

    _, syn_ack, _, push_ack = packet_log[:4]
    listener.dispatch(syn_ack)
    assert conn.state == "ESTABLISHED"

    # Extract the payload (3 levels down: Ether, IP, TCP)
    payload = str(push_ack.payload.payload.payload)
    conn.send(payload)

    # Check to make sure the PUSH-ACK packet packet that gets sent looks good
    our_push_ack = listener.received_packets[-1]

    assert our_push_ack.seq == push_ack.seq
    assert our_push_ack.ack == push_ack.ack
    assert our_push_ack.load == push_ack.load
    assert our_push_ack.sprintf("%TCP.flags%") == push_ack.sprintf("%TCP.flags%")


def test_fin_ack():
    packet_log = rdpcap("test/inputs/tiniest-session.pcap")
    listener, conn = create_session(packet_log)




