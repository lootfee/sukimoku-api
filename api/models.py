from datetime import datetime, timedelta
from hashlib import md5
import secrets
from time import time

from flask import current_app, url_for
import jwt
import sqlalchemy as sqla
from sqlalchemy import orm as sqla_orm
from werkzeug.security import generate_password_hash, check_password_hash

from api.app import db


class Updateable:
    def update(self, data):
        for attr, value in data.items():
            setattr(self, attr, value)


class Token(db.Model):
    __tablename__ = 'tokens'

    id = sqla.Column(sqla.Integer, primary_key=True)
    access_token = sqla.Column(sqla.String(64), nullable=False, index=True)
    access_expiration = sqla.Column(sqla.DateTime, nullable=False)
    refresh_token = sqla.Column(sqla.String(64), nullable=False, index=True)
    refresh_expiration = sqla.Column(sqla.DateTime, nullable=False)
    user_id = sqla.Column(sqla.Integer, sqla.ForeignKey('users.id'),
                          index=True)

    user = sqla_orm.relationship('User', back_populates='tokens')

    def generate(self):
        self.access_token = secrets.token_urlsafe()
        self.access_expiration = datetime.utcnow() + \
            timedelta(minutes=current_app.config['ACCESS_TOKEN_MINUTES'])
        self.refresh_token = secrets.token_urlsafe()
        self.refresh_expiration = datetime.utcnow() + \
            timedelta(days=current_app.config['REFRESH_TOKEN_DAYS'])

    def expire(self):
        self.access_expiration = datetime.utcnow()
        self.refresh_expiration = datetime.utcnow()

    @staticmethod
    def clean():
        """Remove any tokens that have been expired for more than a day."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        db.session.execute(Token.delete().where(
            Token.refresh_expiration < yesterday))


program_subscriptions = sqla.Table(
    'program_subscriptions',
    db.Model.metadata,
    sqla.Column('subscriber_id', sqla.Integer, sqla.ForeignKey('users.id')),
    sqla.Column('program_id', sqla.Integer, sqla.ForeignKey('programs.id'))
)


shop_subscriptions = sqla.Table(
    'shop_subscriptions',
    db.Model.metadata,
    sqla.Column('subscriber_id', sqla.Integer, sqla.ForeignKey('users.id')),
    sqla.Column('shop_id', sqla.Integer, sqla.ForeignKey('shops.id'))
)


managers = sqla.Table(
    'managers',
    db.Model.metadata,
    sqla.Column('user_id', sqla.Integer, sqla.ForeignKey('users.id')),
    sqla.Column('shop_id', sqla.Integer, sqla.ForeignKey('shops.id'))
)


staffs = sqla.Table(
    'staffs',
    db.Model.metadata,
    sqla.Column('staff_id', sqla.Integer, sqla.ForeignKey('users.id')),
    sqla.Column('shop_id', sqla.Integer, sqla.ForeignKey('shops.id'))
)

class User(Updateable, db.Model):
    __tablename__ = 'users'

    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String(64), index=True, unique=True,
                           nullable=False)
    email = sqla.Column(sqla.String(120), index=True, unique=True,
                        nullable=False)
    password_hash = sqla.Column(sqla.String(128))
    first_seen = sqla.Column(sqla.DateTime, default=datetime.utcnow)
    last_seen = sqla.Column(sqla.DateTime, default=datetime.utcnow)

    tokens = sqla_orm.relationship('Token', back_populates='user',
                                   lazy='noload')
    purchases = sqla_orm.relationship('Purchase', foreign_keys='[Purchase.purchase_user_id]', back_populates='purchase_user')
    redemptions = sqla_orm.relationship('Redemption', foreign_keys='[Redemption.redemption_user_id]', back_populates='redemption_user')
    staff_purchases = sqla_orm.relationship('Purchase', foreign_keys='[Purchase.purchase_staff_id]', back_populates='purchase_staff')
    staff_redemptions = sqla_orm.relationship('Redemption', foreign_keys='[Redemption.redemption_staff_id]', back_populates='redemption_staff')

    program_subscriptions = sqla_orm.relationship(
        'Program', secondary=program_subscriptions,
        primaryjoin=(program_subscriptions.c.subscriber_id == id),
        secondaryjoin=(program_subscriptions.c.program_id == id),
        back_populates='subscribers', lazy='noload')

    shop_subscriptions = sqla_orm.relationship(
        'Shop', secondary=shop_subscriptions,
        primaryjoin=(shop_subscriptions.c.subscriber_id == id),
        secondaryjoin=(shop_subscriptions.c.shop_id == id),
        back_populates='subscribers', lazy='noload')

    shops = sqla_orm.relationship(
        'Shop', secondary=managers,
        primaryjoin=(managers.c.user_id == id),
        secondaryjoin=(managers.c.shop_id == id),
        back_populates='managers', lazy='noload')

    employers = sqla_orm.relationship(
        'Shop', secondary=staffs,
        primaryjoin=(staffs.c.staff_id == id),
        secondaryjoin=(staffs.c.shop_id == id),
        back_populates='staffs', lazy='noload')

    def shops_select(self): # shops the user manages
        return Shop.select().where(sqla_orm.with_parent(self, User.shops))

    def subscriptions_select(self): # shops where the user has subscriptions
        return User.select().where(sqla_orm.with_parent(self, User.subscriptions))

    def employers_select(self): # shops where the user is employed
        return User.select().where(sqla_orm.with_parent(self, User.employers))

    def __repr__(self):  # pragma: no cover
        return '<User {}>'.format(self.name)

    @property
    def url(self):
        return url_for('users.get', id=self.id)

    @property
    def avatar_url(self):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon'

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def ping(self):
        self.last_seen = datetime.utcnow()

    def generate_auth_token(self):
        token = Token(user=self)
        token.generate()
        return token

    @staticmethod
    def verify_access_token(access_token, refresh_token=None):
        token = db.session.scalar(Token.select().filter_by(
            access_token=access_token))
        if token:
            if token.access_expiration > datetime.utcnow():
                token.user.ping()
                db.session.commit()
                return token.user

    @staticmethod
    def verify_refresh_token(refresh_token, access_token):
        token = db.session.scalar(Token.select().filter_by(
            refresh_token=refresh_token, access_token=access_token))
        if token:
            if token.refresh_expiration > datetime.utcnow():
                return token

            # someone tried to refresh with an expired token
            # revoke all tokens from this user as a precaution
            token.user.revoke_all()
            db.session.commit()

    def revoke_all(self):
        db.session.execute(Token.delete().where(Token.user == self))

    def generate_reset_token(self):
        return jwt.encode(
            {
                'exp': time() + current_app.config['RESET_TOKEN_MINUTES'] * 60,
                'reset_email': self.email,
            },
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )

    @staticmethod
    def verify_reset_token(reset_token):
        try:
            data = jwt.decode(reset_token, current_app.config['SECRET_KEY'],
                              algorithms=['HS256'])
        except jwt.PyJWTError:
            return
        return db.session.scalar(User.select().filter_by(
            email=data['reset_email']))

    def subscribe(self, program):
        if not self.is_subscribed(program):
            db.session.execute(program_subscriptions.insert().values(
                subscriber_id=self.id, program_id=program.id))

    def unsubscribe(self, program):
        if self.is_subscribed(program):
            db.session.execute(program_subscriptions.delete().where(
                program_subscriptions.c.subscriber_id == self.id,
                program_subscriptions.c.program_id == program.id))

    def is_subscribed(self, program):
        return db.session.scalars(User.select().where(
            User.id == self.id, User.program_subscriptions.contains(
                program))).one_or_none() is not None


shop_programs = sqla.Table(
    'shop_programs',
    db.Model.metadata,
    sqla.Column('program_id', sqla.Integer, sqla.ForeignKey('programs.id')),
    sqla.Column('shop_id', sqla.Integer, sqla.ForeignKey('shops.id'))
)


class Shop(Updateable, db.Model):
    __tablename__ = 'shops'

    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String(280), nullable=False)
    email = sqla.Column(sqla.String(120), index=True, unique=True,
                        nullable=False)
    unit_number = sqla.Column(sqla.String(64), nullable=False)
    street_address = sqla.Column(sqla.String(240), nullable=False)
    city = sqla.Column(sqla.String(64), nullable=False)
    province = sqla.Column(sqla.String(64), nullable=False)
    country = sqla.Column(sqla.String(64), nullable=False)
    zip_code = sqla.Column(sqla.String(32), nullable=False)
    date_registered = sqla.Column(sqla.DateTime, index=True, default=datetime.utcnow,
                            nullable=False)
    # manager_id = sqla.Column(sqla.Integer, sqla.ForeignKey(User.id), index=True)
    #
    # manager = sqla_orm.relationship('User', back_populates='shops')
    program_primary = sqla_orm.relationship('Program', back_populates='primary_shop')
    purchases = sqla_orm.relationship('Purchase', back_populates='shop')
    redemptions = sqla_orm.relationship('Redemption', back_populates='shop')

    def __repr__(self):  # pragma: no cover
        return '<Post {}>'.format(self.text)

    managers = sqla_orm.relationship(
        'User', secondary=managers,
        primaryjoin=(managers.c.user_id == id),
        secondaryjoin=(managers.c.shop_id == id),
        back_populates='shops', lazy='noload')

    staffs = sqla_orm.relationship(
        'User', secondary=staffs,
        primaryjoin=(staffs.c.shop_id == id),
        secondaryjoin=(staffs.c.staff_id == id),
        back_populates='employers', lazy='noload')

    programs = sqla_orm.relationship(
        'Program', secondary=shop_programs,
        primaryjoin=(shop_programs.c.shop_id == id),
        secondaryjoin=(shop_programs.c.program_id == id),
        back_populates='shops', lazy='noload')

    subscribers = sqla_orm.relationship(
        'User', secondary=shop_subscriptions,
        primaryjoin=(shop_subscriptions.c.shop_id == id),
        secondaryjoin=(shop_subscriptions.c.subscriber_id == id),
        back_populates='shop_subscriptions', lazy='noload')

    def subscribers_select(self):
        return Shop.select().where(sqla_orm.with_parent(self, Shop.subscribers))

    def managers_select(self):
        return Shop.select().where(sqla_orm.with_parent(self, Shop.managers))

    def staffs_select(self):
        return Shop.select().where(sqla_orm.with_parent(self, Shop.staffs))

    def programs_select(self):
        return Shop.select().where(sqla_orm.with_parent(self, Shop.programs))

    def is_manager(self, user):
        return db.session.scalars(Shop.select().where(
            Shop.id == self.id, User.managers.contains(
                user))).one_or_none() is not None

    @property
    def full_address(self):
        return f"{self.unit_number} {self.street_address}, {self.city}, {self.province}, {self.country} {self.zip_code}"

    @property
    def url(self):
        return url_for('posts.get', id=self.id)

    @property
    def avatar_url(self):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon'


class Program(Updateable, db.Model):
    __tablename__ = 'programs'

    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String(280), nullable=False)
    ratio = sqla.Column(sqla.Float, nullable=False)
    date_registered = sqla.Column(sqla.DateTime, index=True, default=datetime.utcnow,
                                  nullable=False)
    date_retired = sqla.Column(sqla.DateTime, index=True, default=datetime.utcnow,
                                  nullable=True)
    primary_shop_id = sqla.Column(sqla.Integer, sqla.ForeignKey(Shop.id), index=True)

    primary_shop = sqla_orm.relationship('Shop', back_populates='program_primary') # shop who created the program
    purchases = sqla_orm.relationship('Purchase', back_populates='program')
    redemptions = sqla_orm.relationship('Redemption', back_populates='program')

    shops = sqla_orm.relationship(
        'Shop', secondary=shop_programs,
        primaryjoin=(shop_programs.c.program_id == id),
        secondaryjoin=(shop_programs.c.shop_id == id),
        back_populates='programs', lazy='noload')

    subscribers = sqla_orm.relationship(
        'User', secondary=program_subscriptions,
        primaryjoin=(program_subscriptions.c.program_id == id),
        secondaryjoin=(program_subscriptions.c.subscriber_id == id),
        back_populates='program_subscriptions', lazy='noload')

    def __repr__(self):  # pragma: no cover
        return '<Program {}>'.format(self.text)


class Purchase(Updateable, db.Model):
    __tablename__ = 'purchases'

    id = sqla.Column(sqla.Integer, primary_key=True)
    purchase_user_id = sqla.Column(sqla.Integer, sqla.ForeignKey(User.id), index=True)
    purchase_staff_id = sqla.Column(sqla.Integer, sqla.ForeignKey(User.id), index=True)
    shop_id = sqla.Column(sqla.Integer, sqla.ForeignKey(Shop.id), index=True)
    program_id = sqla.Column(sqla.Integer, sqla.ForeignKey(Program.id), index=True)
    date_purchased = sqla.Column(sqla.DateTime, index=True, default=datetime.utcnow,
                                  nullable=False)
    cost = sqla.Column(sqla.Float, index=True, nullable=False)
    points = sqla.Column(sqla.Integer, index=True, nullable=False)
    comment = sqla.Column(sqla.String(560), nullable=True)

    purchase_user = sqla_orm.relationship('User', back_populates='purchases', foreign_keys=[purchase_user_id]) # user who purchased
    purchase_staff = sqla_orm.relationship('User', back_populates='staff_purchases', foreign_keys=[purchase_staff_id])  # user who purchased
    shop = sqla_orm.relationship('Shop', back_populates='purchases') # shop where purchased
    program = sqla_orm.relationship('Program', back_populates='purchases') # program of user who purchased

    def __repr__(self):  # pragma: no cover
        return '<Purchase {}>'.format(self.text)


class Redemption(Updateable, db.Model):
    __tablename__ = 'redemptions'

    id = sqla.Column(sqla.Integer, primary_key=True)
    redemption_user_id = sqla.Column(sqla.Integer, sqla.ForeignKey(User.id), index=True)
    redemption_staff_id = sqla.Column(sqla.Integer, sqla.ForeignKey(User.id), index=True)
    shop_id = sqla.Column(sqla.Integer, sqla.ForeignKey(Shop.id), index=True)
    program_id = sqla.Column(sqla.Integer, sqla.ForeignKey(Program.id), index=True)
    date_redeemed = sqla.Column(sqla.DateTime, index=True, default=datetime.utcnow,
                                  nullable=False)
    cost = sqla.Column(sqla.Float, index=True, nullable=False)
    points = sqla.Column(sqla.Integer, index=True, nullable=False)
    comment = sqla.Column(sqla.String(560), nullable=True)

    redemption_user = sqla_orm.relationship('User', back_populates='redemptions', foreign_keys=[redemption_user_id]) # user who redeemed
    redemption_staff = sqla_orm.relationship('User', back_populates='staff_redemptions', foreign_keys=[redemption_staff_id])  # staff who processed
    shop = sqla_orm.relationship('Shop', back_populates='redemptions') # shop where redeemed
    program = sqla_orm.relationship('Program', back_populates='redemptions') # program of user at time of redemption

    def __repr__(self):  # pragma: no cover
        return '<Redemption {}>'.format(self.text)

