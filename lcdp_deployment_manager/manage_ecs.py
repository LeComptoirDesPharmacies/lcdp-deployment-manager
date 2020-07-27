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
