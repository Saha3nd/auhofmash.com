# app.py

from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Picture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), unique=True, nullable=False)  # Ensure filenames are unique
    elo_rating = db.Column(db.Integer, default=1500)

def update_elo(winner_elo, loser_elo, k=32):
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

    winner = Picture.query.get(winner_id)
    loser = Picture.query.get(loser_id)

    if winner and loser:
        winner_elo = winner.elo_rating
        loser_elo = loser.elo_rating

        # Update Elo ratings
        new_elo_winner, new_elo_loser = update_elo(winner_elo, loser_elo)

        # Check if a picture with the same Elo rating already exists
        existing_winner = Picture.query.filter_by(elo_rating=new_elo_winner).first()
        existing_loser = Picture.query.filter_by(elo_rating=new_elo_loser).first()

        if existing_winner:
            winner = existing_winner
        else:
            # Save updated Elo rating to the database
            winner.elo_rating = new_elo_winner
            db.session.add(winner)

        if existing_loser:
            loser = existing_loser
        else:
            # Save updated Elo rating to the database
            loser.elo_rating = new_elo_loser
            db.session.add(loser)

        db.session.commit()  # Commit changes to the database

        return jsonify({'message': 'Elo ratings updated successfully'})
    else:
        return jsonify({'message': 'Invalid winner or loser ID'})


@app.route('/podium')
def podium():
    all_pictures = Picture.query.order_by(Picture.elo_rating.desc()).all()
    podium_data = {rank + 1: {'filename': picture.filename, 'elo_rating': picture.elo_rating} for rank, picture in enumerate(all_pictures)}

    return render_template('podium.html', podium_data=podium_data)

@app.route('/')
def index():
    # Route to display two random pictures for comparison
    uploads_folder = os.path.join(app.static_folder, 'uploads')
    picture_filenames = os.listdir(uploads_folder)

    if len(picture_filenames) < 2:
        return "Not enough pictures in the 'uploads' folder."

    picture1_filename, picture2_filename = random.sample(picture_filenames, 2)

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

    print(f"Picture 1 Filename: {picture1_filename}")
    print(f"Picture 2 Filename: {picture2_filename}")
    print(f"Picture 1 Object: {picture1}")
    print(f"Picture 2 Object: {picture2}")

    return render_template('index.html', picture1=picture1, picture2=picture2)

from flask import Flask, render_template, request, jsonify

# ... (your existing code)

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

if __name__ == '__main__':
    app.run(debug=True)
