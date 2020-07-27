import boto3
from . import constant as constant

ecr_client = boto3.client('ecr')


# Récupère le nom des ECR qui sont des services
# Un service commence par 'lcdp-'
def get_service_repositories_name():
    repositories = ecr_client.describe_repositories()
    service_repositories = []
    for repository in repositories['repositories']:
        if repository['repositoryName'].startswith(constant.ECR_SERVICE_PREFIX):
            service_repositories.append(repository['repositoryName'])
    return service_repositories


# Récupère une image possédant un tag précis
def get_repository_image_for_tag(repository_name, tag):
    images = ecr_client.list_images(
        repositoryName=repository_name,
        # TODO: Review if one day we got more than 1000 ecr images !
        maxResults=1000
    )
    for image in images['imageIds']:
        if 'imageTag' in image and image['imageTag'] == tag:
            return image


# Récupère le manifest d'une image
def get_image_manifest(repository_name, image):
    detailed_image = ecr_client.batch_get_image(
        repositoryName=repository_name,
        imageIds=[image]
    )
    return detailed_image['images'][0]['imageManifest']