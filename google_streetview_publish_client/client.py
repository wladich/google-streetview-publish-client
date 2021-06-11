import os

import oauth2client.file
import oauth2client.client
import oauth2client.tools

CREDENTIALS_FILE = os.path.expanduser('~/.config/StreetViewUploader.json')


def update_credentials_on_disk():
    client_id = input('Enter Client ID:')
    client_secret = input('Enter Client secret:')
    os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
    storage = oauth2client.file.Storage(CREDENTIALS_FILE)
    flow = oauth2client.client.OAuth2WebServerFlow(client_id=client_id,
                                                   client_secret=client_secret,
                                                   scope='https://www.googleapis.com/auth/streetviewpublish',
                                                   redirect_uri='http://example.com/auth_return')
    credentials = oauth2client.tools.run_flow(flow, storage, oauth2client.tools.argparser.parse_args([]))
    assert credentials.access_token is not None
