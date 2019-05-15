import logging
import logging.handlers
import re
import os
import sys
import threading
from time import sleep
import socket
import struct
import re
from VMnetwork import dhcp
from VMnetwork import http
from Vmnetwork import tftp
from Vmnetwork.helper import common

class PyNet:

    @staticmethod
    def dict2class(data):

        class foo:
            pass

        for key, value in data.items():
            setattr(foo, key, value)

        return foo

    @staticmethod
    def __get_settings(NETBOOT_DIR, SERVER_IP, DHCP_SUBNET, DHCP_ROUTER):
        server_ip_int = int(socket.inet_aton(SERVER_IP).encode('hex'), 16)
        server_subnet_int = int(socket.inet_aton(DHCP_SUBNET).encode('hex'), 16)
        dhcp_net_addr_int = server_ip_int & server_subnet_int
        DHCP_OFFER_BEGIN = socket.inet_ntoa(struct.pack('>I', dhcp_net_addr_int + 2))
        iptokens = map(int, SERVER_IP.split('.'))
        masktokens = map(int, DHCP_SUBNET.split('.'))
        broadlist = []
        for i in range(len(iptokens)):
            ip = iptokens[i]
            mask = masktokens[i]
            broad = ip & mask | ~mask & 255
            broadlist.append(broad)

        DHCP_OFFER_END = '.'.join(map(str, broadlist))
        if not DHCP_ROUTER:
            DHCP_ROUTER = re.sub('\\.[0-9]{1,3}$', '.1', SERVER_IP)
        setting = {'NETBOOT_DIR': NETBOOT_DIR,
         'NETBOOT_FILE': '',
         'DHCP_SERVER_IP': SERVER_IP,
         'DHCP_SERVER_PORT': 67,
         'TFTP_SERVER_PORT': 69,
         'DHCP_OFFER_BEGIN': DHCP_OFFER_BEGIN,
         'DHCP_OFFER_END': DHCP_OFFER_END,
         'DHCP_SUBNET': DHCP_SUBNET,
         'DHCP_DNS': '192.168.2.1',
         'DHCP_ROUTER': DHCP_ROUTER,
         'DHCP_BROADCAST': '',
         'DHCP_FILESERVER': SERVER_IP,
         'DHCP_WHITELIST': False,
         'LEASES_FILE': '',
         'STATIC_CONFIG': {},
         'USE_IPXE': False,
         'USE_HTTP': False,
         'USE_TFTP': True,
         'USE_DHCP': True,
         'DHCP_MODE_PROXY': False}
        return setting

    @staticmethod
    def start(NETBOOT_DIR, SERVER_IP, DHCP_SUBNET, DHCP_ROUTER):
        settings = PyPXE.__get_settings(NETBOOT_DIR, SERVER_IP, DHCP_SUBNET, DHCP_ROUTER)
        try:
            args = PyPXE.dict2class(settings)
            sys_logger = logging.getLogger('PyPXE')
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s %(message)s')
            handler.setFormatter(formatter)
            sys_logger.addHandler(handler)
            sys_logger.setLevel(logging.INFO)
            if args.USE_HTTP and not args.USE_IPXE and not args.USE_DHCP:
                sys_logger.warning('HTTP selected but iPXE disabled. PXE ROM must support HTTP requests.')
            if args.DHCP_MODE_PROXY:
                args.USE_DHCP = True
            if args.NETBOOT_FILE == str():
                if not args.USE_IPXE:
                    args.NETBOOT_FILE = 'pxelinux.0'
                elif not args.USE_HTTP:
                    args.NETBOOT_FILE = 'boot.ipxe'
                else:
                    args.NETBOOT_FILE = 'boot.http.ipxe'
            if args.USE_DHCP:
                dhcp_logger = common.get_child_logger(sys_logger, 'DHCP')
                if args.DHCP_MODE_PROXY:
                    sys_logger.info('Starting DHCP serverd in ProxyDHCP mode...')
                else:
                    sys_logger.info('Starting DHCP serverd...')
                dhcp_server = dhcp.DHCPD(ip=args.DHCP_SERVER_IP, port=args.DHCP_SERVER_PORT, offer_from=args.DHCP_OFFER_BEGIN, offer_to=args.DHCP_OFFER_END, subnet_mask=args.DHCP_SUBNET, router=args.DHCP_ROUTER, dns_server=args.DHCP_DNS, broadcast=args.DHCP_BROADCAST, file_server=args.DHCP_FILESERVER, file_name=args.NETBOOT_FILE, use_ipxe=args.USE_IPXE, use_http=args.USE_HTTP, mode_proxy=args.DHCP_MODE_PROXY, mode_debug=True, mode_verbose=True, whitelist=args.DHCP_WHITELIST, static_config=args.STATIC_CONFIG, logger=dhcp_logger, saveleases=args.LEASES_FILE, netboot_directory=args.NETBOOT_DIR)
                common.set_server_status(type='DHCP', status='RUNNING')
                dhcpd = threading.Thread(target=dhcp_server.listen)
                dhcpd.daemon = True
                dhcpd.start()
            if args.USE_TFTP:
                tftp_logger = common.get_child_logger(sys_logger, 'TFTP')
                sys_logger.info('Starting TFTP serverd...')
                tftp_server = tftp.TFTPD(mode_debug=True, mode_verbose=True, logger=tftp_logger, netboot_directory=args.NETBOOT_DIR, ip=args.DHCP_SERVER_IP)
                common.set_server_status(type='TFTP', status='RUNNING')
                tftpd = threading.Thread(target=tftp_server.listen)
                tftpd.daemon = True
                tftpd.start()
            if args.USE_HTTP:
                http_logger = common.get_child_logger(sys_logger, 'HTTP')
                sys_logger.info('Starting HTTP serverd...')
                http_server = http.HTTPD(mode_debug=True, mode_verbose=True, logger=http_logger, netboot_directory=args.NETBOOT_DIR)
                httpd = threading.Thread(target=http_server.listen)
                httpd.daemon = True
                httpd.start()
            sys_logger.info('PyPXE successfully initialized and running!')
        except KeyboardInterrupt:
            return False

        return True

    @staticmethod
    def stop():

        def stop():
            server_types = ('DHCP', 'TFTP')
            for type in server_types:
                common.set_server_status(type=type, status='STOPPING')

        over_time = 60
        sleep_time = 0
        while PyPXE.is_alive():
            if sleep_time >= over_time:
                return False
            stop()
            sleep_time = sleep_time + 10

        return True

    @staticmethod
    def is_alive():
        server_types = ('DHCP', 'TFTP')
        ret = True
        for type in server_types:
            status = common.get_server_status(type)
            if status != 'RUNNING':
                ret = False
                break

        if not ret:
            for type in server_types:
                common.set_server_status(type=type, status='STOPPING')

        return ret
