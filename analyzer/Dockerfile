FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies + Node.js (needed for real JS/TS/JSX parsing
# via @babel/parser - a pure-Python parser can't keep up with modern syntax)
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Node dependencies for the JS/TS parser subprocess
COPY js_ast/package.json js_ast/package-lock.json ./js_ast/
RUN cd js_ast && npm ci --omit=dev

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/codesage/repos

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]