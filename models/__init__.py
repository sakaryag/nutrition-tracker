from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.food_entry import FoodEntry
from models.daily_target import DailyTarget
from models.saved_food import SavedFood
from models.user import User
from models.meal_template import MealTemplate
from models.meal_template_item import MealTemplateItem
from models.nutrition_plan import NutritionPlan
from models.plan_task import PlanTask
from models.user_plan_assignment import UserPlanAssignment
from models.plan_task_completion import PlanTaskCompletion
from models.daily_note import DailyNote
from models.water_log import WaterLog
from models.friend_connection import FriendConnection
from models.shared_entry import SharedEntry
from models.feed_visibility import FeedVisibility
from models.user_badge import UserBadge
from models.dietitian_access import DietitianAccess
from models.dietitian_visit import DietitianVisit
from models.program_day import ProgramDay
from models.meal_slot import MealSlot
from models.slot_item import SlotItem
from models.recipe import Recipe
from models.recipe_ingredient import RecipeIngredient
from models.food_exchange_category import FoodExchangeCategory
from models.exchange_category_member import ExchangeCategoryMember
from models.program_guideline import ProgramGuideline
from models.program_version import ProgramVersion
from models.slot_fulfillment import SlotFulfillment
from models.weekly_category_quota import WeeklyCategoryQuota
from models.program_image_upload import ProgramImageUpload
