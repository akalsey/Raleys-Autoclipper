# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install git
RUN apt-get update && apt-get install -y git

# Clone the application code from the Git repository
RUN git clone https://github.com/akalsey/Raleys-Autoclipper.git /app

# Copy .env file if it exists
COPY .env /app/.env

# Alternatively, uncomment these and use them
# ENV RALEYS_EMAIL="your_email@example.com"
# ENV RALEYS_PASSWORD="your_password"

# Install asyncio and python-dotenv in case it's missing
RUN pip install asyncio python-dotenv

# Install Playwright and the required browser binaries
RUN pip install playwright && playwright install && playwright install-deps

# Install cron
RUN apt-get update && apt-get install -y cron

# Set environment variables to prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Add crontab to run the script daily at 9am Pacific Time
RUN echo "0 17 * * * /usr/local/bin/python /app/raleys-autoclipper.py >> /var/log/cron.log 2>&1" > /etc/cron.d/raleys-autoclipper

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/raleys-autoclipper

# Apply cron job
RUN crontab /etc/cron.d/raleys-autoclipper

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Start cron and keep the container running
CMD ["sh", "-c", "cron && /usr/local/bin/python /app/raleys-autoclipper.py >> /var/log/cron.log 2>&1 && tail -f /var/log/cron.log"]
# ENTRYPOINT ["/bin/bash"]
