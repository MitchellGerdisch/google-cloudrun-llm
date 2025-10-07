# Environment Variable Approach - Key Differences from Custom Docker Image

## Pros of Environment Variable Approach:
- No need to build custom Docker images
- Easy to change models by updating environment variables
- Flexibility to pull different models based on configuration
- Leverages Cloud Storage for model persistence across restarts

## Cons of Environment Variable Approach:
- Longer cold start times (model download on first start)
- Network dependency during startup
- Higher startup probe timeouts needed
- Potential for startup failures if model download fails

## Key Changes Needed in __main__.py:

1. **Use base Ollama image instead of custom image:**
   ```python
   "image": "ollama/ollama:latest",  # Instead of ollama_image
   ```

2. **Add environment variables:**
   ```python
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
           "name": "OLLAMA_KEEP_ALIVE",
           "value": "24h"
       },
       {
           "name": "MODEL_NAME",
           "value": "gemma2:2b"
       }
   ],
   ```

3. **Add startup command to download model:**
   ```python
   "command": ["/bin/bash"],
   "args": [
       "-c", 
       "ollama serve & sleep 10 && ollama pull $MODEL_NAME && wait"
   ],
   ```

4. **Increase startup probe timeouts:**
   ```python
   "startup_probe": {
       "initial_delay_seconds": 60,  # More time for model download
       "timeout_seconds": 5,
       "period_seconds": 10,
       "failure_threshold": 360,  # 60 minutes max
       "tcp_socket": {
           "port": 11434,
       },
   },
   ```

5. **Remove dependency on custom Docker image:**
   ```python
   # Remove: opts=pulumi.ResourceOptions(depends_on=[ollama_docker_image])
   ```

6. **Optional: Allow scale to zero:**
   ```python
   "scaling": {      
       "max_instance_count": 3,
       "min_instance_count": 0,  # Can scale to zero since startup is longer anyway
   },
   ```

## When to use each approach:

**Custom Docker Image (Current):**
- Production environments where fast cold starts are critical
- When you have a fixed set of models
- When you want maximum reliability and performance

**Environment Variable Approach:**
- Development/testing environments
- When you frequently change models
- When you want to avoid managing custom Docker images
- When longer cold starts are acceptable