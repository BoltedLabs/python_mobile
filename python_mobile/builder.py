from .builders.sms import SMSBuilder


class Builder:
    def __init__(self):
        pass

    @staticmethod
    def build_sms(to, message, part=True) -> SMSBuilder:
        sms: SMSBuilder = SMSBuilder(
            to=to,
            message=message
        )

        return sms



    
