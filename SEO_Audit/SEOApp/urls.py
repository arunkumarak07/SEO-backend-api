from django.urls import path
from .api import *

urlpatterns = [
    path('api/register/', UserRegisterAPI.as_view()),
    path('api/seo-audit/', SEOAuditAPI.as_view())
]