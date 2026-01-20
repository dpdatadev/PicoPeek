import network
import time
import sys

from machine import Pin

# Implement WiFiManager class to handle Wi-Fi connections and scanning
# TODO :: Add Git Repo

# Wi-Fi credentials
# TODO - do something with these?
SSID = "CasaNonna888"
PASSWORD = "p@s$w0rD!!!"


class WiFiManager:
    """
    WiFiManager class to manage Wi-Fi connections and configurations.
    """

    def __init__(self, ssid, password, type="STA"):
        self.ssid = ssid
        self.password = password

        if type not in ["STA", "AP"]:
            raise ValueError("Type must be either 'STA' or 'AP'")

        if type == "STA":
            interface_type = network.STA_IF
            self.WLAN = network.WLAN(interface_type)
            self.WLAN.active(True)
            self.IPV4 = self.WLAN.ifconfig()[0]
            self.interface_type = interface_type
            self._scan_networks()
        elif type == "AP":
            raise ValueError("Only STA mode supported currently")

    @property
    def AvailableNetworks(self):
        return self._available_networks

    @property
    def PrimaryNetwork(self):
        if len(self._available_networks) > 0:
            return self._available_networks[0]
        else:
            return None

    @property
    def WIFI_SSID(self):
        return self.ssid

    @property
    def InterfaceType(self):
        return self.interface_type

    @property
    def IPV4Address(self):
        return self.IPV4

    @property
    def DefaultGateway(self):
        return self.WLAN.ifconfig()[2]

    @property
    def SubnetMask(self):
        return self.WLAN.ifconfig()[1]

    @property
    def DNS(self):
        return self.WLAN.ifconfig()[3]

    @property
    def Connected(self) -> bool:
        return self.WLAN.isconnected()

    def _connect(self):
        self.WLAN.connect(self.ssid, self.password)

    def _config(self):
        return self.WLAN.ifconfig()

    def WifiTest(self, max_attempts=10):

        wlan = self.WLAN
        if wlan.active() == False:
            wlan.active(True)

        pin = Pin("LED", Pin.OUT)

        print(f"Connecting to WLAN... {self.PrimaryNetwork}")
        self._connect()

        while max_attempts > 0:
            if self.Connected:
                pin.toggle()
                print("Connected to WLAN")
                print("Network config:", self._config())
                return self.IPV4Address  # Return the IP address
            print("Waiting for connection...")
            time.sleep(1)
            max_attempts -= 1

        print("Failed to connect to WLAN")
        pin.off()
        sys.exit()  # Exit if connection fails

    def clear_networks(self) -> None:
        self._available_networks = []

    def _scan_networks(self) -> None:
        wlan = self.WLAN
        if wlan.active() == False:
            wlan.active(True)
        self._available_networks = wlan.scan()


############################################################################
############################################################################
# µPing (MicroPing) for MicroPython
# copyright (c) 2018 Shawwwn <shawwwn1@gmail.com>
# License: MIT


# Internet Checksum Algorithm
# Author: Olav Morken
# https://github.com/olavmrk/python-ping/blob/master/ping.py
# @data: bytes
def checksum(data):
    if len(data) & 0x1:  # Odd number of bytes
        data += b"\0"
    cs = 0
    for pos in range(0, len(data), 2):
        b1 = data[pos]
        b2 = data[pos + 1]
        cs += (b1 << 8) + b2
    while cs >= 0x10000:
        cs = (cs & 0xFFFF) + (cs >> 16)
    cs = ~cs & 0xFFFF
    return cs


def ping(host, count=4, timeout=5000, interval=10, quiet=False, size=64):
    import utime
    import uselect
    import uctypes
    import usocket
    import ustruct
    import urandom

    # prepare packet
    assert size >= 16, "pkt size too small"
    pkt = b"Q" * size
    pkt_desc = {
        "type": uctypes.UINT8 | 0,
        "code": uctypes.UINT8 | 1,
        "checksum": uctypes.UINT16 | 2,
        "id": uctypes.UINT16 | 4,
        "seq": uctypes.INT16 | 6,
        "timestamp": uctypes.UINT64 | 8,
    }  # packet header descriptor
    h = uctypes.struct(uctypes.addressof(pkt), pkt_desc, uctypes.BIG_ENDIAN)
    h.type = 8  # type: ignore # ICMP_ECHO_REQUEST
    h.code = 0  # type: ignore
    h.checksum = 0  # type: ignore
    h.id = urandom.getrandbits(16)  # type: ignore
    h.seq = 1  # type: ignore

    # init socket
    sock = usocket.socket(usocket.AF_INET, usocket.SOCK_RAW, 1)
    sock.setblocking(0)  # type: ignore
    sock.settimeout(timeout / 1000)
    addr = usocket.getaddrinfo(host, 1)[0][-1][0]  # ip address
    sock.connect((addr, 1))
    not quiet and print("PING %s (%s): %u data bytes" % (host, addr, len(pkt)))  # type: ignore

    seqs = list(range(1, count + 1))  # [1,2,...,count]
    c = 1
    t = 0
    n_trans = 0
    n_recv = 0
    finish = False
    while t < timeout:
        if t == interval and c <= count:
            # send packet
            h.checksum = 0  # type: ignore
            h.seq = c  # type: ignore
            h.timestamp = utime.ticks_us()  # type: ignore
            h.checksum = checksum(pkt)  # type: ignore
            if sock.send(pkt) == size:
                n_trans += 1
                t = 0  # reset timeout
            else:
                seqs.remove(c)
            c += 1

        # recv packet
        while 1:
            socks, _, _ = uselect.select([sock], [], [], 0)  # type: ignore
            if socks:
                resp = socks[0].recv(4096)
                resp_mv = memoryview(resp)
                h2 = uctypes.struct(
                    uctypes.addressof(resp_mv[20:]), pkt_desc, uctypes.BIG_ENDIAN
                )
                # TODO: validate checksum (optional)
                seq = h2.seq
                if (
                    h2.type == 0 and h2.id == h.id and (seq in seqs)
                ):  # 0: ICMP_ECHO_REPLY
                    t_elasped = (utime.ticks_us() - h2.timestamp) / 1000
                    ttl = ustruct.unpack("!B", resp_mv[8:9])[0]  # time-to-live
                    n_recv += 1
                    not quiet and print(
                        "%u bytes from %s: icmp_seq=%u, ttl=%u, time=%f ms"
                        % (len(resp), addr, seq, ttl, t_elasped)
                    )  # pyright: ignore[reportUnusedExpression]
                    seqs.remove(seq)
                    if len(seqs) == 0:
                        finish = True
                        break
            else:
                break

        if finish:
            break

        utime.sleep_ms(1)
        t += 1

    # close
    sock.close()
    ret = (n_trans, n_recv)
    not quiet and print(
        "%u packets transmitted, %u packets received" % (n_trans, n_recv)
    )  # pyright: ignore[reportUnusedExpression]
    return (n_trans, n_recv)


############################################################################
############################################################################
# Complete project details: https://RandomNerdTutorials.com/raspberry-pi-pico-w-send-email-micropython/
# uMail (MicroMail) for MicroPython Copyright (c) 2018 Shawwwn <shawwwn1@gmai.com> https://github.com/shawwwn/uMail/blob/master/umail.py License: MIT
import usocket

DEFAULT_TIMEOUT = 10  # sec
LOCAL_DOMAIN = "127.0.0.1"
CMD_EHLO = "EHLO"
CMD_STARTTLS = "STARTTLS"
CMD_AUTH = "AUTH"
CMD_MAIL = "MAIL"
AUTH_PLAIN = "PLAIN"
AUTH_LOGIN = "LOGIN"


class SMTP:
    def cmd(self, cmd_str):
        sock = self._sock
        sock.write("%s\r\n" % cmd_str)
        resp = []
        next = True
        while next:
            code = sock.read(3)
            next = sock.read(1) == b"-"
            resp.append(sock.readline().strip().decode())
        return int(code), resp

    def __init__(self, host, port, ssl=False, username=None, password=None):
        import ssl

        self.username = username
        addr = usocket.getaddrinfo(host, port)[0][-1]
        sock = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        sock.settimeout(DEFAULT_TIMEOUT)
        sock.connect(addr)
        if ssl:
            sock = ssl.wrap_socket(sock)
        code = int(sock.read(3))
        sock.readline()
        assert code == 220, "cant connect to server %d, %s" % (code, resp)  # type: ignore
        self._sock = sock

        code, resp = self.cmd(CMD_EHLO + " " + LOCAL_DOMAIN)
        assert code == 250, "%d" % code
        if not ssl and CMD_STARTTLS in resp:
            code, resp = self.cmd(CMD_STARTTLS)
            assert code == 220, "start tls failed %d, %s" % (code, resp)
            self._sock = ssl.wrap_socket(sock)

        if username and password:
            self.login(username, password)

    def login(self, username, password):
        self.username = username
        code, resp = self.cmd(CMD_EHLO + " " + LOCAL_DOMAIN)
        assert code == 250, "%d, %s" % (code, resp)

        auths = None
        for feature in resp:
            if feature[:4].upper() == CMD_AUTH:
                auths = feature[4:].strip("=").upper().split()
        assert auths != None, "no auth method"

        from ubinascii import b2a_base64 as b64

        if AUTH_PLAIN in auths:
            cren = b64("\0%s\0%s" % (username, password))[:-1].decode()  # type: ignore
            code, resp = self.cmd("%s %s %s" % (CMD_AUTH, AUTH_PLAIN, cren))
        elif AUTH_LOGIN in auths:
            code, resp = self.cmd(
                "%s %s %s" % (CMD_AUTH, AUTH_LOGIN, b64(username)[:-1].decode())
            )
            assert code == 334, "wrong username %d, %s" % (code, resp)
            code, resp = self.cmd(b64(password)[:-1].decode())
        else:
            raise Exception("auth(%s) not supported " % ", ".join(auths))

        assert code == 235 or code == 503, "auth error %d, %s" % (code, resp)
        return code, resp

    def to(self, addrs, mail_from=None):
        mail_from = self.username if mail_from == None else mail_from
        code, resp = self.cmd(CMD_EHLO + " " + LOCAL_DOMAIN)
        assert code == 250, "%d" % code
        code, resp = self.cmd("MAIL FROM: <%s>" % mail_from)
        assert code == 250, "sender refused %d, %s" % (code, resp)

        if isinstance(addrs, str):
            addrs = [addrs]
        count = 0
        for addr in addrs:
            code, resp = self.cmd("RCPT TO: <%s>" % addr)
            if code != 250 and code != 251:
                print("%s refused, %s" % (addr, resp))
                count += 1
        assert count != len(addrs), "recipient refused, %d, %s" % (code, resp)

        code, resp = self.cmd("DATA")
        assert code == 354, "data refused, %d, %s" % (code, resp)
        return code, resp

    def write(self, content):
        self._sock.write(content)

    def send(self, content=""):
        if content:
            self.write(content)
        self._sock.write("\r\n.\r\n")  # the five letter sequence marked for ending
        line = self._sock.readline()
        return (int(line[:3]), line[4:].strip().decode())

    def quit(self):
        self.cmd("QUIT")
        self._sock.close()


############################################################################
############################################################################
# Network Utility
"""
Just for reference..
Python Socket Functions:

socket() -- create a new socket object
socketpair() -- create a pair of new socket objects [*]
fromfd() -- create a socket object from an open file descriptor [*]
send_fds() -- Send file descriptor to the socket.
recv_fds() -- Receive file descriptors from the socket.
fromshare() -- create a socket object from data received from socket.share() [*]
gethostname() -- return the current hostname
gethostbyname() -- map a hostname to its IP number
gethostbyaddr() -- map an IP number or hostname to DNS info
getservbyname() -- map a service name and a protocol name to a port number
getprotobyname() -- map a protocol name (e.g. 'tcp') to a number
ntohs(), ntohl() -- convert 16, 32 bit int from network to host byte order
htons(), htonl() -- convert 16, 32 bit int from host to network byte order
inet_aton() -- convert IP addr string (123.45.67.89) to 32-bit packed format
inet_ntoa() -- convert 32-bit packed format IP to string (123.45.67.89)
socket.getdefaulttimeout() -- get the default timeout value
socket.setdefaulttimeout() -- set the default timeout value
create_connection() -- connects to an address, with an optional timeout and
                       optional source address.
create_server() -- create a TCP socket and bind it to a specified address.
"""


############################################################################
############################################################################
class NetworkUtils:
    """
    A class used for pinging hosts and scanning subnets.
    """

    @staticmethod
    def send_email(
        mail_server, sender_email, sender_name, app_pass, recipient, subject, content
    ):

        # Send boot email
        smtp = SMTP(mail_server, 465, ssl=True)  # Gmail's SSL port

        try:
            smtp.login(sender_email, app_pass)
            smtp.to(recipient)
            smtp.write("From:" + sender_name + "<" + sender_email + ">\n")
            smtp.write("Subject:" + subject + "\n" + content + "\n")
            # smtp.write("Body:" + content + "\n")
            smtp.send()
            print("\nBoot Email Sent Successfully\n")

        except Exception as e:
            print("Failed to send email:", e)
        finally:
            smtp.quit()

    @staticmethod
    def ping_host(host, count=4, timeout=5000, interval=10, quiet=False, size=64):
        return ping(host, count, timeout, interval, quiet, size)

    # TODO
    @classmethod
    def ping_subnet(cls, base_ip, start_suffix, end_suffix):
        live_hosts = []
        for i in range(start_suffix, end_suffix + 1):
            host = f"{base_ip}.{i}"
            try:
                # Call the custom MicroPython ping function
                # The exact call depends on the function's implementation (e.g., uping.ping(host))
                if cls.ping_host(host, count=1, timeout=1000, quiet=True):
                    live_hosts.append(host)
                    print(f"{host} is UP")
            except OSError:
                # Handle cases where the host is down or an error occurs
                # print(f"{host} is DOWN or unreachable")
                pass
        return live_hosts


############################################################################
############################################################################
# Pico Web Server
import network
import socket
import time


class PicoWeb:
    def __init__(self, WifiManager):
        self.wifi_manager = WifiManager

    def run(self):
        addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]

        s = socket.socket()
        s.bind(addr)
        s.listen(1)

        print("listening on", addr)
        # Listen for connections
        while True:
            try:
                cl, addr = s.accept()
                print("client connected from", addr)
                request = cl.recv(1024)
                print(request)

                response = self._serve_index()

                cl.send("HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n")
                cl.send(response)
                cl.close()

            except OSError as e:
                cl.close()
                print("connection closed")

    def _serve_index(self):
        if self.wifi_manager.Connected:
            ip = self.wifi_manager.IPV4Address
            html = f"""
            <html>
                <head>
                    <title>Pico W Web Server</title>
                </head>
                <body>
                    <h1>Welcome to Pico W Web Server!</h1>
                    <p>Your IP address is: {ip}</p>
                </body>
            </html>
            """
            return html
        else:
            raise Exception("Wi-Fi not connected - Properly configure WifiManager!")


############################################################################
############################################################################


# Testing
# Example usage
wifi_manager = WiFiManager(SSID, PASSWORD, type="STA")
print(
    f"Availeble WiFi Networks: {len(wifi_manager.AvailableNetworks)} :: {wifi_manager.AvailableNetworks}\n"
)

print(wifi_manager.WifiTest(max_attempts=10))

primary_network = f"Primary Network: {wifi_manager.PrimaryNetwork}\n"
ssid = f"SSID: {wifi_manager.WIFI_SSID}\n"
ip_address = f"IP Address: {wifi_manager.IPV4Address}\n"
default_gateway = f"Default Gateway: {wifi_manager.DefaultGateway}\n"
subnet_mask = f"Subnet Mask: {wifi_manager.SubnetMask}\n"
dns = f"DNS: {wifi_manager.DNS}\n"

report = primary_network + ssid + ip_address + default_gateway + subnet_mask + dns
print("---- Network Report ----\n")
print(report)

print("<<Checking response from Default Gateway>>\n")
NetworkUtils.ping_host("192.168.1.1")

# Email details
sender_email = "droc37191@gmail.com"
sender_name = "Raspberry Pi Pico"
sender_app_password = "xoig jgac lbos ncfx"  # Google app pass: (pidevelopment)
recipient_email = "dpdatadev@gmail.com"


# import utime TODO, get accurate time on Pico W


# Extract and print specific components
# year, month, day, hour, minute, second, weekday, yearday = now


email_subject = (
    ":::: BOOT ALERT Connected to "
    + wifi_manager.WIFI_SSID
    + " with IP "
    + wifi_manager.IPV4Address
    + " ::::\n"
)

# initial boot email
NetworkUtils.send_email(
    mail_server="smtp.gmail.com",
    sender_email=sender_email,
    sender_name=sender_name,
    app_pass=sender_app_password,
    recipient=recipient_email,
    subject=email_subject,
    content=report,
)

# Load web interface
print("\nLoading Web Interface.....\n")
server = PicoWeb(wifi_manager)
server.run()
