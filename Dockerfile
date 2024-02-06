# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Copy the start script into the container
COPY start.sh /start.sh

RUN apt-get update && apt-get install -y openssh-client sshpass redis-server

RUN chmod +x /start.sh

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make the start script executable

# Expose the port the app runs on
EXPOSE 8000
EXPOSE 5000
EXPOSE 80
EXPOSE 300
EXPOSE 3000


# Start script that handles SSH connection and starts the application
CMD ["/start.sh"]
#CMD ["/bin/bash"]

