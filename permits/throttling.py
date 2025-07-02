from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

class SocietyManagerRateThrottle(UserRateThrottle):
    rate = '100000/day'  # 100 requests per day for society managers

class StaffRateThrottle(UserRateThrottle):
    rate = '2000000/day'  # 200 requests per day for staff members

class FarmerRateThrottle(UserRateThrottle):
    rate = '500000/day'   # 50 requests per day for regular farmers

class AnonRateThrottle(AnonRateThrottle):
    rate = '20000000/day'   # 20 requests per day for anonymous users
