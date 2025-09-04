import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "evalynemarch22")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://test:fEdVuETIqrHr1fCB@chatroom.5vtda.mongodb.net/GBCosmetics?retryWrites=true&w=majority&appName=GBCosmetics")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "geniusbabycosmetics")
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "evalynemwende20")
    PER_PAGE = int(os.getenv("PER_PAGE", "12"))
    
