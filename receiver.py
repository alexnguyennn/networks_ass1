from stp_packet import STPPacket
import pickle
import socket
import sys
import time


class Receiver:
    # Receiver ? match rec seq-num ? good (keep packet) : otherwise, discard
    # packet (or buffer) -> send back ack with ack number 10 (seq is number of
    # thing it's expecting)
    # if received a good packet, Receiver sends Sender an ack indicating next
    # packet with number 10 + len(data)
    #
    # you need to create this
    # receiver needs to have a sequence number so it can deal with
    # out-of-order packets
    # receiver receives stp_packet ad the writes the data inside the packet
    # connection_socket = socket.create_connection(socket.SOCK_DGRAM)
    # TODO on receive, check buffer, find max in order - send ack for highest possible

    def __init__(self, receiver_port, file_path):
        # TODO make file to write into when appropriate
        self.file_name = file_name
        # TODO check hostname - local?
        self.connection_socket = self.open_connection("", receiver_port)
        self.received_bytes = b''
        self.buffer_size = 4096
        self.log_name = "Receiver_log.txt"
        open(self.log_name, 'w').close()  # clear old log
        self.run_stats = {
            "bytes_received": 0,
            "segments_received": 0,
            "duplicates_received": 0
        }
        self.run_stats_msgs = {
            "bytes_received":
            'Amount of (original) Data Received (in bytes): {}\n',
            "segments_received":
            'Number of (original) Data Segments received: {}\n',
            "duplicates_received":
            'Number of Duplicate Segments received: {}\n'
        }
        self.start_time = time.time()
        self.packet_buffer = {}
        # set up in syn/synack/ack?
        self.next_seq_num = None

    def write_file(self, file_path):
        with open(file_path, 'wb') as handle:
            handle.write(self.received_bytes)

    def receive_packet(self):
        """
        return value indicating whether packet modified
        """
        data, addr = self.connection_socket.recvfrom(self.buffer_size)
        stp_packet = pickle.loads(data)  # data is property of stp_packet
        self.sender_address = addr
        print("Received packet. addr: {}".format(addr))
        stp_packet.print_properties()
        self.update_log('rcv', 'D', stp_packet)
        # TODO won't need this when synack is complete
        if not self.next_seq_num:
            self.next_seq_num = stp_packet.seq_num
        # buffer if new - could be out of order, though
        if stp_packet.seq_num not in self.packet_buffer.keys():
            self.packet_buffer[stp_packet.seq_num] = stp_packet
        else:
            self.run_stats["duplicates_received"] += 1

        # check if out of order - if in order, update expected seq
        if stp_packet.seq_num == self.next_seq_num:
            receiver.received_bytes += stp_packet.data
            # move window up; everything past this has been acknowledged
            del (self.packet_buffer[self.next_seq_num])
            self.next_seq_num = stp_packet.seq_num + len(stp_packet.data)
            # import ipdb
            # ipdb.set_trace()
            self.send_ack(stp_packet.ack_num, self.next_seq_num)
        if stp_packet.data != '~':
            return True
        return False

    def send_ack(self, seq_num, ack_num):
        # Data is blank - ack
        # seq num is next byte needed
        # we leave the receiver's sequence number as is as it is not transmitting
        # any data at the moment
        ack_packet = STPPacket('', seq_num, ack_num, ack=True)
        self.connection_socket.sendto(
            pickle.dumps(ack_packet), self.sender_address)
        self.update_log('snd', 'A', ack_packet)

    def open_connection(self, host, receiver_port):
        print("dummy")
        try:
            connection_socket = socket.socket(socket.AF_INET,
                                              socket.SOCK_DGRAM)
            connection_socket.bind((host, receiver_port))
            return connection_socket
        except socket.error:
            print("Failed to create socket")
            sys.exit()

    def close_connection(self):
        self.connection_socket.close()

    def update_log(self, packet_action, packet_type, stp_packet):
        if packet_action == "rcv":
            self.run_stats["bytes_received"] += len(stp_packet.data)
            # TODO Check if duplicate packet, incr counter received instead of below
            self.run_stats["segments_received"] += 1
        time_since_excution = (time.time() - self.start_time) * 1000  # ms
        with open(self.log_name, 'a') as handle:
            handle.write('{} {} {} {} {} {}\n'.format(
                packet_action, time_since_excution, packet_type,
                stp_packet.seq_num, len(stp_packet.data), stp_packet.ack_num))

    def close_log(self):
        with open(self.log_name, 'a') as handle:
            for key in self.run_stats_msgs:
                handle.write(self.run_stats_msgs[key]
                             .format(self.run_stats[key]))


n_expected_args = 3
if __name__ == "__main__":
    # do setup when run TODO make new log file?
    # python receiver.py receiver_port file.txt
    if len(sys.argv) < n_expected_args:
        print("Usage: python receiver.py receiver_port file.txt")
    else:

        receiver_port, file_name = sys.argv[1:]
        receiver = Receiver(int(receiver_port), file_name)
        print("Receiver setup, waiting on port: {}".format(receiver_port))
        while True:
            if receiver.receive_packet():
                # if not in order, this will be the last ordered ack
                print("received data")
            else:
                # receiver.send_ack(receiver.next_seq_num)
                receiver.write_file(file_name)
                receiver.close_connection()
                receiver.close_log()
                break
