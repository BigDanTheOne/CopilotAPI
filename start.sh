#!/bin/bash

# Function to establish SSH tunnel
establish_ssh_tunnel() {
    while true; do
        # Use sshpass to provide the password non-interactively
        sshpass -p 'ncJUftkzearUC9YxNKK1' ssh -N -L 6011:localhost:6011 bohonkomi@lorien.atp-fivt.org \
            -o ServerAliveInterval=60 \
            -o ExitOnForwardFailure=yes \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null

        # Wait a bit before trying to reconnect
        echo "SSH tunnel disconnected. Reconnecting in 1 second..."
        sleep 1
    done
}

# Start the SSH tunnel in the background
establish_ssh_tunnel &

# Start Redis server
redis-server --daemonize yes

# Start the application
python app.py
