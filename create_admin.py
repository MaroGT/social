import sys
from werkzeug.security import generate_password_hash
from src import db
from src.models import User  # Import the User model

def create_admin(email, password):
    # Check if the admin already exists
    existing_admin = User.query.filter_by(is_admin=True).first()
    if existing_admin:
        print("An admin already exists.")
        return

    # Create a new admin user
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')  # Correct hash method
    new_admin = User(email=email, password=hashed_password, is_admin=True)


    # Add to the database
    db.session.add(new_admin)
    db.session.commit()
    print(f"Admin account created successfully with email: {email}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python create_admin.py <email> <password>")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]

    # Initialize the database
    from src import create_app
    app = create_app()
    with app.app_context():
        create_admin(email, password)
