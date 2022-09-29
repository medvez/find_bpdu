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
        self.port_counters = {}
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
                        username=self.username,
                        password=self.password)
        self.port_counters = switch()

    def print_result(self):
        for port, counter in sorted(self.port_counters.items(), key=lambda item: item[0]):
            print(f'{port:25} - {counter}')

    def run(self):
        self.parse_arguments()
        self.input_credentials()
        self.collect_counters()
        self.print_result()


class Device:
    """
    This is API to a device. It runs all needed commands to get BPDU counters
    from its STP active ports and returns ports and non-zero counters in dictionary.
    """

    def __init__(self, ip: str, username: str, password: str) -> None:
        self.device = {
            'device_type': 'cisco_ios',
            'host': ip,
            'username': username,
            'password': password
        }
        self.cli_command_result = []

    def execute_command(self) -> None:
        connection = ConnectHandler(**self.device)
        self.cli_command_result = map(str.strip, connection.send_command(CLI_COMMAND).split('\n'))

    def command_output_processing(self) -> dict:
        _port = ''
        _counter = 0
        _result = defaultdict(int)
        for line in self.cli_command_result:
            line = line.split(maxsplit=1)
            match line:
                case ['Port', rest]:
                    port_match = PORT_REGEX_PATTERN.match(rest)
                    _port = port_match.group(1)
                case ['BPDU:', rest]:
                    bpdu_count_match = BPDU_REGEX_PATTERN.match(rest)
                    _counter = int(bpdu_count_match.group(1))
                    _result[_port] += _counter
        return dict(filter(lambda port_counter: port_counter[1] > 0, _result.items()))

    def __call__(self, *args, **kwargs) -> dict:
        try:
            self.execute_command()
        except NetmikoTimeoutException:
            print(f"Device: {self.device['host']} - not responding")
        except NetmikoAuthenticationException:
            print(f"Device: {self.device['host']} - auth failed")
        else:
            return self.command_output_processing()


def main():
    command_handler = CommandHandler()
    command_handler.run()


if __name__ == '__main__':
    main()
