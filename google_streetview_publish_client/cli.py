import argparse

from . import client


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)
    subparsers.add_parser('login', help='Login and store credentials on disk')
    conf = parser.parse_args()

    if conf.command == 'login':
        client.update_credentials_on_disk()


if __name__ == '__main__':
    main()
