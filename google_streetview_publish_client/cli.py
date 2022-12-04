import argparse

from . import client


class Args(argparse.Namespace):
    command: str
    image: str
    id: str


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("login", help="Login and store credentials on disk")
    upload = subparsers.add_parser("upload", help="Upload panorama")
    upload.add_argument("image")
    delete = subparsers.add_parser("delete")
    delete.add_argument("id")
    conf = parser.parse_args(namespace=Args())

    if conf.command == "login":
        client.update_credentials_on_disk()
    elif conf.command == "upload":
        photo_id = client.upload_panorama(conf.image)
        print("New photo id:", photo_id)
    elif conf.command == "delete":
        client.delete_panorama(conf.id)


if __name__ == "__main__":
    main()
