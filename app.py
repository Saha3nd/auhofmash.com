# app.py

from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import random
from sqlalchemy import or_

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Picture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), unique=True, nullable=False)  # Ensure filenames are unique
    elo_rating = db.Column(db.Integer, default=1500)

def update_elo(winner_elo, loser_elo, k=64):
    # Function to update Elo ratings
    winner_expected = 1 / (1 + 10**((loser_elo - winner_elo) / 400))
    loser_expected = 1 / (1 + 10**((winner_elo - loser_elo) / 400))

    winner_new_elo = winner_elo + k * (1 - winner_expected)
    loser_new_elo = loser_elo + k * (0 - loser_expected)

    return winner_new_elo, loser_new_elo

def get_or_create_picture(filename):
    # Function to get an existing Picture or create a new one
    picture = Picture.query.filter_by(filename=filename).first()

    if not picture:
        picture = Picture(filename=filename)
        db.session.add(picture)
        db.session.commit()

    return picture

@app.route('/update_elo', methods=['POST'])
def update_elo_route():
    data = request.get_json()
    winner_id = data.get('winner')
    loser_id = data.get('loser')

    winner = db.session.get(Picture, winner_id)
    loser = db.session.get(Picture, loser_id)

    if winner and loser:
        winner_elo = winner.elo_rating
        loser_elo = loser.elo_rating

        print(f"Before Update - Winner Elo: {winner_elo}, Loser Elo: {loser_elo}")
        # Update Elo ratings
        new_elo_winner, new_elo_loser = update_elo(winner_elo, loser_elo)
        print(f"After Update - Winner Elo: {new_elo_winner}, Loser Elo: {new_elo_loser}")


        winner.elo_rating = new_elo_winner
        db.session.add(winner)

        loser.elo_rating = new_elo_loser
        db.session.add(loser)

        db.session.commit()  # Commit changes to the database

        return jsonify({'message': 'Elo ratings updated successfully'})
    else:
        return jsonify({'message': 'Invalid winner or loser ID'})


@app.route('/podium')
def podium():
    # Filter out entries with filenames containing digits
    all_pictures = Picture.query.filter(
        Picture.elo_rating != 1500,
    ).order_by(Picture.elo_rating.desc()).all()

    podium_data = {
        rank + 1: {
            'filename': picture.filename,
            'elo_rating': round(picture.elo_rating)
        } for rank, picture in enumerate(all_pictures)
    }

    app.logger.info(f"Podium Data: {podium_data}")  # Log the podium data

    return render_template('podium.html', podium_data=podium_data)

def get_comparable_pictures(elo_rating, picture_filenames, threshold=100):
    # Get a list of picture filenames with Elo ratings close to the given rating
    comparable_filenames = [
        filename for filename in picture_filenames
        if (
            Picture.query.filter_by(filename=filename).first() is not None and
            abs(Picture.query.filter_by(filename=filename).first().elo_rating - elo_rating) < threshold
        )
    ]

    return comparable_filenames

@app.route('/')
def index():
    # Route to display two pictures for comparison based on Elo ratings
    uploads_folder = os.path.join(app.static_folder, 'uploads')
    picture_filenames = os.listdir(uploads_folder)

    if len(picture_filenames) < 2:
        return "Not enough pictures in the 'uploads' folder."

    # Choose a random picture as the base for Elo rating comparison
    base_picture_filename = random.choice(picture_filenames)
    base_picture_elo = Picture.query.filter_by(filename=base_picture_filename).first()

    if base_picture_elo is None:
        return "Base picture not found in the database."

    # Get comparable pictures based on Elo ratings
    comparable_filenames = get_comparable_pictures(base_picture_elo.elo_rating, picture_filenames)

    if len(comparable_filenames) < 2:
        return "Not enough comparable pictures for the chosen base picture."

    # Choose two random comparable pictures for comparison
    picture1_filename, picture2_filename = random.sample(comparable_filenames, 2)

    # Get or create Picture objects from the database using filenames
    picture1 = Picture.query.filter_by(filename=picture1_filename).first()
    picture2 = Picture.query.filter_by(filename=picture2_filename).first()

    if picture1 is None:
        picture1 = Picture(filename=picture1_filename)
        db.session.add(picture1)
        db.session.commit()

    if picture2 is None:
        picture2 = Picture(filename=picture2_filename)
        db.session.add(picture2)
        db.session.commit()

    return render_template('index.html', picture1=picture1, picture2=picture2)

@app.route('/reset_elos', methods=['POST'])
def reset_elos():
    data = request.get_json()
    new_elo = data.get('new_elo', 1500)  # Default new Elo rating is 1500

    pictures = Picture.query.all()

    for picture in pictures:
        picture.elo_rating = new_elo
        db.session.add(picture)

    db.session.commit()

    return jsonify({'message': f'Elo ratings reset to {new_elo} successfully'})

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

# Health check route
@app.route('/healthz')
def health_check():
    # Perform quick sanity checks (e.g., simple database query)
    # Return an "OK" 200 response or an empty 204 response if the app is healthy
    # Adjust the checks based on your application's dependencies

    # Example: Check if the database is reachable
    try:
        # Perform a simple database query here
        # If successful, return an "OK" response
        return jsonify({'status': 'OK'}), 200
    except Exception as e:
        # If there's an error, return a failure response
        return jsonify({'status': 'Error', 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)