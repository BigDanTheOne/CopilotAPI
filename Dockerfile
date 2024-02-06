# Use an official Python runtime as a parent image
FROM python:3.9

# Install SSH client
RUN apt-get update && apt-get install -y openssh-client

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Copy the start script into the container
COPY start.sh /start.sh

RUN apt-get update && apt-get install -y openssh-client sshpass

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make the start script executable
RUN chmod +x /start.sh


# Expose the port the app runs on
EXPOSE 8000

# Install Redis
RUN apt-get update && apt-get install -y redis-server

# Start script that handles SSH connection and starts the application
CMD ["/start.sh"]
