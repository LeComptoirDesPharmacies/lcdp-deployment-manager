import time
from functools import reduce

from . import common as common
from . import constant as constant
from . import manage_alb as alb_manager
from . import manage_cloudwatch as cloudwatch_manager
from . import manage_ecr as ecr_manager


###
#   Classe permettant de gérer le déployement
###
class DeploymentManager:
    alb = None
    http_listener = None
    default_target_group = None
    rules = []
    repositories = []
    prod_color = None
    blue_environment = {}
    green_environment = {}

    # Clients
    elbv2_client = None

    def __init__(self, elbv2_client, alb, http_listener, rules, repositories,
                 prod_color, current_target_group_type,
                 blue_environment,
                 green_environment):
        self.elbv2_client = elbv2_client
        self.alb = alb
        self.http_listener = http_listener
        self.rules = rules
        self.repositories = repositories
        self.prod_color = prod_color
        self.current_target_group_type = current_target_group_type
        self.blue_environment = blue_environment
        self.green_environment = green_environment

    # Constuit une action pour le listener
    def __build_forward_actions(self, target_group_arn):
        return {
            "Type": "forward",
            "TargetGroupArn": target_group_arn,
            "Order": 1
        }

    def get_type(self, rule):
        type_holder = self.http_listener['ListenerArn'] if rule['IsDefault'] else rule['RuleArn']
        target_type = alb_manager.get_type_from_resource(type_holder)

        if target_type:
            return target_type
        else:
            return None

    def get_production_environment(self):
        if self.prod_color == constant.BLUE:
            return self.blue_environment
        elif self.prod_color == constant.GREEN:
            return self.green_environment
        raise Exception('Unable to get prod environment...')

    def get_pre_production_environment(self):
        if self.prod_color == constant.GREEN:
            return self.blue_environment
        elif self.prod_color == constant.BLUE:
            return self.green_environment
        raise Exception('Unable to get pre prod environment...')

    def create_rule(self, conditions, actions, priority, tags):
        self.elbv2_client.create_rule(
            ListenerArn=self.http_listener['ListenerArn'],
            Conditions=conditions,
            Actions=actions,
            Priority=priority,
            Tags=tags
        )

    def update_rule_target_group(self, expected_rule_type, expected_rule_color, new_target_group_arn):
        targeted_rules = self.get_rules_with_type_and_color(expected_rule_type, expected_rule_color)
        for targeted_rule in targeted_rules:
            self.__modify_rule_target_group(targeted_rule, new_target_group_arn)

    def update_rules_target_group(self, rules, new_target_group_arn):
        for rule in rules:
            self.__modify_rule_target_group(rule, new_target_group_arn)

    def __modify_rule_target_group(self, rule, target_group_arn):
        if rule['IsDefault']:
            return self.elbv2_client.modify_listener(
                ListenerArn=self.http_listener['ListenerArn'],
                DefaultActions=[self.__build_forward_actions(target_group_arn)]
            )
        else:
            return self.elbv2_client.modify_rule(
                RuleArn=rule['RuleArn'],
                Actions=[self.__build_forward_actions(target_group_arn)]
            )

    def get_rules_with_type_and_color(self, expected_type, expected_color):
        return [r for r in self.rules if self.__assert_rule(r, expected_type, expected_color)]

    def get_forward_rules(self):
        return self.get_typed_rules('forward')

    def get_fixed_response_rules(self):
        return self.get_typed_rules('fixed-response')

    def get_typed_rules(self, rule_type):
        typed_rules = []
        for rule in self.rules:
            for action in rule['Actions']:
                if action['Type'] == rule_type:
                    typed_rules.append(rule)
        return typed_rules

    def __assert_rule(self, rule, expected_type, expected_color):
        expected = (expected_type, expected_color)

        for action in rule['Actions']:
            if action['Type'] == 'forward':
                tap_tpl = common.get_type_and_color_for_resource(action['TargetGroupArn'], self.elbv2_client)
                if tap_tpl == expected:
                    return True

        return False

    def __assert_target_group(self, target_group, expected_type, expected_color):

        return target_group['Type'].upper() == expected_type.upper() \
            and target_group['Color'].upper() == expected_color.upper()

    # Ajout d'un tag a tous les repository d'un environement
    def add_tag_to_repositories(self, tag):
        for r in self.repositories:
            r.add_tag(tag)

    def set_color_to_list_repositories_name(self, repositories_name):
        print('Add color {} to mismatched repositories: {}'.format(self.prod_color, repositories_name))

        for r in self.repositories:
            if r.name in repositories_name:
                r.add_tag(self.prod_color)

    # Cherche les repositories qui ont un tag mais pour lesquels la couleur active n'est pas appliquée et applique la
    def find_mismatched_repositories_name_between_tag_and_active_color(self, tag):
        return ecr_manager.find_mismatched_repositories_between_tag_and_color(
            ecr_manager.get_service_repositories_name(),
            tag,
            self.prod_color)

    def get_lowest_available_priority_alb_rule(self):
        used_priorities = set()

        for rule in self.rules:
            if not rule['IsDefault']:
                used_priorities.add(int(rule['Priority']))

        # Trouver la plus petite priorité disponible
        for priority in range(1, 50001):  # Les priorités ALB vont de 1 à 50000
            if priority not in used_priorities:
                return priority

        # Si toutes les priorités sont utilisées (cas très improbable)
        return None


###
#   Classe contenant les informations utiles d'un environment blue ou green
###
class Environment:
    ecs_client = None
    workspace = None
    color = None
    target_group_type = None
    cluster_name = None
    ecs_services = []
    target_group_arn = None

    def __init__(self, ecs_client, workspace, color, target_group_type, cluster_name, ecs_services,
                 target_group_arn):
        self.ecs_client = ecs_client
        self.workspace = workspace
        self.color = color
        self.target_group_type = target_group_type
        self.cluster_name = cluster_name
        self.ecs_services = ecs_services
        self.target_group_arn = target_group_arn

    # Démarre tous les services
    def start_up_services(self, desired_count=None):
        for s in self.ecs_services:
            s.start(desired_count)
        # Wait for all service receive startup
        time.sleep(10)

    # Eteint tous les services
    def shutdown_services(self):
        for s in self.ecs_services:
            s.shutdown()
        # Wait for all service receive shutdown
        time.sleep(10)

    def get_unhealthy_services(self):
        return list(filter(lambda s: not s.is_service_healthy(), self.ecs_services))

    # Vérifie que tous les services sont healthy
    def all_services_are_healthy(self):
        return all(s.is_service_healthy() for s in self.ecs_services)

    # Attend que tous les services soit healthy
    def wait_for_services_health(self):
        retry = 1
        print("Waiting {} seconds before first try".format(constant.HEALTHCHECK_SLEEPING_TIME))
        time.sleep(constant.HEALTHCHECK_SLEEPING_TIME)
        while not self.all_services_are_healthy() and constant.HEALTHCHECK_RETRY_LIMIT >= retry:
            print("Retry number {} all services hasnt healthy sleeping {} seconds before retry"
                  .format(retry, constant.HEALTHCHECK_SLEEPING_TIME))
            retry = retry + 1
            time.sleep(constant.HEALTHCHECK_SLEEPING_TIME)
        if constant.HEALTHCHECK_RETRY_LIMIT < retry:
            print("Tried {} but retry limit has been reach before all services been healthy".format(retry))
            # Raise exception
            unhealthy_sve = reduce(lambda a, b: a.service_arn + ',' + b.service_arn, self.get_unhealthy_services())
            raise Exception("Unable to deploy, services still unhealthy. Unhealthy Services : {}".format(unhealthy_sve))
        else:
            print("Tried {} and all service are now healthy".format(retry))

    def get_active_and_pending_smuggler_jobs(self):
        return cloudwatch_manager.get_smuggler_metrics(self.workspace, self.color)


###
# Classe qui map un ECS aws
###
class EcsService:
    cluster_name = None
    service_arn = None
    task = []
    ecs_client = None
    service_healthy = False
    application_autoscaling_client = None
    max_capacity = None
    resource_id = None

    def __init__(self, ecs_client, application_autoscaling_client, cluster_name, service_arn, max_capacity,
                 resource_id):
        self.ecs_client = ecs_client
        self.cluster_name = cluster_name
        self.service_arn = service_arn
        self.application_autoscaling_client = application_autoscaling_client
        self.max_capacity = max_capacity
        self.resource_id = resource_id

    def __get_task(self):
        tasks = self.ecs_client.list_tasks(
            cluster=self.cluster_name,
            serviceName=self.service_arn,
            # TODO: Review if one day we got more than 100 ecs tasks !
            maxResults=100
        )
        return tasks['taskArns']

    def __set_register_scalable_target(self, min_capacity):
        try:
            return self.application_autoscaling_client.register_scalable_target(
                ServiceNamespace=constant.ECS_SERVICE_NAMESPACE,
                ResourceId=self.resource_id,
                ScalableDimension=constant.DEFAULT_SCALABLE_DIMENSION,
                MinCapacity=min_capacity,
                MaxCapacity=self.max_capacity
            )
        except Exception as err:
            print("An exception was raise during creation of new scalable target. Error : {}".format(err))

    def start(self, desired_count=None):
        if not desired_count:
            desired_count = constant.DEFAULT_DESIRED_COUNT
        print('Start service {} with {} instances'.format(self.service_arn, desired_count))
        self.ecs_client.update_service(
            cluster=self.cluster_name,
            service=self.service_arn,
            desiredCount=desired_count,
            forceNewDeployment=True
        )
        response = self.__set_register_scalable_target(desired_count)
        print("Started service: '{}', Updated Capacities => MaxCapacity: {} / MinCapacity: {}, response: {}"
              .format(self.service_arn, self.max_capacity, desired_count, response))

    def shutdown(self):
        print('Shutdown service {}'.format(self.service_arn))
        self.ecs_client.update_service(
            cluster=self.cluster_name,
            service=self.service_arn,
            desiredCount=0
        )
        response = self.__set_register_scalable_target(0)
        print("Stopped service: '{}', Updated Capacities => MaxCapacity: {} / MinCapacity: 0, response: {}"
              .format(self.service_arn, self.max_capacity, response))

    def is_service_healthy(self):
        if not self.service_healthy:
            self.service_healthy = self.__check_service_health()
        return self.service_healthy

    def __check_service_health(self):
        tasks = self.__get_task()
        if not tasks:
            return False
        detailed_task = self.ecs_client.describe_tasks(
            cluster=self.cluster_name,
            tasks=tasks
        )
        nb_healthy_task = len(list(filter(lambda x: x['healthStatus'] == 'HEALTHY', detailed_task['tasks'])))
        is_healthy = nb_healthy_task >= constant.DEFAULT_DESIRED_COUNT
        if is_healthy:
            print('{} has reach the healthy state'.format(self.service_arn))
        else:
            print('{} is not healthy, only has {} task(s) healthy and {} healthy tasks are required to pass'
                  .format(self.service_arn, nb_healthy_task, constant.DEFAULT_DESIRED_COUNT))
        return is_healthy

    def __str__(self):
        return self.service_arn


###
# Classe qui map un ECR aws
###
class Repository:
    name = None
    image = None
    manifest = None
    ecr_client = None

    def __init__(self, ecr_client, name, image, manifest):
        self.ecr_client = ecr_client
        self.name = name
        self.image = image
        self.manifest = manifest

    def add_tag(self, tag):
        try:
            print('Adding tag {} to image {} in repository {}'.format(tag, self.image, self.name))
            new_image = self.ecr_client.put_image(
                repositoryName=self.name,
                imageManifest=self.manifest,
                imageTag=tag
            )
            return new_image
        except self.ecr_client.exceptions.ImageAlreadyExistsException:
            print('Image {} in repository {} already exist with tag {}'.format(self.image, self.name, tag))
