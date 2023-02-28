from apifairy.decorators import other_responses
from flask import Blueprint, abort
from apifairy import authenticate, body, response

from api import db
from api.models import User, Shop, Program, Purchase, Redemption
from api.schemas import UserSchema, EmptySchema, ShopSchema, ProgramSchema, PurchaseSchema, RedemptionSchema
from api.auth import token_auth
from api.decorators import paginated_response

shops = Blueprint('shops', __name__)
user_schema = UserSchema()
users_schema = UserSchema(many=True)
shop_schema = ShopSchema()
shops_schema = ShopSchema(many=True)
program_schema = ProgramSchema()
programs_schema = ProgramSchema(many=True)
purchase_schema = PurchaseSchema()
purchases_schema = PurchaseSchema(many=True)
redemption_schema = RedemptionSchema()
redemptions_schema = RedemptionSchema(many=True)


@shops.route('/shops', methods=['POST'])
@body(shop_schema)
@response(shop_schema, 201)
def new(args):
    """Register a new shop"""
    shop = Shop(**args)
    db.session.add(shop)
    db.session.commit()
    return shop


@shops.route('/shops', methods=['GET'])
@paginated_response(shops_schema)
def all():
    """Retrieve all shops"""
    return Shop.select()


@shops.route('/shops/<int:id>', methods=['GET'])
@response(shop_schema)
@other_responses({404: 'Shop not found'})
def get(id):
    """Retrieve a shop by id"""
    return db.session.get(Shop, id) or abort(404)


@shops.route('/shops/<name>', methods=['GET'])
@response(shop_schema)
@other_responses({404: 'Shop not found'})
def get_by_name(name):
    """Retrieve a shop by name"""
    return db.session.scalar(Shop.select().filter_by(name=name)) or \
        abort(404)


@shops.route('/shop/subscriptions/<int:id>', methods=['GET'])
@paginated_response(users_schema, order_by=Program.name)
def shop_subscriptions(id):
    """Retrieve the users subscribed to a program from the shop"""
    shop = db.session.get(Shop, id)
    return shop.subscribers_select()


# @shops.route('/shop/subscriptions/<int:shop_id>/<int:user_id>', methods=['POST'])
# @authenticate(token_auth)
# @paginated_response(users_schema, order_by=Program.name)
# def shop_subscriptions(shop_id, user_id):
#     """Subscribe a user to a program from the shop"""
#     shop = db.session.get(Shop, shop_id)
#     user = db.session.get(User, user_id)
#     current_user = token_auth.current_user()
#     if shop.is_manager(current_user):
#
#
#     return shop.subscribers_select()


@shops.route('/shop/<int:id>/managers', methods=['GET'])
@paginated_response(users_schema, order_by=Shop.name)
def shop_managers(id):
    """Retrieve the users who manage the shop"""
    shop = db.session.get(Shop, id)
    return shop.managers_select()


@shops.route('/shop/<int:id>/employees', methods=['GET'])
@paginated_response(users_schema, order_by=Shop.name)
def shop_employees(id):
    """Retrieve the users employed by the shop"""
    shop = db.session.get(Shop, id)
    return shop.staffs_select()


@shops.route('/shop/<int:id>/programs', methods=['GET'])
@paginated_response(programs_schema, order_by=Program.name)
def shop_programs(id):
    """Retrieve the programs of the shop"""
    shop = db.session.get(Shop, id)
    return shop.programs_select()


@shops.route('/shop/<int:id>/purchases', methods=['GET'])
@paginated_response(purchases_schema, order_by=Purchase.date_purchased)
def shop_purchases(id):
    """Retrieve the purchases fromm the shop"""
    shop = db.session.get(Shop, id)
    return shop.purchases


@shops.route('/shop/<int:id>/redemptions', methods=['GET'])
@paginated_response(redemptions_schema, order_by=Redemption.date_redeemed)
def shop_redemptions(id):
    """Retrieve the redemptions from the shop"""
    shop = db.session.get(Shop, id)
    return shop.redemptions

