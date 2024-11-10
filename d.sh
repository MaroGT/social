#!/bin/bash

# Activate the virtual environment if it's not already activated
if [[ -z "$VIRTUAL_ENV" ]]; then
  source .venv/bin/activate
fi

# Set the necessary Flask environment variables
export FLASK_APP=main.py
export FLASK_ENV=development  # Activates debug mode

# Run the Flask app
flask --debug run
