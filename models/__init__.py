from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.food_entry import FoodEntry
from models.daily_target import DailyTarget
from models.saved_food import SavedFood
from models.user import User
from models.meal_template import MealTemplate
from models.meal_template_item import MealTemplateItem
