import os
import subprocess
import json
import datetime
import functools

import oauth2client.file
import oauth2client.client
import oauth2client.tools
import google.oauth2.credentials
import google.auth.transport
from google.streetview.publish_v1 import StreetViewPublishServiceClient
from google.streetview.publish_v1.proto import resources_pb2
import requests


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


@functools.lru_cache
def get_credentials():
    credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(CREDENTIALS_FILE)
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials


def get_client():
    return StreetViewPublishServiceClient(credentials=get_credentials())


def get_image_tags(image_path):
    res = subprocess.check_output(['exiftool', '-json', '--printConv', image_path])
    tags = json.loads(res)[0]
    return tags


def check_image_tags(tags):
    assert tags['UsePanoramaViewer'] is True
    assert tags['ProjectionType'] == 'equirectangular'
    assert 'PoseHeadingDegrees' in tags
    assert tags['CroppedAreaImageWidthPixels'] == tags['ImageWidth']
    assert tags['CroppedAreaImageHeightPixels'] == tags['ImageHeight']
    assert tags['FullPanoWidthPixels'] == tags['ImageWidth']
    assert tags['FullPanoHeightPixels'] == tags['ImageHeight']
    assert tags['CroppedAreaLeftPixels'] == 0
    assert tags['CroppedAreaTopPixels'] == 0
    assert tags['GPSImgDirectionRef'] == 'T'
    assert tags['GPSMapDatum'] == 'WGS-84'
    assert 'GPSLatitude' in tags
    assert 'GPSLongitude' in tags
    assert tags['GPSImgDirection'] == tags['PoseHeadingDegrees']
    assert 'GPSTimeStamp' in tags


def upload_panorama(path):
    print(0)
    exif_tags = get_image_tags(path)
    check_image_tags(exif_tags)
    latitude_sign = {'N': 1, 'S': -1}[exif_tags['GPSLatitudeRef']]
    latitude = exif_tags['GPSLatitude'] * latitude_sign
    longitude_sign = {'E': 1, 'W': -1}[exif_tags['GPSLongitudeRef']]
    longitude = exif_tags['GPSLongitude'] * longitude_sign
    heading = exif_tags['PoseHeadingDegrees']
    d = datetime.datetime.strptime(exif_tags['GPSDateTime'], '%Y:%m:%d %H:%M:%SZ')
    d = d.replace(tzinfo=datetime.timezone(datetime.timedelta()))
    timestamp = d.timestamp()
    print(1)
    client = get_client()
    print(2)
    upload_ref = client.start_upload()
    print(3)
    with open(path, 'rb') as f:
        image_data = f.read()
    headers = {
        "Authorization": "Bearer " + get_credentials().token,
        "Content-Type": "image/jpeg",
        "X-Goog-Upload-Protocol": "raw",
        "X-Goog-Upload-Content-Length": str(len(image_data)),
    }
    response = requests.post(upload_ref.upload_url, data=image_data, headers=headers)
    assert response.status_code == 200
    print(4)
    photo = resources_pb2.Photo()
    photo.upload_reference.upload_url = upload_ref.upload_url
    photo.capture_time.seconds = int(timestamp)
    photo.pose.heading = heading
    photo.pose.lat_lng_pair.latitude = latitude
    photo.pose.lat_lng_pair.longitude = longitude
    create_photo_response = client.create_photo(photo)
    photo_id = create_photo_response.photo_id.id
    print(5)
    assert photo_id
    return photo_id


def delete_panorama(panorama_id):
    client = get_client()
    client.delete_photo(panorama_id)
