import argparse

from . import client


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)
    subparsers.add_parser('login', help='Login and store credentials on disk')
    upload = subparsers.add_parser('upload', help='Upload panorama')
    upload.add_argument('image')
    conf = parser.parse_args()

    if conf.command == 'login':
        client.update_credentials_on_disk()
    elif conf.command == 'upload':
        photo_id = client.upload_panorama(conf.image)
        print('New photo id:', photo_id)


if __name__ == '__main__':
    main()
