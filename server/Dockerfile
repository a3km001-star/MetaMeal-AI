# Use an official lightweight Python image
FROM python:3.11-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files to disk
# PYTHONUNBUFFERED: Ensures Python output is sent straight to terminal (good for Docker logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first (to leverage Docker cache)
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
# This will copy your services, controllers, models, and constants (like supplements.json)
COPY . .

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# Command to run the application using Uvicorn
# Note: This assumes your FastAPI instance is named "app" inside a file named "main.py".
# If your entry file is named something else (e.g., app.py), change "main:app" to "app:app"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]