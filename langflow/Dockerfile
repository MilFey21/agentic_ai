# need fix issue https://github.com/langflow-ai/langflow/issues/11313 !!!
FROM langflowai/langflow:1.7.2

# Set working directory
WORKDIR /app

COPY requirements.txt .
RUN python3 -m ensurepip && python -m pip install --no-cache-dir -r requirements.txt

# Copy your components
COPY components /tmp/components

# Find the site-packages directory where langflow is installed
RUN python -c "import site; print(site.getsitepackages()[0])" > /tmp/site_packages.txt

# Replace the file in the site-packages location
RUN SITE_PACKAGES=$(cat /tmp/site_packages.txt) && \
    echo "Site packages at: $SITE_PACKAGES" && \
    mkdir -p "$SITE_PACKAGES/langflow/components/helpers" && \
    cp -rT /tmp/components "$SITE_PACKAGES/langflow/components/helpers/"

# Clear Python cache in the site-packages directory only
RUN SITE_PACKAGES=$(cat /tmp/site_packages.txt) && \
    find "$SITE_PACKAGES" -name "*.pyc" -delete && \
    find "$SITE_PACKAGES" -name "__pycache__" -type d -exec rm -rf {} +

# Expose the default Langflow port
EXPOSE 7860

# Command to run Langflow
CMD ["python", "-m", "langflow", "run", "--host", "0.0.0.0", "--port", "7860"]
