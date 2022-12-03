from db import *
from flask import Flask, request
import json
from sqlalchemy import update

app = Flask(__name__)
db_filename = "hack.db"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    db.create_all()


# generalized response formats
def success_response(data, code=200):
    """
    Generalized success response
    """
    return json.dumps(data), code


def failure_response(message, code=404):
    """
    Generalized failure response
    """
    return json.dumps({"error": message}), code


# General Testing Routes
@app.route("/test/users/")
def get_all_users():
    """
    Testing Endpoint for getting all users
    """
    users = [user.serialize() for user in User.query.all()]
    return success_response({"users": users})


@app.route("/test/users/", methods=["DELETE"])
def delete_user_table():
    """
    Testing Endpoint for deleting the user table
    """
    User.__table__.drop(db.engine)
    return success_response("Table Deleted")


@app.route("/test/songs/")
def get_all_songs():
    """
    Testing Endpoint for getting all songs
    """
    songs = [song.simple_serialize() for song in Song.query.all()]
    return success_response({"songs": songs})


@app.route("/test/songs/", methods=["DELETE"])
def delete_song_table():
    """
    Testing Endpoint for deleting the songs table
    """
    Song.__table__.drop(db.engine)
    return success_response("Table Deleted")


@app.route("/test/playlists/")
def get_all_playlists():
    """
    Testing Endpoint for getting all playlists
    """
    playlists = [playlist.serialize() for playlist in Playlist.query.all()]
    return success_response({"playlists": playlists})


@app.route("/test/playlists/", methods=["DELETE"])
def delete_playlist_table():
    """
    Testing Endpoint for deleting the playlists table
    """
    Playlist.__table__.drop(db.engine)
    return success_response("Table Deleted")


@app.route("/test/assets/")
def get_all_assets():
    """
    Testing Endpoint for getting all assets
    """
    assets = [asset.test_serialize() for asset in Asset.query.all()]
    return success_response({"assets": assets})


@app.route("/test/assets/", methods=["DELETE"])
def delete_asset_table():
    """
    Testing Endpoint for deleting the asset table
    """
    Asset.__table__.drop(db.engine)
    return success_response("Table Deleted")


@app.route("/test/images/")
def get_all_images():
    """
    Testing Endpoint for getting all images
    """
    images = [image.simple_serialize() for image in Img.query.all()]
    return success_response({"images": images})


@app.route("/test/images/", methods=["DELETE"])
def delete_image_table():
    """
    Testing Endpoint for deleting the images table
    """
    Img.__table__.drop(db.engine)
    return success_response("Table Deleted")


# App Routes
@app.route("/users/", methods=["POST"])
def create_new_user():
    """
    Endpoint for creating a user. For the sake of the simplicity of this app/project,
    users will only be able to access their playlist from a single device.
    There is no way to have multiple devices be connected to one account, everything is local.

    The frontend should send a json with these keys and value types:
    {"username": <str>}
    """
    body = json.loads(request.data)
    username = body.get("username")

    if username is None:
        return failure_response("Please input a username", 400)

    user = User(username=username)
    db.session.add(user)
    db.session.commit()

    return success_response(user.serialize())


@app.route("/songs/add/", methods=["POST"])
def add_song_to_database():
    """
    Endpoint for a user to add a new song to the database
    If the song already exists in the database, an error is returned

    The fronted should send a json with these keys and value types:
    {"title": <str>, "artist": <str>, "bpm": <int>, "link": <str>}
    """
    body = json.loads(request.data)
    title = body.get("title")
    artist = body.get("artist")
    bpm = body.get("bpm")
    link = body.get("link")

    if title is None or artist is None or bpm is None or link is None:
        return failure_response("Please input all requested data", 400)

    new_song = Song(title=title, artist=artist, bpm=bpm, link=link)

    if new_song.exists_serialize() in [song.exists_serialize() for song in Song.query.all()]:
        return failure_response("Song already exists", 401)

    db.session.add(new_song)
    db.session.commit()
    return success_response(new_song.simple_serialize(), 201)


@app.route("/songs/search/")
def get_songs_bpm():
    """
    Endpoint for returning songs with a bpm in the specified range
    The bpm is bounded by an upper and lower bpm sent separately in a json

    The frontend should send a json with these keys and value types:
    {"upper_bpm": <int>, "lower_bpm": <int>}
    """
    body = json.loads(request.data)
    lower_bpm = body.get("lower_bpm")
    upper_bpm = body.get("upper_bpm")

    if lower_bpm is None or upper_bpm is None:
        return failure_response("Please input a bpm range", 400)

    all_songs = [song.simple_serialize() for song in Song.query.all()]
    filtered_songs = []

    for song in all_songs:
        if song["bpm"] in range(lower_bpm, upper_bpm + 1):
            filtered_songs.append(song)

    if not filtered_songs:
        return failure_response("No songs in this range were found", 400)

    return success_response(filtered_songs)


@app.route("/users/<int:user_id>/playlists/")
def get_user_playlists(user_id):
    """
    Endpoint for returning all of a user's playlists

    When each playlist is serialized and put into the list, songs are not included.
    This is because the UI would get crowded if the songs were included. The songs will
    only be included in the route to get a specific playlist.
    """
    user = User.query.filter_by(id=user_id).first()

    if user is None:
        return failure_response("User not found")

    playlists = [playlist.simple_serialize() for playlist in Playlist.query.filter_by(user_id=user_id)]

    return success_response({"playlists": playlists})


@app.route("/users/<int:user_id>/playlists/", methods=["POST"])
def create_new_playlist(user_id):
    """
    Endpoint for creating a new playlist

    The frontend should send a json with these keys and value types:
    {"playlist_name": <str>}
    """
    user = User.query.filter_by(id=user_id).first()

    if user is None:
        return failure_response("User not found")

    body = json.loads(request.data)
    playlist_name = body.get("playlist_name")

    if playlist_name is None:
        return failure_response("Please input a playlist name", 400)

    new_playlist = Playlist(playlist_name=playlist_name, user_id=user_id)
    db.session.add(new_playlist)
    db.session.commit()

    return success_response(new_playlist.simple_serialize())


@app.route("/playlists/<int:playlist_id>/")
def get_specific_playlist(playlist_id):
    """
    Endpoint for getting a specific user's playlist by its id
    """
    playlist = Playlist.query.filter_by(id=playlist_id).first()

    if playlist is None:
        return failure_response("Playlist not found")

    return success_response(playlist.serialize())


@app.route("/playlists/<int:playlist_id>/", methods=["DELETE"])
def delete_playlist(playlist_id):
    """
    Endpoint for deleting a user's playlist by its id
    """
    playlist = Playlist.query.filter_by(id=playlist_id).first()

    if playlist is None:
        return failure_response("Playlist not found")

    deleted_playlist = playlist.serialize()

    db.session.delete(playlist)
    db.session.commit()
    return success_response(deleted_playlist)


@app.route("/playlists/<int:playlist_id>/songs/<int:song_id>/", methods=["POST"])
def add_song_to_playlist(playlist_id, song_id):
    """
    Endpoint for adding a song to a playlist
    """
    playlist = Playlist.query.filter_by(id=playlist_id).first()

    if playlist is None:
        return failure_response("Playlist not found")

    song = Song.query.filter_by(id=song_id).first()

    if song is None:
        return failure_response("Song not found")

    playlist.songs.append(song)
    db.session.commit()
    return success_response(song.simple_serialize())


@app.route("/playlists/<int:playlist_id>/songs/<int:song_id>/", methods=["DELETE"])
def remove_song_from_playlist(playlist_id, song_id):
    """
    Endpoint for removing a song from a playlist
    """
    playlist = Playlist.query.filter_by(id=playlist_id).first()

    if playlist is None:
        return failure_response("Playlist not found")

    song = Song.query.filter_by(id=song_id).first()

    if song is None:
        return failure_response("Song not found")

    try:
        playlist.songs.index(song)
    except ValueError:
        return failure_response("Song not in playlist", 400)

    playlist.songs.remove(song)
    db.session.commit()

    return success_response(song.simple_serialize())


@app.route("/songs/<int:song_id>/")
def get_song_from_playlist(song_id):
    """
    Endpoint for getting/playing a song with give id
    """
    song = Song.query.filter_by(id=song_id).first()

    if song is None:
        return failure_response("Song not found")

    return success_response(song.simple_serialize())


@app.route("/playlists/<int:playlist_id>/images/", methods=["POST"])
def upload_playlist_image(playlist_id):
    """
    Endpoint for uploading an image to AWS given a base64 image file
    It will then be uploaded to AWS to be returned when
    a request that returns a playlist is sent.

    The frontend should send a json with these keys and value types:
    {"image_data": <str>}
    Note: The frontend should first convert an image file to a base64 str, then send that
    """
    playlist = Playlist.query.filter_by(id=playlist_id).first()

    if playlist is None:
        return failure_response("Playlist not found")

    body = json.loads(request.data)
    image_data = body.get("image_data")

    if image_data is None:
        return failure_response("No base64 image found.")

    asset = Asset(image_data=image_data)
    db.session.add(asset)
    db.session.commit()

    image = Img(link=asset.serialize()["url"], playlist_id=playlist_id)
    db.session.add(image)
    db.session.commit()

    return success_response(image.serialize(), 201)


@app.route("/playlists/<int:playlist_id>/images/", methods=["DELETE"])
def remove_playlist_image(playlist_id):
    """
    Endpoint for removing a playlist's image thumbnail.
    The image will not be deleted from AWS, but it will be deleted
    from both the Img and Asset tables.
    """
    playlist = Playlist.query.filter_by(id=playlist_id).first()

    if playlist is None:
        return failure_response("Playlist not found")

    # remove from Img
    image_id = playlist.image_id
    image = Img.query.filter_by(id=image_id).first()

    # remove from Asset
    asset_id = playlist.image_id
    asset = Asset.query.filter_by(id=asset_id).first()

    if image is None:
        return failure_response("There is no image associated with this playlist")

    db.session.delete(image)
    db.session.delete(asset)
    db.session.commit()

    return success_response(image.serialize())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
