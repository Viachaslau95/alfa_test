import phonenumbers
from pydantic import BaseModel, validator


class Client(BaseModel):
    phone_number: str

    @validator('phone_number')
    def validate_phone_number(cls, value):
        parsed_number = phonenumbers.parse(value, None)
        if not phonenumbers.is_valid_number(parsed_number):
            raise ValueError('Invalid phone number')
        if not phonenumbers.is_possible_number(parsed_number):
            raise ValueError('Phone number is not possible')
        if phonenumbers.number_type(parsed_number) != phonenumbers.PhoneNumberType.MOBILE:
            raise ValueError('Phone number is not a mobile number')
        return value


class Message(BaseModel):
    text: str
