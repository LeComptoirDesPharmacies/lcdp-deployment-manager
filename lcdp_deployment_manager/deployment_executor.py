import time


# Démarre tous les services d'un environement et attend qu'il soit entièrement up
def start_environment_and_wait_for_health(environment):
    environment.start_up_services()
    environment.wait_for_services_health()


# Passe d'un environnement à l'autre en modifiant les targets groups des règles du listener
def do_balancing(deployment_manager, from_environment, to_environment):
    print("Do balancing from environment {} to environment {}".format(from_environment.color, to_environment.color))
    deployment_manager.update_rule_target_group(
        expected_rule_type=from_environment.target_group_type,
        expected_rule_color=from_environment.color,
        new_target_group_arn=to_environment.target_group_arn
    )


def deploy_services_of_repositories_name(environment, repositories_name):
    print("Deploy services for repositories {}".format(repositories_name))

    # add color to the repository name to avoid starting a service of another color and lower case
    repositories_name_with_color = [(repo + '-' + environment.color).lower() for repo in repositories_name]

    services_to_start = []

    for service in environment.ecs_services:
        # le nom du service est de la forme 'lcdp-<service_name>-<color>
        # Extraire le nom du service
        service_name = service['serviceName'].lower()

        # Vérifier si le nom du service contient le nom d'un des repositories
        if any(repo_name in service_name for repo_name in repositories_name_with_color):
            services_to_start.append(service)

    if services_to_start:
        for service in services_to_start:
            print("Start service {}".format(service['serviceName']))
            service.start()

        # Wait for all service receive startup
        time.sleep(10)
        environment.wait_for_services_health()
