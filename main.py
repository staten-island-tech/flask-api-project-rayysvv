# Imports
import os
from dotenv import load_dotenv
from flask import Flask, request, redirect, session, url_for, render_template
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from requests.exceptions import ReadTimeout

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)

# Load environment variables
load_dotenv()

# Environment Variables
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
redirect_uri = os.getenv('REDIRECT_URI')
scope = 'playlist-read-private'

# Spotify OAuth setup
cache_handler = FlaskSessionCacheHandler(session)
sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_handler=cache_handler,
    show_dialog=True,
    requests_timeout=10  # Increased timeout to handle slow API responses
)

# Spotify API client
sp = Spotify(auth_manager=sp_oauth)

# Global dictionary to store user playlists
user_playlists = {}

# Validate Spotify token
def validate_token():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    return None

# Home route
@app.route('/')
def home():
    validation = validate_token()
    if validation:
        return validation
    return redirect(url_for('get_playlists'))

# Spotify callback route
@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args['code'])
    return redirect(url_for('get_playlists'))

# User page route
@app.route('/user/<user_id>')
def user_page(user_id):
    # Check if the user's playlists are already stored
    if user_id not in user_playlists:
        return "User not found or no playlists available.", 404

    # Retrieve the user's playlists, display name, and profile picture
    user_data = user_playlists[user_id]
    display_name = user_data['display_name']
    profile_picture = user_data['profile_picture']
    playlists_info = user_data['playlists']

    # Render a template for the user's page
    return render_template('user_page.html', 
        user_id=user_id, 
        display_name=display_name, 
        profile_picture=profile_picture, 
        playlists=playlists_info)

# Get playlists route
@app.route('/get_playlists')
def get_playlists():
    validation = validate_token()
    if validation:
        return validation

    try:
        # Fetch current user and playlists
        current_user = sp.current_user()
        user_id = current_user['id']
        display_name = current_user.get('display_name', 'Unknown User')  # Get the display name

        # Get the profile picture URL
        profile_images = current_user.get('images', [])
        profile_picture = profile_images[0]['url'] if profile_images else None

        playlists = sp.current_user_playlists()
        playlists_info = []

        for playlist in playlists['items']:
            name = playlist['name']
            url = playlist['external_urls']['spotify']
            playlist_id = playlist['id']

            # Fetch playlist cover image
            cover_images = sp.playlist_cover_image(playlist_id)
            cover_url = cover_images[0]['url'] if cover_images else None

            playlists_info.append({
                'name': name,
                'url': url,
                'cover_url': cover_url
            })

        # Store playlists, display name, and profile picture in the global dictionary
        user_playlists[user_id] = {
            'display_name': display_name,
            'profile_picture': profile_picture,
            'playlists': playlists_info
        }

        # Redirect to the user's individual page
        return redirect(url_for('user_page', user_id=user_id))
    except ReadTimeout:
        return "The request to Spotify timed out. Please try again later.", 504

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/account')
def account():
    # Fetch the current user's data from the global dictionary
    user_id = session.get('user_id')
    if not user_id or user_id not in user_playlists:
        return redirect(url_for('home'))  # Redirect to home if user is not logged in

    user_data = user_playlists[user_id]
    display_name = user_data['display_name']
    profile_picture = user_data['profile_picture']

    # Render the account page
    return render_template('account.html', display_name=display_name, profile_picture=profile_picture)

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)