# OPTION 2: Environment Variable Approach
# This is an alternative implementation that downloads the model on startup
# Replace the ollama_cr_service definition in __main__.py with this:

ollama_cr_service_env_approach = cloudrun.Service("ollama_cr_service",
    name="ollama-service",
    location=gcp_region,
    deletion_protection= False,
    ingress="INGRESS_TRAFFIC_ALL",
    launch_stage="BETA",
    template={
        "containers":[{
            "image": "ollama/ollama:latest",  # Using base Ollama image
            
            # Environment variables for Ollama configuration
            "envs": [
                # {
                #     "name": "OLLAMA_MODELS",
                #     "value": "/root/.ollama/models"
                # },
                # {
                #     "name": "OLLAMA_HOST", 
                #     "value": "0.0.0.0:11434"
                # },
                # {
                #     "name": "OLLAMA_KEEP_ALIVE",
                #     "value": "24h"  # Keep model loaded for 24 hours
                # },
                {
                    "name": "MODEL_NAME",
                    "value": "gemma2:2b"  # Model to download and run
                }
            ],
            
            # Custom startup command to download model and start server
            "command": ["/bin/bash"],
            "args": [
                "-c", 
                """
                echo "Starting Ollama server in background..."
                ollama serve &
                
                echo "Waiting for Ollama server to start..."
                sleep 10
                
                echo "Pulling model: $MODEL_NAME"
                ollama pull $MODEL_NAME
                
                echo "Model downloaded. Keeping Ollama server running..."
                wait
                """
            ],
            
            "resources": {
                "cpuIdle": False,
                "limits":{
                    "cpu": "8",
                    "memory": "16Gi",
                    "nvidia.com/gpu": "1",
                },
                "startup_cpu_boost": True,
            },
            "ports": {
                "container_port": 11434,
            },
            "volume_mounts": [{
                "name": "ollama-bucket",
                "mount_path": "/root/.ollama/",
            }],
            "startup_probe": {
                "initial_delay_seconds": 60,  # Increased delay for model download
                "timeout_seconds": 5,
                "period_seconds": 10,
                "failure_threshold": 360,  # 60 minutes max (model download can take time)
                "tcp_socket": {
                    "port": 11434,
                },
            },
        }],
        "node_selector": {
            "accelerator": "nvidia-l4", 
        },
        "gpu_zonal_redundancy_disabled": True,
        "scaling": {      
            "max_instance_count": 3,
            "min_instance_count": 0,  # Allow scale to zero since model download takes time
        },
        "volumes":[{
            "name": "ollama-bucket",
            "gcs": {
                "bucket": llm_bucket.name,
                "read_only": False,
            },
        }],
    },
    # No dependency on custom Docker image since we're using base image
)