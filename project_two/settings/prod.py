# In settings/prod.py
# Production settings for project_two.
# This file imports all settings from base.py and overrides specific values for production.
import os
EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY') #  From secret manager