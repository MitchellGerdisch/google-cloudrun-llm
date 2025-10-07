# Alternative approach using init containers to download model on startup
# This would replace the ollama_cr_service definition in __main__.py

ollama_cr_service_with_init = cloudrun.Service("ollama_cr_service",
    name="ollama-service",
    location=gcp_region,
    deletion_protection= False,
    ingress="INGRESS_TRAFFIC_ALL",
    launch_stage="BETA",
    template={
        "containers":[{
            "image": "ollama/ollama:latest",
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
                "initial_delay_seconds": 60,  # Increased to allow model download
                "timeout_seconds": 5,
                "period_seconds": 10,
                "failure_threshold": 180,  # 30 minutes max
                "tcp_socket": {
                    "port": 11434,
                },
            },
        }],
        # Init container to download the model
        "init_containers": [{
            "image": "ollama/ollama:latest",
            "name": "model-downloader",
            "command": ["/bin/sh"],
            "args": ["-c", "ollama serve & sleep 10 && ollama pull gemma2:2b && pkill ollama"],
            "volume_mounts": [{
                "name": "ollama-bucket",
                "mount_path": "/root/.ollama/",
            }],
        }],
        "node_selector": {
            "accelerator": "nvidia-l4", 
        },
        "gpu_zonal_redundancy_disabled": True,
        "scaling": {      
            "max_instance_count":3,
            "min_instance_count":1,
        },
        "volumes":[{
            "name": "ollama-bucket",
            "gcs": {
                "bucket": llm_bucket.name,
                "read_only": False,
            },
        }],
    },
)