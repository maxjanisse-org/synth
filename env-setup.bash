#!/bin/bash
# Max Janisse - 2026

if [[ $1 == "-R" ]]; then
    echo -e "Removing existing 'venv' Python environment..."
    rm -fR venv
fi

if [ ! -d "venv" ]; then
    echo -e "Creating Python environment..."
    python3 -m venv venv > /dev/null
    echo -e "Activating Python environment..."
    source venv/bin/activate
    if [ -f "requirements.txt" ]; then
        echo -e "Restoring packages...\n"
        pip install -r ./requirements.txt > /dev/null
    else
        echo -e "Install required packages and generate a 'requirements.txt'...\n"
    fi
elif [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "Activating existing Python environment..."
    source venv/bin/activate
else
    echo -e "Python environment exists and is active, no action necessary..."
fi