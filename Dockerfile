# Use the Playwright base image for Python
FROM mcr.microsoft.com/playwright/python:v1.48.0-focal

# Set the working directory in the container
WORKDIR /app

# Set environment variable to make installations non-interactive
ENV DEBIAN_FRONTEND=noninteractive

# Install git, mail utilities, and cron
RUN apt-get update && apt-get install -y \
    git \
    mailutils \
    logrotate \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Clone the application code from the Git repository
RUN git clone https://github.com/akalsey/Raleys-Autoclipper.git /app

# Copy .env file if it exists
COPY .env /app/.env

# Alternatively, uncomment these and use them
# ENV RALEYS_EMAIL="your_email@example.com"
# ENV RALEYS_PASSWORD="your_password"
# ENV MAIL_TO="your_email@example.com"

# Install Playwright, asyncio, and python-dotenv in case they are missing
RUN pip install asyncio python-dotenv playwright
RUN playwright install --with-deps chromium

# Set environment variables to prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Add crontab to run the script twice daily and every four hours on Tuesdays
RUN echo "0 9,21 * * * /usr/bin/python3 /app/raleys-autoclipper.py >> /var/log/cron.log 2>&1" > /etc/cron.d/raleys-autoclipper \
    && echo "0 */4 * * 2 /usr/bin/python3 /app/raleys-autoclipper.py >> /var/log/cron.log 2>&1" >> /etc/cron.d/raleys-autoclipper \
    && echo "0 0 * * * git -C /app pull >> /var/log/cron.log 2>&1" >> /etc/cron.d/raleys-autoclipper

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/raleys-autoclipper

# Apply cron job
RUN crontab /etc/cron.d/raleys-autoclipper

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Configure logrotate to rotate the cron log daily and email it
RUN echo "/var/log/cron.log {\n    daily\n    rotate 7\n    compress\n    missingok\n    notifempty\n    create 0644 root root\n    prerotate\n        /usr/bin/mail -s \"Raley's Clipper log\" \$MAIL_TO < /var/log/cron.log\n    endscript\n}" > /etc/logrotate.d/cronlog

# Start cron, pull the latest code, run the script once, and keep the container running
CMD ["sh", "-c", "git -C /app pull && cron && /usr/bin/python3 /app/raleys-autoclipper.py >> /var/log/cron.log 2>&1 && tail -f /var/log/cron.log"]