import boto3
from . import constant as constant

ecs_client = boto3.client('ecs')

# Récupère les arn de tous les services ecs d'un cluster pour une couleur donnée
def get_services_arn_for_color(color, cluster_name):
    colored_services = []
    services = ecs_client.list_services(
        cluster=cluster_name,
        # TODO: Review if one day we got more than 100 ecs services !
        maxResults=100
    )
    for service_arn in services['serviceArns']:
        if color in service_arn.upper():
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