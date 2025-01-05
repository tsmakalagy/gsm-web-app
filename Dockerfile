# Use a base image with Python 2.7
FROM python:2.7-slim

# Set the working directory
WORKDIR /app

# Copy the application files
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

# Install gsm modem library manually
RUN git clone https://github.com/faucamp/python-gsmmodem.git && \
    cd python-gsmmodem && \
    pip install .

# Expose port 5000 for the app
EXPOSE 5000

# Command to run the app with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:app", "--worker-class", "eventlet", "-w", "1"]