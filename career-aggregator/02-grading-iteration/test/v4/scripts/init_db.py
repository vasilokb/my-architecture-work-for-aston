import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.database import engine
from models import Base

Base.metadata.create_all(engine)
print("Tables created.")
