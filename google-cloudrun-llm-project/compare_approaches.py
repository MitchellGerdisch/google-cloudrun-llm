#!/usr/bin/env python3
"""
Script to show the exact changes needed to switch from custom Docker image 
to environment variable approach for model loading.

Run this to see a side-by-side comparison.
"""

print("=== CURRENT APPROACH (Custom Docker Image) ===")
print("""
# Uses custom built image with model pre-installed
"image": ollama_image,  # Custom image built from Dockerfile.ollama

# Fast startup since model is already in image
"startup_probe": {
    "initial_delay_seconds": 0,
    "timeout_seconds": 1,
    "period_seconds": 1,
    "failure_threshold": 1800,
    "tcp_socket": {
        "port": 11434,
    },
},
""")

print("\n=== ENVIRONMENT VARIABLE APPROACH ===")
print("""
# Uses base Ollama image
"image": "ollama/ollama:latest",

# Add environment variables for configuration
"envs": [
    {
        "name": "OLLAMA_MODELS",
        "value": "/root/.ollama/models"
    },
    {
        "name": "OLLAMA_HOST", 
        "value": "0.0.0.0:11434"
    },
    {
        "name": "MODEL_NAME",
        "value": "gemma2:2b"  # Change this to use different models
    }
],

# Custom startup command to download model
"command": ["/bin/bash"],
"args": ["-c", "ollama serve & sleep 10 && ollama pull $MODEL_NAME && wait"],

# Longer startup probe for model download time
"startup_probe": {
    "initial_delay_seconds": 60,
    "timeout_seconds": 5,
    "period_seconds": 10,
    "failure_threshold": 360,  # Up to 60 minutes
    "tcp_socket": {
        "port": 11434,
    },
},
""")

print("\n=== TO SWITCH APPROACHES ===")
print("""
1. Replace the ollama container configuration in __main__.py
2. Remove the ollama_docker_image build (keep only openwebui_docker_image)
3. Remove dependency: opts=pulumi.ResourceOptions(depends_on=[ollama_docker_image])
4. Optional: Delete Dockerfile.ollama if not needed

The environment variable approach is great for:
- Testing different models quickly
- Development environments
- When you don't want to manage custom Docker builds

Just change the MODEL_NAME environment variable to try different models:
- "gemma2:2b"
- "llama3.1:8b"  
- "codellama:7b"
- "mistral:7b"
- "phi3:mini"
""")

if __name__ == "__main__":
    print("Run this script to see the comparison!")