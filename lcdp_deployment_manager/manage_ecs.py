import boto3

from . import constant as constant
from .deployment_manager \
    import EcsService

ecs_client = boto3.client('ecs')
application_autoscaling_client = boto3.client('application-autoscaling')


def get_services_from_cluster(cluster_name, max_results=100):
    return ecs_client.list_services(
        cluster=cluster_name,
        maxResults=max_results
    )


def get_services_arn_from_query(q, cluster_name):
    founded_services = []
    services = get_services_from_cluster(cluster_name)
    for service_arn in services['serviceArns']:
        if q.upper() in service_arn.upper():
            founded_services.append(service_arn)
    return founded_services


# Récupère les arn de tous les services ecs d'un cluster pour une couleur donnée
def get_services_arn_for_color(color, cluster_name):
    colored_services = []
    services = get_services_from_cluster(cluster_name)
    for service_arn in services['serviceArns']:
        if color.upper() in service_arn.upper():
            colored_services.append(service_arn)
    return colored_services


def get_service_max_capacity_from_service_arn(service_arn):
    tag_description_result = ecs_client.list_tags_for_resource(resourceArn=service_arn)
    tags = tag_description_result.get('tags')
    max_capacity_value = None
    for i in range(len(tags)):
        if tags[i].get("key") == "MaxCapacity":
            max_capacity_value = int(tags[i].get("value"))
            break

    return max_capacity_value or constant.DEFAULT_MAX_CAPACITY


def get_service_resource_id_from_service_arn(service_arn):
    return str(service_arn).split(':')[5]


# récupère le nom du repository de l'image des services
def get_map_of_repo_name_service(color, cluster_name):
    repo_name_service_map = {}
    services = get_services_from_cluster(cluster_name)
    for service_arn in services['serviceArns']:
        if color.upper() in service_arn.upper():
            service = ecs_client.describe_services(
                cluster=cluster_name,
                services=[service_arn]
            )
            taskDefinition = ecs_client.describe_task_definition(
                taskDefinition=service['services'][0]['taskDefinition']
            )
            containerDefinitions = taskDefinition['taskDefinition']['containerDefinitions']

            if containerDefinitions:
                image = containerDefinitions[0]['image']

                # Extrait le nom du repository de l'image
                # (ex: 721041490777.dkr.ecr.us-east-1.amazonaws.com/lcdp-api-gateway:BLUE)
                repository_name = image.split('/')[-1].split(':')[0]

                ecsService = EcsService(ecs_client=ecs_client,
                                        application_autoscaling_client=application_autoscaling_client,
                                        cluster_name=cluster_name,
                                        service_arn=service_arn,
                                        max_capacity=get_service_max_capacity_from_service_arn(service_arn),
                                        resource_id=get_service_resource_id_from_service_arn(service_arn))

                repo_name_service_map[repository_name] = ecsService

    return repo_name_service_map
