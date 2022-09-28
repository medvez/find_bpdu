import argparse
import re
from collections import defaultdict
from getpass import getpass
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException


CLI_COMMAND = 'show spanning-tree detail | i forwarding|BPDU'
PORT_REGEX_PATTERN = re.compile(r'^\d+ \((.+)\)')
BPDU_REGEX_PATTERN = re.compile(r'^.+ received (\d+)$')


class CommandHandler:
    """
    This class combines all components into single block.
    We get IP address of target device from CLI, input credentials for SSH access.
    Then run all commands on device and print result in friendly form.
    """

    def __init__(self) -> None:
        self.host_address = ''
        self.port_bpdu_counters = defaultdict(int)
        self.username = ''
        self.password = ''

    def parse_arguments(self) -> None:
        parser = argparse.ArgumentParser(description='Find ports which received BPDU')
        parser.add_argument('ip', type=str, help='- target device IP address')
        args = parser.parse_args()
        self.host_address = args.ip

    def input_credentials(self) -> None:
        self.username = input('Your SSH username: ')
        self.password = getpass('Your SSH password: ')

    def collect_counters(self) -> None:
        switch = Device(ip=self.host_address,
                        result=self.port_bpdu_counters,
                        username=self.username,
                        password=self.password)
        switch()

    def print_result(self):
        for port, count in self.port_bpdu_counters.items():
            if count:
                print(f'{port:30} - {count}')

    def run(self):
        self.parse_arguments()
        self.input_credentials()
        self.collect_counters()
        self.print_result()


class Device:
    """
    This is API to a device. It runs all needed commands to get BPDU counters from it and
    paste collected data int provided dictionary.
    """

    def __init__(self, ip: str, result: defaultdict, username: str, password: str) -> None:
        self.device = {
            'device_type': 'cisco_ios',
            'host': ip,
            'username': username,
            'password': password
        }
        self.result = result
        self.cli_command_result = []

    def execute_command(self) -> None:
        connection = ConnectHandler(**self.device)
        self.cli_command_result = connection.send_command(CLI_COMMAND).split('\n')

    def command_output_processing(self) -> None:
        _port = ''
        _bpdu_count = 0
        for line in self.cli_command_result:
            line = line.strip().split(maxsplit=1)
            match line:
                case ['Port', rest]:
                    port_match = PORT_REGEX_PATTERN.match(rest)
                    _port = port_match.group(1)
                case ['BPDU:', rest]:
                    bpdu_count_match = BPDU_REGEX_PATTERN.match(rest)
                    _bpdu_count = int(bpdu_count_match.group(1))
                    self.result[_port] += _bpdu_count

    def __call__(self, *args, **kwargs):
        try:
            self.execute_command()
        except NetmikoTimeoutException:
            print(f"Device: {self.device['host']} - not responding")
        except NetmikoAuthenticationException:
            print(f"Device: {self.device['host']} - auth failed")
        else:
            self.command_output_processing()


def main():
    command_handler = CommandHandler()
    command_handler.run()


if __name__ == '__main__':
    main()
