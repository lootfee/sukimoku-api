from marshmallow import validate, validates, validates_schema, \
    ValidationError, post_dump
from api import ma, db
from api.auth import token_auth
from api.models import User, Shop, Program, Purchase, Redemption

paginated_schema_cache = {}


class EmptySchema(ma.Schema):
    pass


class DateTimePaginationSchema(ma.Schema):
    class Meta:
        ordered = True

    limit = ma.Integer()
    offset = ma.Integer()
    after = ma.DateTime(load_only=True)
    count = ma.Integer(dump_only=True)
    total = ma.Integer(dump_only=True)

    @validates_schema
    def validate_schema(self, data, **kwargs):
        if data.get('offset') is not None and data.get('after') is not None:
            raise ValidationError('Cannot specify both offset and after')


class StringPaginationSchema(ma.Schema):
    class Meta:
        ordered = True

    limit = ma.Integer()
    offset = ma.Integer()
    after = ma.String(load_only=True)
    count = ma.Integer(dump_only=True)
    total = ma.Integer(dump_only=True)

    @validates_schema
    def validate_schema(self, data, **kwargs):
        if data.get('offset') is not None and data.get('after') is not None:
            raise ValidationError('Cannot specify both offset and after')


def PaginatedCollection(schema, pagination_schema=StringPaginationSchema):
    if schema in paginated_schema_cache:
        return paginated_schema_cache[schema]

    class PaginatedSchema(ma.Schema):
        class Meta:
            ordered = True

        pagination = ma.Nested(pagination_schema)
        data = ma.Nested(schema, many=True)

    PaginatedSchema.__name__ = 'Paginated{}'.format(schema.__class__.__name__)
    paginated_schema_cache[schema] = PaginatedSchema
    return PaginatedSchema


class UserSchema(ma.SQLAlchemySchema):
    class Meta:
        model = User
        ordered = True

    id = ma.auto_field(dump_only=True)
    url = ma.String(dump_only=True)
    name = ma.auto_field(required=True,
                             validate=validate.Length(min=3, max=64))
    email = ma.auto_field(required=True, validate=[validate.Length(max=120),
                                                   validate.Email()])
    password = ma.String(required=True, load_only=True,
                         validate=validate.Length(min=8))
    avatar_url = ma.String(dump_only=True)

    first_seen = ma.auto_field(dump_only=True)
    last_seen = ma.auto_field(dump_only=True)
    # posts_url = ma.URLFor('posts.user_all', values={'id': '<id>'},
    #                       dump_only=True)

    @validates('name')
    def validate_name(self, value):
        if not value[0].isalpha():
            raise ValidationError('Name must start with a letter')
        # user = token_auth.current_user()
        # old_name = user.name if user else None
        # if value != old_name and \
        #         db.session.scalar(User.select().filter_by(name=value)):
        #     raise ValidationError('Use a different name.')

    @validates('email')
    def validate_email(self, value):
        user = token_auth.current_user()
        old_email = user.email if user else None
        if value != old_email and \
                db.session.scalar(User.select().filter_by(email=value)):
            raise ValidationError('Use a different email.')

    @post_dump
    def fix_datetimes(self, data, **kwargs):
        data['first_seen'] += 'Z'
        data['last_seen'] += 'Z'
        return data


class UpdateUserSchema(UserSchema):
    old_password = ma.String(load_only=True, validate=validate.Length(min=3))

    @validates('old_password')
    def validate_old_password(self, value):
        if not token_auth.current_user().verify_password(value):
            raise ValidationError('Password is incorrect')


class ShopSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Shop
        # include_fk = True
        ordered = True

    id = ma.auto_field(dump_only=True)
    name = ma.auto_field(required=True,
                         validate=validate.Length(min=3, max=128))
    email = ma.auto_field(required=True, validate=[validate.Length(max=120),
                                                   validate.Email()])
    unit_number = ma.auto_field(required=True,
                         validate=validate.Length(max=64))
    street_address = ma.auto_field(required=True,
                                validate=validate.Length(max=240))
    city = ma.auto_field(required=True,
                                validate=validate.Length(max=64))
    province = ma.auto_field(required=True,
                                validate=validate.Length(max=64))
    country = ma.auto_field(required=True,
                                validate=validate.Length(max=64))
    zip_code = ma.auto_field(required=True,
                                validate=validate.Length(max=32))
    # url = ma.String(dump_only=True)
    # text = ma.auto_field(required=True, validate=validate.Length(
    #     min=1, max=280))
    date_registered = ma.auto_field(dump_only=True)

    @post_dump
    def fix_datetimes(self, data, **kwargs):
        data['date_registered'] += 'Z'
        return data


class ProgramSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Program
        ordered = True

    id = ma.auto_field(dump_only=True)
    name = ma.auto_field(required=True,
                         validate=validate.Length(min=3, max=128))
    ratio = ma.auto_field(required=True)
    date_registered = ma.auto_field(dump_only=True)
    date_retired = ma.auto_field(dump_only=True)
    primary_shop = ma.Nested(ShopSchema, dump_only=True)

    @post_dump
    def fix_datetimes(self, data, **kwargs):
        data['date_registered'] += 'Z'
        data['date_retired'] += 'Z'
        return data


class PurchaseSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Purchase
        ordered = True

    id = ma.auto_field(dump_only=True)
    cost = ma.auto_field(required=True)
    points = ma.auto_field(required=True)
    date_purchased = ma.auto_field(dump_only=True)
    comment = ma.auto_field(required=False, validate=validate.Length(
        min=1, max=560))
    shop = ma.Nested(ShopSchema, dump_only=True)
    program = ma.Nested(ShopSchema, dump_only=True)
    purchase_user = ma.Nested(UserSchema, dump_only=True)
    purchase_staff = ma.Nested(UserSchema, dump_only=True)

    @post_dump
    def fix_datetimes(self, data, **kwargs):
        data['date_purchased'] += 'Z'
        return data


class RedemptionSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Redemption
        ordered = True

    id = ma.auto_field(dump_only=True)
    cost = ma.auto_field(required=True)
    points = ma.auto_field(required=True)
    date_redeemed = ma.auto_field(dump_only=True)
    comment = ma.auto_field(required=False, validate=validate.Length(
        min=1, max=560))
    shop = ma.Nested(ShopSchema, dump_only=True)
    program = ma.Nested(ShopSchema, dump_only=True)
    redemption_user = ma.Nested(UserSchema, dump_only=True)
    redemption_staff = ma.Nested(UserSchema, dump_only=True)

    @post_dump
    def fix_datetimes(self, data, **kwargs):
        data['date_redeemed'] += 'Z'
        return data


class TokenSchema(ma.Schema):
    class Meta:
        ordered = True

    access_token = ma.String(required=True)
    refresh_token = ma.String()


class PasswordResetRequestSchema(ma.Schema):
    class Meta:
        ordered = True

    email = ma.String(required=True, validate=[validate.Length(max=120),
                                               validate.Email()])


class PasswordResetSchema(ma.Schema):
    class Meta:
        ordered = True

    token = ma.String(required=True)
    new_password = ma.String(required=True, validate=validate.Length(min=3))
