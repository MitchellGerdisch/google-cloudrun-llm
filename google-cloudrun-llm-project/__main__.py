import pulumi
from pulumi_command import local
from pulumi import Output, Config
import pulumi_gcp as gcp
import pulumi_docker as docker
import pulumi_docker_build as docker_build
from pulumi_gcp import cloudrunv2 as cloudrun

# Get some provider-namespaced configuration values such as project
gconfig = pulumi.Config("gcp")
gcp_project = gconfig.require("project")
gcp_region = gconfig.get("region", "us-central1")
gcp_zone = gconfig.get("zone", "us-central1-a")

# LLM Bucket
llm_bucket = gcp.storage.Bucket("llm-bucket",
    name=str(gcp_project)+"-llm-bucket",
    location=gcp_region,
    force_destroy=True,
    uniform_bucket_level_access=True,
    )

# Artifact Registry Repo for Docker Images
llm_repo = gcp.artifactregistry.Repository("llm-repo",
    location=gcp_region,
    repository_id="openwebui",
    description="Repo for Open WebUI usage",
    format="DOCKER",
    docker_config={
        "immutable_tags": True,
    }
)

# Docker image URLs
openwebui_image = str(gcp_region)+"-docker.pkg.dev/"+str(gcp_project)+"/openwebui/openwebui"

# Build and Deploy Open WebUI Docker
openwebui_docker_image = docker_build.Image('openwebui',
    tags=[openwebui_image],                                  
    context=docker_build.BuildContextArgs(
        location="./",
    ),
    dockerfile=docker_build.DockerfileArgs(
        location="./Dockerfile.openwebui",
    ),
    platforms=[
        docker_build.Platform.LINUX_AMD64,
        docker_build.Platform.LINUX_ARM64,
    ],
    push=True,
)

# # Build and Deploy Ollama Docker with pre-installed model
# ollama_image = str(gcp_region)+"-docker.pkg.dev/"+str(gcp_project)+"/openwebui/ollama-with-model"
# ollama_docker_image = docker_build.Image('ollama_with_model',
#     tags=[ollama_image],                                  
#     context=docker_build.BuildContextArgs(
#         location="./",
#     ),
#     dockerfile=docker_build.DockerfileArgs(
#         location="./Dockerfile.ollama",
#     ),
#     platforms=[
#         docker_build.Platform.LINUX_AMD64,
#         docker_build.Platform.LINUX_ARM64,
#     ],
#     push=True,
# )

# Ollama Cloud Run instance cloudrunv2 api
# # OPTION 1: Using custom Docker image with pre-installed model (current implementation)
# ollama_cr_service = cloudrun.Service("ollama_cr_service",
#     name="ollama-service",
#     location=gcp_region,
#     deletion_protection= False,
#     ingress="INGRESS_TRAFFIC_ALL",
#     launch_stage="BETA",
#     template={
#         "containers":[{
#             "image": ollama_image,  # Custom image with pre-installed model
#             "resources": {
#                 "cpuIdle": False,
#                 "limits":{
#                     "cpu": "8",
#                     "memory": "16Gi",
#                     "nvidia.com/gpu": "1",
#                 },
#                 "startup_cpu_boost": True,
#             },
#             "ports": {
#                 "container_port": 11434,
#             },
#             "volume_mounts": [{
#                 "name": "ollama-bucket",
#                 "mount_path": "/root/.ollama/",
#             }],
#             "startup_probe": {
#                 "initial_delay_seconds": 0,
#                 "timeout_seconds": 1,
#                 "period_seconds": 1,
#                 "failure_threshold": 1800,
#                 "tcp_socket": {
#                     "port": 11434,
#                 },
#             },
#         }],
#         "node_selector": {
#             "accelerator": "nvidia-l4", 
#         },
#         "gpu_zonal_redundancy_disabled": True,
#         "scaling": {      
#             "max_instance_count":3,
#             "min_instance_count":1,
#         },
#         "volumes":[{
#             "name": "ollama-bucket",
#             "gcs": {
#                 "bucket": llm_bucket.name,
#                 "read_only": False,
#             },
#         }],
#     },
#     opts=pulumi.ResourceOptions(depends_on=[ollama_docker_image]),
# )

# OPTION 2: Using base Ollama image with environment variables and startup command
ollama_cr_service = cloudrun.Service("ollama_cr_service",
    name="ollama-service",
    location=gcp_region,
    deletion_protection= False,
    ingress="INGRESS_TRAFFIC_ALL",
    launch_stage="BETA",
    template={
        "containers":[{
            "image": "ollama/ollama:latest",
            
            # # Environment variables for Ollama configuration
            # "envs": [
            #     {
            #         "name": "OLLAMA_MODELS",
            #         "value": "/root/.ollama/models"
            #     },
            #     {
            #         "name": "OLLAMA_HOST", 
            #         "value": "0.0.0.0:11434"
            #     },
            #     {
            #         "name": "OLLAMA_KEEP_ALIVE",
            #         "value": "24h"
            #     },
            #     {
            #         "name": "MODEL_NAME",
            #         "value": "gemma2:2b"
            #     }
            # ],
            
            # # Custom startup command to download model and start server
            # "command": ["/bin/bash"],
            # "args": ["-c", "ollama serve & sleep 10 && ollama pull $MODEL_NAME && wait"],
            
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
                "initial_delay_seconds": 0,  # Increased to allow model download
                "timeout_seconds": 1,
                "period_seconds": 1,
                "failure_threshold": 360,  # 60 minutes max for model download
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

ollama_binding = cloudrun.ServiceIamBinding("ollama-binding",
    project=gcp_project,
    location=gcp_region,
    name=ollama_cr_service,
    role="roles/run.invoker",
    members=["allUsers"],
    opts=pulumi.ResourceOptions(depends_on=[ollama_cr_service]),
)

ollama_url = ollama_cr_service.uri

# Open WebUI Cloud Run instance
openwebui_cr_service = cloudrun.Service("openwebui-service",
    name="openwebui-service",
    location=gcp_region,
    deletion_protection= False,
    ingress="INGRESS_TRAFFIC_ALL",
    launch_stage="BETA",
    template={
        "containers":[{
            "image": "us-central1-docker.pkg.dev/"+str(gcp_project)+"/openwebui/openwebui",
            "envs": [{
                "name":"OLLAMA_BASE_URL",
                "value":ollama_url,
            }
            ,{
                "name":"WEBUI_AUTH",
                "value":'false',  
            }],
            "resources": {
                "cpuIdle": False,
                "limits":{
                    "cpu": "8",
                    "memory": "16Gi",
                },
                "startup_cpu_boost": True,
            },
            "startup_probe": {
                "initial_delay_seconds": 0,
                "timeout_seconds": 1,
                "period_seconds": 1,
                "failure_threshold": 1800,
                "tcp_socket": {
                    "port": 8080,
                },
            },
        }],
        "scaling": {      
            "max_instance_count":3,
            "min_instance_count":1,
        },
    },
    traffics=[{
        "type": "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST",
        "percent": 100,
    }],
    opts=pulumi.ResourceOptions(depends_on=[ollama_binding, openwebui_docker_image]),
)

openwebui_binding = cloudrun.ServiceIamBinding("openwebui-binding",
    project=gcp_project,
    location=gcp_region,
    name=openwebui_cr_service,
    role="roles/run.invoker",
    members=["allUsers"],
    opts=pulumi.ResourceOptions(depends_on=[openwebui_cr_service]),
)

install_model_command = ollama_cr_service.uri.apply(lambda ollama_service_uri:  f"curl {ollama_service_uri}/api/pull -d '{{\"model\":\"tinyllama:1.1b\"}}'")
install_model = local.Command("install_model",
    create=install_model_command,
)


pulumi.export("ollama_url", ollama_cr_service.uri)
pulumi.export("open_webui_url", openwebui_cr_service.uri)