import boto3
import logging
from . import common as common
from . import constant as constant

# Client
elbv2_client = boto3.client('elbv2')


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
    return __get_color_from_resource(current_target_group_arn).upper()


def get_production_type(listener):
    """
    Récupère le type actuellement en production
    :param listener:    listener actuel
    :type listener:     dict
    :return:            default/maintenance
    :rtype:             str
    """
    current_target_group_arn = __get_default_forward_target_group_arn_from_listener(listener)
    return __get_type_from_resource(current_target_group_arn).upper()


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


def __get_tag_value_from_resource(resource_arn, tag_name):
    """
    Récupère la couleur d'une ressource donnée
    :param resource_arn:    Ressource AWS arn
    :type resource_arn:     str
    :return:                tag value
    :rtype:                 str
    """
    tag_desc = elbv2_client.describe_tags(
        ResourceArns=[resource_arn]
    )
    tags = tag_desc['TagDescriptions'][0]['Tags']
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


def __get_type_from_resource(resource_arn):
    """
    Récupère la couleur d'une ressource donnée
    :param resource_arn:    Ressource AWS arn
    :type resource_arn:     str
    :return:                default/maintenance
    :rtype:                 str
    """
    return __get_tag_value_from_resource(resource_arn, constant.TARGET_GROUP_TYPE_TAG_NAME)


# ~~~~~~~~~~~~~~~~ Rules ~~~~~~~~~~~~~~~~


# Récupère les règles qui n'ont pas une couleur dans l'url de redirection
# ex : blue.beta.verde -> NON ; beta.verde -> OUI
def get_uncolored_rules(listener):
    rules_desc = elbv2_client.describe_rules(
        ListenerArn=listener['ListenerArn']
    )
    uncolored_rules = []
    for rule in rules_desc['Rules']:
        for condition in rule['Conditions']:
            host = condition.get('HostHeaderConfig', None)
            if host:
                if all(__is_uncolored_host_header_value(v) for v in host['Values']):
                    uncolored_rules.append(rule)
    return uncolored_rules


def __is_uncolored_host_header_value(value):
    return constant.BLUE not in value.upper() and constant.GREEN not in value.upper()


# ~~~~~~~~~~~~~~~~ TARGET GROUP ~~~~~~~~~~~~~~~~

def get_target_group_with_type_and_color(target_groups, color, tg_type):
    """
    Récupère un target group ayant un type et une couleur précise
    :param target_groups: Liste des targets groups
    :type target_groups:  Target group list
    :param color:   Couleur recherché
    :type color:    str
    :param tg_type: Type recherché
    :type tg_type:  str
    :return:        Target group trouvé
    :rtype:         dict
    """
    expected = (tg_type.upper(), color.upper())

    for tg in target_groups:
        if expected == (tg['Type'].upper(), tg['Color'].upper()):
            return tg
    raise Exception("No target group found with type {} and color {}".format(tg_type, color))


def get_default_and_maintenance_target_groups_by_environment(environment):
    """
    Gets target groups of type 'default' or 'maintenance'
    :param environment:
    :param type: str
    :type type: str
    :param color:
    :type color: str
    :return: Target group or empty list if not found
    :rtype: str
    """
    if not environment:
        return []
    return __get_target_groups_with_types_and_environment(environment, [constant.TARGET_GROUP_DEFAULT_TYPE,
                                                                        constant.TARGET_GROUP_MAINTENANCE_TYPE])


def __get_target_groups_with_types_and_environment(environment, types):
    """
    Gets target group from type and color
    :param environment:
    :type : str
    :param types:
    :type types: list of str
    :return: Target groups or empty list if not found
    :rtype: list of target groups
    """
    target_groups_with_tags = __get_target_groups_with_tags(__get_all_target_groups_arns())
    matching_target_group_arns = []
    matching_target_group_map_with_type_and_color = {}
    environment_tag = {'Key': 'Environment', 'Value': environment}

    for target_group_with_tags in target_groups_with_tags:
        tags = target_group_with_tags['Tags']
        if len(tags) > 0:
            if environment_tag in tags:
                target_group_type = None
                target_group_color = None
                for tag in tags:
                    if tag['Key'] == 'Type':
                        target_group_type = tag['Value']
                    if tag['Key'] == 'Color':
                        target_group_color = tag['Value']
                if target_group_type and target_group_type.upper() in types:
                    matching_target_group_arns.append(target_group_with_tags['ResourceArn'])
                    matching_target_group_map_with_type_and_color.update(
                        {target_group_with_tags['ResourceArn']: {
                            'Type': target_group_type,
                            'Color': target_group_color
                        }})

    if len(matching_target_group_arns) > 0:
        matching_target_groups = __get_all_target_groups_by_arns(matching_target_group_arns)
        for matching_target_group in matching_target_groups:
            matching_target_group.update(
                matching_target_group_map_with_type_and_color[matching_target_group['TargetGroupArn']])
    else:
        matching_target_groups = []

    return matching_target_groups


def __get_target_groups_with_tags(target_groups_arns):
    target_groups_with_tags = []
    target_groups_number = len(target_groups_arns)
    i = 0
    while i < target_groups_number:
        target_groups_with_tags \
            .extend(elbv2_client.describe_tags(ResourceArns=target_groups_arns[i:i + 20])['TagDescriptions'])
        i += 20
    return target_groups_with_tags


def __get_all_target_groups_arns():
    """
    Gets target groups arns
    :return: Target groups arns or empty list if not found
    :rtype: list of str
    """
    target_groups = __get_all_target_groups()
    return [target_group['TargetGroupArn'] for target_group in target_groups]


def __get_all_target_groups():
    """
    Gets target groups
    :return: Target groups or empty list if not found
    :rtype: list or target groups
    """
    return elbv2_client.describe_target_groups()['TargetGroups']


def __get_all_target_groups_by_arns(arns):
    """
    Gets target groups
    :param arns:
    :param arns: list of str
    :return: Target groups or empty list if not found
    :rtype: list or target groups
    """
    return elbv2_client.describe_target_groups(TargetGroupArns=arns)['TargetGroups']
