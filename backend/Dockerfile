# Dockerfile for LocalChess Backend

FROM python:3.8-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code
COPY . .

# Expose the necessary port (e.g. 5000)
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]