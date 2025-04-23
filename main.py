# Imports

import os
from dotenv import load_dotenv
from flask import Flask, request, redirect, session, url_for, render_template
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)

load_dotenv()

# Environment Variables

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
redirect_uri = os.getenv('REDIRECT_URI')
scope = 'playlist-read-private'

cache_handler = FlaskSessionCacheHandler(session)
sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_handler=cache_handler,
    show_dialog=True
)

sp = Spotify(auth_manager=sp_oauth)

user_playlists = {}

def validate_token():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    return None

@app.route('/')
def home():
    validation = validate_token()
    if validation:
        return validation
    return redirect(url_for('get_playlists'))

@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args['code'])
    return redirect(url_for('get_playlists'))

@app.route('/get_playlists')
def get_playlists():
    validation = validate_token()
    if validation:
        return validation

    current_user = sp.current_user()
    user_id = current_user['id']

    playlists = sp.current_user_playlists()
    playlists_info = []

    for playlist in playlists['items']:
        name = playlist['name']
        url = playlist['external_urls']['spotify']
        playlist_id = playlist['id']

        cover_images = sp.playlist_cover_image(playlist_id)
        cover_url = cover_images[0]['url'] if cover_images else None

        playlists_info.append({
            'name': name,
            'url': url,
            'cover_url': cover_url
        })

    user_playlists[user_id] = playlists_info

    return render_template('playlists.html', playlists=playlists_info)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)