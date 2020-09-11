import boto3

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


# Récupère les tags des services colorés
def get_services_max_capacities_for_colored_resources(colored_services):
    colored_services_max_capacities = []
    for service_arn in colored_services:
        tag_description_result = ecs_client.list_tags_for_resource(resourceArn=service_arn)
        tags = tag_description_result.get('tags')
        for i in range(len(tags)):
            if tags[i].get("key") == "max_capacity":
                colored_services_max_capacities.append(int(tags[i].get("value")))
    return colored_services_max_capacities


# Récupère les resources_ids des services colorés
def get_services_resource_ids_for_colored_resources(colored_services):
    colored_services_resource_ids = []
    for service_arn in colored_services:
        colored_services_resource_ids.append(str(service_arn).split(':')[5])
    return colored_services_resource_ids
