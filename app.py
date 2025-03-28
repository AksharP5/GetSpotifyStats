import os
from datetime import timedelta
from flask import Flask, render_template, request, redirect, session, url_for
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
import spotipy
from decouple import config
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

CLIENT_ID = config("CLIENT_ID")
CLIENT_SECRET = config("CLIENT_SECRET")
REDIRECT_URL = config("REDIRECT_URL")
SCOPES = "user-read-recently-played,user-top-read"

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URL,
    scope=SCOPES
)

@app.route("/")
@app.route("/home")
def main():
    auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    sp = spotipy.Spotify(auth_manager=auth_manager)
    top_tracks = sp.playlist('2DCBk0AdKhUxb2ANXckhMO')['tracks']['items']
    return render_template("index.html", top_tracks=top_tracks)

@app.route("/login")
def login():
    return redirect(sp_oauth.get_authorize_url())

@app.route("/callback")
def callback():
    session["token_info"] = sp_oauth.get_access_token(request.args.get("code"))
    return redirect(url_for("main"))

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/recent_limit", methods = ["POST", "GET"])
def before_recent():
    return render_template("recent_limit.html")

@app.route("/recent", methods = ["POST", "GET"])
def recent():
    limit = recent_vars(request)
    my_dict = get_Users_Recently_Played(gen_Spotipy(), int(limit))
    return render_template("recent.html", my_dict=my_dict)

@app.route("/before_top_songs", methods=["GET"])
def before_top_songs():
    return render_template("before_top_songs.html")

@app.route("/top_songs", methods = ["POST", "GET"])
def top_songs():
    limit, offset, time_length = top_songs_vars(request=request)
    if int(limit) >= 1 and int(limit) <= 50 and int(offset) >= 0 and int(offset) <= 20:
        top_tracks = get_Users_Top_Tracks(gen_Spotipy(), int(limit), int(offset), time_length)
        return render_template("top_songs.html", top_tracks = top_tracks)
    else:
        return render_template("invalid_input.html")

@app.route("/before_top_artists", methods=["GET"])
def before_top_artists():
    return render_template("before_top_artists.html")

@app.route("/top_artists", methods = ["POST", "GET"])
def top_artists():
    limit, offset, time_length = top_artists_vars(request=request)
    try: 
        if int(limit) >= 1 and int(limit) <= 50 and int(offset) >= 0 and int(offset) <= 20:
            top_artists = get_Users_Top_Artists(gen_Spotipy(), int(limit), int(offset), time_length)
            return render_template("top_artists.html", top_artists = top_artists)
        else:
            return render_template("invalid_input.html")
    except:
        return render_template("invalid_input.html") 
   
@app.route("/before_recommended", methods = ["POST", "GET"])
def before_recommended():
    seed_artists, seed_songs, seed_genres, seed_countries, gen_genre, countries, recent_songs_top, recent_songs, short_top_artists, medium_top_artists, long_top_artists, short_top_songs, medium_top_songs, long_top_songs, Song_count, Artist_count = gen_before_rec_vars()
    seed_artists = get_artists_before_rec(seed_artists, recent_songs_top, short_top_artists, medium_top_artists, long_top_artists, Artist_count)
    seed_songs = get_songs_before_rec(seed_songs, recent_songs, short_top_songs, medium_top_songs, long_top_songs, Song_count)
    seed_genres, seed_countries = get_genre_and_country_before_rec(seed_genres, seed_countries, gen_genre, countries)
    return render_template("before_recommended.html", seed_artists = seed_artists, seed_genres = seed_genres, seed_songs = seed_songs, seed_countries = seed_countries)

@app.route("/recommended", methods = ["POST", "GET"])
def recommended():
    top, limit, country, artists, genres, songs = gen_rec_vars(request=request)
    artists, genres, songs = check_None(artists, genres, songs)
    check_invalid(artists=artists, genres=genres, songs=songs)
    if artists is not None and genres is not None and songs is not None and len(artists) + len(genres) + len(songs) <= 5:
        rec = gen_rec(top, limit, country, artists, genres, songs)
        return render_template("recommended.html", rec = rec)
    else:
        return render_template("invalid_input.html")

def format_duration(milliseconds):
    duration = timedelta(milliseconds=milliseconds)
    minutes, seconds = divmod(duration.total_seconds(), 60)
    return f"{int(minutes)}:{int(seconds):02d}"

app.jinja_env.filters["format_duration"] = format_duration

def get_genre_and_country_before_rec(seed_genres, seed_countries, gen_genre, countries):
    for idx, value in enumerate(gen_genre.get("genres")):
        seed_genres[idx+1] = value
    for idx, value in enumerate(countries.get("markets")):
        seed_countries[idx+1] = value
    return seed_genres, seed_countries

def get_songs_before_rec(seed_songs, recent_songs, short_top_songs, medium_top_songs, long_top_songs, Song_count):
    for songs_dict in [long_top_songs, medium_top_songs, short_top_songs]:
        for key, value in songs_dict.items():
            if value[0] not in seed_songs:
                seed_songs[value[0]] = [Song_count, value[1], value[2]]
                Song_count += 1
    
    for key, value in recent_songs.items():
        if value[0][0] not in seed_songs:
            seed_songs[value[0][0]] = [Song_count, value[1], value[2]]
            Song_count += 1
    
    return seed_songs

def get_artists_before_rec(seed_artists, recent_songs_top, short_top_artists, medium_top_artists, long_top_artists, Artist_count):
    for artists_dict in [long_top_artists, medium_top_artists, short_top_artists]:
        for key, value in artists_dict.items():
            if value[0] not in seed_artists:
                seed_artists[value[0]] = [Artist_count, value[1], value[2]]
                Artist_count += 1
    
    for key, value in recent_songs_top.items():
        if value[0][0] not in seed_artists:
            seed_artists[value[0][0]] = [Artist_count, value[1], value[2]]
            Artist_count += 1
    
    return seed_artists


def gen_before_rec_vars():
    seed_artists = {}
    seed_songs = {}
    seed_genres = {}
    seed_countries = {}
    top = gen_Spotipy()
    recent = gen_Spotipy()

    gen_genre = {
        "genres": [
            "acoustic", "afrobeat", "alt-rock", "alternative", "ambient", "anime", "black-metal", "bluegrass", "blues", "bossanova",
            "brazil", "breakbeat", "british", "cantopop", "chicago-house", "children", "chill", "classical", "club", "comedy",
            "country", "dance", "dancehall", "death-metal", "deep-house", "detroit-techno", "disco", "disney", "drum-and-bass",
            "dub", "dubstep", "edm", "electro", "electronic", "emo", "folk", "forro", "french", "funk", "garage", "german",
            "gospel", "goth", "grindcore", "groove", "grunge", "guitar", "happy", "hard-rock", "hardcore", "hardstyle",
            "heavy-metal", "hip-hop", "holidays", "honky-tonk", "house", "idm", "indian", "indie", "indie-pop", "industrial",
            "iranian", "j-dance", "j-idol", "j-pop", "j-rock", "jazz", "k-pop", "kids", "latin", "latino", "malay",
            "mandopop", "metal", "metal-misc", "metalcore", "minimal-techno", "movies", "mpb", "new-age", "new-release",
            "opera", "pagode", "party", "philippines-opm", "piano", "pop", "pop-film", "post-dubstep", "power-pop",
            "progressive-house", "psych-rock", "punk", "punk-rock", "r-n-b", "rainy-day", "reggae", "reggaeton", "road-trip",
            "rock", "rock-n-roll", "rockabilly", "romance", "sad", "salsa", "samba", "sertanejo", "show-tunes", "singer-songwriter",
            "ska", "sleep", "songwriter", "soul", "soundtracks", "spanish", "study", "summer", "swedish", "synth-pop",
            "tango", "techno", "trance", "trip-hop", "turkish", "work-out", "world-music"
        ]
    }
    countries = top.available_markets()

    recent_songs_top = get_Recent_Top(recent, 50)
    recent_songs = get_Recent_ID(recent, 50)

    short_top_artists = get_Artists_ID(top, 50, 0, "short_term")
    medium_top_artists = get_Artists_ID(top, 50, 0, "medium_term")
    long_top_artists = get_Artists_ID(top, 50, 0, "long_term")

    short_top_songs = get_Track_ID(top, 50, 0, "short_term")
    medium_top_songs = get_Track_ID(top, 50, 0, "medium_term")
    long_top_songs = get_Track_ID(top, 50, 0, "long_term")

    Song_count = 1
    Artist_count = 1
    return seed_artists,seed_songs,seed_genres,seed_countries,gen_genre,countries,recent_songs_top,recent_songs,short_top_artists,medium_top_artists,long_top_artists,short_top_songs,medium_top_songs,long_top_songs,Song_count,Artist_count

def gen_rec(top, limit, country, artists, genres, songs):
    if artists is None and songs is None and genres is not None:
        rec = top.recommendations(seed_genres=genres, limit=limit, country=country)
    elif artists is None and genres is None and songs is not None:
        rec = top.recommendations(seed_tracks=songs, limit=limit, country=country)
    elif genres is None and songs is None and artists is not None:
        rec = top.recommendations(seed_artists=artists, limit=limit, country=country)
    elif artists is None and songs is not None and genres is not None:
        rec = top.recommendations(seed_genres=genres, seed_tracks=songs, limit=limit, country=country)
    elif artists is not None and genres is not None and songs is None:
        rec = top.recommendations(seed_artists=artists, seed_genres=genres, limit=limit, country=country)
    elif artists is not None and songs is not None and genres is None:
        rec = top.recommendations(seed_artists=artists, seed_tracks=songs, limit=limit, country=country)
    else:
        rec = top.recommendations(seed_artists=artists, seed_genres=genres, seed_tracks=songs, limit=limit, country=country)
    return rec

def check_invalid(artists, genres, songs):
    if all(x is None for x in [artists, genres, songs]):
        return render_template("invalid_input.html")
    
    total_seeds = sum(len(x) for x in [artists, genres, songs] if x is not None)
    if total_seeds > 5:
        return render_template("invalid_input.html")

def check_None(artists, genres, songs):
    if artists[0] == "None":
        artists = None
    if genres[0] == "None":
        genres = None
    if songs[0] == "None":
        songs = None
    return artists,genres,songs

def gen_rec_vars(request):
    top = gen_Spotipy()
    output = request.form.to_dict(flat=False)
    limit = int(output.get("before_recommended_limit", 1)[0])
    country = output.get("selected_country", "US")[0]
    artists = output.get("selected_artists[]", None)
    genres = output.get("selected_genres[]", None)
    songs = output.get("selected_songs[]", None)
    return top,limit,country,artists,genres,songs

def recent_vars(request):
    output = request.form.to_dict()
    limit = output.get("recent_limit", 1)
    return limit

def top_songs_vars(request):
    output = request.form.to_dict()
    limit = output.get("songs_limit", -1)
    offset = output.get("songs_offset", -1)
    time_length = output.get("songs_time_length", "")
    return limit, offset, time_length

def top_artists_vars(request):
    output = request.form.to_dict()
    limit = output.get("artists_limit", -1)
    offset = output.get("artists_offset", -1)
    time_length = output.get("artists_time_length", "")
    return limit,offset,time_length


def get_Users_Top_Tracks(top_Spotipy: spotipy, limit: int, offset: int, time_length: str):
    top_tracks = top_Spotipy.current_user_top_tracks(
        limit, offset, time_length)
    my_dict = {}
    for idx, item in enumerate(top_tracks["items"]):
        my_dict[idx + 1] = [item["name"] , item["album"]["images"][0]["url"]]
    return my_dict

def get_Track_ID(top_Spotipy: spotipy, limit: int, offset: int, time_length: str):
    top_tracks = top_Spotipy.current_user_top_tracks(
        limit, offset, time_length)
    my_dict = {}
    for idx, item in enumerate(top_tracks["items"]):
        my_dict[idx] = [item["name"], item["id"], item["album"]["images"][0]["url"]]
    return my_dict

def get_Users_Top_Artists(top_Spotipy: spotipy, limit: int, offset: int, time_length: str):
    top_artists = top_Spotipy.current_user_top_artists(
        limit, offset, time_length)
    my_dict = {}
    for idx, item in enumerate(top_artists["items"]):
        artist = item["name"]
        my_dict[idx + 1] = [artist , item["images"][0]["url"]]
    return my_dict

def get_Artists_ID(top_Spotipy: spotipy, limit: int, offset: int, time_length: str):
    top_artists = top_Spotipy.current_user_top_artists(
        limit, offset, time_length)
    my_dict = {}
    for idx, item in enumerate(top_artists["items"]):
        my_dict[idx] = [item["name"], item["id"], item["images"][0]["url"]]
    return my_dict

def get_Users_Recently_Played(recently_played_spotipy: spotipy, limit: int):
    my_dict = {}
    results = recently_played_spotipy.current_user_recently_played(limit)
    for idx, item in enumerate(results['items']):
        track = item['track']
        my_dict[idx + 1] = [track['artists'][0]['name'], track['name'] , item["track"]["album"]["images"][0]["url"]]
    return my_dict

def get_Recent_ID(recently_played_spotipy: spotipy, limit: int):
    my_dict = {}
    results = recently_played_spotipy.current_user_recently_played(limit)
    for idx, item in enumerate(results['items']):
        track = item['track']
        my_dict[idx] = [track['name']], track["artists"][0]["id"], item["track"]["album"]["images"][0]["url"]
    return my_dict

def get_Recent_Top(recently_played_spotipy: spotipy, limit: int):
    my_dict = {}
    results = recently_played_spotipy.current_user_recently_played(limit)
    for idx, item in enumerate(results['items']):
        track = item['track']
        my_dict[idx] = [track["artists"][0]['name']], track["artists"][0]["id"], item["track"]["album"]["images"][0]["url"]
    return my_dict

def gen_Spotipy():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URL,
        scope=SCOPES
    ))

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 9001)))
