from rest_framework.throttling import UserRateThrottle

class AdminActionThrottle(UserRateThrottle):
    """
    Throttle for admin actions to prevent abuse
    """
    rate = '400/minute'

class SocietyActionThrottle(UserRateThrottle):
    """
    Throttle for society-related actions
    """
    rate = '500/minute'

class RegistrationThrottle(UserRateThrottle):
    """
    Throttle for registration attempts
    """
    rate = '5/hour'
