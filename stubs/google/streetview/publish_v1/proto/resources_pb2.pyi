class UploadRef:
    upload_url: str

class Timestamp:
    seconds: int

class LatLng:
    latitude: float
    longitude: float

class Pose:
    heading: float
    lat_lng_pair: LatLng

class PhotoId:
    id: str

class Photo:
    photo_id: PhotoId
    upload_reference: UploadRef
    capture_time: Timestamp
    pose: Pose
