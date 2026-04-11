import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-2024'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///college.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ============================================
    # TWILIO CREDENTIALS - YAHAN ADD KARO
    # ============================================
    TWILIO_ACCOUNT_SID = 'ACf38ee849bde7220520912321ef63b9f6'   
    TWILIO_AUTH_TOKEN = 'fde437e10e1ab7fa1600e10ae3193363'   
    TWILIO_PHONE_NUMBER = '+16624958018'                      
    # ============================================