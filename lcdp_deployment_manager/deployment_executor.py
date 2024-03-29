

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
