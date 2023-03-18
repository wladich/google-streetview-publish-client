import datetime
import functools
import os
import subprocess
from typing import Literal, cast

import google.auth.transport.requests
import google.oauth2.credentials
import oauth2client.client
import oauth2client.file
import oauth2client.tools
import pydantic
import requests
from google.streetview.publish_v1 import StreetViewPublishServiceClient
from google.streetview.publish_v1.proto import resources_pb2

CREDENTIALS_FILE = os.path.expanduser("~/.config/StreetViewUploader.json")


class ExifTagsRequiredForUpload(pydantic.BaseModel):
    class Latitude(pydantic.StrictFloat):
        ge = 0
        le = 90

    class Longitude(pydantic.StrictFloat):
        ge = 0
        le = 180

    class Azimuth(pydantic.ConstrainedFloat):
        ge = 0
        le = 360

    class ImageSize(pydantic.StrictInt):
        ge = 1000
        le = 50000

    UsePanoramaViewer: Literal[True]
    ProjectionType: Literal["equirectangular"]
    PoseHeadingDegrees: Azimuth
    ImageHeight: ImageSize
    ImageWidth: ImageSize
    CroppedAreaImageWidthPixels: pydantic.StrictInt
    CroppedAreaImageHeightPixels: pydantic.StrictInt
    FullPanoWidthPixels: pydantic.StrictInt
    FullPanoHeightPixels: pydantic.StrictInt
    CroppedAreaLeftPixels: Literal[0]
    CroppedAreaTopPixels: Literal[0]
    GPSImgDirectionRef: Literal["T"]
    GPSMapDatum: Literal["WGS-84"]
    GPSLatitude: Latitude
    GPSLatitudeRef: Literal["S", "N"]
    GPSLongitude: Longitude
    GPSLongitudeRef: Literal["W", "E"]
    GPSImgDirection: Azimuth
    GPSDateTime: str

    @pydantic.validator("ImageWidth")
    def check_width_is_twice_the_height(
        cls, value: int, values: dict[str, object]
    ) -> int:
        assert value == 2 * cast(int, values["ImageHeight"])
        return value

    @pydantic.validator("FullPanoWidthPixels", "CroppedAreaImageWidthPixels")
    def check_panorama_is_full_image_width(
        cls, value: int, values: dict[str, object]
    ) -> int:
        assert value == values["ImageWidth"], "must be equal to image width"
        return value

    @pydantic.validator("FullPanoHeightPixels", "CroppedAreaImageHeightPixels")
    def check_panorama_is_full_image_height(
        cls, value: int, values: dict[str, object]
    ) -> int:
        assert value == values["ImageHeight"], "must be equal to image height"
        return value

    @pydantic.validator("GPSImgDirection")
    def check_gpsimgdirection_equal_poseheadingdegrees(
        cls, value: float, values: dict[str, object]
    ) -> None:
        assert value == values["PoseHeadingDegrees"]


class ExiftoolOutputTags(pydantic.BaseModel):
    # pylint: disable-next=unsubscriptable-object
    raw_data: pydantic.Json[list[ExifTagsRequiredForUpload]]

    @pydantic.validator("raw_data")
    def check_output_contains_one_tags_object(
        cls, value: list[ExifTagsRequiredForUpload]
    ) -> list[ExifTagsRequiredForUpload]:
        assert isinstance(value, list)
        assert len(value) == 1
        return value

    @property
    def tags(self) -> ExifTagsRequiredForUpload:
        return self.raw_data[0]


def update_credentials_on_disk() -> None:
    client_id = input("Enter Client ID:")
    client_secret = input("Enter Client secret:")
    os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
    storage = oauth2client.file.Storage(CREDENTIALS_FILE)
    flow = oauth2client.client.OAuth2WebServerFlow(
        client_id=client_id,
        client_secret=client_secret,
        scope="https://www.googleapis.com/auth/streetviewpublish",
        redirect_uri="http://example.com/auth_return",
    )
    credentials = oauth2client.tools.run_flow(
        flow, storage, oauth2client.tools.argparser.parse_args([])
    )
    assert credentials.access_token is not None


def get_credentials() -> google.oauth2.credentials.Credentials:
    credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(
        CREDENTIALS_FILE
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials


@functools.cache  # type: ignore[misc] # bug https://github.com/python/mypy/issues/5107
def get_client() -> StreetViewPublishServiceClient:
    return StreetViewPublishServiceClient(credentials=get_credentials())


def get_image_tags(image_path: str) -> ExifTagsRequiredForUpload:
    res = subprocess.check_output(["exiftool", "-json", "--printConv", image_path])
    return ExiftoolOutputTags(raw_data=res).tags


def upload_image(path: str) -> str:
    client = get_client()
    upload_ref = client.start_upload()
    with open(path, "rb") as f:
        image_data = f.read()
    headers = {
        "Authorization": "Bearer " + get_credentials().token,
        "Content-Type": "image/jpeg",
        "X-Goog-Upload-Protocol": "raw",
        "X-Goog-Upload-Content-Length": str(len(image_data)),
    }
    response = requests.post(
        upload_ref.upload_url, data=image_data, headers=headers, timeout=60
    )
    assert response.status_code == 200
    return upload_ref.upload_url


def create_panorama(
    upload_url: str, timestamp: float, heading: float, latitude: float, longitude: float
) -> str:
    photo = resources_pb2.Photo()
    # pylint: disable = no-member
    photo.upload_reference.upload_url = upload_url
    photo.capture_time.seconds = int(timestamp)
    photo.pose.heading = heading
    photo.pose.lat_lng_pair.latitude = latitude
    photo.pose.lat_lng_pair.longitude = longitude
    # pylint: enable = no-member
    client = get_client()
    create_photo_response = client.create_photo(photo)
    photo_id = create_photo_response.photo_id.id
    assert photo_id
    return photo_id


def upload_panorama(path: str) -> str:
    exif_tags = get_image_tags(path)
    latitude_sign = {"N": 1, "S": -1}[exif_tags.GPSLatitudeRef]
    latitude = exif_tags.GPSLatitude * latitude_sign
    longitude_sign = {"E": 1, "W": -1}[exif_tags.GPSLongitudeRef]
    longitude = exif_tags.GPSLongitude * longitude_sign
    heading = exif_tags.PoseHeadingDegrees
    dt = datetime.datetime.strptime(exif_tags.GPSDateTime, "%Y:%m:%d %H:%M:%SZ")
    dt = dt.replace(tzinfo=datetime.timezone(datetime.timedelta()))
    timestamp = dt.timestamp()
    upload_url = upload_image(path)
    return create_panorama(upload_url, timestamp, heading, latitude, longitude)


def delete_panorama(panorama_id: str) -> None:
    client = get_client()
    client.delete_photo(panorama_id)
