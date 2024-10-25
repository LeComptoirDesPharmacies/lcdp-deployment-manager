# Constant.py

# Color
BLUE = 'blue'
GREEN = 'green'

# LISTENER
HTTPS_TUPLE = ('HTTPS', 443)
HTTP_TUPLE = ('HTTP', 80)

# Target group
TARGET_GROUP_COLOR_TAG_NAME = 'Color'
TARGET_GROUP_TYPE_TAG_NAME = 'Type'
# Default type means 'api gateway'
TARGET_GROUP_DEFAULT_TYPE = 'default'
TARGET_GROUP_MAINTENANCE_TYPE = 'maintenance'

# ECR
ECR_SERVICE_PREFIX = 'lcdp-'

# ECS
DEFAULT_DESIRED_COUNT = 2
DEFAULT_MAX_CAPACITY = 4
HEALTHCHECK_RETRY_LIMIT = 26
HEALTHCHECK_SLEEPING_TIME = 30
ECS_SERVICE_NAMESPACE = 'ecs'

# SES
FROM_MAIL = 'no-reply@lecomptoirdespharmacies.fr'
DEVELOPERS_MAIL = 'webmaster@lecomptoirdespharmacies.fr'
DEFAULT_CHARSET = 'UTF-8'

# ASG
DEFAULT_SCALABLE_DIMENSION = 'ecs:service:DesiredCount'
