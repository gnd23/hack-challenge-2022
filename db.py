import datetime
import hashlib
import os

import bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import update

import base64
import boto3
from mimetypes import guess_type, guess_extension
from PIL import Image
import random
import re
import string
from io import BytesIO

EXTENSIONS = ["png", "gif", "jpg", "jpeg"]
BASE_DIR = os.getcwd()
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
S3_BASE_URL = f"https://{S3_BUCKET_NAME}.s3.us-east-1.amazonaws.com"

db = SQLAlchemy()

# association table
association_table = db.Table(
    "playlist_song_association",
    db.Column("playlist_id", db.Integer, db.ForeignKey("playlist.id")),
    db.Column("song_id", db.Integer, db.ForeignKey("song.id"))
)


# tables
class User(db.Model):
    """
    Contains all users of the app
    Includes id, username, and the relationship with Playlist table

    Has a One-to-Many relationship with Playlist
    """
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, nullable=False)

    # playlist relationship
    playlists = db.relationship("Playlist", cascade="delete")

    def __init__(self, **kwargs):
        """
        Creates a user object
        """
        self.username = kwargs.get("username")

    def serialize(self):
        """
        Serializes a user object
        """
        return {
            "id": self.id,
            "username": self.username,
            "playlists": [p.simple_serialize() for p in self.playlists]
        }

    def simple_serialize(self):
        """
        Serializes a user object without playlists
        """
        return{
            "id": self.id,
            "username": self.username
        }


class Playlist(db.Model):
    """
    Contains all playlists on the app
    Includes id, playlist name, and the foreign key user id

    Has a Many-to-One relationship with User
    Has a Many-to-Many relationship with Song
    Has a One-to-One relationship with Img
    """
    __tablename__ = "playlist"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    playlist_name = db.Column(db.String(), nullable=False)

    # user relationship
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", back_populates="playlists")

    # song relationship
    songs = db.relationship("Song", secondary=association_table, back_populates="playlists")

    # image relationship
    image_id = db.Column(db.Integer, db.ForeignKey("image.id"))
    image = db.relationship(
        "Img",
        back_populates="playlist",
        uselist=False,
        single_parent=True,
        cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        """
        Creates a playlist object
        """
        self.playlist_name = kwargs.get("playlist_name")
        self.user_id = kwargs.get("user_id")

    def serialize(self):
        """
        Serializes a playlist object
        """
        return {
            "id": self.id,
            "playlist_name": self.playlist_name,
            "image": self.image.simple_serialize() if self.image is not None else None,
            "user": self.user.simple_serialize(),
            "songs": [s.simple_serialize() for s in self.songs]
        }

    def simple_serialize(self):
        """
        Serializes a playlist object without songs or user
        """
        return {
            "id": self.id,
            "playlist_name": self.playlist_name,
            "image": self.image.simple_serialize() if self.image is not None else None
        }

    def no_image_serialize(self):
        """
        Serializes a playlist object without songs, user, or image
        Used for the testing route get_all_images
        """
        return {
            "id": self.id,
            "playlist_name": self.playlist_name
        }


class Song(db.Model):
    """
    Contains all songs on the app
    Includes id, title, artist, bpm, and link

    Has a Many-to-Many relationship with Playlist
    """
    __tablename__ = "song"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String, nullable=False)
    artist = db.Column(db.String, nullable=False)
    bpm = db.Column(db.Integer, nullable=False)
    link = db.Column(db.String, nullable=False)

    # playlist relationship
    playlists = db.relationship("Playlist", secondary=association_table, back_populates="songs")

    def __init__(self, **kwargs):
        """
        Creates a song object
        """
        self.title = kwargs.get("title")
        self.artist = kwargs.get("artist")
        self.bpm = kwargs.get("bpm")
        self.link = kwargs.get("link")

    def serialize(self):
        """
        Serializes a song object
        """
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "bpm": self.bpm,
            "link": self.link,
            "playlists": [p.simple_serialize for p in self.playlists]
        }

    def simple_serialize(self):
        """
        Serializes a song object without playlists
        """
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "bpm": self.bpm,
            "link": self.link
        }

    def exists_serialize(self):
        """
        Serializes a song object without id (for use in add_song_to_database())
        """
        return {
            "title": self.title,
            "artist": self.artist,
            "bpm": self.bpm,
            "link": self.link
        }


# Images classes
class Img(db.Model):
    """
    Contains all User-uploaded images on the app
    Includes id and AWS link
    In practice, every playlist can have an image thumbnail,
    which is the purpose of this table

    Has a One-to-One relationship with Playlist
    """
    __tablename__ = "image"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    link = db.Column(db.String, nullable=False)

    # playlist relationship
    playlist = db.relationship("Playlist", back_populates="image", uselist=False)

    def __init__(self, **kwargs):
        """
        Initializes an image object
        """
        self.link = kwargs.get("link")
        self.playlist_id = kwargs.get("playlist_id")
        self.playlist = Playlist.query.filter_by(id=self.playlist_id).first()

    def serialize(self):
        """
        Serializes an image object
        """
        return {
            "id": self.id,
            "link": self.link,
            "playlist": self.playlist.no_image_serialize()
        }

    def simple_serialize(self):
        """
        Serializes an image object without playlist
        """
        return{
            "id": self.id,
            "link": self.link
        }


class Asset(db.Model):
    """
    Asset Model
    """
    __tablename__ = "asset"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    base_url = db.Column(db.String, nullable=False)
    salt = db.Column(db.String, nullable=False)
    extension = db.Column(db.String, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

    def __init__(self, **kwargs):
        """
        Initializes an Asset Object
        """
        self.create(kwargs.get("image_data"))

    def serialize(self):
        """
        Serializes an Asset object
        """
        return {
            "url": f"{self.base_url}/{self.salt}.{self.extension}",
            "created_at": str(self.created_at)
        }

    def test_serialize(self):
        """
        Serializes an Asset Object (with id) for testing purposes
        """
        return {
            "id": self.id,
            "url": f"{self.base_url}/{self.salt}.{self.extension}",
            "created_at": str(self.created_at)
        }

    def create(self, image_data):
        """
        Given an image in base64 encoding, does the following:
        1. Rejects the image if it is not a supported file type
        2. Generate a random string for the image filename
        3. Decodes the image and attempts to upload it to AWS
        """
        try:
            ext = guess_extension(guess_type(image_data)[0])[1:]
            if ext not in EXTENSIONS:
                raise Exception(f"Extension {ext} is not valid.")

            salt = "".join(
                random.SystemRandom().choice(
                    string.ascii_uppercase + string.digits
                )
                for _ in range(16)
            )

            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_data = base64.b64decode(img_str)
            img = Image.open(BytesIO(img_data))

            self.base_url = S3_BASE_URL
            self.salt = salt
            self.extension = ext
            self.width = img.width
            self.height = img.height
            self.created_at = datetime.datetime.now()

            img_filename = f"{self.salt}.{self.extension}"
            self.upload(img, img_filename)

        except Exception as e:
            print(f"Error when creating image: {e}")

    def upload(self, img, img_filename):
        """
        Attempts to upload the image into the specified S3 bucket
        """
        try:
            # save image into temporary location
            img_temp_loc = f"{BASE_DIR}/{img_filename}"
            img.save(img_temp_loc)

            # upload image into S3 bucket
            s3_client = boto3.client("s3")
            s3_client.upload_file(img_temp_loc, S3_BUCKET_NAME, img_filename)

            # make image public
            s3_resource = boto3.resource("s3")
            object_acl = s3_resource.ObjectAcl(S3_BUCKET_NAME, img_filename)
            object_acl.put(ACL="public-read")

            # remove image from temporary location
            os.remove(img_temp_loc)

        except Exception as e:
            print(f"Error when uploading image: {e}")
