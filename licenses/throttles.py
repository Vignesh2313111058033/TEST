from rest_framework.throttling import AnonRateThrottle


class ActivationRateThrottle(AnonRateThrottle):
    scope = "activation"


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"

