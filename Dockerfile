# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set environment variables to prevent Python from writing pyc files and to buffer stdout and stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install ODBC libraries and dependencies for SQL Server
RUN apt-get update && \
    apt-get install -y curl gnupg2 apt-transport-https unixodbc-dev && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    apt-get install -y libpq-dev build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create a directory for the application code
RUN mkdir /app
WORKDIR /app

# Copy the requirements.txt file and install the dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the container
COPY . /app/

# Expose the port the app runs on
EXPOSE 5000

# Run the application
CMD ["gunicorn", "--worker-tmp-dir", "/dev/shm", "--bind", "0.0.0.0:5000", "wsgi:app"]
