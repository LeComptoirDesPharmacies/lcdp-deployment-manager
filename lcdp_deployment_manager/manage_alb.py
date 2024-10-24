import boto3
from . import constant as constant

# Client
elbv2_client = boto3.client('elbv2')
tagging_client = boto3.client('resourcegroupstaggingapi')


# ~~~~~~~~~~~~~~~~ ALB ~~~~~~~~~~~~~~~~

def get_alb_from_aws(alb_name):
    """
    Récupère l'application load balancer sur aws
    :param alb_name:    Nom du load balance
    :type alb_name:     str
    :return:            Load balancer trouvé
    :rtype:             dict
    """
    alb_desc = elbv2_client.describe_load_balancers(
        Names=[alb_name]
    )
    # WARNING: If we got multiple alb
    return alb_desc['LoadBalancers'][0]


# ~~~~~~~~~~~~~~~~ Listener ~~~~~~~~~~~~~~~~

def get_current_listener(alb_arn, ssl_enabled):
    alb_desc = elbv2_client.describe_listeners(
        LoadBalancerArn=alb_arn
    )
    return __get_listener(alb_desc, ssl_enabled)


def get_production_color(listener):
    """
    Récupère la couleur actuellement en production
    :param listener:    listener actuel
    :type listener:     dict
    :return:            BLUE/GREEN
    :rtype:             str
    """
    current_target_group_arn = __get_default_forward_target_group_arn_from_listener(listener)
    return __get_color_from_resource(current_target_group_arn)

def get_production_type(listener):
    """
    Récupère le type actuellement en production
    :param listener:    listener actuel
    :type listener:     dict
    :return:            default/maintenance
    :rtype:             str
    """
    current_target_group_arn = __get_default_forward_target_group_arn_from_listener(listener)
    return get_type_from_resource(current_target_group_arn)


def __get_listener(listeners, ssl_enabled):
    """
    Récupère le listener qui contient les règles de redirection vers les services
    :param listeners:   liste de listener disponible
    :type listeners:    dict
    :param ssl_enabled: indique si le ssl est activé ou non
    :type ssl_enabled:  bool
    :return:            listener correspondant au port et protocol donné
    :rtype:             dict
    """
    protocol_port = constant.HTTPS_TUPLE if ssl_enabled else constant.HTTP_TUPLE
    # Careful if we got multiple http listener
    for listener in listeners['Listeners']:
        if (listener['Protocol'], listener['Port']) == protocol_port:
            return listener


def __get_default_forward_target_group_arn_from_listener(listener):
    # Careful if we got multiple forward target group
    for action in listener['DefaultActions']:
        if action['Type'] == 'forward':
            return action['TargetGroupArn']


def __get_tags_from_resource(resource_arn):
    """
    Récupère les tags d'une ressource donnée
    :param resource_arn:    Ressource AWS arn
    :type resource_arn:     str
    :return:                tag value
    :rtype:                 str
    """
    tag_desc = elbv2_client.describe_tags(
        ResourceArns=[resource_arn]
    )
    tags = tag_desc['TagDescriptions'][0]['Tags']
    return tags

def __get_tag_value_from_resource(resource_arn, tag_name):
    tags = __get_tags_from_resource(resource_arn)
    for tag in tags:
        if tag['Key'] == tag_name:
            return tag['Value']


def __get_color_from_resource(resource_arn):
    """
    Récupère la couleur d'une ressource donnée
    :param resource_arn:    Ressource AWS arn
    :type resource_arn:     str
    :return:                BLUE/GREEN
    :rtype:                 str
    """
    return __get_tag_value_from_resource(resource_arn, constant.TARGET_GROUP_COLOR_TAG_NAME)


def get_type_from_resource(resource_arn):
    """
    Récupère le type d'une ressource donnée
    :param resource_arn:    Ressource AWS arn
    :type resource_arn:     str
    :return:                default/maintenance
    :rtype:                 str
    """
    return __get_tag_value_from_resource(resource_arn, constant.TARGET_GROUP_TYPE_TAG_NAME)


# ~~~~~~~~~~~~~~~~ Rules ~~~~~~~~~~~~~~~~


# Récupère les règles qui n'ont pas une couleur dans l'url
# ex : blue.beta.verde -> NON ; beta.verde -> OUI
def get_uncolored_rules(listener):
    rules_desc = elbv2_client.describe_rules(
        ListenerArn=listener['ListenerArn']
    )
    uncolored_rules = []
    for rule in rules_desc['Rules']:
        is_colored = False
        for condition in rule['Conditions']:
            host = condition.get('HostHeaderConfig', None)
            if host:
                is_colored = any(__is_colored_host_header_value(v) for v in host['Values'])

        if not is_colored:
          uncolored_rules.append(rule)
    return uncolored_rules


def __is_colored_host_header_value(value):
    return constant.BLUE in value or constant.GREEN in value


# ~~~~~~~~~~~~~~~~ TARGET GROUP ~~~~~~~~~~~~~~~~

def get_target_group_with_type_color_and_workspace(tg_type, color, workspace):
    """
    Récupère un target group ayant un type et une couleur précise
    :param tg_type: Type recherché
    :type tg_type:  str
    :param color:   Couleur recherché
    :type color:    str
    :param workspace: Workspace
    :type workspace:  str
    :return:        Target group trouvé
    :rtype:         dict
    """

    tag_filter = \
        [
            {
                'Key': 'Type',
                'Values': [
                    tg_type.lower(),
                ]
            },
            {
                'Key': 'Workspace',
                'Values': [
                    workspace.lower(),
                ]
            }
        ]

    if color:
        tag_filter.append({
            'Key': 'Color',
            'Values': [
                color.lower(),
            ]
        })

    response = tagging_client.get_resources(
        TagFilters=tag_filter,
        ResourceTypeFilters=[
            'elasticloadbalancing:targetgroup',
        ],
    )

    if len(response['ResourceTagMappingList']) != 1:
        raise Exception('Expected one target group with type {}, color {}, and workspace {}. But found {}'
                        .format(tg_type, color, workspace, str(len(response['ResourceTagMappingList']))))

    return response['ResourceTagMappingList'][0]['ResourceARN']
