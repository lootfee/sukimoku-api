from apifairy.decorators import other_responses
from flask import Blueprint, abort
from apifairy import authenticate, body, response

from api import db
from api.models import User, Shop, Program, Purchase, Redemption
from api.schemas import UserSchema, UpdateUserSchema, EmptySchema, ShopSchema, ProgramSchema, PurchaseSchema, RedemptionSchema
from api.auth import token_auth
from api.decorators import paginated_response

users = Blueprint('users', __name__)
user_schema = UserSchema()
users_schema = UserSchema(many=True)
update_user_schema = UpdateUserSchema(partial=True)
# shop_schema = ShopSchema()
shops_schema = ShopSchema(many=True)
# program_schema = ProgramSchema()
programs_schema = ProgramSchema(many=True)
# purchase_schema = PurchaseSchema()
purchases_schema = PurchaseSchema(many=True)
# redemption_schema = RedemptionSchema()
redemptions_schema = RedemptionSchema(many=True)


@users.route('/users', methods=['POST'])
@body(user_schema)
@response(user_schema, 201)
def new(args):
    """Register a new user"""
    user = User(**args)
    db.session.add(user)
    db.session.commit()
    return user


@users.route('/users', methods=['GET'])
@authenticate(token_auth)
@paginated_response(users_schema)
def all():
    """Retrieve all users"""
    return User.select()


@users.route('/users/<int:id>', methods=['GET'])
@authenticate(token_auth)
@response(user_schema)
@other_responses({404: 'User not found'})
def get(id):
    """Retrieve a user by id"""
    return db.session.get(User, id) or abort(404)


@users.route('/users/<username>', methods=['GET'])
@authenticate(token_auth)
@response(user_schema)
@other_responses({404: 'User not found'})
def get_by_username(username):
    """Retrieve a user by username"""
    return db.session.scalar(User.select().filter_by(username=username)) or \
        abort(404)


@users.route('/me', methods=['GET'])
@authenticate(token_auth)
@response(user_schema)
def me():
    """Retrieve the authenticated user"""
    return token_auth.current_user()


@users.route('/me', methods=['PUT'])
@authenticate(token_auth)
@body(update_user_schema)
@response(user_schema)
def put(data):
    """Edit user information"""
    user = token_auth.current_user()
    if 'password' in data and ('old_password' not in data or
                               not user.verify_password(data['old_password'])):
        abort(400)
    user.update(data)
    db.session.commit()
    return user


@users.route('/me/shops', methods=['GET'])
@authenticate(token_auth)
@paginated_response(shops_schema, order_by=Shop.name)
def my_shops():
    """Retrieve the shops the logged in user is managing"""
    user = token_auth.current_user()
    return user.shops_select()


@users.route('/me/subscriptions', methods=['GET'])
@authenticate(token_auth)
@paginated_response(programs_schema, order_by=Program.name)
def my_subscriptions():
    """Retrieve the programs the logged in user is subscribed"""
    user = token_auth.current_user()
    return user.subscriptions_select()


@users.route('/me/employers', methods=['GET'])
@authenticate(token_auth)
@paginated_response(shops_schema, order_by=Shop.name)
def my_employers():
    """Retrieve the shops the logged in user is employed"""
    user = token_auth.current_user()
    return user.employers_select()


@users.route('/me/purchases', methods=['GET'])
@authenticate(token_auth)
@paginated_response(purchases_schema, order_by=Purchase.date_purchased)
def my_purchases():
    """Retrieve the purchases of the logged in user"""
    user = token_auth.current_user()
    return user.purchases


@users.route('/me/redemptions', methods=['GET'])
@authenticate(token_auth)
@paginated_response(redemptions_schema, order_by=Redemption.date_redeemed)
def my_redemptions():
    """Retrieve the redemptions of the logged in user"""
    user = token_auth.current_user()
    return user.redemptions


# @users.route('/me/followers', methods=['GET'])
# @authenticate(token_auth)
# @paginated_response(users_schema, order_by=User.username)
# def my_followers():
#     """Retrieve the followers of the logged in user"""
#     user = token_auth.current_user()
#     return user.followers_select()


@users.route('/me/subscribed/<int:program_id>', methods=['GET'])
@authenticate(token_auth)
@response(EmptySchema, status_code=204,
          description='User is subscribed.')
@other_responses({404: 'User is not subscribed'})
def is_subscribed(id):
    """Check if a user is subscribed to a program"""
    user = token_auth.current_user()
    followed_user = db.session.get(User, id) or abort(404)
    if not user.is_following(followed_user):
        abort(404)
    return {}


# @users.route('/me/following/<int:id>', methods=['POST'])
# @authenticate(token_auth)
# @response(EmptySchema, status_code=204,
#           description='User followed successfully.')
# @other_responses({404: 'User not found', 409: 'User already followed.'})
# def follow(id):
#     """Follow a user"""
#     user = token_auth.current_user()
#     followed_user = db.session.get(User, id) or abort(404)
#     if user.is_following(followed_user):
#         abort(409)
#     user.follow(followed_user)
#     db.session.commit()
#     return {}
#
#
# @users.route('/me/following/<int:id>', methods=['DELETE'])
# @authenticate(token_auth)
# @response(EmptySchema, status_code=204,
#           description='User unfollowed successfully.')
# @other_responses({404: 'User not found', 409: 'User is not followed.'})
# def unfollow(id):
#     """Unfollow a user"""
#     user = token_auth.current_user()
#     unfollowed_user = db.session.get(User, id) or abort(404)
#     if not user.is_following(unfollowed_user):
#         abort(409)
#     user.unfollow(unfollowed_user)
#     db.session.commit()
#     return {}
#
#
# @users.route('/users/<int:id>/following', methods=['GET'])
# @authenticate(token_auth)
# @paginated_response(users_schema, order_by=User.username)
# @other_responses({404: 'User not found'})
# def following(id):
#     """Retrieve the users this user is following"""
#     user = db.session.get(User, id) or abort(404)
#     return user.following_select()
#
#
# @users.route('/users/<int:id>/followers', methods=['GET'])
# @authenticate(token_auth)
# @paginated_response(users_schema, order_by=User.username)
# @other_responses({404: 'User not found'})
# def followers(id):
#     """Retrieve the followers of the user"""
#     user = db.session.get(User, id) or abort(404)
#     return user.followers_select()
