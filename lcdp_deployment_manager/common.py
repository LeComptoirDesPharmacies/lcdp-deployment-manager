from .constant import *


# Récupère les tags pour une ressource donnée
def get_tags_from_resource(resource, client):
    tag_descriptions_result = client.describe_tags(ResourceArns=[resource])
    for tag_desc in tag_descriptions_result['TagDescriptions']:
        return tag_desc['Tags']


# Récupère les attribues type et color dans une liste de tag
def get_type_and_color_for_resource(arn, client):
    tags = get_tags_from_resource(arn, client)
    return get_type_tag(tags), get_color_tag(tags)


# Récupère l'attribue type dans une liste de tag
def get_type_tag(tags):
    for tag in tags:
        if tag['Key'].upper() == TARGET_GROUP_TYPE_TAG_NAME.upper():
            return tag['Value']

# Récupère l'attribue color dans une liste de tag
def get_color_tag(tags):
    for tag in tags:
        if tag['Key'].upper() == TARGET_GROUP_COLOR_TAG_NAME.upper():
            return tag['Value']
